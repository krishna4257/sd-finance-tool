import json
import logging
import traceback
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz

from flask import Blueprint, render_template, request, jsonify, session, redirect, flash

from db import get_pg_connection
from services.chit_calc_engine import round_curr
from security.auth import login_required
from services.audit_service import audit_log
from services.mobile_service import normalize_account_number
from services.customer_service import (
    parse_date_input,
    format_date_display,
    recalc_customer_balance,
    invalidate_village_health_cache,
)
from services.payment_service import (
    is_village_monthly,
    ttl_cache,
    global_ttl_cache,
)

logger = logging.getLogger(__name__)

payment_bp = Blueprint("payment_bp", __name__)


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


def _call_recalc_balance(*args, **kwargs):
    return _resolve_func("recalc_customer_balance", recalc_customer_balance)(*args, **kwargs)


def _call_invalidate_cache(*args, **kwargs):
    return _resolve_func("invalidate_village_health_cache", invalidate_village_health_cache)(*args, **kwargs)


@payment_bp.route("/api/posting_report", methods=["GET", "QUERY"])
@login_required
@ttl_cache(ttl_seconds=300)
def api_posting_report():
    vid = session.get("vid")

    if not vid:
        return jsonify(success=False, error="Please select Village first"), 400

    if request.method == "QUERY" or request.is_json:
        data = request.get_json(silent=True) or {}
        view = data.get("view", "current")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        ano_val = str(data.get("ano", "")).strip()
    else:
        view = request.args.get("view", "current")
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        ano_val = request.args.get("ano", "").strip()

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:
        conditions = ["p.vid = %s"]
        params = [vid]

        if view == "historic":
            conditions.append("p.record_tier = 'historic'")
        elif view == "current":
            conditions.append("p.record_tier IN ('active', 'closed')")

        if start_date_str:
            try:
                start_date = parse_date_input(start_date_str)
                if start_date:
                    conditions.append("p.payment_date >= %s")
                    params.append(start_date)
            except Exception:
                pass

        if end_date_str:
            try:
                end_date = parse_date_input(end_date_str)
                if end_date:
                    conditions.append("p.payment_date <= %s")
                    params.append(end_date)
            except Exception:
                pass

        if ano_val and ano_val.isdigit():
            conditions.append("p.ano = %s")
            params.append(int(ano_val))

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT
                p.pid,
                p.ano,
                p.payment_date,
                p.amt,
                p.created_at,
                p.eid,
                p.cid,
                p.vid,
                p.record_tier AS payment_status,
                c.name AS customer_name
            FROM v_all_payments p
            LEFT JOIN v_all_customers c ON p.cid = c.cid
            WHERE {where_clause}
            ORDER BY p.payment_date DESC, p.pid DESC
        """
        cur.execute(query, tuple(params))

        rows = cur.fetchall()
        if cur.description:
            headers = [desc[0] for desc in cur.description]
        else:
            headers = ["pid", "ano", "payment_date", "amt", "created_at", "eid", "cid", "vid", "payment_status", "customer_name"]

        payments = []
        for r in rows:
            row_dict = dict(zip(headers, r))
            if row_dict.get("payment_date"):
                row_dict["payment_date"] = row_dict["payment_date"].isoformat()
            if row_dict.get("created_at"):
                row_dict["created_at"] = row_dict["created_at"].isoformat()
            if row_dict.get("amt") is not None:
                row_dict["amt"] = float(row_dict["amt"])
            payments.append(row_dict)

        resp_headers = {
            "Accept-Query": "application/json",
            "Cache-Control": "public, max-age=300"
        }
        return jsonify(success=True, headers=headers, payments=payments), 200, resp_headers

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@payment_bp.route("/posting", methods=["GET"])
@login_required
def posting_page():
    vid = session.get("vid")

    if not vid:
        flash("Please select Village first", "warning")
        return redirect("/dashboard")

    return render_template("post_payment.html", customers=[])

@payment_bp.route("/api/posting/customers", methods=["GET"])
@login_required
def api_posting_customers():
    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="No active village context"), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                cid,
                ano,
                name,
                start_date,
                total_amount,
                paid_amount,
                balance_amount,
                installment_amount
            FROM customer
            WHERE vid = %s AND (status IS NULL OR status != 'closed')
        """, (vid,))

        customers = [
            dict(
                cid=r[0],
                ano=r[1],
                name=r[2],
                start_date=r[3].isoformat() if isinstance(r[3], (date, datetime)) else r[3],
                total_amount=float(r[4]) if r[4] is not None else 0.0,
                paid_amount=float(r[5]) if r[5] is not None else 0.0,
                balance_amount=float(r[6]) if r[6] is not None else 0.0,
                installment_amount=float(r[7]) if r[7] is not None else 0.0,
            )
            for r in cur.fetchall()
        ]
        return jsonify(success=True, customers=customers)
    except Exception as e:
        logger.error(f"Error fetching posting customers: {e}")
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@payment_bp.route("/get_customer_info")
@login_required
def get_customer_info():
    ano = request.args.get("ano")
    vid = session.get("vid")

    if not ano or not vid:
        return jsonify({"error": "Missing context"}), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            cid,
            name,
            total_amount,
            paid_amount,
            balance_amount,
            installment_amount
        FROM customer
        WHERE vid = %s AND ano = %s
    """, (vid, ano))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Account number not found"})

    return jsonify({
        "cid": row[0],
        "name": row[1],
        "loan_amount": row[2],
        "total_repaid": row[3],
        "outstanding": row[4],
        "installment_amount": row[5],
    })

@payment_bp.route("/api/payment_day_stats")
@login_required
def payment_day_stats():

    vid = session.get("vid")

    if not vid:
        return jsonify({"error": "Missing village context"}), 400

    date_str = request.args.get("date")

    if not date_str:
        return jsonify({"error": "Missing date"}), 400

    try:
        payment_date = parse_date_input(date_str)
        if not payment_date:
            raise ValueError("bad date")
    except Exception:
        return jsonify({"error": "Invalid date"}), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:

        is_monthly = is_village_monthly(vid, cur)

        if is_monthly:
            cur.execute("""
                WITH eligible_customers AS (
                    SELECT
                        COUNT(*) AS expected_accounts
                    FROM v_all_customers c
                    WHERE c.vid = %s
                      AND (c.closed_at IS NULL OR c.closed_at::date > %s::date)
                      AND c.start_date <= %s::date
                ),
                actual_payments AS (
                    SELECT
                        COUNT(DISTINCT ano) AS paid_accounts
                    FROM v_all_payments all_p
                    WHERE vid = %s
                      AND payment_date = %s
                )
                SELECT
                    COALESCE(ec.expected_accounts, 0)
                        AS expected_accounts,
                    COALESCE(ap.paid_accounts, 0)
                        AS already_paid
                FROM eligible_customers ec
                CROSS JOIN actual_payments ap
            """, (
                vid,
                payment_date,
                payment_date,
                vid,
                payment_date
            ))
        else:
            cur.execute("""
                WITH village_collection_day AS (
                    SELECT DISTINCT ON (p.vid)
                        p.vid,
                        TRIM(TO_CHAR(p.payment_date, 'Day'))
                            AS collection_day,
                        COUNT(*) AS payment_count
                    FROM v_all_payments p
                    WHERE p.vid = %s
                    GROUP BY
                        p.vid,
                        collection_day
                    ORDER BY
                        p.vid,
                        payment_count DESC
                ),
                eligible_customers AS (
                    SELECT
                        COUNT(*) AS expected_accounts
                    FROM v_all_customers c
                    JOIN village_collection_day vcd
                        ON vcd.vid = c.vid
                    WHERE c.vid = %s
                      AND c.type = 'W'
                      AND (c.closed_at IS NULL OR c.closed_at::date > %s::date)
                      AND (
                            c.start_date + INTERVAL '7 days'
                          )::date <= %s
                      AND TRIM(TO_CHAR(%s::date, 'Day'))
                          = vcd.collection_day
                ),
                actual_payments AS (
                    SELECT
                        COUNT(DISTINCT ano) AS paid_accounts
                    FROM v_all_payments all_p
                    WHERE vid = %s
                      AND payment_date = %s
                )
                SELECT
                    COALESCE(ec.expected_accounts, 0)
                        AS expected_accounts,
                    COALESCE(ap.paid_accounts, 0)
                        AS already_paid
                FROM eligible_customers ec
                CROSS JOIN actual_payments ap
            """, (
                vid,
                vid,
                payment_date,
                payment_date,
                payment_date,
                vid,
                payment_date
            ))

        row = cur.fetchone()

        expected_accounts = int(row[0] or 0) if row else 0
        already_paid = int(row[1] or 0) if row else 0

        return jsonify({
            "expected_accounts": expected_accounts,
            "already_paid": already_paid
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@payment_bp.route("/api/post_payment_analytics", methods=["GET"])
@login_required
def post_payment_analytics():
    KOLKATA = pytz.timezone('Asia/Kolkata')
    vid = session.get("vid")
    if not vid:
        return jsonify(error="Village context not set"), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:
        # 1. Get last posting date for the village
        cur.execute("""
            SELECT MAX(payment_date) FROM payment WHERE vid = %s
        """, (vid,))
        last_date = cur.fetchone()[0]

        if not last_date:
            last_date = datetime.today().date()
            last_date_str = format_date_display(last_date) + " (No postings yet)" # type: ignore
        else:
            days_ago = (datetime.now(KOLKATA).date() - last_date).days
            last_date_str = format_date_display(last_date) + f" ({days_ago} days ago)" # type: ignore

        # 2. Get all active or historically active customers for this village (both open and closed)
        cur.execute("""
            SELECT cid, ano, name, total_amount, installment_amount, start_date, closed_at
            FROM v_all_customers
            WHERE vid = %s
        """, (vid,))
        customers = []
        for r in cur.fetchall():
            customers.append({
                "cid": r[0],
                "ano": r[1],
                "name": r[2],
                "total_amount": float(r[3] or 0),
                "installment_amount": float(r[4] or 0),
                "start_date": r[5],
                "closed_at": r[6]
            })

        # 3. Get all payments (both active and closed) for this village
        cur.execute("""
            SELECT cid, amt, payment_date
            FROM v_all_payments
            WHERE vid = %s
        """, (vid,))
        payments = []
        payments_by_cid = {}
        for r in cur.fetchall():
            p = {
                "cid": r[0],
                "amt": float(r[1] or 0),
                "payment_date": r[2]
            }
            payments.append(p)
            
            cid = p["cid"]
            if cid not in payments_by_cid:
                payments_by_cid[cid] = []
            payments_by_cid[cid].append(p)

        is_monthly = is_village_monthly(vid, cur)

        if is_monthly:
            cur.execute("""
                SELECT DISTINCT payment_date 
                FROM v_all_payments
                WHERE vid = %s AND payment_date IS NOT NULL
                ORDER BY payment_date DESC
            """, (vid,))
            posting_dates = [r[0] for r in cur.fetchall()]
            target_dates = list(reversed(posting_dates[:5])) if posting_dates else [last_date]
            
            weeks = []
            for idx, p_dt in enumerate(target_dates):
                active_c = [
                    c for c in customers
                    if c["start_date"] and c["start_date"] <= p_dt
                    and (not c["closed_at"] or (c["closed_at"].date() if isinstance(c["closed_at"], datetime) else c["closed_at"]) > p_dt)
                ]
                expected = sum(c["installment_amount"] for c in active_c)
                
                pmts_at_dt = [p for p in payments if p["payment_date"] == p_dt]
                actual = sum(p["amt"] for p in pmts_at_dt)
                paying_cids = {p["cid"] for p in pmts_at_dt}
                
                paid_cnt = len(paying_cids)
                active_cnt = len(active_c)
                unpaid_cnt = max(0, active_cnt - paid_cnt)
                failed = max(0.0, expected - actual)
                
                offset = len(target_dates) - 1 - idx
                label = "This Month" if offset == 0 else (f"{offset} Mos Ago" if offset > 1 else "1 Mo Ago")
                
                weeks.append({
                    "label": label,
                    "start": p_dt,
                    "end": p_dt,
                    "active_customers": active_cnt,
                    "paid_customers": paid_cnt,
                    "unpaid_customers": unpaid_cnt,
                    "expected_collection": expected,
                    "actual_collection": actual,
                    "failed_to_collect": failed
                })
        else:
            # Calculate weeks: We generate 5 weeks ending at last_date
            # Week 0: [last_date - 6, last_date]
            # Week 1: [last_date - 13, last_date - 7]
            # Week 2: [last_date - 20, last_date - 14]
            # Week 3: [last_date - 27, last_date - 21]
            # Week 4: [last_date - 34, last_date - 28]
            weeks = []
            for i in range(4, -1, -1):
                w_end = last_date - timedelta(days=7 * i)
                w_start = w_end - timedelta(days=6)
                
                label = "This Week" if i == 0 else f"{i} Wk{'s' if i > 1 else ''} Ago"
                
                weeks.append({
                    "label": label,
                    "start": w_start,
                    "end": w_end,
                    "active_customers": 0,
                    "paid_customers": 0,
                    "unpaid_customers": 0,
                    "expected_collection": 0.0,
                    "actual_collection": 0.0,
                    "failed_to_collect": 0.0
                })

            for w in weeks:
                start_dt = w["start"]
                end_dt = w["end"]
                
                for c in customers:
                    # Check if customer loan started on or before the end of the week
                    if c["start_date"] and c["start_date"] <= end_dt:
                        # If customer was closed before start_dt, they are not active in this week
                        if c["closed_at"]:
                            cl_dt = c["closed_at"].date() if isinstance(c["closed_at"], datetime) else c["closed_at"]
                            if cl_dt < start_dt:
                                continue
                        cust_payments = payments_by_cid.get(c["cid"], [])
                        # Calculate total paid before this week
                        paid_before = sum(p["amt"] for p in cust_payments if p["payment_date"] < start_dt)
                        
                        # If loan balance at start of week was greater than 0, they were active
                        if c["total_amount"] - paid_before > 0.01:
                            w["active_customers"] += 1
                            w["expected_collection"] += c["installment_amount"]
                            
                            # Calculate paid during this week
                            paid_this_week = sum(p["amt"] for p in cust_payments if start_dt <= p["payment_date"] <= end_dt)
                            
                            if paid_this_week > 0.01:
                                w["paid_customers"] += 1
                                w["actual_collection"] += paid_this_week
                            else:
                                w["unpaid_customers"] += 1
                                w["failed_to_collect"] += c["installment_amount"]

        # Format and round data
        for w in weeks:
            w["expected_collection"] = round_curr(w["expected_collection"])
            w["actual_collection"] = round_curr(w["actual_collection"])
            w["failed_to_collect"] = round_curr(w["failed_to_collect"])
            w["start"] = format_date_display(w["start"])
            w["end"] = format_date_display(w["end"])

        return jsonify(
            last_posting_date=last_date_str,
            weeks=weeks,
            is_monthly=is_monthly
        )

    except Exception as e:
        logger.error(f"Error calculating post payment analytics: {e}")
        return jsonify(error="Internal server error"), 500
    finally:
        cur.close()
        conn.close()



# ----------------------------------------------------
# BULK LEDGER OCR EXTRACTION (GEMINI AI)
# ----------------------------------------------------
LEDGER_OCR_PROMPT = """You are an OCR extraction engine.
Your task is to extract handwritten ledger data from the attached images with maximum accuracy.
Do NOT summarize, explain, calculate totals, or reformat beyond what is requested.

