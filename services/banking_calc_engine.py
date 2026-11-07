"""
Banking Calculation Engine
SD Finance Banking & Chit System

Provides pure, robust, mathematically exact calculation functions for:
- Compound interest accrual with 365.25 fractional day conventions
- Annual compounding capitalization with 365-day milestone tracking
- Office expense reallocation across branch/chit groups with exact paise balancing
- 3-tier withdrawal waterfall settlement (Principal -> Interest -> Profit Share)
- Indian currency (INR Lakh/Crore) and datetime formatting
"""

from __future__ import annotations

import calendar
import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Numerical Helpers & Rounding Utilities
# ---------------------------------------------------------------------------

def round_currency(val: Union[float, int, Decimal, str, None]) -> float:
    """
    Rounds any numeric value to nearest integer whole number using standard banker's/commercial
    ROUND_HALF_UP precision.

    Args:
        val: Input value (float, int, Decimal, or numeric str).

    Returns:
        float: Value rounded to nearest integer (whole number), or 0.0 on None / conversion failure.
    """
    if val is None or val == "":
        return 0.0
    try:
        dec = Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return float(dec)
    except Exception:
        return 0.0


def _parse_date(d: Union[date, datetime, str, None]) -> Optional[date]:
    """Helper to normalize date, datetime, or ISO date string to a date object."""
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


def _parse_time(t: Union[datetime, time, str, None]) -> Optional[time]:
    """Helper to normalize datetime, time, or time string to a time object."""
    if t is None:
        return None
    if isinstance(t, datetime):
        return t.time()
    if isinstance(t, time):
        return t
    if isinstance(t, str):
        t_str = t.strip()
        if not t_str:
            return None
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
            try:
                return datetime.strptime(t_str, fmt).time()
            except ValueError:
                pass
    return None


# ---------------------------------------------------------------------------
# Unified Interest Engine Integration (Single Canonical Source of Truth)
# ---------------------------------------------------------------------------

from services.interest_calc_engine import (
    calculate_days_30_360,
    calculate_interest_30_360,
    calculate_simple_interest_30_360,
    calculate_accrued_interest_30_360,
    calculate_compound_interest,
    apply_annual_capitalization_30_360,
)

# Canonical alias for milestone tracking
apply_annual_capitalization = apply_annual_capitalization_30_360


# ---------------------------------------------------------------------------
# 3. Office Expense Reallocation Engine
# ---------------------------------------------------------------------------

