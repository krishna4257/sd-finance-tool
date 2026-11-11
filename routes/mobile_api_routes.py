import os
import re
import json
import time
import uuid
import hmac
import hashlib
import traceback
import logging
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from functools import wraps

from flask import Blueprint, request, jsonify, g, current_app, Response, stream_with_context
from werkzeug.security import check_password_hash

from db import get_pg_connection
from extensions import limiter
from services.audit_service import audit_log
from services.chit_calc_engine import round_curr
from services.cashbag_engine import resolve_employee_cashbags, compute_cashbag_metrics
from security.mobile_auth import (
    mobile_auth_required,
    verify_mobile_token,
    get_active_mobile_user,
    check_user_village_access,
    verify_queue_integrity,
    register_mobile_request_integrity,
    parse_mobile_timestamp,
    generate_mobile_token,
    get_mobile_queue_hmac_secret,
    _canonical_json,
)
from services.mobile_service import (
    to_decimal,
    normalize_account_number,
    merge_edit_payload,
    normalize_mobile_customer_payload,
    normalize_mobile_payment_payload,
    ensure_feed_tables_exist,
    ensure_user_devices_table,
)

logger = logging.getLogger(__name__)

mobile_bp = Blueprint("mobile_bp", __name__)


def _resolve_func(name, default_func):
    """
    Allow backwards-compatible mock patching where tests or callers patch `app.<name>`.
    If `app.<name>` exists and was replaced (e.g. by a MagicMock), use it instead.
    """
    try:
        import sys
        app_mod = sys.modules.get("app")
        if app_mod is not None and hasattr(app_mod, name):
            val = getattr(app_mod, name)
            if val is not default_func:
                return val
    except Exception:
        pass
    return default_func


def get_resolved_pg_conn():
    get_conn = _resolve_func("get_pg_connection", get_pg_connection)
    return get_conn()



class _CSRFExemptHelper:
    @staticmethod
    def exempt(view):
        view._csrf_exempt = True
        return view

csrf = _CSRFExemptHelper()


# ROUTES - mobile app
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("5 per minute")
@mobile_bp.post("/api/mobile/login")
def mobile_login():

    data = request.json
    if not data:
        return {"error": "invalid"}, 401
    
    username = data.get("username")
    password = data.get("password")

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT u.id, u.password_hash, u.is_active, e.level
            FROM users u
            JOIN employee e ON e.eid = u.employee_id
            WHERE u.username=%s
        """,(username,))

        user = cur.fetchone()

        if not user:
            return {"error":"invalid"},401

        user_id,password_hash,is_active,level = user

        if not is_active:
            return {"error": "Account credentials locked by administrator. Login prohibited.", "action": "wipe_and_lock"}, 403

        if not check_password_hash(password_hash,password):
            return {"error":"invalid"},401
        
        cur.execute("SELECT eid FROM employee WHERE eid IN (SELECT employee_id FROM users WHERE id = %s)", (user_id,))
        result = cur.fetchone()
        if not result:
            return {"error":"employee not found"},401
        eid = result[0]

        # ---------------------------
        # Multi-Device Installation Tracking & Lock Check
        # ---------------------------
        device_id = data.get("device_id")
        device_model = data.get("device_model") or data.get("device_name") or "Mobile Device"

        if device_id and device_id != 'PENDING':
            ensure_user_devices_table(cur)
            # Check if this physical hardware is locked by administrator
            cur.execute("""
                SELECT is_locked, is_active FROM user_devices 
                WHERE user_id = %s AND device_id = %s
            """, (user_id, device_id))
            chk_lock = cur.fetchone()
            if chk_lock and chk_lock[0]: # is_locked == True
                return {
                    "error": "This device has been locked by the administrator. Login prohibited.",
                    "action": "wipe_and_lock"
                }, 403
            # If this user already has an active record for the same device_model with an older UUID,
            # retire the older record so reinstalling or clearing app data does not create duplicate entries.
            if device_model and device_model != "Mobile Device":
                cur.execute("""
                    UPDATE user_devices
                    SET is_active = FALSE
                    WHERE user_id = %s AND device_model = %s AND device_id != %s AND is_active = TRUE
                """, (user_id, device_model, device_id))

            # Record/Upsert this device for the user account (including admins)
            cur.execute("""
                INSERT INTO user_devices (user_id, device_id, device_model, is_active, is_locked, last_active, created_at)
                VALUES (%s, %s, %s, TRUE, FALSE, NOW(), NOW())
                ON CONFLICT (user_id, device_id)
                DO UPDATE SET
                    last_active = NOW(),
                    device_model = COALESCE(EXCLUDED.device_model, user_devices.device_model),
                    is_active = CASE WHEN user_devices.is_locked THEN FALSE ELSE TRUE END
            """, (user_id, device_id, device_model))

            # Deactivate any open PENDING slot since a physical device is now bound
            cur.execute("""
                UPDATE user_devices
                SET is_active = FALSE
                WHERE user_id = %s AND device_id = 'PENDING' AND is_active = TRUE
            """, (user_id,))
            conn.commit()

        if level and level.strip().lower() in ("j", "m", "s"):
            if not device_id:
                return {"error": "device_id required"}, 400

            cur.execute("""
                SELECT is_active 
                FROM user_devices 
                WHERE user_id = %s AND device_id = %s
            """, (user_id, device_id))
            dev_row = cur.fetchone()

            if dev_row and not dev_row[0]:
                return {"error": "Device disabled. Contact administrator."}, 403

        token = generate_mobile_token(user_id, eid)

        audit_log(
          action="mobile_login",
          entity_type="user",
          entity_id=user_id,
          details={
              "eid": eid,
              "username": username,
              "level": level
            }
        )

        return {
            "token":token,
            "user_id":user_id,
            "username":username,
            "eid": eid,
            "level": level
        }
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@mobile_bp.get("/api/mobile/villages")
@mobile_auth_required(verify_village=False)
def mobile_villages():
    user_id = g.mobile_user["user_id"]
    eid = g.mobile_user["eid"]
    user_level = g.mobile_user["level"]

    # Fetch employee name
    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM employee WHERE eid = %s", (eid,))
        emp_row = cur.fetchone()
        employee_name = emp_row[0] if emp_row else ""

        # 🔹 Fetch villages from user_village_access
        cur.execute("""
            SELECT v.vid, v.village_name, v.village_code, v.district, v.interest_rate, v.cutting_rate
            FROM user_village_access uva
            JOIN village v ON v.vid = uva.village_id
            WHERE uva.user_id = %s
            ORDER BY v.village_name
        """, (user_id,))

        villages = cur.fetchall()

        if not villages:
            # Fallback 1: Check if user is admin or management
            cur.execute("SELECT level FROM users WHERE id = %s", (user_id,))
            user_level_row = cur.fetchone()
            user_level = (user_level_row[0] if user_level_row else "").lower()
            if user_level in ["admin", "superadmin", "mgmt"]:
                cur.execute("""
                    SELECT vid, village_name, village_code, district, interest_rate, cutting_rate
                    FROM village
                    ORDER BY village_name
                """)
                villages = cur.fetchall()
            elif eid:
                # Fallback 2: Check employee village assignment (emp1 or emp2)
                cur.execute("""
                    SELECT vid, village_name, village_code, district, interest_rate, cutting_rate
                    FROM village
                    WHERE emp1 = %s OR emp2 = %s
                    ORDER BY village_name
                """, (eid, eid))
                villages = cur.fetchall()
                if villages:
                    try:
                        for v_row in villages:
                            cur.execute("""
                                INSERT INTO user_village_access (user_id, village_id)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, (user_id, v_row[0]))
                        conn.commit()
                    except Exception:
                        conn.rollback()

        return {
            "villages": [
                {
                    "vid": v[0],
                    "village_name": v[1],
                    "village_code": v[2] or "",
                    "district": v[3],
                    "interest_rate": float(v[4]) if v[4] is not None else 0.0,
                    "cutting_rate": float(v[5]) if v[5] is not None else 0.0,
                    "employee_name": employee_name
                }
                for v in villages
            ]
        }
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@mobile_bp.get("/api/mobile/cashbag")
@mobile_auth_required(verify_village=False)
def mobile_cashbag_get():
    eid = g.mobile_user["eid"]
    is_admin = g.mobile_user.get("role") in ["admin", "superadmin"] or g.mobile_user.get("level") in ["admin", "superadmin"]

    bank_id = request.args.get("bank_id", type=str)
    cashbag_id = request.args.get("cashbag_id", type=str)
    emp1_arg = request.args.get("emp1", type=int)
    emp2_arg = request.args.get("emp2", type=int)
    limit_val = request.args.get("limit", default=250, type=int)

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        available_cashbags = resolve_employee_cashbags(cur, eid, is_admin=is_admin)

        target_cb = None
        if bank_id:
            target_cb = next((cb for cb in available_cashbags if cb.get("bank_id") == bank_id), None)
        elif cashbag_id:
            target_cb = next((cb for cb in available_cashbags if cb.get("cashbag_id") == cashbag_id), None)
        elif emp1_arg:
            target_cb = next((cb for cb in available_cashbags if cb.get("emp1") == emp1_arg and (emp2_arg is None or cb.get("emp2") == emp2_arg)), None)

        if not target_cb and available_cashbags:
            target_cb = available_cashbags[0]

        if target_cb:
            emp1 = target_cb.get("emp1") or eid
            emp2 = target_cb.get("emp2")
            b_id = target_cb.get("bank_id") or bank_id
            c_id = target_cb.get("cashbag_id") or cashbag_id
        else:
            emp1 = emp1_arg or eid
            emp2 = emp2_arg
            b_id = bank_id
            c_id = cashbag_id

        data = compute_cashbag_metrics(cur, emp1=emp1, emp2=emp2, bank_id=b_id, cashbag_id=c_id, limit_val=limit_val)
        data["available_cashbags"] = available_cashbags
        data["selected_cashbag_id"] = target_cb["id"] if target_cb else (b_id or c_id or "default")
        return data, 200
    except Exception as e:
        logger.error(f"mobile_cashbag_get error: {e}", exc_info=True)
        return {"error": f"Failed to load cashbag data: {str(e)}"}, 500
    finally:
        cur.close()
        conn.close()

