"""
Unified Interest Calculation Engine
SD Finance System (Smart Counting, Chit Fund, Central Bank)

This module serves as the SINGLE CANONICAL SOURCE OF TRUTH for all interest,
day-count conventions, fee splits, and discount validations across the entire application.

CONVENTIONS & FORMULAS:
1. Day-Count Convention: Strict 30/360 Indian Commercial Day Count
   - Every calendar month has strictly 30 days (including February, and 31-day months).
   - 1 Year = 360 days.
   - Example: 01-Jan-2026 to 31-Oct-2026 = 9 elapsed months * 30 + 30 = 300 days.
   - Example: 01-Jan-2026 to 31-Dec-2026 = 12 * 30 = 360 days.
   - Example: 01-Jan-2026 to 28-Feb-2026 = 60 days.

2. Commercial Daily Accrual Formula (User Standard):
   - Daily Accrual = (Principal * annual_rate / 100.0) / 360.0
   - Accrued Interest = round_currency(Daily Accrual * days_elapsed)
   - Example: ₹1,00,000 @ 24% for 300 days = ((100000 * 24%) / 360) * 300 = ₹20,000.00.

3. Annual Capitalization Milestones (Multi-Year):
   - For duration <= 360 days: Pure linear daily accrual.
   - For duration > 360 days: Interest capitalizes after every completed 360-day cycle into
     the active principal base, and remaining days accrue linear daily interest on the capitalized base.

4. Smart Counting Microfinance Flat Upfront Cut:
   - Interest Amount = round_currency(Total * (interest_rate / 100.0))
   - Cutting Amount = round_currency(Total * (cutting_rate / 100.0))
   - Base Amount = Total - Interest Amount - Cutting Amount

5. Currency Rounding:
   - All monetary amounts use Banker's/Commercial ROUND_HALF_UP whole rupee precision.
"""

from __future__ import annotations

import calendar
import math
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Numerical Helpers & Rounding Utilities
# ---------------------------------------------------------------------------

def round_currency(val: Union[float, int, Decimal, str, None]) -> float:
    """
    Rounds any numeric value to nearest integer whole number using standard
    commercial ROUND_HALF_UP precision.
    """
    if val is None or val == "":
        return 0.0
    try:
        dec = Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return float(dec)
    except Exception:
        return 0.0