Image Structure
Each image represents one page.
Each page contains three independent vertical sections (columns).
Each section contains rows.
Every row contains:
Account Number (left side of that section)
Amount (right side of that section)
Treat every section independently.
Read rows top to bottom.
Read sections left → middle → right.
When moving to the next image, start a new page.

Extraction Rules
For every row output exactly:
(AccountNumber,Amount)
Examples:
(1,500)
(25,1000)
(94,700)

Important Rules
1. Never skip rows
Every account number that appears in the image must appear exactly once in the output.

2. If amount is a dash
If the amount field contains only a dash, blank dash, horizontal line, or intentionally empty value, output
(account,-)
Example
Image:
24    —
Output
(24,-)

3. If the amount is unreadable
If you are less than 95% confident about the handwritten amount,
DO NOT guess.
Output
(account,N)
Examples
(15,N)
(43,N)
Never invent numbers.

4. If the account number is unreadable
If the account number itself cannot be read with at least 95% confidence,
skip that row completely.
Do not invent account numbers.

5. Preserve values exactly
Do not:
round numbers
correct handwriting
infer missing digits
calculate missing values
Only transcribe what is actually written.

6. Ignore everything except ledger rows
Ignore:
titles
dates
totals
page totals
notes
signatures
scribbles
headings
Only extract account-number/amount pairs.

