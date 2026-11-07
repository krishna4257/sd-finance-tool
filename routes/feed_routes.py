import json
import logging
import base64
import pytz
import traceback
from datetime import datetime, date, timedelta
from decimal import Decimal

from flask import Blueprint, render_template, request, jsonify, session, redirect, flash

from db import get_pg_connection
from security.auth import login_required
from services.audit_service import audit_log
from psycopg2.extras import execute_values
from services.mobile_service import (
    broadcast_submission_event,
    to_decimal,
    ensure_feed_tables_exist,
    merge_edit_payload,
    normalize_account_number,
    normalize_mobile_customer_payload,
    normalize_mobile_payment_payload,
)
from services.customer_service import (
    parse_date_input,
    format_date_display,
    format_date_iso,
    recalc_customer_balance,
    recalc_customer_repayment_score,
    invalidate_village_health_cache,
)

logger = logging.getLogger(__name__)

feed_bp = Blueprint("feed_bp", __name__)


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


def _call_audit_log(*args, **kwargs):
    return _resolve_func("audit_log", audit_log)(*args, **kwargs)


def _call_broadcast(*args, **kwargs):
    return _resolve_func("broadcast_submission_event", broadcast_submission_event)(*args, **kwargs)


def _call_invalidate_cache(*args, **kwargs):
    return _resolve_func("invalidate_village_health_cache", invalidate_village_health_cache)(*args, **kwargs)


def _call_recalc_balance(*args, **kwargs):
    return _resolve_func("recalc_customer_balance", recalc_customer_balance)(*args, **kwargs)


def _call_execute_values(*args, **kwargs):
    return _resolve_func("execute_values", execute_values)(*args, **kwargs)