def _parse_date(d: Union[date, datetime, str, None]) -> Optional[date]:
    """Helper to normalize date, datetime, or ISO/formatted date string to a date object."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        d_str = d.strip()
        if not d_str:
            return None
        try:
            return date.fromisoformat(d_str[:10])
        except Exception:
            try:
                return datetime.strptime(d_str[:10], "%d-%m-%Y").date()
            except Exception:
                return None
    return None


# ---------------------------------------------------------------------------
# Strict 30/360 Indian Commercial Day-Count Convention
# ---------------------------------------------------------------------------

def calculate_days_30_360(
    d1: Union[date, datetime, str, None],
    d2: Union[date, datetime, str, None],
) -> int:
    """
    Computes elapsed days using the strict 30/360 Indian commercial day-count convention.
    Every month is treated as having strictly 30 days; 1 year = 360 days.

    Examples:
        Jan 1, 2026 to Oct 31, 2026 = (9 months * 30) + 30 = 300 days.
        Jan 1, 2026 to Jan 31, 2026 = 30 days.
        Jan 1, 2026 to Feb 28, 2026 = 60 days.
        Jan 1, 2026 to Dec 31, 2026 = 360 days.
        Jan 1, 2026 to Jan 1, 2026  = 0 days.
        Jan 15, 2026 to Feb 15, 2026 = 30 days.
    """
    start = _parse_date(d1)
    end = _parse_date(d2)
    if start is None or end is None or end <= start:
        return 0

    y1, m1, day1 = start.year, start.month, start.day
    y2, m2, day2 = end.year, end.month, end.day

    is_d2_eom = (day2 == calendar.monthrange(y2, m2)[1])
    is_d1_bom = (day1 == 1)

    # If start is 1st of month and end is end of month, exact whole months!
    if is_d1_bom and is_d2_eom:
        months = (y2 - y1) * 12 + (m2 - m1) + 1
        return int(months * 30)

    # General 30/360 formula:
    # Cap day1 and day2 at 30 (or EOM to 30)
    d1_capped = 30 if day1 >= 30 else day1
    d2_capped = 30 if (is_d2_eom or day2 >= 30) else day2

    days = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2_capped - d1_capped)
    return max(0, int(days))


# ---------------------------------------------------------------------------
# Strict 30/360 Commercial Daily Simple Interest
# ---------------------------------------------------------------------------

def calculate_simple_interest_30_360(
    principal: float,
    annual_rate: float,
    start_date: Union[date, datetime, str, None],
    as_of_date: Union[date, datetime, str, None],
) -> Dict[str, Any]:
    """
    Computes exact simple interest using the user's 30/360 commercial convention:
        Interest = (Principal * annual_rate / 100.0) / 360.0 * days_30_360

    Example:
        1,00,000 invested on 01-01-2026 @ 24% as of 31-10-2026 (300 days):
        ((100000 * 24%) / 360) * 300 = ₹20,000.00
    """
    p = max(0.0, float(principal or 0.0))
    r = float(annual_rate or 0.0)
    days = calculate_days_30_360(start_date, as_of_date)
    if p <= 0.0 or days <= 0 or r <= 0.0:
        return {"days_elapsed": days, "interest": 0.0, "total": round_currency(p)}

    interest = round_currency((p * (r / 100.0) / 360.0) * days)
    return {
        "days_elapsed": days,
        "interest": interest,
        "total": round_currency(p + interest),
    }


# Backwards compatibility alias for calculate_simple_interest_30_360
calculate_interest_30_360 = calculate_simple_interest_30_360


# ---------------------------------------------------------------------------
# Canonical Accrued Interest with 360-Day Milestone Capitalization
# ---------------------------------------------------------------------------

def calculate_accrued_interest_30_360(
    principal: float,
    annual_rate: float = 24.0,
    start_date: Union[date, datetime, str, None] = None,
    as_of_date: Union[date, datetime, str, None] = None,
    repaid_interest: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculates interest using the strict 30/360 Indian commercial day-count convention:
        Interest = (Principal * annual_rate / 100.0) / 360.0 * days_elapsed
    For multi-year durations (>360 days), interest capitalizes after every completed 360-day cycle.

    Computes:
        - days_elapsed (30/360 convention)
        - gross_interest / gross_accrued_interest
        - repaid_interest
        - net_unpaid_interest
        - current_payoff_balance / total_payoff
    """
    p = max(0.0, float(principal or 0.0))
    r = float(annual_rate or 0.0)
    rep_int = max(0.0, float(repaid_interest or 0.0))

    d_start = _parse_date(start_date)
    d_as_of = _parse_date(as_of_date)

    days_elapsed = calculate_days_30_360(d_start, d_as_of)

    if p <= 0.0 or days_elapsed == 0 or r <= 0.0:
        gross_amount = round_currency(p)
        gross_interest = 0.0
        net_unpaid = 0.0
        payoff_bal = round_currency(max(0.0, p - rep_int))
        completed_years = 0
        rem_days = 0
    else:
        completed_years = days_elapsed // 360
        rem_days = days_elapsed % 360
        curr_p = p
        total_interest = 0.0
        for _ in range(completed_years):
            yr_int = round_currency(curr_p * (r / 100.0))
            total_interest += yr_int
            curr_p = round_currency(curr_p + yr_int)
        if rem_days > 0:
            rem_int = round_currency((curr_p * (r / 100.0) / 360.0) * rem_days)
            total_interest += rem_int

        gross_interest = round_currency(total_interest)
        gross_amount = round_currency(p + gross_interest)
        net_unpaid = round_currency(max(0.0, gross_interest - rep_int))
        payoff_bal = round_currency(max(0.0, p + gross_interest - rep_int))

    return {
        "days_elapsed": int(days_elapsed),
        "completed_years": int(completed_years),
        "gross_interest": gross_interest,
        "gross_accrued_interest": gross_interest,
        "gross_compound_amount": gross_amount,
        "net_unpaid_interest": net_unpaid,
        "current_payoff_balance": payoff_bal,
        "total_payoff": payoff_bal,
        "total": gross_amount,
        "principal": round_currency(p),
        "annual_rate": r,
        "repaid_interest": round_currency(rep_int),
    }


def calculate_compound_interest(
    principal: float,
    start_date: Union[date, datetime, str, None],
    as_of_date: Union[date, datetime, str, None],
    annual_rate: float = 24.0,
    repaid_interest: float = 0.0,
) -> Dict[str, Any]:
    """
    Direct drop-in signature compatible wrapper for Central Bank and existing code:
    Calls calculate_accrued_interest_30_360.
    """
    return calculate_accrued_interest_30_360(
        principal=principal,
        annual_rate=annual_rate,
        start_date=start_date,
        as_of_date=as_of_date,
        repaid_interest=repaid_interest,
    )


# ---------------------------------------------------------------------------
# Annual Capitalization Milestones Engine (Central Bank & Chit Loans)
# ---------------------------------------------------------------------------