def calculate_office_expense_reallocation(
    total_expenses: float,
    group_days_map: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Reallocates total office expenses across groups based on active operational days:
        share = (total_expenses / total_days) * group_days

    Handles exact rounding to 2 decimal places (paise) and balances any 1-2 paise
    discrepancy using the largest-remainder method (Hamilton-Hare method) so that
    sum(reallocated_expense) == round(total_expenses, 2) ALWAYS.

    Args:
        total_expenses: Total office expenses to distribute across groups.
        group_days_map: List of dicts, each specifying group metadata and active days.
                        Accepts either 'days' or 'group_days' as the day count key.

    Returns:
        List[Dict[str, Any]]: Modified list of group dictionaries including:
            - 'days' (int): Group operational days.
            - 'allocated_expense' (float): Exact allocated share rounded to 2 decimals.
            - 'reallocated_expense' (float): Alias for allocated_expense.
            - 'expense_share' (float): Alias for allocated_expense.
            - 'share_pct' (float): Percentage share of total expenses.
    """
    if not group_days_map:
        return []

    tot_exp = max(0.0, float(total_expenses or 0.0))
    tot_exp_dec = Decimal(str(round_currency(tot_exp)))

    # Parse and extract days for each group
    extracted: List[Dict[str, Any]] = []
    total_days = 0

    for item in group_days_map:
        copy_item = dict(item)
        raw_days = copy_item.get("days")
        if raw_days is None:
            raw_days = copy_item.get("group_days", 0)
        try:
            d_count = max(0, int(raw_days))
        except (ValueError, TypeError):
            d_count = 0
        copy_item["days"] = d_count
        extracted.append(copy_item)
        total_days += d_count

    # Edge cases: 0 days or 0 expenses
    if total_days == 0 or tot_exp_dec == Decimal("0.00"):
        for entry in extracted:
            entry["allocated_expense"] = 0.0
            entry["reallocated_expense"] = 0.0
            entry["expense_share"] = 0.0
            entry["share_pct"] = 0.0
        return extracted

    tot_days_dec = Decimal(str(total_days))

    # Calculate raw shares and initial ROUND_HALF_UP rounded shares
    raw_shares: List[Decimal] = []
    rounded_shares: List[Decimal] = []
    remainders: List[Decimal] = []

    for entry in extracted:
        days_dec = Decimal(str(entry["days"]))
        raw_share = (tot_exp_dec * days_dec) / tot_days_dec
        rounded_share = raw_share.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        raw_shares.append(raw_share)
        rounded_shares.append(rounded_share)
        remainders.append(raw_share - rounded_share)

    # Balance whole rupee discrepancy
    sum_rounded = sum(rounded_shares)
    rupee_diff = int((tot_exp_dec - sum_rounded).to_integral_value(rounding=ROUND_HALF_UP))

    if rupee_diff > 0:
        # Under-allocated by rupee_diff: allocate +₹1 to highest positive remainders
        # (groups that were rounded down the most)
        sorted_indices = sorted(
            range(len(extracted)),
            key=lambda idx: remainders[idx],
            reverse=True,
        )
        for i in range(min(rupee_diff, len(extracted))):
            rounded_shares[sorted_indices[i]] += Decimal("1")
    elif rupee_diff < 0:
        # Over-allocated by |rupee_diff|: deduct -₹1 from lowest remainders
        # (groups that were rounded up the most)
        sorted_indices = sorted(
            range(len(extracted)),
            key=lambda idx: remainders[idx],
        )
        for i in range(min(abs(rupee_diff), len(extracted))):
            if rounded_shares[sorted_indices[i]] >= Decimal("1"):
                rounded_shares[sorted_indices[i]] -= Decimal("1")

    # Assemble final enriched dictionary list
    for idx, entry in enumerate(extracted):
        final_amt = float(rounded_shares[idx])
        days_cnt = entry["days"]
        pct = round(float((Decimal(str(days_cnt)) / tot_days_dec) * Decimal("100")), 4)

        entry["allocated_expense"] = final_amt
        entry["reallocated_expense"] = final_amt
        entry["expense_share"] = final_amt
        entry["share_pct"] = round(pct, 2)

    return extracted


# ---------------------------------------------------------------------------
# 4. Withdrawal Waterfall Engine
# ---------------------------------------------------------------------------

def calculate_withdrawal_waterfall(
    withdrawn_amount: float,
    principal_owed: float,
    interest_owed: float,
    shares: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Executes a 3-tier withdrawal waterfall distribution:
        - Tier 1: Covers outstanding principal owed.
        - Tier 2: Covers outstanding accrued interest owed.
        - Tier 3: Profit surplus split strictly among shareholders by share_pct.

    Also handles exact paise balancing for Tier 3 profit split across shareholders
    using the largest-remainder method.

    Args:
        withdrawn_amount: Total cash withdrawn or distributed.
        principal_owed: Outstanding principal capital owed (Tier 1 requirement).
        interest_owed: Outstanding accrued interest owed (Tier 2 requirement).
        shares: List of partner / shareholder dicts, each with 'share_pct'
                (e.g., [{'partner_id': 'P1', 'share_pct': 60.0}, ...]).

    Returns:
        Dict[str, Any] containing:
            - withdrawn_amount (float): Total withdrawal processed.
            - tier1_principal_covered (float): Amount allocated to principal.
            - remaining_principal_owed (float): Principal still unpaid after waterfall.
            - tier2_interest_covered (float): Amount allocated to accrued interest.
            - remaining_interest_owed (float): Accrued interest still unpaid.
            - tier3_profit_surplus (float): Remaining funds available as profit.
            - total_distributed (float): Total of Tier 1 + Tier 2 + Tier 3.
            - distributions (List[Dict]): Partner-level breakdowns containing:
                * partner metadata
                * share_pct (float)
                * principal_share (float)
                * interest_share (float)
                * profit_share (float)
                * total_received (float)
    """
    withdrawn = max(0.0, round_currency(withdrawn_amount))
    p_owed = max(0.0, round_currency(principal_owed))
    i_owed = max(0.0, round_currency(interest_owed))

    rem = withdrawn

    # --- Tier 1: Principal Coverage ---
    tier1_principal_covered = round_currency(min(rem, p_owed))
    rem = round_currency(max(0.0, rem - tier1_principal_covered))
    remaining_p_owed = round_currency(max(0.0, p_owed - tier1_principal_covered))

    # --- Tier 2: Accrued Interest Coverage ---
    tier2_interest_covered = round_currency(min(rem, i_owed))
    rem = round_currency(max(0.0, rem - tier2_interest_covered))
    remaining_i_owed = round_currency(max(0.0, i_owed - tier2_interest_covered))

    # --- Tier 3: Profit Surplus Split ---
    tier3_profit_surplus = round_currency(rem)

    # Distribute among partners
    distributions: List[Dict[str, Any]] = []

    if shares:
        # Normalize / sum share percentages
        total_share_pct = sum(float(s.get("share_pct", 0.0) or 0.0) for s in shares)

        if total_share_pct > 0.0 and tier3_profit_surplus > 0.0:
            surplus_dec = Decimal(str(tier3_profit_surplus))
            tot_pct_dec = Decimal(str(total_share_pct))

            raw_profits: List[Decimal] = []
            rounded_profits: List[Decimal] = []
            profit_remainders: List[Decimal] = []

            for s in shares:
                s_pct = Decimal(str(float(s.get("share_pct", 0.0) or 0.0)))
                raw_p = (surplus_dec * s_pct) / tot_pct_dec
                rnd_p = raw_p.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                raw_profits.append(raw_p)
                rounded_profits.append(rnd_p)
                profit_remainders.append(raw_p - rnd_p)

            # Rebalance whole rupee discrepancy for profit
            p_diff = int((surplus_dec - sum(rounded_profits)).to_integral_value(rounding=ROUND_HALF_UP))
            if p_diff > 0:
                s_idxs = sorted(range(len(shares)), key=lambda i: profit_remainders[i], reverse=True)
                for i in range(min(p_diff, len(shares))):
                    rounded_profits[s_idxs[i]] += Decimal("1")
            elif p_diff < 0:
                s_idxs = sorted(range(len(shares)), key=lambda i: profit_remainders[i])
                for i in range(min(abs(p_diff), len(shares))):
                    if rounded_profits[s_idxs[i]] >= Decimal("1"):
                        rounded_profits[s_idxs[i]] -= Decimal("1")

            for idx, s in enumerate(shares):
                partner_item = dict(s)
                s_pct_val = float(partner_item.get("share_pct", 0.0) or 0.0)
                profit_amt = float(rounded_profits[idx])

                # Partner share of principal & interest if partners share equity pro-rata
                pct_ratio = s_pct_val / total_share_pct if total_share_pct > 0 else 0.0
                p_share = round_currency(tier1_principal_covered * pct_ratio)
                i_share = round_currency(tier2_interest_covered * pct_ratio)
                tot_recv = round_currency(p_share + i_share + profit_amt)

                partner_item.update({
                    "share_pct": s_pct_val,
                    "principal_share": p_share,
                    "interest_share": i_share,
                    "profit_share": profit_amt,
                    "total_received": tot_recv,
                })
                distributions.append(partner_item)
        else:
            for s in shares:
                partner_item = dict(s)
                s_pct_val = float(partner_item.get("share_pct", 0.0) or 0.0)
                pct_ratio = (s_pct_val / total_share_pct) if total_share_pct > 0 else 0.0
                p_share = round_currency(tier1_principal_covered * pct_ratio)
                i_share = round_currency(tier2_interest_covered * pct_ratio)
                tot_recv = round_currency(p_share + i_share)

                partner_item.update({
                    "share_pct": s_pct_val,
                    "principal_share": p_share,
                    "interest_share": i_share,
                    "profit_share": 0.0,
                    "total_received": tot_recv,
                })
                distributions.append(partner_item)

    total_distributed = round_currency(
        tier1_principal_covered + tier2_interest_covered + tier3_profit_surplus
    )

    return {
        "withdrawn_amount": withdrawn,
        "tier1_principal_covered": tier1_principal_covered,
        "remaining_principal_owed": remaining_p_owed,
        "tier2_interest_covered": tier2_interest_covered,
        "remaining_interest_owed": remaining_i_owed,
        "tier3_profit_surplus": tier3_profit_surplus,
        "total_distributed": total_distributed,
        "distributions": distributions,
    }


# ---------------------------------------------------------------------------
# 5. Currency & Indian Formatting Helpers
# ---------------------------------------------------------------------------

def format_currency_inr(amount: Union[float, int, Decimal, str, None]) -> str:
    """
    Formats a numeric amount into standard Indian Lakh/Crore grouping with the
    Indian Rupee symbol (₹) as a whole number without decimals.

    Examples:
        1245670.00 -> '₹12,45,670'
        100000.00  -> '₹1,00,000'
        10000000.0 -> '₹1,00,00,000'
        -50000.5   -> '-₹50,001'
        0          -> '₹0'

    Args:
        amount: Number to format.

    Returns:
        str: Formatted currency string with ₹ symbol without decimals.
    """
    if amount is None or amount == "":
        return "₹0"

    try:
        val = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except Exception:
        return "₹0"

    is_negative = val < Decimal("0")
    val_abs = abs(val)

    int_part = str(val_abs)

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        # The rightmost 3 digits
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        # Group preceding digits in pairs of 2 from right to left
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last_three

    res = f"₹{formatted_int}"
    return f"-{res}" if is_negative else res


def format_date_in(d: Union[date, datetime, str, None]) -> str:
    """
    Formats a date object, datetime object, or ISO string into DD-MM-YYYY display format.

    Examples:
        date(2026, 10, 6) -> '06-10-2026'
        '2026-10-06'      -> '06-10-2026'

    Args:
        d: Date, datetime, or date string.

    Returns:
        str: Formatted date string as DD-MM-YYYY or empty string if invalid/None.
    """
    parsed = _parse_date(d)
    if parsed is None:
        return ""
    return parsed.strftime("%d-%m-%Y")


def format_time_in(dt: Union[datetime, time, str, None]) -> str:
    """
    Formats a datetime, time object, or time string into standard 12-hour AM/PM format.

    Examples:
        datetime(2026, 10, 6, 19, 45) -> '07:45 PM'
        datetime(2026, 10, 6, 9, 5)   -> '09:05 AM'

    Args:
        dt: Datetime, time, or time string.

    Returns:
        str: Formatted time string as 'HH:MM AM/PM' or empty string if invalid/None.
    """
    parsed = _parse_time(dt)
    if parsed is None:
        return ""
    return parsed.strftime("%I:%M %p")