@feed_bp.route("/feed")
@login_required
def feed():
    logger.debug("Accessing feed page")
    vid = session.get("vid")
    if not vid:
        return redirect("/dashboard")
    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:
        # Fetch village mapping
        village_map = {}
        try:
            cur.execute("SELECT vid, village_name FROM village")
            village_map = {row[0]: row[1] for row in cur.fetchall()}
        except Exception as ve:
            logger.warning(f"Failed to fetch village_map: {ve}")

        # CUSTOMER FEED
        cur.execute("""
            SELECT
                cf.feed_id,
                cf.payload,
                cf.status,
                cf.vid,
                COALESCE(
                    (cf.payload->'payload'->>'ano')::INT,
                    (cf.payload->>'ano')::INT
                ) AS ano,
                COALESCE(
                    cf.payload->'payload'->>'name',
                    cf.payload->>'name'
                ) AS name,
                COALESCE(
                    cf.payload->'payload'->>'type',
                    cf.payload->>'type'
                ) AS type,
                COALESCE(feed_docs.aadhaar_front_pic, docs.aadhaar_front_pic) AS aadhaar_front_pic,
                COALESCE(feed_docs.aadhaar_back_pic, docs.aadhaar_back_pic) AS aadhaar_back_pic,
                COALESCE(feed_docs.house_photo, docs.house_photo) AS house_photo,
                v.village_name
            FROM customer_feed cf
            LEFT JOIN village v ON v.vid = cf.vid
            LEFT JOIN LATERAL (
                SELECT
                    cdf.aadhaar_front_pic,
                    cdf.aadhaar_back_pic,
                    cdf.house_photo
                FROM customer_docs_feed cdf
                WHERE cdf.vid = cf.vid
                  AND cdf.status = 'pending'
                  AND cdf.ano = COALESCE(
                      (cf.payload->'payload'->>'ano')::INT,
                      (cf.payload->>'ano')::INT
                  )
                ORDER BY cdf.created_at DESC NULLS LAST, cdf.docs_feed_id DESC
                LIMIT 1
            ) AS feed_docs ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    cd.aadhaar_front_pic,
                    cd.aadhaar_back_pic,
                    cd.house_photo
                FROM customer_docs cd
                WHERE cd.vid = cf.vid
                  AND cd.ano = COALESCE(
                      (cf.payload->'payload'->>'ano')::INT,
                      (cf.payload->>'ano')::INT
                  )
                ORDER BY cd.uploaded_at DESC NULLS LAST, cd.doc_id DESC
                LIMIT 1
            ) AS docs ON TRUE
            WHERE cf.vid = %s AND cf.status='pending'
            ORDER BY cf.feed_id DESC
        """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore

        customers = []
        for r in rows:
            row_dict = dict(zip(columns, r))

            payload = row_dict.get("payload")

            # âœ… Normalize payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            elif payload is None:
                payload = {}

            customer_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
            # ✅ Flatten payload into row_dict (VERY IMPORTANT)
            row_dict.update({
                "ano": customer_payload.get("ano"), # type: ignore
                "name": customer_payload.get("name"), # type: ignore
                "pano": customer_payload.get("pano"), # type: ignore
                "phone_number": customer_payload.get("phone_number"), # type: ignore
                "type": customer_payload.get("type"), # type: ignore
                "period": customer_payload.get("period"), # type: ignore
                "start_date": customer_payload.get("start_date"), # type: ignore
                "end_date": customer_payload.get("end_date"), # type: ignore
                "total_amount": customer_payload.get("total_amount"), # type: ignore
                "installment_amount": customer_payload.get("installment_amount"), # type: ignore
                "aadhaar_number": customer_payload.get("aadhaar_number"), # type: ignore
                "notes": customer_payload.get("notes"), # type: ignore
                "latitude": customer_payload.get("latitude"), # type: ignore
                "longitude": customer_payload.get("longitude"), # type: ignore
                "eid": customer_payload.get("eid"), # type: ignore
                "vid": customer_payload.get("vid"), # type: ignore
            })

            # Resolved village_name
            row_dict["village_name"] = (
                row_dict.get("village_name")
                or (customer_payload.get("village_name") if customer_payload else None)
                or village_map.get(row_dict.get("vid"))
                or session.get("village_name")
                or (f"Village {row_dict.get('vid')}" if row_dict.get('vid') else "Village")
            )

            # keep payload also (optional)
            row_dict["payload"] = customer_payload
            row_dict["raw_payload"] = payload

            # format dates for HTML5 date inputs (must be yyyy-mm-dd)
            if row_dict.get("start_date"):
                row_dict["start_date"] = format_date_iso(row_dict["start_date"])
            if row_dict.get("end_date"):
                row_dict["end_date"] = format_date_iso(row_dict["end_date"])

            customers.append(row_dict)
        # PAYMENT FEED (Left join customer by vid and ano to detect mapped/unmapped status)
        cur.execute("""
        SELECT
            pfi.feed_payment_id,
            pfi.local_uuid,
            pfi.payload->>'ano' AS ano,
            pfi.payload->>'amt' AS amt,
            COALESCE(pfi.payload->>'payment_date', pfi.payload->>'pdate') AS pdt,
            COALESCE(pfi.payload->>'payment_type', 'cash') AS payment_type,
            pfi.payload->>'cash_amount' AS cash_amount,
            pfi.payload->>'upi_amount' AS upi_amount,
            pfi.payload->>'vid' AS vid,
            pfi.status,
            c.cid,
            c.name AS customer_name,
            c.start_date AS customer_start_date
        FROM payment_feed_items pfi
        LEFT JOIN LATERAL (
            SELECT cid, name, start_date
            FROM customer c
            WHERE c.vid = (pfi.payload->>'vid')::INT
              AND c.ano = (pfi.payload->>'ano')::INT
            ORDER BY c.cid DESC
            LIMIT 1
        ) c ON TRUE
        WHERE pfi.status='pending'
          AND (pfi.payload->>'vid')::INT = %s
        ORDER BY pfi.feed_payment_id DESC
    """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore

        payments = [dict(zip(columns, r)) for r in rows]
        for p in payments:
            raw_pdt = p.get("pdt")
            p["display_date"] = format_date_display(raw_pdt)
            p["iso_date"] = format_date_iso(raw_pdt)
            p["pdt"] = p["display_date"]

        cur.execute("""
            SELECT
                cdf.docs_feed_id,
                cdf.local_uuid,
                cdf.vid,
                cdf.ano,
                cdf.eid,
                cdf.cid,
                cdf.aadhaar_front_pic,
                cdf.aadhaar_back_pic,
                cdf.house_photo,
                cdf.status,
                cdf.created_at,
                COALESCE(
                    c.name,
                    cf.payload->>'name',
                    'Customer ' || cdf.ano::text
                ) AS name
            FROM customer_docs_feed cdf
            LEFT JOIN LATERAL (
                SELECT cid, name
                FROM customer c
                WHERE c.vid = cdf.vid
                  AND c.ano = cdf.ano
                ORDER BY c.cid DESC
                LIMIT 1
            ) c ON TRUE
            LEFT JOIN LATERAL (
                SELECT payload
                FROM customer_feed cf_inner
                WHERE cf_inner.vid = cdf.vid
                  AND cf_inner.status = 'pending'
                  AND (cf_inner.payload->>'ano')::bigint = cdf.ano
                ORDER BY cf_inner.feed_id DESC
                LIMIT 1
            ) cf ON TRUE
            WHERE cdf.vid = %s
              AND cdf.status = 'pending'
              AND c.cid IS NOT NULL
            ORDER BY cdf.docs_feed_id DESC
        """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore
        existing_customer_docs = [dict(zip(columns, r)) for r in rows]

        # Fetch customer edits submitted from mobile (customer_feed_edits)
        customer_edit_map = {}
        try:
            cur.execute("""
                SELECT local_uuid, edited_payload
                FROM customer_feed_edits
                WHERE edit_status = 'pending'
            """)
            for edit_row in cur.fetchall():
                ep = edit_row[1]
                if isinstance(ep, str):
                    try:
                        ep = json.loads(ep)
                    except Exception:
                        ep = {}
                customer_edit_map[edit_row[0]] = ep
        except Exception:
            conn.rollback()  # Table may not exist yet on first run; rollback aborted transaction

        # Attach edits to customers (match by local_uuid stored in customer_feed)
        for c in customers:
            local_uuid = None
            raw = c.get("raw_payload") or {}
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    raw = {}
            local_uuid = raw.get("local_uuid") or c.get("local_uuid")
            edit = customer_edit_map.get(local_uuid) if local_uuid else None
            if edit:
                if edit.get("start_date"):
                    edit["start_date"] = format_date_iso(edit["start_date"])
                if edit.get("end_date"):
                    edit["end_date"] = format_date_iso(edit["end_date"])
            c["edit"] = edit

        # Pre-screen duplicate Aadhaar cards across pending customer registrations
        feed_aadhaars = set()
        for c in customers:
            raw_a = str((c.get("edit") and c.get("edit", {}).get("aadhaar_number")) or c.get("aadhaar_number") or "").replace(" ", "").replace("-", "").strip()
            clean_a = "".join(ch for ch in raw_a if ch.isdigit())
            if len(clean_a) == 12:
                feed_aadhaars.add(clean_a)

        aadhaar_dupe_map = {}
        if feed_aadhaars:
            try:
                cur.execute("""
                    SELECT 
                        c.cid,
                        c.vid,
                        COALESCE(v.village_name, 'Village ' || c.vid::text) AS village_name,
                        c.ano,
                        c.name,
                        c.phone_number,
                        c.start_date,
                        c.end_date,
                        c.total_amount,
                        c.balance_amount,
                        COALESCE(c.status, 'open') AS status,
                        REPLACE(REPLACE(COALESCE(c.aadhaar_number, ''), ' ', ''), '-', '') AS clean_aadhaar
                    FROM customer c
                    LEFT JOIN village v ON v.vid = c.vid
                    WHERE REPLACE(REPLACE(COALESCE(c.aadhaar_number, ''), ' ', ''), '-', '') = ANY(%s)
                    UNION ALL
                    SELECT 
                        ca.cid,
                        ca.vid,
                        COALESCE(v.village_name, 'Village ' || ca.vid::text) AS village_name,
                        ca.ano,
                        ca.name,
                        ca.phone_number,
                        ca.start_date,
                        ca.end_date,
                        ca.total_amount,
                        ca.balance_amount,
                        'closed' AS status,
                        REPLACE(REPLACE(COALESCE(ca.aadhaar_number, ''), ' ', ''), '-', '') AS clean_aadhaar
                    FROM closed_cust_account ca
                    LEFT JOIN village v ON v.vid = ca.vid
                    WHERE REPLACE(REPLACE(COALESCE(ca.aadhaar_number, ''), ' ', ''), '-', '') = ANY(%s)
                    ORDER BY cid DESC
                """, (list(feed_aadhaars), list(feed_aadhaars)))
                dupe_rows = cur.fetchall()
                for dr in dupe_rows:
                    a_key = dr[11]
                    if a_key not in aadhaar_dupe_map:
                        aadhaar_dupe_map[a_key] = []
                    aadhaar_dupe_map[a_key].append({
                        "cid": dr[0],
                        "vid": dr[1],
                        "village_name": dr[2] or f"Village {dr[1]}",
                        "ano": dr[3],
                        "name": dr[4] or "Unnamed",
                        "phone_number": dr[5] or "",
                        "start_date": format_date_display(str(dr[6])) if dr[6] else "",
                        "end_date": format_date_display(str(dr[7])) if dr[7] else "",
                        "total_amount": float(dr[8] or 0),
                        "balance_amount": float(dr[9] or 0),
                        "status": dr[10] or "open"
                    })
            except Exception as e:
                logger.error(f"Error pre-screening duplicate aadhaars for feed: {e}")

        for c in customers:
            raw_a = str((c.get("edit") and c.get("edit", {}).get("aadhaar_number")) or c.get("aadhaar_number") or "").replace(" ", "").replace("-", "").strip()
            clean_a = "".join(ch for ch in raw_a if ch.isdigit())
            dupes = aadhaar_dupe_map.get(clean_a, [])
            c["duplicate_accounts"] = dupes
            c["duplicate_count"] = len(dupes)

        # Fetch payment edits submitted from mobile (payment_feed_edits)
        payment_edit_map = {}
        try:
            cur.execute("""
                SELECT local_uuid, edited_payload
                FROM payment_feed_edits
                WHERE edit_status = 'pending'
            """)
            for edit_row in cur.fetchall():
                ep = edit_row[1]
                if isinstance(ep, str):
                    try:
                        ep = json.loads(ep)
                    except Exception:
                        ep = {}
                payment_edit_map[edit_row[0]] = ep
        except Exception:
            conn.rollback()  # Table may not exist yet on first run; rollback aborted transaction

        # Attach edits to payments and re-verify cid if ano was edited
        for p in payments:
            local_uuid = p.get("local_uuid")
            edit = payment_edit_map.get(local_uuid) if local_uuid else None
            p["edit"] = edit
            if edit and edit.get("ano"):
                try:
                    edited_ano = int(edit["ano"])
                    cur.execute(
                        "SELECT cid, name, start_date FROM customer WHERE vid = %s AND ano = %s",
                        (vid, edited_ano)
                    )
                    cust_match = cur.fetchone()
                    if cust_match:
                        p["cid"] = cust_match[0]
                        p["customer_name"] = cust_match[1]
                        p["customer_start_date"] = cust_match[2]
                    else:
                        p["cid"] = None
                        p["customer_name"] = None
                except Exception:
                    pass

        # ACCOUNT CLOSURE FEED
        cur.execute("""
            SELECT
                acf.feed_id,
                acf.local_uuid,
                acf.device_id,
                acf.eid,
                acf.vid,
                acf.ano,
                acf.status,
                acf.created_at,
                COALESCE(c.name, ca.name, 'Customer Not Found') AS name,
                COALESCE(c.cid, ca.cid) AS cid,
                COALESCE(c.total_amount, ca.total_amount, 0) AS total_amount,
                COALESCE(c.paid_amount, ca.paid_amount, 0) AS paid_amount,
                COALESCE(c.balance_amount, ca.balance_amount, 0) AS balance_amount,
                COALESCE(c.interest_amount, ca.interest_amount, 0) AS interest_amount,
                COALESCE(c.type, ca.type, 'weekly') AS type,
                COALESCE(c.period, ca.period, 0) AS period,
                COALESCE(c.installment_amount, ca.installment_amount, 0) AS installment_amount,
                COALESCE(c.start_date, ca.start_date) AS start_date,
                COALESCE(c.end_date, ca.end_date) AS end_date,
                COALESCE(c.phone_number, ca.phone_number, '') AS phone_number,
                COALESCE(c.aadhaar_number, ca.aadhaar_number, '') AS aadhaar_number,
                COALESCE(c.notes, ca.notes, '') AS notes,
                COALESCE(c.latitude, ca.latitude) AS latitude,
                COALESCE(c.longitude, ca.longitude) AS longitude,
                COALESCE(c.status, ca.status, 'open') AS account_status,
                COALESCE(v.village_name, 'Village ' || acf.vid::text) AS village_name,
                docs.aadhaar_front_pic,
                docs.aadhaar_back_pic,
                docs.house_photo
            FROM account_closure_feed acf
            LEFT JOIN LATERAL (
                SELECT cid, name, total_amount, paid_amount, balance_amount, interest_amount, type, period, installment_amount, start_date, end_date, phone_number, aadhaar_number, notes, latitude, longitude, status
                FROM customer c
                WHERE c.vid = acf.vid
                  AND c.ano = acf.ano
                ORDER BY c.cid DESC
                LIMIT 1
            ) c ON TRUE
            LEFT JOIN LATERAL (
                SELECT cid, name, total_amount, paid_amount, balance_amount, interest_amount, type, period, installment_amount, start_date, end_date, phone_number, aadhaar_number, notes, latitude, longitude, status
                FROM closed_cust_account ca
                WHERE ca.vid = acf.vid
                  AND ca.ano = acf.ano
                ORDER BY ca.cid DESC
                LIMIT 1
            ) ca ON TRUE
            LEFT JOIN village v
              ON v.vid = acf.vid
            LEFT JOIN LATERAL (
                SELECT cd.aadhaar_front_pic, cd.aadhaar_back_pic, cd.house_photo
                FROM customer_docs cd
                WHERE cd.vid = acf.vid AND cd.ano = acf.ano
                ORDER BY cd.uploaded_at DESC NULLS LAST, cd.doc_id DESC
                LIMIT 1
            ) docs ON TRUE
            WHERE acf.vid = %s AND acf.status = 'pending'
            ORDER BY acf.feed_id DESC
        """, (vid,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore
        closure_requests = [dict(zip(columns, r)) for r in rows]

        for req in closure_requests:
            for pic_key in ("aadhaar_front_pic", "aadhaar_back_pic", "house_photo"):
                pic_val = req.get(pic_key)
                if isinstance(pic_val, memoryview):
                    req[pic_key] = base64.b64encode(pic_val.tobytes()).decode("ascii")
                elif isinstance(pic_val, (bytes, bytearray)):
                    req[pic_key] = base64.b64encode(pic_val).decode("ascii")

            if req.get("created_at"):
                try:
                    dt = req["created_at"]
                    if hasattr(dt, "strftime"):
                        req["created_at_display"] = dt.strftime("%d %b %Y, %I:%M %p")
                    else:
                        req["created_at_display"] = str(dt)
                except Exception:
                    req["created_at_display"] = str(req.get("created_at"))
            else:
                req["created_at_display"] = "Recently"

            if req.get("start_date"):
                try:
                    s_dt = req["start_date"]
                    req["start_date_display"] = s_dt.strftime("%d %b %Y") if hasattr(s_dt, "strftime") else str(s_dt)
                except Exception:
                    req["start_date_display"] = str(req.get("start_date"))
            else:
                req["start_date_display"] = "—"

            if req.get("end_date"):
                try:
                    e_dt = req["end_date"]
                    req["end_date_display"] = e_dt.strftime("%d %b %Y") if hasattr(e_dt, "strftime") else str(e_dt)
                except Exception:
                    req["end_date_display"] = str(req.get("end_date"))
            else:
                req["end_date_display"] = "—"

            t_raw = str(req.get("type") or "W").upper()
            if t_raw in ("W", "WEEKLY"):
                req["type_display"] = "Weekly"
                req["installment_freq"] = "/ week"
            elif t_raw in ("D", "DAILY"):
                req["type_display"] = "Daily"
                req["installment_freq"] = "/ day"
            elif t_raw in ("M", "MONTHLY"):
                req["type_display"] = "Monthly"
                req["installment_freq"] = "/ month"
            else:
                req["type_display"] = req.get("type", "Standard")
                req["installment_freq"] = ""

        # Highest account number recorded in DB for this village
        cur.execute("SELECT COALESCE(MAX(ano), 0) FROM customer WHERE vid = %s", (vid,))
        max_ano_res = cur.fetchone()
        max_ano = max_ano_res[0] if max_ano_res and max_ano_res[0] else 0

        # Highest payment date recorded in DB for this village
        cur.execute("SELECT MAX(payment_date) FROM payment WHERE vid = %s", (vid,))
        max_pdt_res = cur.fetchone()
        max_payment_date = max_pdt_res[0] if max_pdt_res and max_pdt_res[0] else None
        max_payment_date_display = format_date_display(str(max_payment_date)) if max_payment_date else "No payments yet"

        # Calculate pending summary totals for All Queues Dashboard
        def _parse_dec(val):
            try:
                return Decimal(str(val)) if val is not None else Decimal(0)
            except Exception:
                return Decimal(0)

        pending_payments_total = sum(
            _parse_dec(p.get("edit", {}).get("amt") if p.get("edit") and p.get("edit", {}).get("amt") else p.get("amt"))
            for p in payments
        )
        pending_customers_total = sum(
            _parse_dec(c.get("edit", {}).get("total_amount") if c.get("edit") and c.get("edit", {}).get("total_amount") else c.get("total_amount"))
            for c in customers
        )
        pending_closures_total = sum(_parse_dec(cl.get("balance_amount")) for cl in closure_requests)

        return render_template(
            "feed.html",
            customers=customers,
            payments=payments,
            existing_customer_docs=existing_customer_docs,
            closure_requests=closure_requests,
            village_map=village_map,
            max_ano=max_ano,
            max_payment_date_display=max_payment_date_display,
            pending_payments_total=pending_payments_total,
            pending_customers_total=pending_customers_total,
            pending_closures_total=pending_closures_total
        )

    finally:
        cur.close()
        conn.close()


@feed_bp.post("/feed/closure/accept/<feed_id>")
@login_required
def accept_closure_request(feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        action = data.get("action")  # 'defaulted' or 'written_off' or 'discount_interest' or None
        discount_amount = data.get("discount_amount")

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        # Get the feed item
        cur.execute("""
            SELECT ano, vid, status
            FROM account_closure_feed
            WHERE feed_id = %s
        """, (feed_id,))
        feed_row = cur.fetchone()
        if not feed_row:
            return jsonify({"success": False, "error": "Closure request not found"}), 404

        ano, vid, status = feed_row
        if status != 'pending':
            return jsonify({"success": False, "error": "Closure request already processed"}), 400

        # Find the customer
        cur.execute("""
            SELECT cid, total_amount, paid_amount, balance_amount, interest_amount, COALESCE(interest_discount, 0.00)
            FROM customer
            WHERE ano = %s AND vid = %s
            FOR UPDATE
        """, (ano, vid))
        cust_row = cur.fetchone()
        if not cust_row:
            cur.execute("SELECT cid FROM closed_cust_account WHERE ano = %s AND vid = %s", (ano, vid))
            closed_row = cur.fetchone()
            if closed_row:
                cur.execute("UPDATE account_closure_feed SET status = 'accepted' WHERE feed_id = %s", (feed_id,))
                conn.commit()
                return jsonify({"success": True, "message": "Customer account was already closed; closure feed request marked as accepted."})
            return jsonify({"success": False, "error": f"Customer with Account Number {ano} not found in this village"}), 404

        cid, total_amount, paid_amount, balance_amount, interest_amount, interest_discount = cust_row

        # status decision logic (identical to close_customer_account_pg)
        if balance_amount == 0:
            final_status = "closed"
        elif balance_amount > 0:
            if action == "discount_interest":
                if discount_amount is None:
                    return jsonify({"success": False, "error": "Missing discount amount"}), 400
                try:
                    discount_val = Decimal(str(discount_amount))
                except Exception:
                    return jsonify({"success": False, "error": "Invalid discount amount"}), 400

                if discount_val <= 0:
                    return jsonify({"success": False, "error": "Discount amount must be greater than 0"}), 400

                if balance_amount > interest_amount:
                    return jsonify({"success": False, "error": "Balance is greater than interest amount. Cannot apply discount."}), 400

                new_discount = Decimal(str(interest_discount)) + discount_val
                new_balance = balance_amount - discount_val

                cur.execute("""
                    UPDATE customer
                    SET interest_discount = %s,
                        balance_amount = %s
                    WHERE cid = %s
                """, (new_discount, new_balance, cid))

                balance_amount = new_balance
                final_status = "closed"
            elif action == "defaulted":
                final_status = "defaulted"
            else:
                return jsonify({
                    "success": False,
                    "error": "Balance > 0. Must mark as defaulted or discount interest."
                }), 400
        else: # balance_amount < 0
            if action != "written_off":
                return jsonify({
                    "success": False,
                    "error": "Balance < 0. Must mark as written_off."
                }), 400
            final_status = "written_off"

        # Recalculate and freeze rating in customer table before moving
        recalc_customer_repayment_score(cur, cid, force_recalc=True)

        # Move customer
        cur.execute("""
            INSERT INTO closed_cust_account (
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, status, phone_number,
                closed_by, closed_at,
                customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                base_amount, cutting_amount, interest_amount, interest_discount
            )
            SELECT
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, %s, phone_number,
                %s, NOW() AT TIME ZONE 'Asia/Kolkata',
                customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                base_amount, cutting_amount, interest_amount, interest_discount
            FROM customer
            WHERE cid = %s
        """, (final_status, session.get("employee_id") or session.get("eid"), cid))

        # Move payments
        cur.execute("""
            INSERT INTO closed_cust_payment (
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            )
            SELECT
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            FROM payment
            WHERE cid = %s
        """, (cid,))

        # Delete from active tables
        cur.execute("DELETE FROM payment WHERE cid = %s", (cid,))
        cur.execute("DELETE FROM customer WHERE cid = %s", (cid,))

        # Update customer_loan_link lineage tier to closed
        cur.execute("""
            UPDATE customer_loan_link
            SET record_tier = 'closed',
                status = %s
            WHERE cid = %s
        """, (final_status, cid))

        # Mark all pending closure requests for this customer in this village as accepted
        cur.execute("""
            UPDATE account_closure_feed
            SET status = 'accepted'
            WHERE ano = %s AND vid = %s AND status = 'pending'
            RETURNING local_uuid
        """, (ano, vid))
        closed_uuids = [r[0] for r in cur.fetchall() if r[0]]

        # Invalidate village health cache (matching customer dashboard pipeline)
        KOLKATA = pytz.timezone('Asia/Kolkata')
        today = datetime.now(KOLKATA).date()
        _call_invalidate_cache(cur, vid, today)

        _call_audit_log(
            action="close_customer_account_via_feed",
            entity_type="account_closure_feed",
            entity_id=feed_id,
            details={
                "ano": ano,
                "vid": vid,
                "cid": cid,
                "final_status": final_status,
                "action": action,
                "discount_amount": str(discount_amount) if discount_amount else None
            },
            status="success"
        )

        conn.commit()

        for lu in closed_uuids:
            _call_broadcast(vid, {
                "type": "status_update",
                "feed_type": "closure",
                "local_uuid": lu,
                "ano": ano,
                "vid": vid,
                "status": "accepted"
            })

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error accepting closure request: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/closure/edit/<feed_id>")
@login_required
def edit_closure_request(feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        ano = data.get("ano")
        vid = data.get("vid")

        if ano is None or vid is None:
            return jsonify({"success": False, "error": "Account number and village ID are required"}), 400

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE account_closure_feed
            SET ano = %s, vid = %s
            WHERE feed_id = %s AND status = 'pending'
            RETURNING feed_id, local_uuid
        """, (ano, vid, feed_id))

        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Pending closure request not found"}), 404

        conn.commit()

        c_lu = row[1]
        if c_lu:
            _call_broadcast(vid, {
                "type": "status_update",
                "feed_type": "closure",
                "local_uuid": c_lu,
                "ano": ano,
                "vid": vid,
                "status": "rejected_edit"
            })

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing closure request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/customer/edit/<feed_id>")
@login_required
def edit_customer_feed(feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT local_uuid, payload
            FROM customer_feed
            WHERE feed_id = %s
        """, (feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Customer feed item not found"}), 404

        local_uuid, payload_raw = row
        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if not isinstance(payload, dict):
            payload = {}

        # Fields that can be edited
        editable_keys = [
            "name", "ano", "total_amount", "installment_amount", "aadhaar_number",
            "phone_number", "type", "period", "start_date", "end_date", "notes", "vid", "pano"
        ]

        edited_payload = {}
        for k in editable_keys:
            if k in data and data[k] is not None:
                val = str(data[k]).strip()
                if k in ("ano", "total_amount", "installment_amount", "period", "vid", "pano"):
                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                payload[k] = val
                edited_payload[k] = val

        cur.execute("""
            UPDATE customer_feed
            SET payload = %s
            WHERE feed_id = %s
        """, (json.dumps(payload), feed_id))

        if local_uuid:
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
            existing_edit = cur.fetchone()

            if existing_edit:
                cur.execute("""
                    UPDATE customer_feed_edits
                    SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                    WHERE local_uuid = %s
                """, (json.dumps(edited_payload), local_uuid))
            else:
                cur.execute("""
                    INSERT INTO customer_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', NOW())
                """, (local_uuid, json.dumps(edited_payload), payload.get("eid"), payload.get("vid")))

        conn.commit()

        if local_uuid:
            c_vid = payload.get("vid")
            c_ano = payload.get("ano")
            _call_broadcast(c_vid, {
                "type": "status_update",
                "feed_type": "customer",
                "local_uuid": local_uuid,
                "ano": c_ano,
                "vid": c_vid,
                "status": "rejected_edit",
                "edited_payload": edited_payload
            })

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing customer feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/closure/delete/<feed_id>")
@login_required
def delete_closure_request(feed_id):
    conn = None
    cur = None
    try:
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("SELECT local_uuid, ano, vid, eid FROM account_closure_feed WHERE feed_id = %s", (feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Closure request not found"}), 404

        local_uuid, c_ano, c_vid, c_eid = row
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        if local_uuid:
            ensure_feed_tables_exist(cur)
            cur.execute("""
                INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                VALUES ('closure', %s, %s, %s, %s, 'rejected_deleted', %s)
            """, (local_uuid, c_ano, c_vid, c_eid, logged_user))

        cur.execute("DELETE FROM account_closure_feed WHERE feed_id = %s", (feed_id,))
        conn.commit()

        if local_uuid:
            _call_broadcast(c_vid, {
                "type": "status_update",
                "feed_type": "closure",
                "local_uuid": local_uuid,
                "ano": c_ano,
                "vid": c_vid,
                "status": "rejected_deleted"
            })

        _call_audit_log(
            action="delete_closure_feed",
            entity_type="account_closure_feed",
            entity_id=feed_id,
            details={"deleted_by": logged_user}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting closure request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/customer/delete/<feed_id>")
@login_required
def delete_customer_feed(feed_id):
    conn = None
    cur = None
    try:
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("SELECT local_uuid, payload, status FROM customer_feed WHERE feed_id = %s FOR UPDATE", (feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Customer feed item not found"}), 404

        local_uuid, payload_raw, feed_status = row
        if feed_status != "pending":
            return jsonify({"success": False, "error": f"Cannot delete feed that has already been {feed_status}"}), 400

        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        c_ano = payload.get("ano")
        c_vid = payload.get("vid")
        c_eid = payload.get("eid")
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        if local_uuid:
            ensure_feed_tables_exist(cur)
            cur.execute("""
                INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                VALUES ('customer', %s, %s, %s, %s, 'rejected_deleted', %s)
            """, (local_uuid, c_ano, c_vid, c_eid, logged_user))

        cur.execute("DELETE FROM customer_feed WHERE feed_id = %s", (feed_id,))
        if local_uuid:
            try:
                cur.execute("DELETE FROM customer_feed_edits WHERE local_uuid = %s", (local_uuid,))
            except Exception:
                pass

        conn.commit()

        if local_uuid:
            _call_broadcast(c_vid, {
                "type": "status_update",
                "feed_type": "customer",
                "local_uuid": local_uuid,
                "ano": c_ano,
                "vid": c_vid,
                "status": "rejected_deleted"
            })

        _call_audit_log(
            action="delete_customer_feed",
            entity_type="customer_feed",
            entity_id=feed_id,
            details={"deleted_by": logged_user}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting customer feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()




@feed_bp.post("/feed/customer/accept/<feed_id>")
@login_required
def accept_customer(feed_id):

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    # Safety check: ensure logged-in employee
    # employee_id is always set at login.
    # eid may only exist after village/context selection.
    logged_user = session.get("employee_id") or session.get("eid")

    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT local_uuid, payload, status
        FROM customer_feed
        WHERE feed_id = %s
        FOR UPDATE
    """, (feed_id,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Feed not found"}, 404
    
    local_uuid = row[0]
    raw_payload = row[1]
    data: dict = json.loads(raw_payload) if isinstance(raw_payload, str) else (raw_payload if isinstance(raw_payload, dict) else {})
    feed_status = row[2]

    if feed_status != "pending":
        cur.close()
        conn.close()
        return {"success": False, "error": f"Customer feed item has already been {feed_status}"}, 400

    # Ensure payload is dict
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid payload format"}, 400

    # Ensure feed edit tracking tables exist safely
    ensure_feed_tables_exist(cur)

    # Merge pending edit if any
    if local_uuid:
        cur.execute("""
            SELECT edited_payload
            FROM customer_feed_edits
            WHERE local_uuid = %s AND edit_status = 'pending'
            LIMIT 1
        """, (local_uuid,))
        edit_row = cur.fetchone()
        if edit_row:
            ep = edit_row[0]
            if isinstance(ep, str):
                try:
                    ep = json.loads(ep)
                except Exception:
                    ep = {}
            data = merge_edit_payload(data, ep)

        # Mark edit as accepted
        cur.execute("""
            UPDATE customer_feed_edits
            SET edit_status = 'accepted'
            WHERE local_uuid = %s AND edit_status = 'pending'
        """, (local_uuid,))

    try:
        data = normalize_mobile_customer_payload(data)
    except ValueError as exc:
        cur.close()
        conn.close()
        return {"success": False, "error": str(exc)}, 400

    # Check if (ano, vid) already exists in customer, exactly as in manual web entry (/add_customer)
    c_ano = data.get("ano")
    c_vid = data.get("vid")
    if c_ano is not None and c_vid is not None:
        cur.execute("""
            SELECT 1
            FROM customer
            WHERE ano = %s AND vid = %s
            LIMIT 1
        """, (c_ano, c_vid))
        if cur.fetchone():
            cur.close()
            conn.close()
            return {"success": False, "error": f"Account number {c_ano} already exists in this village"}, 400

    loan_type = data.get("type") # type: ignore
    if loan_type == "weekly":
        loan_type = "W"
    elif loan_type == "monthly":
        loan_type = "M"

    # Robust date parsing to ensure PostgreSQL DATE format (YYYY-MM-DD)
    start_date_obj = parse_date_input(data.get("start_date")) # type: ignore
    end_date_obj = parse_date_input(data.get("end_date")) # type: ignore
    start_date_val = start_date_obj.strftime("%Y-%m-%d") if start_date_obj else data.get("start_date") # type: ignore
    end_date_val = end_date_obj.strftime("%Y-%m-%d") if end_date_obj else data.get("end_date") # type: ignore

    cur.execute("""
        INSERT INTO customer
        (
            ano,
            name,
            vid,
            start_date,
            end_date,
            total_amount,
            base_amount,
            cutting_amount,
            interest_amount,
            paid_amount,
            balance_amount,
            installment_amount,
            type,
            period,
            pano,
            aadhaar_number,
            notes,
            latitude,
            longitude,
            eid,
            phone_number,
            status
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open')
        RETURNING cid
    """,
    (
        data.get("ano"), # type: ignore
        data.get("name"), # type: ignore
        data.get("vid"), # type: ignore
        start_date_val,
        end_date_val,
        data.get("total_amount"), # type: ignore
        data.get("base_amount", 0), # type: ignore
        data.get("cutting_amount", 0), # type: ignore
        data.get("interest_amount", 0), # type: ignore
        data.get("paid_amount"), # type: ignore
        data.get("balance_amount"), # type: ignore
        data.get("installment_amount"), # type: ignore
        loan_type,
        data.get("period"), # type: ignore
        data.get("pano"), # type: ignore
        data.get("aadhaar_number"), # type: ignore
        data.get("notes"), # type: ignore
        data.get("latitude"), # type: ignore
        data.get("longitude"), # type: ignore
        data.get("eid"), # type: ignore
        data.get("phone_number") # type: ignore
        
    ))
    cid = cur.fetchone()[0]
    recalc_customer_repayment_score(cur, cid, force_recalc=True)

    # Auto-approve and link all pending customer documents for this new customer
    try:
        v_val = data.get("vid")
        a_val = data.get("ano")
        vid_int = int(v_val) if v_val is not None else None
        ano_int = int(a_val) if a_val is not None else None
    except (TypeError, ValueError):
        vid_int = None
        ano_int = None

    if vid_int is not None and ano_int is not None:
        cur.execute("""
            SELECT docs_feed_id, aadhaar_front_pic, aadhaar_back_pic, house_photo
            FROM customer_docs_feed
            WHERE vid = %s AND ano = %s AND status = 'pending'
            ORDER BY docs_feed_id ASC
        """, (vid_int, ano_int))
        pending_docs_list = cur.fetchall()

        if pending_docs_list:
            cur.execute("""
                SELECT aadhaar_front_pic, aadhaar_back_pic, house_photo
                FROM customer_docs
                WHERE vid = %s AND ano = %s
                LIMIT 1
            """, (vid_int, ano_int))
            existing_docs = cur.fetchone()

            final_aadhaar_front = existing_docs[0] if existing_docs else None
            final_aadhaar_back = existing_docs[1] if existing_docs else None
            final_house = existing_docs[2] if existing_docs else None

            doc_feed_ids = []
            for d_row in pending_docs_list:
                doc_feed_ids.append(d_row[0])
                if d_row[1] is not None:
                    final_aadhaar_front = d_row[1]
                if d_row[2] is not None:
                    final_aadhaar_back = d_row[2]
                if d_row[3] is not None:
                    final_house = d_row[3]

            if final_aadhaar_front is not None or final_aadhaar_back is not None or final_house is not None:
                cur.execute("""
                    INSERT INTO customer_docs (
                        vid,
                        ano,
                        aadhaar_front_pic,
                        aadhaar_back_pic,
                        house_photo,
                        uploaded_at
                    )
                    VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
                    ON CONFLICT (vid, ano)
                    DO UPDATE SET
                        aadhaar_front_pic = COALESCE(EXCLUDED.aadhaar_front_pic, customer_docs.aadhaar_front_pic),
                        aadhaar_back_pic = COALESCE(EXCLUDED.aadhaar_back_pic, customer_docs.aadhaar_back_pic),
                        house_photo = COALESCE(EXCLUDED.house_photo, customer_docs.house_photo),
                        uploaded_at = CURRENT_TIMESTAMP
                """, (
                    vid_int,
                    ano_int,
                    final_aadhaar_front,
                    final_aadhaar_back,
                    final_house
                ))

            cur.execute("""
                UPDATE customer_docs_feed
                SET status = 'accepted',
                    cid = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
                WHERE docs_feed_id = ANY(%s::bigint[])
            """, (cid, logged_user, doc_feed_ids))

    cur.execute("""
        UPDATE customer_feed
        SET status = 'accepted',
            reviewed_by = %s,
            reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE feed_id = %s
    """, (logged_user, feed_id))

    cur.execute("SET TIME ZONE 'UTC'")

    # Invalidate cache for this village
    if data.get("vid"):
        _call_invalidate_cache(cur, data.get("vid"), start_date_val)

    conn.commit()
    if local_uuid:
        _call_broadcast(data.get("vid"), {
            "type": "status_update",
            "feed_type": "customer",
            "local_uuid": local_uuid,
            "ano": data.get("ano"),
            "vid": data.get("vid"),
            "status": "accepted"
        })
    _call_audit_log(
        action="accept_customer_feed",
        entity_type="customer_feed",
        entity_id=feed_id,
        details={
            "ano": data.get("ano"), # type: ignore
            "vid": data.get("vid"), # type: ignore
            "eid": data.get("eid"), # type: ignore
            "reviewed_by": logged_user
        }
    )
    cur.close()
    conn.close()

    return {"success":True}


@feed_bp.post("/feed/docs/accept/<feed_id>")
@login_required
def accept_customer_feed_docs(feed_id):
    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    logged_user = session.get("employee_id") or session.get("eid")
    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT vid, payload
        FROM customer_feed
        WHERE feed_id = %s
    """, (feed_id,))

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Feed not found"}

    vid, payload = row
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid payload format"}

    customer_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    ano = normalize_account_number(customer_payload.get("ano"))
    vid = payload.get("vid") or customer_payload.get("vid") or vid
    if ano is None or vid is None:
        cur.close()
        conn.close()
        return {"success": False, "error": "Missing ano or vid in customer feed"}

    cur.execute("""
        SELECT aadhaar_front_pic, aadhaar_back_pic, house_photo
        FROM customer_docs
        WHERE vid = %s AND ano = %s
        LIMIT 1
    """, (vid, ano))
    docs = cur.fetchone()

    if not docs or (not docs[0] and not docs[1] and not docs[2]):
        cur.close()
        conn.close()
        return {"success": False, "error": "No customer documents found for this feed item"}

    _call_audit_log(
        action="accept_customer_feed_docs",
        entity_type="customer_feed",
        entity_id=feed_id,
        details={
            "ano": ano,
            "vid": vid,
            "reviewed_by": logged_user
        }
    )

    cur.close()
    conn.close()
    return {"success": True}


@feed_bp.post("/feed/existing-docs/accept/<docs_feed_id>")
@login_required
def accept_existing_customer_docs(docs_feed_id):
    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    logged_user = session.get("employee_id") or session.get("eid")
    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT vid, ano, aadhaar_front_pic, aadhaar_back_pic, house_photo, status
        FROM customer_docs_feed
        WHERE docs_feed_id = %s
        FOR UPDATE
    """, (docs_feed_id,))

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Docs feed item not found"}

    vid, ano, aadhaar_front_pic, aadhaar_back_pic, house_photo, status = row
    if status != "pending":
        cur.close()
        conn.close()
        return {"success": False, "error": "Docs feed item is not pending"}

    if not aadhaar_front_pic and not aadhaar_back_pic and not house_photo:
        cur.close()
        conn.close()
        return {"success": False, "error": "No documents attached"}

    cur.execute("""
        SELECT aadhaar_front_pic, aadhaar_back_pic, house_photo
        FROM customer_docs
        WHERE vid = %s AND ano = %s
        LIMIT 1
    """, (vid, ano))
    existing_docs = cur.fetchone()

    existing_aadhaar_front = existing_docs[0] if existing_docs else None
    existing_aadhaar_back = existing_docs[1] if existing_docs else None
    existing_house = existing_docs[2] if existing_docs else None

    final_aadhaar_front = aadhaar_front_pic if aadhaar_front_pic is not None else existing_aadhaar_front
    final_aadhaar_back = aadhaar_back_pic if aadhaar_back_pic is not None else existing_aadhaar_back
    final_house = house_photo if house_photo is not None else existing_house

    cur.execute("""
        INSERT INTO customer_docs (
            vid,
            ano,
            aadhaar_front_pic,
            aadhaar_back_pic,
            house_photo,
            uploaded_at
        )
        VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
        ON CONFLICT (vid, ano)
        DO UPDATE SET
            aadhaar_front_pic = EXCLUDED.aadhaar_front_pic,
            aadhaar_back_pic = EXCLUDED.aadhaar_back_pic,
            house_photo = EXCLUDED.house_photo,
            uploaded_at = CURRENT_TIMESTAMP
    """, (
        vid,
        ano,
        final_aadhaar_front,
        final_aadhaar_back,
        final_house
    ))

    cur.execute("""
        UPDATE customer_docs_feed
        SET status = 'accepted',
            reviewed_by = %s,
            reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE docs_feed_id = %s
    """, (logged_user, docs_feed_id))

    conn.commit()
    _call_audit_log(
        action="accept_existing_customer_docs",
        entity_type="customer_docs_feed",
        entity_id=docs_feed_id,
        details={
            "ano": ano,
            "vid": vid,
            "reviewed_by": logged_user
        }
    )

    cur.close()
    conn.close()
    return {"success": True}


@feed_bp.post("/feed/existing-docs/edit/<docs_feed_id>")
@login_required
def edit_existing_customer_docs(docs_feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        ano = data.get("ano")
        vid = data.get("vid")

        if ano is None or vid is None:
            return jsonify({"success": False, "error": "Account number and village ID are required"}), 400

        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE customer_docs_feed
            SET ano = %s, vid = %s
            WHERE docs_feed_id = %s AND status = 'pending'
            RETURNING docs_feed_id
        """, (ano, vid, docs_feed_id))

        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Pending docs feed item not found"}), 404

        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing docs feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/payment/edit/<feed_payment_id>")
@login_required
def edit_payment_feed(feed_payment_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT local_uuid, payload
            FROM payment_feed_items
            WHERE feed_payment_id = %s
        """, (feed_payment_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Payment feed item not found"}), 404

        local_uuid, payload_raw = row
        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if not isinstance(payload, dict):
            payload = {}

        # Update payload fields
        if "ano" in data and data["ano"] is not None:
            try:
                payload["ano"] = int(data["ano"])
            except ValueError:
                payload["ano"] = str(data["ano"]).strip()
        if "amt" in data and data["amt"] is not None:
            try:
                payload["amt"] = float(data["amt"])
            except ValueError:
                pass
        if "payment_date" in data and data["payment_date"]:
            payload["payment_date"] = str(data["payment_date"]).strip()
            payload["pdt"] = str(data["payment_date"]).strip()
        if "pdt" in data and data["pdt"]:
            payload["pdt"] = str(data["pdt"]).strip()
            payload["payment_date"] = str(data["pdt"]).strip()
        if "payment_type" in data and data["payment_type"]:
            payload["payment_type"] = str(data["payment_type"]).strip()

        cur.execute("""
            UPDATE payment_feed_items
            SET payload = %s
            WHERE feed_payment_id = %s
        """, (json.dumps(payload), feed_payment_id))

        if local_uuid:
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
            existing_edit = cur.fetchone()

            if existing_edit:
                cur.execute("""
                    UPDATE payment_feed_edits
                    SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                    WHERE local_uuid = %s
                """, (json.dumps(payload), local_uuid))
            else:
                cur.execute("""
                    INSERT INTO payment_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', NOW())
                """, (local_uuid, json.dumps(payload), payload.get("eid"), payload.get("vid")))

        # Check customer mapping with updated ano and vid
        customer_mapped = False
        cid = None
        customer_name = None
        chk_vid = payload.get("vid") or session.get("vid")
        chk_ano = payload.get("ano")
        if chk_vid and chk_ano is not None:
            try:
                cur.execute("""
                    SELECT cid, name
                    FROM customer
                    WHERE vid = %s AND ano = %s
                    LIMIT 1
                """, (chk_vid, int(chk_ano)))
                cust_row = cur.fetchone()
                if cust_row:
                    customer_mapped = True
                    cid = cust_row[0]
                    customer_name = cust_row[1]
            except Exception:
                pass

        conn.commit()

        if local_uuid:
            p_vid = payload.get("vid") or session.get("vid")
            p_ano = payload.get("ano")
            _call_broadcast(p_vid, {
                "type": "status_update",
                "feed_type": "payment",
                "local_uuid": local_uuid,
                "ano": p_ano,
                "vid": p_vid,
                "status": "rejected_edit",
                "edited_payload": payload
            })

        return jsonify({
            "success": True,
            "mapped": customer_mapped,
            "cid": cid,
            "customer_name": customer_name
        })

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing payment feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/existing-docs/delete/<docs_feed_id>")
@login_required
def delete_existing_customer_docs(docs_feed_id):
    conn = None
    cur = None
    try:
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM customer_docs_feed WHERE docs_feed_id = %s RETURNING docs_feed_id", (docs_feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Pending docs feed item not found"}), 404

        conn.commit()
        _call_audit_log(
            action="delete_existing_customer_docs",
            entity_type="customer_docs_feed",
            entity_id=docs_feed_id,
            details={"deleted_by": session.get("employee_id") or session.get("eid")}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting docs feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/payment/delete/<feed_payment_id>")
@login_required
def delete_payment_feed(feed_payment_id):
    conn = None
    cur = None
    try:
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        cur.execute("SELECT local_uuid, payload, status FROM payment_feed_items WHERE feed_payment_id = %s FOR UPDATE", (feed_payment_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Payment feed item not found"}), 404

        local_uuid, payload_raw, feed_status = row
        if feed_status != "pending":
            return jsonify({"success": False, "error": f"Cannot delete payment feed item that has already been {feed_status}"}), 400

        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        p_ano = payload.get("ano")
        p_vid = payload.get("vid") or session.get("vid")
        p_eid = payload.get("eid")
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        if local_uuid:
            ensure_feed_tables_exist(cur)
            cur.execute("""
                INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                VALUES ('payment', %s, %s, %s, %s, 'rejected_deleted', %s)
            """, (local_uuid, p_ano, p_vid, p_eid, logged_user))

        cur.execute("DELETE FROM payment_feed_items WHERE feed_payment_id = %s", (feed_payment_id,))
        if local_uuid:
            try:
                cur.execute("DELETE FROM payment_feed_edits WHERE local_uuid = %s", (local_uuid,))
            except Exception:
                pass

        conn.commit()

        if local_uuid:
            _call_broadcast(p_vid, {
                "type": "status_update",
                "feed_type": "payment",
                "local_uuid": local_uuid,
                "ano": p_ano,
                "vid": p_vid,
                "status": "rejected_deleted"
            })

        _call_audit_log(
            action="delete_payment_feed",
            entity_type="payment_feed",
            entity_id=feed_payment_id,
            details={"deleted_by": logged_user}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting payment feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@feed_bp.post("/feed/payment/delete_batch")
@login_required
def delete_payment_batch():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    try:
        ids = [int(i) for i in ids]
    except Exception:
        return jsonify({"success": False, "error": "Invalid IDs format"}), 400

    if not ids:
        return jsonify({"success": False, "error": "No payments selected"}), 400

    conn = None
    cur = None
    try:
        conn = get_resolved_pg_conn()
        cur = conn.cursor()

        # Find items and local_uuids
        cur.execute("SELECT feed_payment_id, local_uuid, payload FROM payment_feed_items WHERE feed_payment_id = ANY(%s::bigint[])", (ids,))
        rows = cur.fetchall()
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        batch_events = []
        if rows:
            ensure_feed_tables_exist(cur)
        for f_id, lu, pl_raw in rows:
            pl = pl_raw
            if isinstance(pl, str):
                try:
                    pl = json.loads(pl)
                except Exception:
                    pl = {}
            if not isinstance(pl, dict):
                pl = {}
            b_ano = pl.get("ano")
            b_vid = pl.get("vid") or session.get("vid")
            b_eid = pl.get("eid")
            if lu:
                cur.execute("""
                    INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                    VALUES ('payment', %s, %s, %s, %s, 'rejected_deleted', %s)
                """, (lu, b_ano, b_vid, b_eid, logged_user))
                batch_events.append((b_vid, {
                    "type": "status_update",
                    "feed_type": "payment",
                    "local_uuid": lu,
                    "ano": b_ano,
                    "vid": b_vid,
                    "status": "rejected_deleted"
                }))

        local_uuids = [r[1] for r in rows if r[1]]
        cur.execute("DELETE FROM payment_feed_items WHERE feed_payment_id = ANY(%s::bigint[])", (ids,))
        if local_uuids:
            try:
                cur.execute("DELETE FROM payment_feed_edits WHERE local_uuid = ANY(%s)", (local_uuids,))
            except Exception:
                pass

        conn.commit()

        for b_vid, evt in batch_events:
            _call_broadcast(b_vid, evt)

        _call_audit_log(
            action="delete_payment_batch",
            entity_type="payment_feed",
            entity_id=None,
            details={
                "deleted_by": logged_user,
                "count": len(ids),
                "ids": ids
            }
        )
        return jsonify({"success": True, "count": len(ids)})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error batch deleting payment feed items: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()




@feed_bp.post("/feed/payment/accept/<feed_payment_id>")
@login_required
def accept_payment(feed_payment_id):
    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    logged_user = session.get("employee_id")
    if not logged_user:
        cur.close()
        conn.close()
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT local_uuid, payload, status
        FROM payment_feed_items
        WHERE feed_payment_id = %s
        FOR UPDATE
    """, (feed_payment_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Feed payment not found"}

    local_uuid = row[0]
    data = row[1]
    feed_status = row[2]

    if feed_status != "pending":
        cur.close()
        conn.close()
        return {"success": False, "error": f"Payment feed item has already been {feed_status}"}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid payload format"}

    ensure_feed_tables_exist(cur)

    # Merge pending edit if any
    if local_uuid:
        cur.execute("""
            SELECT edited_payload
            FROM payment_feed_edits
            WHERE local_uuid = %s AND edit_status = 'pending'
            LIMIT 1
        """, (local_uuid,))
        edit_row = cur.fetchone()
        if edit_row:
            ep = edit_row[0]
            if isinstance(ep, str):
                try:
                    ep = json.loads(ep)
                except Exception:
                    ep = {}
            data = merge_edit_payload(data, ep)

    try:
        data = normalize_mobile_payment_payload(data)
    except ValueError as exc:
        cur.close()
        conn.close()
        return {"success": False, "error": str(exc)}

    ano = data.get("ano")
    vid = data.get("vid")
    eid = data.get("eid")
    if ano is None or vid is None or eid is None:
        cur.close()
        conn.close()
        return {"success": False, "error": "Missing account number, village ID, or employee ID in payment payload"}

    amt = Decimal(str(data.get("amt", 0)))
    if amt <= 0:
        cur.close()
        conn.close()
        return {"success": False, "error": "Payment amount must be greater than 0"}

    try:
        raw_pdt = str(data.get("payment_date") or data.get("pdate"))[:10]
        payment_date = datetime.fromisoformat(raw_pdt).date()
    except Exception:
        cur.close()
        conn.close()
        return {"success": False, "error": "Invalid payment date format"}

    payment_type = data.get("payment_type", "cash")
    cash_amount = Decimal(str(data.get("cash_amount", 0)))
    upi_amount = Decimal(str(data.get("upi_amount", 0)))

    # Fetch customer from DB for this village
    cur.execute("""
        SELECT cid, total_amount, start_date
        FROM customer
        WHERE ano = %s AND vid = %s
    """, (ano, vid))
    cust = cur.fetchone()

    if not cust:
        cur.close()
        conn.close()
        return {
            "success": False,
            "error": f"Customer Account #{ano} not found in database for this village! Please approve the new customer registration first."
        }

    cid, total_amt, start_date = cust

    # Validate payment_date >= start_date
    if start_date and payment_date < start_date:
        cur.close()
        conn.close()
        return {
            "success": False,
            "error": f"Customer Account #{ano} start date is {format_date_display(str(start_date))}. Payment date ({format_date_display(str(payment_date))}) cannot be earlier than start date."
        }

    # Duplicate check in payment table
    cur.execute("""
        SELECT COUNT(*) FROM payment
        WHERE ano = %s AND vid = %s AND payment_date = %s
    """, (ano, vid, payment_date))
    if cur.fetchone()[0] > 0:
        cur.close()
        conn.close()
        return {
            "success": False,
            "error": f"Duplicate payment already recorded in database for Account #{ano} on {format_date_display(str(payment_date))}."
        }

    # Insert payment
    cur.execute("""
        INSERT INTO payment
        (cid, vid, eid, ano, amt, payment_date, payment_type, cash_amount, upi_amount)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        cid,
        vid,
        eid,
        ano,
        amt,
        payment_date,
        payment_type,
        cash_amount,
        upi_amount
    ))

    # Recalculate balance
    _call_recalc_balance(cur, cid)

    # Mark edit as accepted
    if local_uuid:
        cur.execute("""
            UPDATE payment_feed_edits
            SET edit_status = 'accepted'
            WHERE local_uuid = %s AND edit_status = 'pending'
        """, (local_uuid,))

    # Mark feed item as accepted
    cur.execute("""
        UPDATE payment_feed_items
        SET status='accepted',
            review_by = %s,
            review_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE feed_payment_id = %s
    """, (logged_user, feed_payment_id))

    # Invalidate cache for this village
    _call_invalidate_cache(cur, vid, payment_date)

    conn.commit()
    if local_uuid:
        _call_broadcast(vid, {
            "type": "status_update",
            "feed_type": "payment",
            "local_uuid": local_uuid,
            "ano": ano,
            "vid": vid,
            "status": "accepted"
        })
    _call_audit_log(
        action="accept_payment_feed",
        entity_type="payment_feed",
        entity_id=feed_payment_id,
        details={
            "ano": ano,
            "vid": vid,
            "eid": eid,
            "amt": str(amt),
            "reviewed_by": logged_user
        }
    )
    cur.close()
    conn.close()

    return {"success": True}


# ----------- Batch accept payments -----------
@feed_bp.post("/feed/payment/accept_batch")
@login_required
def accept_payment_batch():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    try:
        ids = [int(i) for i in ids]
    except Exception:
        return {"success": False, "error": "Invalid IDs format"}

    if not ids:
        return {"success": False, "error": "No payments selected"}

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    logged_user = session.get("employee_id")
    if not logged_user:
        cur.close()
        conn.close()
        return {"success": False, "error": "User not logged properly"}

    try:
        ensure_feed_tables_exist(cur)

        # 1. Fetch selected items with their specific feed_payment_id
        cur.execute("""
            SELECT feed_payment_id, local_uuid, payload, status
            FROM payment_feed_items
            WHERE feed_payment_id = ANY(%s::bigint[])
            FOR UPDATE
        """, (ids,))
        all_rows = cur.fetchall()
        rows = [r for r in all_rows if r[3] == 'pending']

        if not rows:
            cur.close()
            conn.close()
            return {"success": False, "error": "No pending payments found in queue"}

        # Fetch pending edits if any for these local_uuids
        local_uuids = [r[1] for r in rows if r[1]]
        payment_edit_map = {}
        if local_uuids:
            cur.execute("""
                SELECT local_uuid, edited_payload
                FROM payment_feed_edits
                WHERE local_uuid = ANY(%s) AND edit_status = 'pending'
            """, (local_uuids,))
            for edit_row in cur.fetchall():
                ep = edit_row[1]
                if isinstance(ep, str):
                    try:
                        ep = json.loads(ep)
                    except Exception:
                        ep = {}
                payment_edit_map[edit_row[0]] = ep

        # 2. Prefetch customers for all unique (vid, ano) pairs
        session_vid = session.get("vid")
        village_ano_pairs = set()
        for r in rows:
            l_uuid = r[1]
            p_data = r[2]
            if isinstance(p_data, str):
                try:
                    p_data = json.loads(p_data)
                except Exception:
                    p_data = {}
            if l_uuid and l_uuid in payment_edit_map:
                p_data = merge_edit_payload(p_data, payment_edit_map[l_uuid])
            p_vid = p_data.get("vid") or session_vid
            a_val = p_data.get("ano")
            if p_vid is not None and a_val is not None:
                try:
                    village_ano_pairs.add((int(p_vid), int(a_val)))
                except (ValueError, TypeError):
                    pass

        customer_map = {}
        if village_ano_pairs:
            pair_list = list(village_ano_pairs)
            placeholders = ", ".join(["(%s, %s)"] * len(pair_list))
            flat_params = [item for pair in pair_list for item in pair]
            cur.execute(f"""
                SELECT cid, vid, ano, total_amount, paid_amount, balance_amount, start_date
                FROM customer
                WHERE (vid, ano) IN ({placeholders})
            """, flat_params)
            for crow in cur.fetchall():
                c_cid, c_vid, c_ano, c_tot, c_paid, c_bal, c_sdate = crow
                customer_map[(int(c_vid), int(c_ano))] = {
                    "cid": c_cid,
                    "vid": int(c_vid),
                    "ano": int(c_ano),
                    "total_amount": c_tot,
                    "paid_amount": c_paid,
                    "balance_amount": c_bal,
                    "start_date": c_sdate
                }

        insert_values = []
        successful_feed_ids = []
        successful_local_uuids = []
        successful_uuid_vid_pairs = []
        affected_cids = set()
        failed_items = []
        seen_in_batch = set()

        for r in rows:
            f_id = r[0]
            l_uuid = r[1]
            p = r[2]
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except Exception:
                    failed_items.append({
                        "feed_payment_id": f_id,
                        "ano": "?",
                        "reason": "Invalid payload format"
                    })
                    continue

            if l_uuid and l_uuid in payment_edit_map:
                p = merge_edit_payload(p, payment_edit_map[l_uuid])

            try:
                p = normalize_mobile_payment_payload(p)
            except Exception as exc:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": str(p.get("ano", "?")),
                    "reason": f"Payload error: {str(exc)}"
                })
                continue

            ano_raw = p.get("ano")
            vid_val = p.get("vid") or session_vid
            eid_val = p.get("eid")
            if ano_raw is None or vid_val is None or eid_val is None:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": str(ano_raw or "?"),
                    "reason": "Missing account number, village ID, or employee ID"
                })
                continue

            try:
                ano_int = int(ano_raw)
            except Exception:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": str(ano_raw),
                    "reason": "Account number must be numeric"
                })
                continue

            try:
                vid_val = int(vid_val)
            except Exception:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": "Village ID must be numeric"
                })
                continue

            amt = to_decimal(p.get("amt", 0))

            if amt <= 0:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Payment amount must be greater than 0"
                })
                continue

            try:
                raw_pdt = str(p.get("payment_date") or p.get("pdate"))[:10]
                payment_date = datetime.fromisoformat(raw_pdt).date()
            except Exception:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Invalid payment date"
                })
                continue

            # Check 1: Customer existence in database for this village
            customer = customer_map.get((vid_val, ano_int))
            if not customer:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Customer not found in database for Village {vid_val}. Please approve new customer registration first."
                })
                continue

            cid = customer["cid"]
            cust_start = customer.get("start_date")

            # Check 2: Payment date >= Customer start date
            if cust_start and payment_date < cust_start:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Payment date ({format_date_display(str(payment_date))}) cannot be earlier than customer start date ({format_date_display(str(cust_start))})."
                })
                continue

            # Check 3: Intra-batch duplicate check (keyed by (vid, ano, payment_date))
            batch_pair = (vid_val, ano_int, str(payment_date))
            if batch_pair in seen_in_batch:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Multiple payments for date {format_date_display(str(payment_date))} in the same selection."
                })
                continue
            seen_in_batch.add(batch_pair)

            # Check 4: Database duplicate check
            cur.execute("""
                SELECT COUNT(*) FROM payment
                WHERE ano = %s AND vid = %s AND payment_date = %s
            """, (ano_int, vid_val, payment_date))
            if cur.fetchone()[0] > 0:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Duplicate payment already recorded in database on {format_date_display(str(payment_date))}."
                })
                continue

            # Check 5: Future date guardrail
            if payment_date and payment_date > (date.today() + timedelta(days=1)):
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Payment date ({format_date_display(str(payment_date))}) cannot be in the future."
                })
                continue

            payment_type = p.get("payment_type", "cash")
            cash_amount = to_decimal(p.get("cash_amount", 0))
            upi_amount = to_decimal(p.get("upi_amount", 0))
            if (cash_amount + upi_amount) != amt:
                if upi_amount > 0 and upi_amount <= amt:
                    cash_amount = amt - upi_amount
                else:
                    cash_amount = amt
                    upi_amount = Decimal("0.00")

            insert_values.append((
                cid,
                vid_val,
                eid_val,
                ano_int,
                amt,
                payment_date,
                payment_type,
                cash_amount,
                upi_amount
            ))
            successful_feed_ids.append(f_id)
            if l_uuid:
                successful_local_uuids.append(l_uuid)
                successful_uuid_vid_pairs.append((l_uuid, vid_val))
            affected_cids.add(cid)

        # 3. If there are valid payments to insert
        if insert_values:
            _call_execute_values(
                cur,
                """
                    INSERT INTO payment (
                        cid,
                        vid,
                        eid,
                        ano,
                        amt,
                        payment_date,
                        payment_type,
                        cash_amount,
                        upi_amount
                    )
                    VALUES %s
                """,
                insert_values,
                template="(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )

            # Recalculate customer balances for affected customers
            for c_id in affected_cids:
                _call_recalc_balance(cur, c_id)

            # ONLY update status for successful payments!
            cur.execute("""
                UPDATE payment_feed_items
                SET status = 'accepted',
                    review_by = %s,
                    review_at = NOW() AT TIME ZONE 'Asia/Kolkata'
                WHERE feed_payment_id = ANY(%s::bigint[])
            """, (logged_user, successful_feed_ids))

            if successful_local_uuids:
                cur.execute("""
                    UPDATE payment_feed_edits
                    SET edit_status = 'accepted'
                    WHERE local_uuid = ANY(%s) AND edit_status = 'pending'
                """, (successful_local_uuids,))

            # Invalidate cache for all affected villages
            affected_villages = {}
            for val in insert_values:
                v_id = val[1]
                p_date = val[5]
                if v_id not in affected_villages or p_date < affected_villages[v_id]:
                    affected_villages[v_id] = p_date

            for v_id, min_date in affected_villages.items():
                _call_invalidate_cache(cur, v_id, min_date)

            _call_audit_log(
                action="accept_payment_batch",
                entity_type="payment_feed",
                entity_id=session_vid or "batch",
                details={
                    "reviewed_by": logged_user,
                    "selected_count": len(ids),
                    "accepted_count": len(successful_feed_ids),
                    "failed_count": len(failed_items),
                    "affected_villages": list(affected_villages.keys())
                },
                cur=cur
            )

            conn.commit()

            if successful_uuid_vid_pairs:
                for lu, v_id in successful_uuid_vid_pairs:
                    _call_broadcast(v_id, {
                        "type": "status_update",
                        "feed_type": "payment",
                        "local_uuid": lu,
                        "vid": v_id,
                        "status": "accepted"
                    })

        cur.close()
        conn.close()

        if successful_feed_ids:
            accepted_sum = float(sum(val[4] for val in insert_values)) if insert_values else 0.0
            return {
                "success": True,
                "accepted_count": len(successful_feed_ids),
                "accepted_sum": accepted_sum,
                "failed_count": len(failed_items),
                "failed_items": failed_items,
                "accepted_ids": successful_feed_ids,
                "message": f"{len(successful_feed_ids)} payments posted successfully." if not failed_items else f"{len(successful_feed_ids)} payments posted. {len(failed_items)} could not be posted."
            }
        else:
            return {
                "success": False,
                "accepted_count": 0,
                "failed_count": len(failed_items),
                "failed_items": failed_items,
                "error": "None of the selected payments could be posted.",
                "message": "None of the selected payments could be posted."
            }

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"success": False, "error": str(e)}