def apply_annual_capitalization_30_360(
    principal: float,
    start_date: Union[date, datetime, str, None],
    as_of_date: Union[date, datetime, str, None],
    annual_rate: float = 24.0,
) -> Dict[str, Any]:
    """
    Computes 360-day compounding milestones (30/360 convention), capitalizes unpaid interest after
    every 360 days into the active principal base, and computes accrued interest
    since the last anniversary.
    """
    p_init = max(0.0, float(principal or 0.0))
    r = float(annual_rate or 0.0)

    d_start = _parse_date(start_date)
    d_as_of = _parse_date(as_of_date)

    days_elapsed = calculate_days_30_360(d_start, d_as_of)

    if p_init <= 0.0 or days_elapsed == 0 or r <= 0.0:
        base = round_currency(p_init)
        return {
            "days_elapsed": int(days_elapsed),
            "completed_milestones": 0,
            "milestones": [],
            "initial_principal": base,
            "active_principal": base,
            "current_principal_base": base,
            "days_since_last_anniversary": 0,
            "accrued_interest_since_anniversary": 0.0,
            "accrued_interest": 0.0,
            "total_capitalized_interest": 0.0,
            "total_accrued_interest": 0.0,
            "current_payoff_balance": base,
            "annual_rate": r,
        }

    completed_milestones = days_elapsed // 360
    days_since_anniversary = days_elapsed % 360

    current_principal = round_currency(p_init)
    total_capitalized = 0.0
    milestones: List[Dict[str, Any]] = []

    rate_fraction = r / 100.0

    # Step through each completed 360-day milestone
    for m in range(1, completed_milestones + 1):
        m_days = m * 360
        m_date = d_start + timedelta(days=int(m * 365.25)) if d_start else None
        m_date_str = m_date.isoformat() if m_date else ""

        open_p = current_principal
        cap_interest = round_currency(open_p * rate_fraction)
        close_p = round_currency(open_p + cap_interest)

        milestones.append({
            "milestone_index": m,
            "milestone_days": m_days,
            "milestone_date": m_date_str,
            "opening_principal": open_p,
            "capitalized_interest": cap_interest,
            "closing_principal": close_p,
        })

        total_capitalized = round_currency(total_capitalized + cap_interest)
        current_principal = close_p

    active_principal = current_principal

    # Accrued interest on current active base since last anniversary (30/360)
    if days_since_anniversary > 0:
        accrued_since_anniversary = round_currency(
            active_principal * rate_fraction * (days_since_anniversary / 360.0)
        )
    else:
        accrued_since_anniversary = 0.0

    total_accrued = round_currency(total_capitalized + accrued_since_anniversary)
    payoff_balance = round_currency(active_principal + accrued_since_anniversary)

    return {
        "days_elapsed": int(days_elapsed),
        "completed_milestones": int(completed_milestones),
        "milestones": milestones,
        "initial_principal": round_currency(p_init),
        "active_principal": active_principal,
        "current_principal_base": active_principal,
        "days_since_last_anniversary": int(days_since_anniversary),
        "accrued_interest_since_anniversary": accrued_since_anniversary,
        "accrued_interest": accrued_since_anniversary,
        "total_capitalized_interest": total_capitalized,
        "total_accrued_interest": total_accrued,
        "current_payoff_balance": payoff_balance,
        "annual_rate": r,
    }


# ---------------------------------------------------------------------------
# Smart Counting Upfront Flat Loan Split Engine
# ---------------------------------------------------------------------------

def calculate_smart_counting_loan_split(
    total_amount: float,
    interest_rate: float,
    cutting_rate: float,
) -> Dict[str, float]:
    """
    Computes the upfront microloan commission & cutting split for Smart Counting:
        interest_amount = round_currency(total_amount * (interest_rate / 100.0))
        cutting_amount  = round_currency(total_amount * (cutting_rate / 100.0))
        base_amount     = round_currency(total_amount - interest_amount - cutting_amount)
    """
    tot = max(0.0, float(total_amount or 0.0))
    ir = max(0.0, float(interest_rate or 0.0))
    cr = max(0.0, float(cutting_rate or 0.0))

    interest_amount = round_currency(tot * (ir / 100.0))
    cutting_amount = round_currency(tot * (cr / 100.0))
    base_amount = round_currency(tot - interest_amount - cutting_amount)

    return {
        "total_amount": tot,
        "interest_amount": interest_amount,
        "cutting_amount": cutting_amount,
        "base_amount": base_amount,
    }


def validate_interest_discount(
    balance_amount: float,
    interest_amount: float,
    discount_amount: float,
) -> Tuple[bool, str]:
    """
    Validates whether an interest discount can be granted during customer loan closure:
    1. discount_amount must be > 0.
    2. balance_amount must be <= interest_amount (principal cannot be discounted, only interest).
    3. discount_amount must not exceed balance_amount.
    """
    try:
        bal = float(balance_amount or 0.0)
        i_amt = float(interest_amount or 0.0)
        disc = float(discount_amount or 0.0)
    except (ValueError, TypeError):
        return False, "Invalid numeric amounts for discount validation"

    if disc <= 0:
        return False, "Discount amount must be greater than 0"
    if bal > i_amt:
        return False, f"Balance (₹{bal:,.0f}) is greater than interest amount (₹{i_amt:,.0f}). Cannot apply discount."
    if disc > bal:
        return False, f"Discount (₹{disc:,.0f}) cannot exceed remaining balance (₹{bal:,.0f})."

    return True, "Valid"