7. Do NOT output totals
Ignore every total written at the bottom.
Never calculate totals.
Never mention totals.

Output Format
Separate every page.
Separate every section with one blank line.
Example:
Page 1

(1,500), (2,500), (3,300), (4,200), (5,200)

(21,400), (22,10000), (23,100), (24,-), (25,100)

(41,300), (42,100), (43,N), (44,100), (45,-)


Page 2

(61,150), (62,100), (63,200), (64,100)

(81,100), (82,500), (83,500), (84,100)

Accuracy Policy
Before producing the final output, verify:
Every section has been processed.
Rows are in the correct order.
No account numbers are duplicated.
No rows are skipped.
Every unreadable amount is replaced with N.
Every dash remains -.
No totals appear.
No explanations appear.
Output contains only the requested pairs.
Return nothing except the formatted extraction."""




@payment_bp.route("/submit_post_payment", methods=["POST"])
@login_required
def submit_post_payment():
    vid = session.get("vid")
    eid = session.get("eid") or session.get("employee_id")

    if not vid:
        return jsonify(error="Context not set"), 400

    rows = request.get_json()
    if not rows:
        return jsonify(error="No data received"), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    if not eid:
        try:
            cur.execute("SELECT emp1 FROM village WHERE vid = %s", (vid,))
            v_emp = cur.fetchone()
            if v_emp and v_emp[0]:
                eid = v_emp[0]
        except Exception:
            pass

    submitted = 0
    skipped = []
    seen_in_batch = set()

    try:
        for row in rows:
            ano = normalize_account_number(row.get("ano"))
            if ano is None:
                skipped.append({**row, "reason": "Invalid or missing account number"})
                continue

            try:
                amt = Decimal(str(row.get("amt", 0)))
            except Exception:
                amt = Decimal(0)
            if amt <= 0:
                skipped.append({**row, "reason": f"Account #{ano}: Payment amount must be greater than 0"})
                continue

            payment_date = parse_date_input(row.get("pdt"))
            if not payment_date:
                skipped.append({**row, "reason": f"Account #{ano}: Invalid payment date '{row.get('pdt')}'"})
                continue

            # 🔹 Fetch customer
            cur.execute("""
                SELECT cid, total_amount, paid_amount, start_date
                FROM customer
                WHERE vid = %s AND ano = %s
            """, (vid, ano))

            cust = cur.fetchone()
            if not cust:
                skipped.append({**row, "reason": f"Account #{ano} not found in database for this village"})
                continue

            cid, total_amt, paid_amt, cust_start_date = cust

            # Validate payment_date >= start_date
            if cust_start_date and payment_date < cust_start_date:
                skipped.append({
                    **row,
                    "reason": f"Account #{ano}: Payment date ({format_date_display(str(payment_date))}) cannot be earlier than start date ({format_date_display(str(cust_start_date))})"
                })
                continue

            # 🔹 Intra-batch duplicate check
            batch_key = (ano, str(payment_date))
            if batch_key in seen_in_batch:
                skipped.append({
                    **row,
                    "reason": f"Account #{ano}: Multiple payments for date {format_date_display(str(payment_date))} in the same submission"
                })
                continue
            seen_in_batch.add(batch_key)

            # 🔹 Database duplicate check (prevent duplicate payment for same customer on same date)
            cur.execute("""
                SELECT pid, amt FROM payment
                WHERE vid = %s AND ano = %s AND payment_date = %s
                LIMIT 1
            """, (vid, ano, payment_date))
            existing = cur.fetchone()
            if existing:
                skipped.append({
                    **row,
                    "reason": f"Account #{ano}: Payment already recorded on {format_date_display(str(payment_date))} (Amount: ₹{existing[1]})"
                })
                continue

            total_amt = Decimal(total_amt)
            paid_amt = Decimal(paid_amt or 0)

            payment_type = str(row.get("payment_type") or "cash").lower()
            if payment_type not in ("cash", "upi", "partial", "mixed"):
                payment_type = "cash"
            cash_amount = Decimal(str(row.get("cash_amount", amt if payment_type == "cash" else 0)))
            upi_amount = Decimal(str(row.get("upi_amount", amt if payment_type == "upi" else 0)))
            if (cash_amount + upi_amount) != amt:
                if upi_amount > 0 and upi_amount <= amt:
                    cash_amount = amt - upi_amount
                else:
                    cash_amount = amt
                    upi_amount = Decimal("0.00")

            # 🔹 Insert payment (pid auto-generated)
            cur.execute("""
                INSERT INTO payment (cid, vid, eid, ano, amt, payment_date, payment_type, cash_amount, upi_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (cid, vid, eid, ano, amt, payment_date, payment_type, cash_amount, upi_amount))

            # 🔹 Recalculate balances (centralized logic)
            _call_recalc_balance(cur, cid)

            submitted += 1

        # Invalidate cache for this village
        min_pdt = None
        for r in rows:
            try:
                pdt = parse_date_input(r["pdt"])
                if not min_pdt or pdt < min_pdt:# type: ignore
                    min_pdt = pdt
            except Exception:
                pass
        _call_invalidate_cache(cur, vid, min_pdt)

        global_ttl_cache.clear()
        conn.commit()

        _call_audit_log(
            action="submit_post_payment",
            entity_type="payment",
            entity_id=vid,
            details={
                "eid": eid,
                "vid": vid,
                "submitted_count": submitted,
                "skipped_count": len(skipped),
                "skipped_reasons": [s.get("reason") for s in skipped] if skipped else []
            }
        )

        return jsonify( 
            success=True,
            message=f"{submitted} payment(s) posted" + (f", {len(skipped)} skipped" if skipped else ""),
            submitted_count=submitted,
            skipped_count=len(skipped),
            skipped_rows=skipped
        )

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(error=str(e)), 500

    finally:
        cur.close()
        conn.close()





