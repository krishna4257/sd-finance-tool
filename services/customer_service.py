import logging
from decimal import Decimal
from datetime import datetime, date, timedelta
import pytz
from dateutil.relativedelta import relativedelta
from services.chit_calc_engine import round_curr

logger = logging.getLogger(__name__)


def parse_date_input(value):
    """Parse a date from any common format into a Python date object.
    Accepts: 'yyyy-mm-dd' (ISO), 'dd-mm-yyyy', 'dd/mm/yyyy', date, datetime.
    Returns: datetime.date or None if parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    # Try ISO first (yyyy-mm-dd)
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        pass
    # Try dd-mm-yyyy (hyphens)
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError:
        pass
    # Try dd/mm/yyyy (slashes)
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        pass
    return None


def format_date_display(value):
    """Format a date for frontend display as dd-mm-yyyy.
    Accepts: date, datetime, or ISO string.
    Returns: 'dd-mm-yyyy' string or '' if None/invalid.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        value = parse_date_input(value)
        if value is None:
            return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return ""


def format_date_iso(value):
    """Format a date for HTML5 <input type='date'> as yyyy-mm-dd.
    Accepts: date, datetime, or date string (iso, dd-mm-yyyy, dd/mm/yyyy).
    Returns: 'yyyy-mm-dd' string or '' if None/invalid.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            return value
        parsed = parse_date_input(value)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
        return value
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return ""


def calculate_customer_rating_details(start_date, end_date, installment_amount, period, payments, balance_amount, loan_type="W", today=None):
    KOLKATA = pytz.timezone('Asia/Kolkata')

    if not today:
        today = datetime.now(KOLKATA).date()

    start_date = parse_date_input(start_date)
    end_date = parse_date_input(end_date)
    today = parse_date_input(today)

    if not start_date or not end_date or not installment_amount or not period or installment_amount <= 0 or period <= 0:
        return 100.0, "Excellent", 0.0, []

    # Filter out future-dated payments
    valid_payments = []
    for p in payments:
        p_date = p.get("payment_date")
        if not p_date:
            continue
        p_date = parse_date_input(p_date)

        if p_date <= today:
            valid_payments.append({
                "amt": Decimal(str(p.get("amt", 0))),
                "payment_date": p_date
            })

    # Day aggregation: multiple payments on the same calendar day for the same customer will be aggregated into a single amount.
    aggregated_payments = {}
    for p in valid_payments:
        d = p["payment_date"]
        aggregated_payments[d] = aggregated_payments.get(d, Decimal("0")) + p["amt"]

    # Generate rolling sequential due windows, expanding beyond period if customer is overdue
    max_eval_date = end_date
    if today > max_eval_date:
        max_eval_date = today
    for p in valid_payments:
        if p["payment_date"] > max_eval_date:
            max_eval_date = p["payment_date"]

    if loan_type == "M":
        total_periods_cap = int(period) + 36
    elif loan_type == "D":
        total_periods_cap = int(period) + 1095
    else:
        total_periods_cap = int(period) + 156

    due_dates = []
    w = 1
    while True:
        if loan_type == "M":
            due = start_date + relativedelta(months=w) + timedelta(days=1)
        elif loan_type == "D":
            due = start_date + timedelta(days=w)
        else:
            due = start_date + timedelta(days=7 * w + 1)
        due_dates.append(due)
        if w >= int(period):
            if due >= max_eval_date or w >= total_periods_cap:
                break
        w += 1
    total_weeks = len(due_dates)

    # Determine how many weeks to evaluate
    num_weeks_to_evaluate = 0
    for w in range(1, total_weeks + 1):
        window_start = start_date if w == 1 else due_dates[w - 2] + timedelta(days=1)
        if window_start <= today:
            num_weeks_to_evaluate = w
        else:
            break

    # Sum of valid payments
    total_paid = sum(p["amt"] for p in valid_payments)
    rem_balance = Decimal(str(balance_amount or 0)) + total_paid
    inst_amt = Decimal(str(installment_amount))

    # Allocation state
    payments_by_week = {}
    for w in range(1, num_weeks_to_evaluate + 1):
        window_start = start_date if w == 1 else due_dates[w - 2] + timedelta(days=1)
        window_end = due_dates[w - 1]

        week_p_sum = Decimal("0")
        for p_date, p_amt in list(aggregated_payments.items()):
            if window_start <= p_date <= window_end:
                week_p_sum += p_amt

        payments_by_week[w] = week_p_sum

    # Allocation algorithm
    virtual_paid = {w: Decimal("0") for w in range(1, num_weeks_to_evaluate + 1)}
    initial_status = {}

    carry_forward = Decimal("0")

    for w in range(1, num_weeks_to_evaluate + 1):
        current_inst = inst_amt if w <= int(period) else Decimal("0")
        available = payments_by_week.get(w, Decimal("0")) + carry_forward

        if current_inst > 0:
            if available >= current_inst:
                initial_status[w] = "SUCCESS"
                allocated = current_inst
                excess = available - current_inst
                virtual_paid[w] = allocated

                # 1. Repair oldest MISSED first
                if excess > 0:
                    for j in range(1, w):
                        if j <= int(period) and virtual_paid[j] == 0:
                            needed = inst_amt
                            if excess >= needed:
                                virtual_paid[j] = inst_amt
                                excess -= needed
                            else:
                                virtual_paid[j] = excess
                                excess = Decimal("0")
                                break

                # 2. Repair oldest PARTIAL second
                if excess > 0:
                    for j in range(1, w):
                        if j <= int(period) and 0 < virtual_paid[j] < inst_amt:
                            needed = inst_amt - virtual_paid[j]
                            if excess >= needed:
                                virtual_paid[j] = inst_amt
                                excess -= needed
                            else:
                                virtual_paid[j] += excess
                                excess = Decimal("0")
                                break

                carry_forward = excess
            else:
                if available > 0:
                    initial_status[w] = "PARTIAL"
                else:
                    initial_status[w] = "MISSED"
                virtual_paid[w] = available
                carry_forward = Decimal("0")
        else:
            initial_status[w] = "OVERDUE"
            virtual_paid[w] = available
            carry_forward = Decimal("0")

    # Score calculation loop
    score = 100.0
    consecutive_success = 0
    week_details = []
    total_excess_payments = Decimal("0")

    for w in range(1, num_weeks_to_evaluate + 1):
        p_actual = payments_by_week.get(w, Decimal("0"))
        v_paid = virtual_paid.get(w, Decimal("0"))
        init_st = initial_status.get(w, "MISSED")

        if p_actual > inst_amt:
            total_excess_payments += (p_actual - inst_amt)

        due_dt = due_dates[w - 1]
        window_start = start_date if w == 1 else due_dates[w - 2] + timedelta(days=1)

        paid_dates = [
            p["payment_date"] for p in valid_payments
            if window_start <= p["payment_date"] <= due_dt
        ]
        paid_date_val = paid_dates[-1].isoformat() if paid_dates else None

        if w <= int(period):
            if v_paid == 0:
                display_status = "MISSED"
                penalty = 5.0
                score = max(0.0, score - penalty)
                consecutive_success = 0
            elif 0 < v_paid < inst_amt:
                display_status = "PARTIAL"
                penalty = 2.0
                score = max(0.0, score - penalty)
                consecutive_success = 0
            else:
                if init_st == "SUCCESS":
                    display_status = "SUCCESS"
                    penalty = 0.0
                    consecutive_success += 1
                    if consecutive_success >= 3:
                        score = min(100.0, score + 1.0)
                else:
                    display_status = "REPAIRED"
                    penalty = 0.0
                    consecutive_success = 0
            allocated_val = float(v_paid)
        else:
            display_status = "OVERDUE"
            penalty = 0.0
            if p_actual == 0:
                periods_past = w - int(period)
                grace_threshold = 2 if loan_type == "M" else (3 if loan_type == "W" else 3)
                if periods_past >= grace_threshold:
                    if due_dt <= today:
                        penalty = 5.0
                        score = max(0.0, score - penalty)

            allocated_val = float(p_actual)

        week_details.append({
            "week": w,
            "due_date": due_dt.isoformat(),
            "paid_date": paid_date_val,
            "status": display_status,
            "allocated": allocated_val,
            "penalty": float(round_curr(penalty)),
            "score_after": float(round_curr(score))
        })

    # Apply Closure Recovery Bonus ONLY if balance_amount <= 0
    if balance_amount is not None and balance_amount <= 0:
        bonus_installments = float(total_excess_payments / inst_amt) if inst_amt > 0 else 0.0
        closure_bonus = bonus_installments * 5.0
        score = min(100.0, score + closure_bonus)
        if week_details:
            week_details[-1]["score_after"] = float(round_curr(score))

    score = min(max(score, 0.0), 100.0)

    overdue_penalty = 0.0
    if rem_balance > 0 and today > end_date:
        days_overdue = (today - end_date).days
        if loan_type == "M":
            if days_overdue >= 30:
                overdue_months = ((days_overdue - 30) // 30) + 1
                overdue_penalty = overdue_months * 5.0
        elif loan_type == "D":
            if days_overdue >= 3:
                overdue_days = ((days_overdue - 3) // 1) + 1
                overdue_penalty = overdue_days * 5.0
        else:
            if days_overdue >= 21:
                overdue_weeks = ((days_overdue - 21) // 7) + 1
                overdue_penalty = overdue_weeks * 5.0

    rounded_score = int(round(score))
    if rounded_score >= 90:
        risk_level = "Excellent"
    elif rounded_score >= 75:
        risk_level = "Good"
    elif rounded_score >= 60:
        risk_level = "Risky"
    else:
        risk_level = "Critical"

    return float(round_curr(score)), risk_level, overdue_penalty, week_details


def recalc_customer_repayment_score(cur, cid, force_recalc=False):
    cur.execute("""
        SELECT start_date, end_date, installment_amount, period, balance_amount, 
               customer_rating, final_frozen_rating, final_risk_level, freeze_date, 
               status, record_tier AS source_table, type
        FROM v_all_customers
        WHERE cid = %s
        LIMIT 1
    """, (cid,))
    row = cur.fetchone()
    if not row:
        return None

    start_date, end_date, installment_amount, period, balance_amount, customer_rating, final_frozen_rating, final_risk_level, freeze_date, status, source_table, loan_type = row

    if balance_amount is not None and balance_amount <= 0 and freeze_date is not None and not force_recalc:
        return {
            "score": float(customer_rating),
            "risk_level": final_risk_level,
            "freeze_date": freeze_date.isoformat() if freeze_date else None
        }

    cur.execute("SELECT amt, payment_date FROM v_all_payments WHERE cid = %s ORDER BY payment_date, pid", (cid,))
    prows = cur.fetchall()
    payments = [{"amt": prow[0], "payment_date": prow[1]} for prow in prows]

    score, risk_level, overdue_penalty, week_details = calculate_customer_rating_details(
        start_date, end_date, installment_amount, period, payments, balance_amount, loan_type=loan_type
    )

    if source_table == "active":
        target_table = "customer"
    elif source_table == "closed":
        target_table = "closed_cust_account"
    elif source_table == "historic":
        target_table = "historic_customer_data"
    else:
        target_table = source_table

    KOLKATA = pytz.timezone('Asia/Kolkata')

    new_freeze_date = freeze_date
    new_final_frozen_rating = final_frozen_rating
    new_final_risk_level = final_risk_level

    if balance_amount is not None and balance_amount <= 0:
        if new_freeze_date is None:
            new_freeze_date = datetime.now(KOLKATA)
        new_final_frozen_rating = score
        new_final_risk_level = risk_level
    else:
        new_freeze_date = None
        new_final_frozen_rating = None
        new_final_risk_level = None

    cur.execute(f"""
        UPDATE {target_table}
        SET customer_rating = %s,
            final_frozen_rating = %s,
            final_risk_level = %s,
            freeze_date = %s
        WHERE cid = %s
    """, (score, new_final_frozen_rating, new_final_risk_level, new_freeze_date, cid))

    return {
        "score": score,
        "risk_level": risk_level,
        "overdue_penalty": overdue_penalty,
        "week_details": week_details
    }


def invalidate_village_health_cache(cur, vid, invalidation_date=None):
    if invalidation_date:
        if isinstance(invalidation_date, datetime):
            invalidation_date = invalidation_date.date()
        cur.execute("""
            DELETE FROM village_health_cache 
            WHERE vid = %s AND (date_key >= %s OR time_range = 'dashboard')
        """, (vid, invalidation_date))
    else:
        cur.execute("DELETE FROM village_health_cache WHERE vid = %s", (vid,))


def recalc_customer_balance(cur, cid):
    cur.execute("SELECT record_tier, total_amount, COALESCE(interest_discount, 0) FROM v_all_customers WHERE cid = %s LIMIT 1", (cid,))
    cust_row = cur.fetchone()
    if not cust_row:
        return

    tier, total_amt, interest_discount = cust_row
    if tier == "active":
        table_customer = "customer"
    elif tier == "closed":
        table_customer = "closed_cust_account"
    elif tier == "historic":
        table_customer = "historic_customer_data"
    else:
        table_customer = "customer"

    cur.execute("SELECT COALESCE(SUM(amt), 0) FROM v_all_payments WHERE cid = %s", (cid,))
    paid_amt = cur.fetchone()[0]
    balance_amt = total_amt - paid_amt - interest_discount

    if table_customer == "customer":
        cur.execute(f"""
            UPDATE {table_customer}
            SET paid_amount = %s,
                balance_amount = %s,
                updated_at = NOW()
            WHERE cid = %s
        """, (paid_amt, balance_amt, cid))
    else:
        cur.execute(f"""
            UPDATE {table_customer}
            SET paid_amount = %s,
                balance_amount = %s
            WHERE cid = %s
        """, (paid_amt, balance_amt, cid))