@mobile_bp.get("/api/mobile/ledger")
@mobile_auth_required(verify_village=False)
def mobile_ledger_get():
    eid = g.mobile_user["eid"]

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        return {"error": "Missing start_date or end_date"}, 400

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format"}, 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:
        cur.execute("SELECT emp1, emp2 FROM village WHERE emp1 = %s OR emp2 = %s LIMIT 1", (eid, eid))
        row = cur.fetchone()
        if row:
            emp1, emp2 = row[0], row[1]
        else:
            emp1, emp2 = eid, None

        if emp2:
            pair_filter = "emp1 = %s AND emp2 = %s"
            pair_params_single = (emp1, emp2)
        else:
            pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
            pair_params_single = (emp1,)

        if emp2:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND emp2 = %s AND status = 'active'
            """, (emp1, emp2))
        else:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
            """, (emp1,))
        
        village_rows = cur.fetchall()
        vids = [r[0] for r in village_rows]

        if not vids:
            return {
                "success": True,
                "opening_balance": 0.0,
                "dates": {},
                "dates_list": []
            }

        cur.execute(f"""
            SELECT txn, txn_sub, amount
            FROM cashbag_transactions
            WHERE {pair_filter} AND created_at::date < %s
        """, pair_params_single + (start_date,))
        hist_manual = cur.fetchall()

        office_cash_h = 0.0
        expenses_h = 0.0
        adj_add_h = 0.0
        adj_minus_h = 0.0

        for txn, txn_sub, amount in hist_manual:
            amt = float(amount or 0)
            if txn == 'OFFICE_CASH':
                office_cash_h += amt
            elif txn == 'EXPENSE':
                expenses_h += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    adj_add_h += amt
                elif txn_sub == 'MINUS':
                    adj_minus_h += amt

        cur.execute("""
            SELECT COALESCE(SUM(amt), 0)
            FROM payment p
            JOIN customer c ON p.cid = c.cid
            WHERE c.vid = ANY(%s) AND p.payment_date < %s
        """, (vids, start_date))
        installments_h = float(cur.fetchone()[0] or 0)

        cur.execute("""
            SELECT c.base_amount, c.cutting_amount, c.total_amount,
                   v.interest_rate, v.cutting_rate
            FROM customer c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted' AND c.start_date < %s
        """, (vids, start_date))
        hist_loans = cur.fetchall()

        loans_disbursed_h = 0.0
        loan_commission_h = 0.0

        for base_amt_db, cutting_amt_db, total_amt_db, ir_db, cr_db in hist_loans:
            base_amt = float(base_amt_db or 0)
            cutting_amt = float(cutting_amt_db or 0)
            total_amt = float(total_amt_db or 0)

            if base_amt <= 0.0:
                ir = float(ir_db or 0)
                cr = float(cr_db or 0)
                interest = round_curr(total_amt * (ir / 100.0))
                cutting_amt = round_curr(total_amt * (cr / 100.0))
                base_amt = round_curr(total_amt - interest - cutting_amt)

            loans_disbursed_h += base_amt
            loan_commission_h += cutting_amt

        opening_balance = (
            office_cash_h
            + installments_h
            + loan_commission_h
            + adj_add_h
            - loans_disbursed_h
            - expenses_h
            - adj_minus_h
        )

        cur.execute("""
            SELECT c.cid, c.ano, c.name, c.base_amount, c.cutting_amount, c.total_amount, c.start_date,
                   v.village_code, v.interest_rate, v.cutting_rate
            FROM customer c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted'
              AND c.start_date >= %s AND c.start_date <= %s
            ORDER BY c.start_date ASC, c.cid ASC
        """, (vids, start_date, end_date))
        loans_rows = cur.fetchall()

        cur.execute("""
            SELECT p.pid, c.ano, c.name, p.amt, p.payment_date, v.village_code
            FROM payment p
            JOIN customer c ON p.cid = c.cid
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s)
              AND p.payment_date >= %s AND p.payment_date <= %s
            ORDER BY p.payment_date ASC, p.pid ASC
        """, (vids, start_date, end_date))
        payments_rows = cur.fetchall()

        cur.execute(f"""
            SELECT id, txn, txn_sub, txn_type, amount, notes, created_at
            FROM cashbag_transactions
            WHERE {pair_filter}
              AND created_at::date >= %s AND created_at::date <= %s
            ORDER BY created_at ASC, id ASC
        """, pair_params_single + (start_date, end_date))
        manual_rows = cur.fetchall()

        dates_in_range = []
        curr = start_date
        while curr <= end_date:
            dates_in_range.append(curr)
            curr += timedelta(days=1)

        dates_data = {}
        for d in dates_in_range:
            d_str = d.strftime("%Y-%m-%d")
            dates_data[d_str] = {
                "date_label": d.strftime("%d-%m-%Y"),
                "villages": [],
                "loans": [],
                "loans_total": {"commission": 0.0, "amount": 0.0, "interest": 0.0},
                "payments": [],
                "payments_total": 0.0,
                "expenses": [],
                "expenses_total": 0.0,
                "office_cash": [],
                "office_cash_total": 0.0,
                "adjustments_add": [],
                "adjustments_total_add": 0.0,
                "adjustments_minus": [],
                "adjustments_total_minus": 0.0
            }

        for cid, ano, name, base_amt_db, cutting_amt_db, total_amt_db, start_dt, v_code, ir_db, cr_db in loans_rows:
            d_str = start_dt.strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            base_amt = float(base_amt_db or 0)
            cutting_amt = float(cutting_amt_db or 0)
            total_amt = float(total_amt_db or 0)

            ir = float(ir_db or 0)
            cr = float(cr_db or 0)
            interest = round_curr(total_amt * (ir / 100.0))
            if base_amt <= 0.0:
                cutting_amt = round_curr(total_amt * (cr / 100.0))
                base_amt = round_curr(total_amt - interest - cutting_amt)

            dates_data[d_str]["loans"].append({
                "ano": ano,
                "name": name,
                "amount": base_amt,
                "interest": interest,
                "commission": cutting_amt,
                "village_code": v_code
            })
            dates_data[d_str]["loans_total"]["amount"] += base_amt
            dates_data[d_str]["loans_total"]["interest"] += interest
            dates_data[d_str]["loans_total"]["commission"] += cutting_amt
            if v_code not in dates_data[d_str]["villages"]:
                dates_data[d_str]["villages"].append(v_code)

        for pid, ano, name, amt, payment_date, v_code in payments_rows:
            d_str = payment_date.strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            dates_data[d_str]["payments"].append({
                "ano": ano,
                "name": name,
                "amount": float(amt or 0),
                "village_code": v_code
            })
            dates_data[d_str]["payments_total"] += float(amt or 0)
            if v_code not in dates_data[d_str]["villages"]:
                dates_data[d_str]["villages"].append(v_code)

        for tid, txn, txn_sub, txn_type, amount_db, notes, created_at in manual_rows:
            d_str = created_at.date().strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            amt = float(amount_db or 0)
            if txn == 'OFFICE_CASH':
                dates_data[d_str]["office_cash"].append({
                    "notes": notes or "Office Cash",
                    "amount": amt,
                    "txn_type": txn_type
                })
                dates_data[d_str]["office_cash_total"] += amt
            elif txn == 'EXPENSE':
                dates_data[d_str]["expenses"].append({
                    "notes": notes or "Expense",
                    "amount": amt,
                    "txn_type": txn_type
                })
                dates_data[d_str]["expenses_total"] += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    dates_data[d_str]["adjustments_add"].append({
                        "notes": notes or "Adjustment Add",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_add"] += amt
                elif txn_sub == 'MINUS':
                    dates_data[d_str]["adjustments_minus"].append({
                        "notes": notes or "Adjustment Minus",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_minus"] += amt

        dates_list = [d.strftime("%Y-%m-%d") for d in dates_in_range]

        return {
            "success": True,
            "opening_balance": opening_balance,
            "dates": dates_data,
            "dates_list": dates_list
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}, 500
    finally:
        cur.close()
        conn.close()


@csrf.exempt
@mobile_bp.post("/api/mobile/cashbag/add")
@mobile_auth_required(verify_village=False)
def mobile_cashbag_add():
    eid = g.mobile_user["eid"]

    body = request.json or {}
    txn = body.get("txn", "").strip().upper()
    txn_sub = body.get("txn_sub", "").strip().upper()
    txn_type = body.get("txn_type", "CASH").strip().upper()
    amount_raw = body.get("amount")
    notes = body.get("notes", "").strip()

    allowed_txn = ["OFFICE_CASH", "EXPENSE", "ADJUSTMENT"]
    if txn not in allowed_txn:
        return {"error": f"Invalid transaction category: {txn}"}, 400

    if txn == "OFFICE_CASH":
        txn_sub = ""

    allowed_txn_type = ["CASH", "UPI"]
    if txn_type not in allowed_txn_type:
        txn_type = "CASH"

    try:
        amount = float(amount_raw or 0)
        if amount <= 0:
            return {"error": "Amount must be greater than zero"}, 400
    except Exception:
        return {"error": "Invalid amount format"}, 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        # Get username
        cur.execute("SELECT username FROM users WHERE employee_id = %s LIMIT 1", (eid,))
        user_row = cur.fetchone()
        username = user_row[0] if user_row else f"Employee {eid}"

        # Resolve emp1, emp2, and group_id
        bank_id = body.get("bank_id") or body.get("group_id")
        emp1 = body.get("emp1")
        emp2 = body.get("emp2")

        if not emp1:
            if bank_id:
                cur.execute("SELECT emp1_id, emp2_id FROM village_groups WHERE id = %s", (bank_id,))
                brow = cur.fetchone()
                if brow:
                    emp1, emp2 = brow[0], brow[1]
            if not emp1:
                cur.execute("SELECT emp1, emp2 FROM village WHERE emp1 = %s OR emp2 = %s LIMIT 1", (eid, eid))
                row = cur.fetchone()
                if row:
                    emp1, emp2 = row[0], row[1]
                else:
                    emp1, emp2 = eid, None

        cur.execute("""
            INSERT INTO cashbag_transactions (
                emp1,
                emp2,
                eid,
                txn,
                txn_sub,
                txn_type,
                amount,
                notes,
                created_by,
                group_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            emp1,
            emp2,
            eid,
            txn,
            txn_sub or None,
            txn_type,
            amount,
            notes or None,
            username,
            bank_id or None
        ))

        conn.commit()

        audit_log(
            action="mobile_cashbag_transaction_added",
            entity_type="cashbag_transaction",
            entity_id=emp1,
            details={
                "emp1":     emp1,
                "emp2":     emp2,
                "txn":      txn,
                "txn_sub":  txn_sub,
                "txn_type": txn_type,
                "amount":   amount,
                "notes":    notes
            }
        )

        return {"success": True, "message": "Cashbag entry added successfully"}
    except Exception as e:
        return {"error": f"Failed to add cashbag entry: {str(e)}"}, 500
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@mobile_bp.get("/api/mobile/customers")
@mobile_auth_required(verify_village=True)
def mobile_customers():
    vid = request.args.get("vid")
    if not vid:
        return {"error": "vid parameter required"}, 400

    updated_after_raw = request.args.get("updated_after")
    updated_after = parse_mobile_timestamp(updated_after_raw)

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("SET TIME ZONE 'UTC'")

        if updated_after:
            cur.execute("""
                SELECT *
                FROM customer
                WHERE vid = %s
                  AND (
                    created_at > %s
                    OR COALESCE(updated_at, created_at) > %s
                  )
            """, (vid, updated_after, updated_after))
        else:
            cur.execute("""
                SELECT *
                FROM customer
                WHERE vid = %s
            """, (vid,))

        columns = [desc[0] for desc in cur.description] if cur.description else []

        rows = cur.fetchall()

        customers = []

        for r in rows:
            customers.append(dict(zip(columns, r)))

        return {"customers": customers}
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@mobile_bp.get("/api/mobile/payments")
@mobile_auth_required(verify_village=True)
def mobile_payments():
    vid = request.args.get("vid")
    if not vid:
        return {"error": "vid parameter required"}, 400

    updated_after_raw = request.args.get("updated_after")
    updated_after = parse_mobile_timestamp(updated_after_raw)

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("SET TIME ZONE 'UTC'")

        if updated_after:
            cur.execute("""
                SELECT 
                    p.pid, p.cid, p.ano, p.amt, p.payment_date, p.vid, p.eid, p.created_at, p.updated_at,
                    COALESCE(p.payment_type, 'cash') AS payment_type,
                    COALESCE(p.cash_amount, p.amt) AS cash_amount,
                    COALESCE(p.upi_amount, 0) AS upi_amount
                FROM payment p
                WHERE p.vid = %s
                  AND (
                    p.created_at > %s
                    OR p.updated_at > %s
                  )

                UNION ALL

                SELECT 
                    cp.pid, cp.cid, cp.ano, cp.amt, cp.payment_date, cp.vid, cp.eid, cp.created_at, cp.created_at AS updated_at,
                    'cash' AS payment_type,
                    cp.amt AS cash_amount,
                    0.0 AS upi_amount
                FROM closed_cust_payment cp
                LEFT JOIN closed_cust_account cca ON cp.cid = cca.cid
                WHERE cp.vid = %s
                  AND (
                    cp.created_at > %s
                    OR (cca.closed_at IS NOT NULL AND cca.closed_at > %s)
                  )
            """, (vid, updated_after, updated_after, vid, updated_after, updated_after))
        else:
            cur.execute("""
                SELECT 
                    p.pid, p.cid, p.ano, p.amt, p.payment_date, p.vid, p.eid, p.created_at, p.updated_at,
                    COALESCE(p.payment_type, 'cash') AS payment_type,
                    COALESCE(p.cash_amount, p.amt) AS cash_amount,
                    COALESCE(p.upi_amount, 0) AS upi_amount
                FROM payment p
                WHERE p.vid = %s

                UNION ALL

                SELECT 
                    cp.pid, cp.cid, cp.ano, cp.amt, cp.payment_date, cp.vid, cp.eid, cp.created_at, cp.created_at AS updated_at,
                    'cash' AS payment_type,
                    cp.amt AS cash_amount,
                    0.0 AS upi_amount
                FROM closed_cust_payment cp
                WHERE cp.vid = %s
            """, (vid, vid))

        columns = [desc[0] for desc in cur.description] if cur.description else []

        rows = cur.fetchall()

        payments = []

        for r in rows:
            payments.append(dict(zip(columns, r)))

        return {"payments": payments}
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@mobile_bp.get("/api/mobile/closed_customers")
@mobile_auth_required(verify_village=True)
def mobile_closed_customers():
    vid = request.args.get("vid")
    if not vid:
        return {"error": "vid parameter required"}, 400

    updated_after_raw = request.args.get("updated_after")
    updated_after = parse_mobile_timestamp(updated_after_raw)

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("SET TIME ZONE 'UTC'")

        if updated_after:
            cur.execute("""
                SELECT
                    cid,
                    ano,
                    name,
                    vid,
                    status,
                    balance_amount,
                    closed_at,
                    closed_at AS updated_at
                FROM closed_cust_account
                WHERE vid = %s
                  AND closed_at > %s
            """, (vid, updated_after))
        else:
            cur.execute("""
                SELECT
                    cid,
                    ano,
                    name,
                    vid,
                    status,
                    balance_amount,
                    closed_at,
                    closed_at AS updated_at
                FROM closed_cust_account
                WHERE vid = %s
            """, (vid,))

        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        customers = [dict(zip(columns, r)) for r in rows]

        return {"customers": customers}
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@limiter.limit("200 per minute")
@mobile_bp.route("/api/mobile/customer_feed", methods=["POST"])
@mobile_auth_required(verify_village=False)
def customer_feed():
    conn = None
    cur = None
    try:
        data_token = g.mobile_token_data

        payload_json = request.form.get("payload")
        if not payload_json:
            return jsonify({"error": "missing payload"}), 400

        try:
            data = json.loads(payload_json)  # queue envelope from mobile
        except Exception:
            return jsonify({"error": "invalid payload json"}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "invalid envelope"}), 400

        required_fields = [
            "type",
            "eid",
            "vid",
            "nonce",
            "timestamp",
            "idempotency_key",
            "payload",
            "signature",
        ]
        missing = [field for field in required_fields if data.get(field) in (None, "")]
        if missing:
            return jsonify({
                "error": f"missing integrity fields: {', '.join(missing)}"
            }), 400

        try:
            # use defaults to satisfy type checkers; presence/emptiness validated above
            envelope_eid = int(data.get("eid", 0))
            envelope_vid = int(data.get("vid", 0))
            token_eid = int(data_token.get("eid", 0))
        except Exception:
            return jsonify({"error": "invalid identity fields"}), 400

        if envelope_eid != token_eid or envelope_eid != g.mobile_user["eid"]:
            return jsonify({"error": "eid mismatch with session token"}), 403

        if not check_user_village_access(g.mobile_user["user_id"], g.mobile_user["eid"], g.mobile_user["level"], envelope_vid):
            return jsonify({"error": f"Access denied: Village {envelope_vid} not assigned to this account"}), 403

        # Verify nested payload matches envelope
        inner_payload = data.get("payload")
        if isinstance(inner_payload, str):
            try:
                inner_payload = json.loads(inner_payload)
            except Exception:
                inner_payload = {}
        if isinstance(inner_payload, dict):
            p_vid = inner_payload.get("vid")
            if p_vid is not None and int(p_vid) != envelope_vid:
                return jsonify({"error": "inner customer payload vid does not match envelope vid"}), 400
            p_eid = inner_payload.get("eid")
            if p_eid is not None and int(p_eid) != envelope_eid:
                return jsonify({"error": "inner customer payload eid does not match envelope eid"}), 403

        parsed_ts = parse_mobile_timestamp(data.get("timestamp"))
        if parsed_ts is None:
            return jsonify({"error": "invalid timestamp"}), 400

        age_seconds = abs((datetime.now(timezone.utc) - parsed_ts).total_seconds())
        if age_seconds > 900:
            return jsonify({"error": "stale timestamp"}), 400

        signing_secret = get_mobile_queue_hmac_secret()

        signed_payload = {
            "type": data.get("type"),
            "eid": envelope_eid,
            "vid": envelope_vid,
            "nonce": data.get("nonce"),
            "timestamp": data.get("timestamp"),
            "idempotency_key": data.get("idempotency_key"),
            "payload": data.get("payload"),
        }

        expected_signature = hmac.new(
            signing_secret.encode("utf-8"),
            _canonical_json(signed_payload).encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        provided_signature = str(data.get("signature") or "")
        if not hmac.compare_digest(provided_signature, expected_signature):
            audit_log(
                action="mobile_customer_upload_rejected",
                entity_type="customer_feed",
                entity_id=data.get("local_uuid"),
                details={
                    "reason": "invalid signature",
                    "eid": data.get("eid"),
                    "vid": data.get("vid"),
                    "nonce": data.get("nonce"),
                    "idempotency_key": data.get("idempotency_key"),
                },
                status="failed"
            )
            return jsonify({"error": "invalid signature"}), 400

        conn = get_resolved_pg_conn()
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC'")

        # Optional replay protection if you create a dedicated table:
        # cur.execute(
        #     "SELECT 1 FROM mobile_request_integrity WHERE idempotency_key = %s OR nonce = %s LIMIT 1",
        #     (data.get("idempotency_key"), data.get("nonce"))
        # )
        # if cur.fetchone():
        #     return jsonify({"error": "duplicate request"}), 409

        local_uuid = data.get("local_uuid")
        device_id = data.get("device_id", "mobile")
        eid = envelope_eid
        vid = envelope_vid
        status = data.get("status", "pending")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        gps_accuracy = data.get("gps_accuracy")

        ok, reason = register_mobile_request_integrity(
            cur,
            endpoint="/api/mobile/customer_feed",
            eid=eid,
            vid=vid,
            local_uuid=local_uuid,
            idempotency_key=data.get("idempotency_key"),
            nonce=data.get("nonce"),
            request_signature=provided_signature,
            request_timestamp=parsed_ts,
        )
        if not ok:
            conn.rollback()
            audit_log(
                action="mobile_customer_upload_rejected",
                entity_type="customer_feed",
                entity_id=local_uuid,
                details={
                    "reason": reason,
                    "eid": eid,
                    "vid": vid,
                    "nonce": data.get("nonce"),
                    "idempotency_key": data.get("idempotency_key"),
                },
                status="failed"
            )
            return jsonify({"error": reason}), 409

        customer_payload = data.get("payload")

        if isinstance(customer_payload, str):
            customer_payload = json.loads(customer_payload)

        if not isinstance(customer_payload, dict):
            return jsonify({"error": "invalid customer payload"}), 400

        try:
            customer_payload = normalize_mobile_customer_payload(customer_payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        ano = customer_payload.get("ano") # type: ignore
        payload = json.dumps(customer_payload, default=str)

        logger.debug(
            "Customer feed received for vid=%s ano=%s nonce=%s idempotency_key=%s",
            vid,
            ano,
            data.get("nonce"),
            data.get("idempotency_key"),
        )

        cur.execute("""
            INSERT INTO customer_feed
            (
                local_uuid,
                device_id,
                eid,
                vid,
                status,
                payload,
                latitude,
                longitude,
                gps_accuracy
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (local_uuid) DO NOTHING
        """, (
            local_uuid,
            device_id,
            eid,
            vid,
            status,
            payload,
            latitude,
            longitude,
            gps_accuracy
        ))

        # 2️⃣ Read images
        aadhaar_front_file = request.files.get("aadhaar_front_pic")
        aadhaar_back_file = request.files.get("aadhaar_back_pic")
        house_file = request.files.get("house_photo")

        aadhaar_front_bytes = aadhaar_front_file.read() if aadhaar_front_file else None
        aadhaar_back_bytes = aadhaar_back_file.read() if aadhaar_back_file else None
        house_bytes = house_file.read() if house_file else None

        # 3️⃣ Insert into customer_docs
        if aadhaar_front_bytes or aadhaar_back_bytes or house_bytes:
            cur.execute("""
                INSERT INTO customer_docs (vid, ano, aadhaar_front_pic, aadhaar_back_pic, house_photo)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (vid, ano)
                DO UPDATE SET
                    aadhaar_front_pic = COALESCE(EXCLUDED.aadhaar_front_pic, customer_docs.aadhaar_front_pic),
                    aadhaar_back_pic = COALESCE(EXCLUDED.aadhaar_back_pic, customer_docs.aadhaar_back_pic),
                    house_photo = COALESCE(EXCLUDED.house_photo, customer_docs.house_photo)
            """, (
                vid,
                ano,
                aadhaar_front_bytes,
                aadhaar_back_bytes,
                house_bytes
            ))

        # Optional replay ledger insert if you create the table:
        # cur.execute("""
        #     INSERT INTO mobile_request_integrity
        #     (idempotency_key, nonce, eid, vid, endpoint, local_uuid, created_at)
        #     VALUES (%s, %s, %s, %s, %s, %s, NOW())
        # """, (
        #     data.get("idempotency_key"),
        #     data.get("nonce"),
        #     eid,
        #     vid,
        #     "/api/mobile/customer_feed",
        #     local_uuid,
        # ))

        conn.commit()
        audit_log(
            action="mobile_customer_upload",
            entity_type="customer_feed",
            entity_id=local_uuid,
            details={
                "eid": eid,
                "vid": vid,
                "ano": ano,
                "device_id": device_id,
                "status": status,
                "nonce": data.get("nonce"),
                "idempotency_key": data.get("idempotency_key"),
            }
        )

        return jsonify({"status": "ok"})

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("Customer feed processing failed")
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


# ----------------------------------------------------
# /api/mobile/close_account_feed
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("200 per minute")
@mobile_bp.route("/api/mobile/close_account_feed", methods=["POST"])
@mobile_bp.route("/close_account_feed", methods=["POST"])
@mobile_auth_required(verify_village=False)
def close_account_feed():
    conn = None
    cur = None
    try:
        data_token = g.mobile_token_data

        payload_json = request.form.get("payload")
        if not payload_json:
            return jsonify({"error": "missing payload"}), 400

        try:
            data = json.loads(payload_json)  # queue envelope from mobile
        except Exception:
            return jsonify({"error": "invalid payload json"}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "invalid envelope"}), 400

        required_fields = [
            "type",
            "eid",
            "vid",
            "nonce",
            "timestamp",
            "idempotency_key",
            "payload",
            "signature",
        ]
        missing = [field for field in required_fields if data.get(field) in (None, "")]
        if missing:
            return jsonify({
                "error": f"missing integrity fields: {', '.join(missing)}"
            }), 400

        try:
            envelope_eid = int(data.get("eid", 0))
            envelope_vid = int(data.get("vid", 0))
            token_eid = int(data_token.get("eid", 0))
        except Exception:
            return jsonify({"error": "invalid identity fields"}), 400

        if envelope_eid != token_eid or envelope_eid != g.mobile_user["eid"]:
            return jsonify({"error": "eid mismatch with session token"}), 403

        if not check_user_village_access(g.mobile_user["user_id"], g.mobile_user["eid"], g.mobile_user["level"], envelope_vid):
            return jsonify({"error": f"Access denied: Village {envelope_vid} not assigned to this account"}), 403

        parsed_ts = parse_mobile_timestamp(data.get("timestamp"))
        if parsed_ts is None:
            return jsonify({"error": "invalid timestamp"}), 400

        age_seconds = abs((datetime.now(timezone.utc) - parsed_ts).total_seconds())
        if age_seconds > 900:
            return jsonify({"error": "stale timestamp"}), 400

        signing_secret = get_mobile_queue_hmac_secret()

        signed_payload = {
            "type": data.get("type"),
            "eid": envelope_eid,
            "vid": envelope_vid,
            "nonce": data.get("nonce"),
            "timestamp": data.get("timestamp"),
            "idempotency_key": data.get("idempotency_key"),
            "payload": data.get("payload"),
        }

        expected_signature = hmac.new(
            signing_secret.encode("utf-8"),
            _canonical_json(signed_payload).encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        provided_signature = str(data.get("signature") or "")
        if not hmac.compare_digest(provided_signature, expected_signature):
            return jsonify({"error": "invalid signature"}), 400

        conn = get_resolved_pg_conn()
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC'")

        local_uuid = data.get("local_uuid")
        device_id = data.get("device_id", "mobile")
        eid = envelope_eid
        vid = envelope_vid

        ok, reason = register_mobile_request_integrity(
            cur,
            endpoint="/api/mobile/close_account_feed",
            eid=eid,
            vid=vid,
            local_uuid=local_uuid,
            idempotency_key=data.get("idempotency_key"),
            nonce=data.get("nonce"),
            request_signature=provided_signature,
            request_timestamp=parsed_ts,
        )
        if not ok:
            conn.rollback()
            return jsonify({"error": reason}), 409

        closure_payload = data.get("payload")
        if isinstance(closure_payload, str):
            closure_payload = json.loads(closure_payload)

        ano = int(closure_payload.get("ano", 0)) # type: ignore

        cur.execute("""
            INSERT INTO account_closure_feed
            (
                local_uuid,
                device_id,
                eid,
                vid,
                ano,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (local_uuid) DO NOTHING
        """, (local_uuid, device_id, eid, vid, ano, 'pending'))

        conn.commit()
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Account closure feed processing failed")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ----------------------------------------------------
# REAL-TIME SUBMISSION STATUS & STREAMING API
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("300 per minute")
@mobile_bp.route("/api/mobile/submissions/status", methods=["GET"])
@mobile_auth_required(verify_village=True)
def get_submission_statuses():
    vid = request.args.get("vid", type=int)
    if not vid:
        return jsonify({"error": "vid required"}), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        ensure_feed_tables_exist(cur)
        statuses = []

        # 1. Customer feed items for vid
        cur.execute("""
            SELECT cf.local_uuid, cf.status, cf.payload, cfe.edit_status, cfe.edited_payload
            FROM customer_feed cf
            LEFT JOIN customer_feed_edits cfe ON cfe.local_uuid = cf.local_uuid
            WHERE cf.vid = %s AND cf.local_uuid IS NOT NULL
        """, (vid,))
        for lu, st, pl, est, epl in cur.fetchall():
            effective_status = st
            if st == 'pending' and est == 'pending':
                effective_status = 'rejected_edit'
            statuses.append({
                "local_uuid": lu,
                "feed_type": "customer",
                "status": effective_status,
                "edited_payload": epl if effective_status == 'rejected_edit' else None
            })

        # 2. Payment feed items for vid
        cur.execute("""
            SELECT pfi.local_uuid, pfi.status, pfi.payload, pfe.edit_status, pfe.edited_payload
            FROM payment_feed_items pfi
            LEFT JOIN payment_feed_edits pfe ON pfe.local_uuid = pfi.local_uuid
            WHERE (pfi.payload->>'vid')::int = %s AND pfi.local_uuid IS NOT NULL
        """, (vid,))
        for lu, st, pl, est, epl in cur.fetchall():
            effective_status = st
            if st == 'pending' and est == 'pending':
                effective_status = 'rejected_edit'
            statuses.append({
                "local_uuid": lu,
                "feed_type": "payment",
                "status": effective_status,
                "edited_payload": epl if effective_status == 'rejected_edit' else None
            })

        # 3. Account closure feed items for vid
        cur.execute("""
            SELECT local_uuid, status
            FROM account_closure_feed
            WHERE vid = %s AND local_uuid IS NOT NULL
        """, (vid,))
        for lu, st in cur.fetchall():
            statuses.append({
                "local_uuid": lu,
                "feed_type": "closure",
                "status": st
            })

        # 4. Feed rejections for vid
        cur.execute("""
            SELECT local_uuid, feed_type, action_type, reason
            FROM feed_rejections
            WHERE vid = %s AND local_uuid IS NOT NULL
        """, (vid,))
        for lu, ft, at, rsn in cur.fetchall():
            statuses.append({
                "local_uuid": lu,
                "feed_type": ft,
                "status": at or "rejected_deleted",
                "reason": rsn
            })

        return jsonify({"success": True, "statuses": statuses}), 200
    except Exception as e:
        logger.error(f"Error fetching submission statuses: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@csrf.exempt
@mobile_bp.route("/api/mobile/submissions/stream", methods=["GET"])
def submission_events_stream():
    token = request.headers.get("X-Mobile-Token") or request.args.get("token")
    if not token or not verify_mobile_token(token):
        return jsonify({"error": "unauthorized"}), 401

    vid = request.args.get("vid", type=int)
    if not vid:
        return jsonify({"error": "vid required"}), 400

    # Deprecated endpoint: Return immediately so legacy clients do not pin Gunicorn threads.
    # Real-time status updates are authoritatively served via /api/mobile/submissions/status.
    def stream():
        yield ": stream_deprecated\n\n"
        yield f"data: {json.dumps({'type': 'stream_deprecated', 'message': 'Please poll /api/mobile/submissions/status'})}\n\n"

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "close",
            "X-Accel-Buffering": "no"
        }
    )


# ----------------------------------------------------
# /api/mobile/customer_docs_update
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("300 per minute")
@mobile_bp.route("/api/mobile/customer_docs_update", methods=["POST"])
@mobile_auth_required(verify_village=False)
def customer_docs_update():
    conn = None
    cur = None
    try:
        local_uuid = (request.form.get("local_uuid") or "").strip()
        device_id = (request.form.get("device_id") or "mobile").strip()

        cid = normalize_account_number(request.form.get("cid"))
        ano = normalize_account_number(request.form.get("ano"))
        vid = normalize_account_number(request.form.get("vid"))
        eid = normalize_account_number(request.form.get("eid"))

        if not ano or not vid or not eid:
            return jsonify({"error": "ano, vid and eid are required"}), 400

        if int(eid) != g.mobile_user["eid"]:
            return jsonify({"error": "eid mismatch with session token"}), 403

        if not check_user_village_access(g.mobile_user["user_id"], g.mobile_user["eid"], g.mobile_user["level"], vid):
            return jsonify({"error": f"Access denied: Village {vid} not assigned to this account"}), 403

        aadhaar_front_file = request.files.get("aadhaar_front_pic")
        aadhaar_back_file = request.files.get("aadhaar_back_pic")
        house_file = request.files.get("house_photo")
        logger.info(
            "customer_docs_update request: local_uuid=%s vid=%s ano=%s eid=%s has_aadhaar_front=%s has_aadhaar_back=%s has_house=%s",
            local_uuid,
            vid,
            ano,
            eid,
            bool(aadhaar_front_file),
            bool(aadhaar_back_file),
            bool(house_file),
        )

        aadhaar_front_bytes = aadhaar_front_file.read() if aadhaar_front_file else None
        aadhaar_back_bytes = aadhaar_back_file.read() if aadhaar_back_file else None
        house_bytes = house_file.read() if house_file else None

        if not aadhaar_front_bytes and not aadhaar_back_bytes and not house_bytes:
            logger.warning(
                "customer_docs_update no documents provided: local_uuid=%s vid=%s ano=%s",
                local_uuid,
                vid,
                ano,
            )
            return jsonify({"error": "no documents provided"}), 400

        if not local_uuid:
            local_uuid = str(uuid.uuid4())

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT cid
            FROM customer
            WHERE vid = %s AND ano = %s
            LIMIT 1
        """, (vid, ano))
        customer_row = cur.fetchone()

        resolved_cid = None
        if customer_row:
            logger.info(
                "customer_docs_update matched existing customer: local_uuid=%s vid=%s ano=%s cid=%s",
                local_uuid,
                vid,
                ano,
                customer_row[0],
            )
            resolved_cid = cid or customer_row[0]
        else:
            # Allow docs while collecting payment for customers still pending
            # in customer_feed (added on mobile, not yet accepted), or when a
            # matching payment is already in the payment feed queue.
            cur.execute("""
                SELECT feed_id
                FROM customer_feed
                WHERE vid = %s
                  AND status = 'pending'
                  AND COALESCE(
                      (payload->'payload'->>'ano')::bigint,
                      (payload->>'ano')::bigint
                  ) = %s
                ORDER BY feed_id DESC
                LIMIT 1
            """, (vid, ano))
            feed_row = cur.fetchone()

            if feed_row:
                logger.info(
                    "customer_docs_update matched pending customer_feed: local_uuid=%s vid=%s ano=%s feed_id=%s",
                    local_uuid,
                    vid,
                    ano,
                    feed_row[0],
                )
            else:
                logger.warning(
                    "customer_docs_update no customer/customer_feed match yet: local_uuid=%s vid=%s ano=%s",
                    local_uuid,
                    vid,
                    ano,
                )
                cur.execute("""
                    SELECT 1
                    FROM payment_feed_items
                    WHERE status = 'pending'
                      AND (payload->>'ano')::bigint = %s
                      AND (payload->>'vid')::bigint = %s
                    LIMIT 1
                """, (ano, vid))
                payment_row = cur.fetchone()
                if payment_row:
                    logger.info(
                        "customer_docs_update matched pending payment_feed_items: local_uuid=%s vid=%s ano=%s",
                        local_uuid,
                        vid,
                        ano,
                    )
                else:
                    logger.warning(
                        "customer_docs_update customer not found: local_uuid=%s vid=%s ano=%s",
                        local_uuid,
                        vid,
                        ano,
                    )
                    return jsonify({"error": "customer not found"}), 404

            resolved_cid = cid or None

        cur.execute("""
            INSERT INTO customer_docs_feed (
                local_uuid,
                device_id,
                eid,
                vid,
                ano,
                cid,
                aadhaar_front_pic,
                aadhaar_back_pic,
                house_photo,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
            ON CONFLICT (local_uuid) DO UPDATE SET
                device_id = EXCLUDED.device_id,
                eid = EXCLUDED.eid,
                vid = EXCLUDED.vid,
                ano = EXCLUDED.ano,
                cid = EXCLUDED.cid,
                aadhaar_front_pic = COALESCE(EXCLUDED.aadhaar_front_pic, customer_docs_feed.aadhaar_front_pic),
                aadhaar_back_pic = COALESCE(EXCLUDED.aadhaar_back_pic, customer_docs_feed.aadhaar_back_pic),
                house_photo = COALESCE(EXCLUDED.house_photo, customer_docs_feed.house_photo),
                status = 'pending',
                reviewed_by = NULL,
                reviewed_at = NULL
            WHERE customer_docs_feed.status = 'pending'
        """, (
            local_uuid,
            device_id,
            eid,
            vid,
            ano,
            resolved_cid,
            aadhaar_front_bytes,
            aadhaar_back_bytes,
            house_bytes
        ))

        conn.commit()

        audit_log(
            action="mobile_customer_docs_update",
            entity_type="customer_docs_feed",
            entity_id=resolved_cid,
            details={
                "cid": resolved_cid,
                "ano": ano,
                "eid": eid,
                "vid": vid,
                "device_id": device_id,
                "local_uuid": local_uuid,
                "aadhaar_uploaded": (aadhaar_front_bytes is not None or aadhaar_back_bytes is not None),
                "house_uploaded": house_bytes is not None
            }
        )

        return jsonify({
            "status": "ok",
            "cid": resolved_cid,
            "ano": ano,
            "vid": vid,
            "local_uuid": local_uuid
        })

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("Existing customer docs update failed")
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


# ----------------------------------------------------
# /api/mobile/payment_feed_batch
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("300 per minute")
@mobile_bp.route("/api/mobile/payment_feed_batch", methods=["POST"])
@mobile_auth_required(verify_village=True)
def payment_feed_batch():
    conn = None
    cur = None
    try:
        data = request.json # type: ignore
        if not data:
            return jsonify({"error": "missing body"}), 400

        payments = data.get("payments", []) # type: ignore
        vid = data.get("vid") # type: ignore
        eid = data.get("eid") # type: ignore
        device_id = data.get("device_id", "mobile") # type: ignore

        if not payments:
            return jsonify({"error": "no payments provided"}), 400

        if eid is not None and int(eid) != g.mobile_user["eid"]:
            return jsonify({"error": "eid mismatch with session token"}), 403

        if vid is not None and not check_user_village_access(g.mobile_user["user_id"], g.mobile_user["eid"], g.mobile_user["level"], vid):
            return jsonify({"error": f"Access denied: Village {vid} not assigned to this account"}), 403

        normalized_payments = []
        for p in payments:
            try:
                normalized = normalize_mobile_payment_payload(p)
                if p.get("local_uuid"):
                    normalized["local_uuid"] = p.get("local_uuid")

                p_vid = normalized.get("vid")
                if p_vid and vid and str(p_vid) != str(vid):
                    return jsonify({"error": "batch contains payment for different village"}), 400

                p_eid = normalized.get("eid")
                if p_eid and int(p_eid) != g.mobile_user["eid"]:
                    return jsonify({"error": "batch contains payment for different employee"}), 403

                normalized_payments.append(normalized)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        total_records = len(normalized_payments)

        # insert each payment as JSON payload
        for p in normalized_payments:
            p_ano = p.get("ano")
            p_vid = p.get("vid")
            p_date = p.get("payment_date")
            local_uuid = p.get("local_uuid")
            payload = json.dumps(p, default=str)

            # Prevent duplicate payment for the same ANO, VID, and payment_date
            if p_ano is not None and p_vid is not None and p_date:
                # 1. Check if already in accepted payment table
                cur.execute("""
                    SELECT 1 FROM payment 
                    WHERE vid = %s AND ano = %s AND payment_date = %s
                    LIMIT 1
                """, (p_vid, p_ano, p_date))
                if cur.fetchone():
                    logger.warning("Skipping duplicate payment feed item (already in payment table): ano=%s, vid=%s, date=%s", p_ano, p_vid, p_date)
                    continue

                # 2. Check if already pending in payment_feed_items
                cur.execute("""
                    SELECT 1 FROM payment_feed_items
                    WHERE (payload->>'vid')::int = %s 
                      AND (payload->>'ano')::int = %s 
                      AND (payload->>'payment_date') = %s
                      AND status IN ('pending', 'approved', 'synced')
                      AND (local_uuid != %s OR local_uuid IS NULL)
                    LIMIT 1
                """, (p_vid, p_ano, str(p_date), local_uuid or ''))
                if cur.fetchone():
                    logger.warning("Skipping duplicate payment feed item (already pending in feed): ano=%s, vid=%s, date=%s", p_ano, p_vid, p_date)
                    continue

            cur.execute("""
                INSERT INTO payment_feed_items (
                    local_uuid,
                    payload,
                    status,
                    created_at
                )
                VALUES (%s,%s,'pending',NOW())
                ON CONFLICT (local_uuid) DO NOTHING
            """, (
                local_uuid,
                payload
            ))

        conn.commit()
        audit_log(
            action="mobile_payment_upload",
            entity_type="payment_feed",
            entity_id=vid,
            details={
                "eid": eid,
                "vid": vid,
                "device_id": device_id,
                "payments_received": total_records
            }
        )

        return jsonify({
            "status": "ok",
            "payments_received": total_records
        })

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("Payment feed batch processing failed")
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()

# ----------------------------------------------------
# /api/mobile/customer_feed_edit
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("60 per minute")
@mobile_bp.route("/api/mobile/customer_feed_edit", methods=["POST"])
@mobile_auth_required(verify_village=True)
def customer_feed_edit():
    """Receive an edit request for a pending customer feed item from mobile.
    Stores the edited payload alongside the original in customer_feed_edits table.
    The /feed page shows original (strikethrough) + edited data.
    """
    conn = None
    cur = None
    try:
        data = request.json
        if not data:
            return jsonify({"error": "missing body"}), 400

        local_uuid = (data.get("local_uuid") or "").strip()
        edited_payload = data.get("edited_payload")
        eid = data.get("eid")
        vid = data.get("vid")

        if eid is not None and int(eid) != g.mobile_user["eid"]:
            return jsonify({"error": "eid mismatch with session token"}), 403

        if vid is not None and not check_user_village_access(g.mobile_user["user_id"], g.mobile_user["eid"], g.mobile_user["level"], vid):
            return jsonify({"error": f"Access denied: Village {vid} not assigned to this account"}), 403

        if not local_uuid:
            return jsonify({"error": "missing local_uuid"}), 400
        if not edited_payload or not isinstance(edited_payload, dict):
            return jsonify({"error": "missing or invalid edited_payload"}), 400

        data_token = getattr(g, "mobile_token_data", {}) or {}
        token_eid = int(data_token.get("eid", 0))
        req_eid = int(eid or 0)
        if req_eid and req_eid != token_eid:
            return jsonify({"error": "eid mismatch"}), 403

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_feed_edits (
                edit_id SERIAL PRIMARY KEY,
                local_uuid TEXT NOT NULL,
                edited_payload JSONB NOT NULL,
                eid INTEGER,
                vid INTEGER,
                edit_status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            SELECT edit_id FROM customer_feed_edits WHERE local_uuid = %s LIMIT 1
        """, (local_uuid,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE customer_feed_edits
                SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                WHERE local_uuid = %s
            """, (json.dumps(edited_payload), local_uuid))
        else:
            cur.execute("""
                INSERT INTO customer_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW())
            """, (local_uuid, json.dumps(edited_payload), token_eid, vid))

        conn.commit()
        audit_log(
            action="mobile_customer_feed_edit",
            entity_type="customer_feed_edit",
            entity_id=local_uuid,
            details={"eid": token_eid, "vid": vid, "local_uuid": local_uuid}
        )
        return jsonify({"status": "ok"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Customer feed edit failed")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ----------------------------------------------------
# /api/mobile/payment_feed_edit
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("60 per minute")
@mobile_bp.route("/api/mobile/payment_feed_edit", methods=["POST"])
@mobile_auth_required(verify_village=True)
def payment_feed_edit():
    """Receive an edit request for a pending payment feed item from mobile.
    Stores the edited payload in payment_feed_edits table.
    The /feed page shows original (strikethrough) + edited data.
    """
    conn = None
    cur = None
    try:
        data = request.json
        if not data:
            return jsonify({"error": "missing body"}), 400

        local_uuid = (data.get("local_uuid") or "").strip()
        edited_payload = data.get("edited_payload")
        eid = data.get("eid")
        vid = data.get("vid")

        if eid is not None and int(eid) != g.mobile_user["eid"]:
            return jsonify({"error": "eid mismatch with session token"}), 403

        if vid is not None and not check_user_village_access(g.mobile_user["user_id"], g.mobile_user["eid"], g.mobile_user["level"], vid):
            return jsonify({"error": f"Access denied: Village {vid} not assigned to this account"}), 403

        if not local_uuid:
            return jsonify({"error": "missing local_uuid"}), 400
        if not edited_payload or not isinstance(edited_payload, dict):
            return jsonify({"error": "missing or invalid edited_payload"}), 400

        data_token = getattr(g, "mobile_token_data", {}) or {}
        token_eid = int(data_token.get("eid", 0))
        req_eid = int(eid or 0)
        if req_eid and req_eid != token_eid:
            return jsonify({"error": "eid mismatch"}), 403

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payment_feed_edits (
                edit_id SERIAL PRIMARY KEY,
                local_uuid TEXT NOT NULL,
                edited_payload JSONB NOT NULL,
                eid INTEGER,
                vid INTEGER,
                edit_status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            SELECT edit_id FROM payment_feed_edits WHERE local_uuid = %s LIMIT 1
        """, (local_uuid,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE payment_feed_edits
                SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                WHERE local_uuid = %s
            """, (json.dumps(edited_payload), local_uuid))
        else:
            cur.execute("""
                INSERT INTO payment_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW())
            """, (local_uuid, json.dumps(edited_payload), token_eid, vid))

        conn.commit()
        audit_log(
            action="mobile_payment_feed_edit",
            entity_type="payment_feed_edit",
            entity_id=local_uuid,
            details={"eid": token_eid, "vid": vid, "local_uuid": local_uuid}
        )
        return jsonify({"status": "ok"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Payment feed edit failed")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ----------------------------------------------------
# /api/mobile/payment_feed_edits_debug  (temp debug)
# ----------------------------------------------------
@csrf.exempt
@mobile_bp.route("/api/mobile/payment_feed_edits_debug", methods=["GET"])
@mobile_auth_required(allowed_levels=["admin", "mgmt"], verify_village=False)
def payment_feed_edits_debug():
    """Temporary debug endpoint — returns all rows in payment_feed_edits."""
    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT edit_id, local_uuid, edited_payload, eid, vid, edit_status, created_at::text
            FROM payment_feed_edits
            ORDER BY edit_id DESC
            LIMIT 20
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return jsonify({"edits": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------
# /api/mobile/parent_customer_info
# ----------------------------------------------------
@csrf.exempt
@mobile_bp.route("/api/mobile/parent_customer_info")
@mobile_auth_required(verify_village=True)
def mobile_parent_customer_info():
    pano = request.args.get("pano")
    vid = request.args.get("vid")

    if not pano or not vid:
        return jsonify({"error": "Missing pano or vid"}), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT name, phone_number, aadhaar_number, notes, type, period, total_amount, base_amount, cutting_amount, interest_amount, ucid, cycle_number
            FROM v_all_customers
            WHERE vid = %s AND ano = %s
            ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
            LIMIT 1
        """, (int(vid), int(pano)))
        row = cur.fetchone()
        if not row:
            return jsonify({"found": False})
        
        return jsonify({
            "found": True,
            "name": row[0] or "",
            "phone_number": row[1] or "",
            "aadhaar_number": row[2] or "",
            "notes": row[3] or "",
            "type": row[4] or "",
            "period": row[5] or 0,
            "total_amount": row[6] or 0.0,
            "base_amount": row[7] or 0.0,
            "cutting_amount": row[8] or 0.0,
            "interest_amount": row[9] or 0.0,
            "ucid": row[10] if len(row) > 10 and row[10] is not None else None,
            "cycle_number": row[11] if len(row) > 11 and row[11] is not None else 1
        })
    except Exception as e:
        logger.error(f"Error in mobile_parent_customer_info: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------
# /api/mobile/reset_database
# ----------------------------------------------------
@csrf.exempt
@mobile_bp.route("/api/mobile/reset_database", methods=["POST"])
@mobile_auth_required(allowed_levels=["admin", "mgmt"], verify_village=False)
def reset_database():
    conn = None
    cur = None
    try:
        # 1. Environment Guard: Strictly blocked in production environment
        is_prod = (
            os.environ.get("FLASK_ENV", "").strip().lower() == "production"
            or os.environ.get("ENV", "").strip().lower() == "production"
            or os.environ.get("ENVIRONMENT", "").strip().lower() == "production"
            or os.environ.get("PRODUCTION", "").strip().lower() in ("1", "true")
        )
        if is_prod:
            logger.warning("SECURITY ALERT: Blocked reset_database call in production environment by user_id=%s", g.mobile_user["user_id"])
            return jsonify({"error": "Database reset is strictly disabled in production environment"}), 403

        # 2. Extract password from request
        data = request.get_json(silent=True) or {}
        password = data.get("password") or request.form.get("password")
        if not password:
            return jsonify({"error": "Admin password required to confirm database reset"}), 400

        user_id = g.mobile_user["user_id"]
        eid = g.mobile_user["eid"]
        level = g.mobile_user["level"]

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        # 3. Fetch user password_hash and verify
        cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        pw_row = cur.fetchone()
        if not pw_row or not pw_row[0]:
            return jsonify({"error": "User account verification failed"}), 401

        if not check_password_hash(pw_row[0], password):
            logger.warning("FAILED RESET ATTEMPT: Incorrect admin password for user_id=%s", user_id)
            return jsonify({"error": "Incorrect admin password. Database reset aborted."}), 401

        # Delete all data
        cur.execute("""
            TRUNCATE TABLE
                payment,
                closed_cust_payment,
                customer,
                closed_cust_account,
                customer_docs,
                customer_docs_feed,
                customer_feed,
                payment_feed_items,
                user_devices,
                user_village_access,
                users,
                village,
                employee
            RESTART IDENTITY CASCADE
        """)
        
        conn.commit()
        audit_log(
            action="reset_database",
            entity_type="system",
            entity_id="full_database",
            details={
                "performed_by_user_id": user_id,
                "performed_by_eid": eid,
                "level": level
            }
        )

        return {"success": True, "message": "All data deleted successfully"}

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except:
            pass
        return {"error": str(e)}, 500

    finally:
        try:
            if cur:
                cur.close()

            if conn:
                conn.close()
        except:
            pass