@payment_bp.route("/api/payment/update_record_pg", methods=["POST"])
@login_required
def update_payment_record_pg():
    payload = request.get_json()
    if not payload:
        return jsonify(success=False, error="Missing payload"), 400

    data = payload.get("data")
    if not data:
        return jsonify(success=False, error="Missing data"), 400

    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="Context not set"), 400

    pid = data.get("pid")
    ano = data.get("ano")
    amt = Decimal(str(data.get("amt")))
    
    # Parse payment date
    pdt_str = data.get("payment_date")
    try:
        pdt = parse_date_input(pdt_str)
        if not pdt:
            raise ValueError("bad date")
    except (ValueError, TypeError):
        return jsonify(success=False, error="Invalid date format. Use DD-MM-YYYY or YYYY-MM-DD."), 400

    if not pid or not ano or amt is None:
        return jsonify(success=False, error="Missing required fields"), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:
        # 1. Fetch current payment details
        cur.execute("SELECT cid, ano, vid, payment_date FROM payment WHERE pid = %s", (pid,))
        payment_row = cur.fetchone()
        is_active = True
        is_historic = False
        if not payment_row:
            cur.execute("SELECT cid, ano, vid, payment_date FROM closed_cust_payment WHERE pid = %s", (pid,))
            payment_row = cur.fetchone()
            is_active = False
        if not payment_row:
            cur.execute("SELECT cid, ano, vid, payment_date FROM historic_payment_data WHERE pid = %s", (pid,))
            payment_row = cur.fetchone()
            is_historic = True

        if not payment_row:
            return jsonify(success=False, error="Payment record not found"), 404

        old_cid, old_ano, p_vid, old_pdt = payment_row
        if p_vid != vid:
            return jsonify(success=False, error="Access denied: Different village context"), 403

        if is_historic:
            table_payment = "historic_payment_data"
            table_customer = "historic_customer_data"
            amount_col = "amount"
        else:
            table_payment = "payment" if is_active else "closed_cust_payment"
            table_customer = "customer" if is_active else "closed_cust_account"
            amount_col = "amt"

        # 2. If ano is changing, we must fetch the new customer's cid
        new_cid = old_cid
        if int(ano) != int(old_ano):
            cur.execute(f"SELECT cid FROM {table_customer} WHERE vid = %s AND ano = %s", (vid, ano))
            cust_row = cur.fetchone()
            if not cust_row:
                return jsonify(success=False, error=f"Customer with Account Number {ano} not found in this village"), 404
            new_cid = cust_row[0]

        # Check for duplicate payment date for this customer (another payment on same date)
        cur.execute(f"""
            SELECT pid, {amount_col} FROM {table_payment}
            WHERE vid = %s AND ano = %s AND payment_date = %s AND pid != %s
            LIMIT 1
        """, (vid, ano, pdt, pid))
        dup = cur.fetchone()
        if dup:
            return jsonify(
                success=False,
                error=f"A payment for Account #{ano} already exists on {format_date_display(str(pdt))} (Amount: ₹{dup[1]}). Only one payment per date is allowed."
            ), 400

        # 3. Update the payment record
        if is_historic:
            cur.execute("""
                UPDATE historic_payment_data
                SET ano = %s,
                    cid = %s,
                    payment_date = %s,
                    amount = %s
                WHERE pid = %s
            """, (ano, new_cid, pdt, amt, pid))
        else:
            cur.execute(f"""
                UPDATE {table_payment}
                SET ano = %s,
                    cid = %s,
                    payment_date = %s,
                    amt = %s,
                    updated_at = NOW()
                WHERE pid = %s
            """, (ano, new_cid, pdt, amt, pid))

        # 4. Recalculate balances for old and new customers
        _call_recalc_balance(cur, old_cid)
        if new_cid != old_cid:
            _call_recalc_balance(cur, new_cid)

        # Invalidate cache for this village
        min_date = min(pdt, old_pdt.date() if isinstance(old_pdt, datetime) else old_pdt)
        _call_invalidate_cache(cur, vid, min_date)

        _call_audit_log(
            action="update_payment",
            entity_type="payment",
            entity_id=pid,
            details={
                "pid": pid,
                "vid": vid,
                "ano": ano,
                "amount": str(amt),
                "payment_date": str(pdt)
            },
            cur=cur
        )

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@payment_bp.route("/delete_payment", methods=["POST"])
@login_required
def delete_payment():
    data = request.get_json() or {}

    pid = data.get("pid")
    ano = data.get("ano")
    pdt_raw = data.get("pdt")
    vid = session.get("vid")

    if not vid:
        return jsonify(success=False, error="Missing village in session"), 400

    conn = get_resolved_pg_conn()
    cur = conn.cursor()

    try:
        is_active = True
        is_historic = False
        payment_row = None
        resolved_pid = None

        if pid:
            try:
                resolved_pid = int(pid)
            except (ValueError, TypeError):
                return jsonify(success=False, error="Invalid payment ID format"), 400

            # Query by primary key across active, closed, and historic tables
            cur.execute("SELECT cid, ano, vid, payment_date, amt FROM payment WHERE pid = %s", (resolved_pid,))
            payment_row = cur.fetchone()
            if not payment_row:
                cur.execute("SELECT cid, ano, vid, payment_date, amt FROM closed_cust_payment WHERE pid = %s", (resolved_pid,))
                payment_row = cur.fetchone()
                is_active = False
            if not payment_row:
                cur.execute("SELECT cid, ano, vid, payment_date, amount FROM historic_payment_data WHERE pid = %s", (resolved_pid,))
                payment_row = cur.fetchone()
                is_historic = True

            if not payment_row:
                return jsonify(success=False, error="Payment not found"), 404

            p_cid, p_ano, p_vid, p_pdt, p_amt = payment_row
        else:
            # Fallback for legacy requests without pid
            if not ano or not pdt_raw:
                return jsonify(success=False, error="Missing required fields: pid (or ano and pdt)"), 400

            try:
                pdt = datetime.fromisoformat(str(pdt_raw).strip()[:10]).date()
            except (ValueError, TypeError):
                return jsonify(success=False, error="Invalid date format"), 400

            # Count payments matching (vid, ano, pdt) in active payment table
            cur.execute("""
                SELECT pid, cid, ano, vid, payment_date, amt
                FROM payment
                WHERE vid = %s AND ano = %s AND payment_date = %s
            """, (vid, ano, pdt))
            matching_rows = cur.fetchall()

            if len(matching_rows) > 1:
                return jsonify(
                    success=False,
                    error="Multiple payments exist on this date. Specific payment ID (pid) is required to prevent accidental data loss."
                ), 400
            elif len(matching_rows) == 1:
                resolved_pid, p_cid, p_ano, p_vid, p_pdt, p_amt = matching_rows[0]
            else:
                # Check closed accounts table
                cur.execute("""
                    SELECT pid, cid, ano, vid, payment_date, amt
                    FROM closed_cust_payment
                    WHERE vid = %s AND ano = %s AND payment_date = %s
                """, (vid, ano, pdt))
                closed_rows = cur.fetchall()
                if len(closed_rows) > 1:
                    return jsonify(
                        success=False,
                        error="Multiple payments exist on this date in closed accounts. Specific payment ID (pid) is required."
                    ), 400
                elif len(closed_rows) == 1:
                    resolved_pid, p_cid, p_ano, p_vid, p_pdt, p_amt = closed_rows[0]
                    is_active = False
                else:
                    return jsonify(success=False, error="Payment not found"), 404

        # Security check: Ensure payment belongs to the current village context
        if p_vid != vid:
            return jsonify(success=False, error="Access denied: Different village context"), 403

        # Determine target table
        if is_historic:
            table_payment = "historic_payment_data"
        elif is_active:
            table_payment = "payment"
        else:
            table_payment = "closed_cust_payment"

        # Delete strictly by primary key (pid)
        cur.execute(f"DELETE FROM {table_payment} WHERE pid = %s", (resolved_pid,))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify(success=False, error="Payment not found or already deleted"), 404

        # Recalculate customer balance
        _call_recalc_balance(cur, p_cid)

        # Audit log
        _call_audit_log(
            action="delete_payment",
            entity_type="payment",
            entity_id=resolved_pid,
            details={
                "pid": resolved_pid,
                "vid": vid,
                "ano": p_ano,
                "cid": p_cid,
                "payment_date": str(p_pdt),
                "amount": str(p_amt),
                "table": table_payment
            },
            cur=cur
        )

        # Invalidate cache for this village
        _call_invalidate_cache(cur, vid, p_pdt)

        global_ttl_cache.clear()
        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

def format_waiting_duration(seconds):
    if seconds <= 0:
        return ""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

