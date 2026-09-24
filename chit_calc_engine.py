"""
Siva Durga Chit Fund - Calculation Engine
Implements the exact mathematical formulas from the 20-month and 25-month fixed charts:
- Column 1: Month #
- Column 2: Chit Loss (Discount)
- Column 3: Net Cash Received (Prize Payout)
- Column 4: Bonus / Dividend Saved
- Column 5: Installment Due (Net Payment)
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Base 20-Month bonus values for ₹5,000 chit (from physical chart 1)
BONUS_20M_BASE_5000 = [
    75.0, 71.5, 68.0, 64.0, 60.0, 56.0, 52.0, 48.0, 44.0, 40.0,
    36.0, 32.0, 28.0, 24.0, 20.0, 16.0, 12.0, 7.5, 3.0, 0.0
]

# Base 25-Month bonus values for ₹5,000 chit (from physical chart 2)
BONUS_25M_BASE_5000 = [
    67.5, 65.0, 62.5, 60.0, 57.5, 55.0, 52.5, 50.0, 47.5, 45.0,
    42.0, 39.0, 36.0, 33.0, 30.0, 27.0, 24.0, 21.0, 18.0, 15.0,
    12.0, 9.0, 6.0, 3.0, 0.0
]

def round_curr(val):
    if val is None or val == "":
        return 0.0
    try:
        return float(Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except Exception:
        return 0.0

def generate_chit_schedule(chit_value: float, duration_months: int, start_month_year: str = None, commission_pct: float = 3.0, is_month1_company: bool = False):
    """
    Generates the complete fixed schedule matching Siva Durga Chit Fund charts.
    """
    chit_val = float(chit_value)
    duration = int(duration_months)
    comm_pct = float(commission_pct)
    commission = chit_val * (comm_pct / 100.0)
    base_installment = chit_val / float(duration)
    multiplier = chit_val / 5000.0

    if not start_month_year:
        start_month_year = datetime.now().strftime("%Y-%m")

    try:
        start_dt = datetime.strptime(start_month_year, "%Y-%m")
    except Exception:
        start_dt = datetime.now()

    if duration == 20:
        base_bonuses = BONUS_20M_BASE_5000
    elif duration == 25:
        base_bonuses = BONUS_25M_BASE_5000
    else:
        # Linear interpolation fallback for custom durations
        start_bonus = round_curr(base_installment * 0.35)
        step = start_bonus / float(duration - 1)
        base_bonuses = [max(0.0, start_bonus - (i * step)) for i in range(duration)]
        multiplier = 1.0

    schedule = []
    for idx in range(1, duration + 1):
        m_dt = start_dt + relativedelta(months=idx - 1)
        m_label = m_dt.strftime("%Y-%m")

        is_co_month = (idx == 1 and is_month1_company)

        if is_co_month:
            bonus = 0.0
            kattubadi = round_curr(base_installment)
            loss = round_curr(chit_val)
            receive = 0.0
        else:
            bonus = round_curr(base_bonuses[idx - 1] * multiplier)
            kattubadi = round_curr(base_installment - bonus)
            loss = round_curr((bonus * duration) + commission)
            receive = round_curr(chit_val - loss)

        schedule.append({
            'month_index': idx,
            'month_year': m_label,
            'month_display': f"{m_dt.strftime('%b %y')} M{idx}",
            'chit_loss': loss,
            'amount_received': receive,
            'bonus': bonus,
            'installment_kattubadi': kattubadi,
            'commission': round_curr(commission),
            'is_company_month': is_co_month
        })

    return schedule

def get_fixed_installment_amount(chit_value: float, duration_months: int) -> float:
    """
    Computes the uniform fixed monthly installment amount for a fixed chit scheme:
    - Base ₹5,000 / 20M chit: ₹212.15 / month
    - Base ₹5,000 / 25M chit: ₹164.90 / month
    - Scaled proportionally by chit_value / 5000.0 for higher pot values
    """
    chit_val = float(chit_value)
    duration = int(duration_months)
    multiplier = chit_val / 5000.0

    if duration == 20:
        return round_curr(212.15 * multiplier)
    elif duration == 25:
        return round_curr(164.90 * multiplier)
    else:
        sched = generate_chit_schedule(chit_val, duration)
        tot = sum(r['installment_kattubadi'] for r in sched)
        return round_curr(tot / float(duration))

def calculate_monthly_margins(schedule, total_members: int = 1, chit_total_value: float = None):
    """
    Computes the exact fixed schedule margin tile and matrix:
    - Collected: total collected amount * desired members share (sum(installments) * desired_members_share)
    - Payout: max payout amount (M20 payout amount * desired members share)
    - You Keep: 3% of chit value * desired members share
    """
    desired_shares = float(total_members if total_members is not None else 1)
    if desired_shares <= 0:
        desired_shares = 1.0

    if not chit_total_value and schedule:
        last_payout = schedule[-1].get('amount_received', 0.0)
        if last_payout > 0:
            chit_total_value = round_curr(last_payout / 0.97)

    chit_val = float(chit_total_value or 500000.0)

    single_share_collected = sum(r.get('installment_kattubadi', 0.0) for r in schedule)
    total_collected = round_curr(single_share_collected * desired_shares)

    max_payout_single = schedule[-1].get('amount_received', 0.0) if schedule else 0.0
    total_payout = round_curr(max_payout_single * desired_shares)

    you_keep = round_curr((chit_val * 0.03) * desired_shares)

    matrix = []
    for r in schedule:
        collect = round_curr(r.get('installment_kattubadi', 0.0) * desired_shares)
        payout = r.get('amount_received', 0.0) if not r.get('is_company_month') else 0.0
        keep = round_curr(collect - payout)

        matrix.append({
            'month_index': r['month_index'],
            'month_label': f"M{r['month_index']}{' · co' if r.get('is_company_month') else ''}",
            'collect': collect,
            'payout': payout,
            'prize': payout,
            'keep': keep
        })

    return {
        'matrix': matrix,
        'total_collected': total_collected,
        'total_payout': total_payout,
        'total_prizes': total_payout,
        'you_keep': you_keep
    }

def calculate_schedule_totals(schedule):
    """
    Returns summary metrics across all months for the schedule.
    """
    total_bonus = sum(r['bonus'] for r in schedule)
    total_kattubadi = sum(r['installment_kattubadi'] for r in schedule)
    final_payout = schedule[-1]['amount_received'] if schedule else 0.0
    saver_profit = final_payout - total_kattubadi
    m1_cost = total_kattubadi - (schedule[0]['amount_received'] if schedule else 0.0)

    return {
        'total_bonus': round_curr(total_bonus),
        'total_installments_paid': round_curr(total_kattubadi),
        'final_month_payout': round_curr(final_payout),
        'saver_net_profit': round_curr(saver_profit),
        'saver_return_pct': round_curr((saver_profit / total_kattubadi) * 100.0) if total_kattubadi > 0 else 0.0,
        'month1_borrower_cost': round_curr(m1_cost)
    }

def calculate_member_financials(schedule, lifted_month_index=None, current_month_index=1, share_units=1.0):
    """
    Calculates exact member-specific figures with support for fractional shares (0.5x, 1x, 2x, etc.).
    """
    totals = calculate_schedule_totals(schedule)
    cur_m = max(1, min(current_month_index, len(schedule)))
    share = float(share_units or 1.0)

    paid_to_date_projected = sum(r['installment_kattubadi'] * share for r in schedule if r['month_index'] <= cur_m)
    future_dues_projected = sum(r['installment_kattubadi'] * share for r in schedule if r['month_index'] > cur_m)

    current_month_info = schedule[cur_m - 1]

    lift_info = None
    if lifted_month_index and 1 <= lifted_month_index <= len(schedule):
        lift_m_info = schedule[lifted_month_index - 1]
        amt_rec = lift_m_info['amount_received'] * share
        total_paid = totals['total_installments_paid'] * share
        borrow_cost = total_paid - amt_rec
        lift_info = {
            'lifted_month': lifted_month_index,
            'amount_received': round_curr(amt_rec),
            'chit_loss': round_curr(lift_m_info['chit_loss'] * share),
            'borrow_cost': round_curr(borrow_cost),
            'future_dues_after_lift': round_curr(sum(r['installment_kattubadi'] * share for r in schedule if r['month_index'] > lifted_month_index))
        }

    return {
        'share_units': share,
        'current_month_index': cur_m,
        'current_month_due': round_curr(current_month_info['installment_kattubadi'] * share),
        'current_month_bonus': round_curr(current_month_info['bonus'] * share),
        'current_month_lift_available': round_curr(current_month_info['amount_received'] * share),
        'paid_to_date_projected': round_curr(paid_to_date_projected),
        'future_dues_projected': round_curr(future_dues_projected),
        'total_cycle_obligation': round_curr(totals['total_installments_paid'] * share),
        'final_maturity_payout': round_curr(totals['final_month_payout'] * share),
        'saver_net_profit': round_curr(totals['saver_net_profit'] * share),
        'lift_info': lift_info
    }
