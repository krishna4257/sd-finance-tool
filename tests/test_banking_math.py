"""
Unit Tests for Banking Calculation Engine (30/360 Day-Count Convention)
SD Finance Banking & Chit System
"""

import unittest
from datetime import date, datetime
from decimal import Decimal

from banking_calc_engine import (
    apply_annual_capitalization,
    calculate_compound_interest,
    calculate_days_30_360,
    calculate_interest_30_360,
    calculate_office_expense_reallocation,
    calculate_withdrawal_waterfall,
    format_currency_inr,
    format_date_in,
    round_currency,
)


class TestDayCount30360(unittest.TestCase):
    """Tests the strict 30/360 day count convention."""

    def test_zero_days(self):
        self.assertEqual(calculate_days_30_360(date(2026, 1, 1), date(2026, 1, 1)), 0)
        self.assertEqual(calculate_days_30_360(date(2026, 5, 10), date(2026, 5, 1)), 0)

    def test_user_example_jan1_to_oct31(self):
        """User example: Jan 1 2026 to Oct 31 2026 = 300 days."""
        days = calculate_days_30_360(date(2026, 1, 1), date(2026, 10, 31))
        self.assertEqual(days, 300)
        res = calculate_interest_30_360(100000.0, 24.0, date(2026, 1, 1), date(2026, 10, 31))
        self.assertEqual(res["days_elapsed"], 300)
        self.assertEqual(res["interest"], 20000.0)
        self.assertEqual(res["total"], 120000.0)

    def test_one_full_month(self):
        """Jan 1 to Jan 31 = 30 days."""
        days = calculate_days_30_360(date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual(days, 30)

    def test_feb_end_of_month(self):
        """Jan 1 to Feb 28 = 60 days (2 full months)."""
        days = calculate_days_30_360(date(2026, 1, 1), date(2026, 2, 28))
        self.assertEqual(days, 60)

    def test_full_year_360_days(self):
        """Jan 1 to Dec 31 = 360 days."""
        days = calculate_days_30_360(date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(days, 360)


class TestCompoundInterest30360(unittest.TestCase):
    """Tests calculate_compound_interest under 30/360."""

    def test_zero_days_elapsed(self):
        res = calculate_compound_interest(
            principal=100000.0,
            start_date=date(2025, 1, 1),
            as_of_date=date(2025, 1, 1),
            annual_rate=24.0,
        )
        self.assertEqual(res["days_elapsed"], 0)
        self.assertEqual(res["gross_compound_amount"], 100000.0)
        self.assertEqual(res["gross_accrued_interest"], 0.0)
        self.assertEqual(res["net_unpaid_interest"], 0.0)
        self.assertEqual(res["current_payoff_balance"], 100000.0)

    def test_full_year_360_days(self):
        principal = 100000.0
        rate = 24.0
        res = calculate_compound_interest(
            principal=principal,
            start_date=date(2025, 1, 1),
            as_of_date=date(2025, 12, 31),
            annual_rate=rate,
        )
        self.assertEqual(res["days_elapsed"], 360)
        # 100000 * 1.24 = 124000
        self.assertEqual(res["gross_compound_amount"], 124000.0)
        self.assertEqual(res["gross_accrued_interest"], 24000.0)
        self.assertEqual(res["current_payoff_balance"], 124000.0)

    def test_with_repaid_interest(self):
        principal = 100000.0
        res = calculate_compound_interest(
            principal=principal,
            start_date=date(2025, 1, 1),
            as_of_date=date(2025, 12, 31),
            annual_rate=24.0,
            repaid_interest=10000.0,
        )
        self.assertEqual(res["gross_accrued_interest"], 24000.0)
        self.assertEqual(res["net_unpaid_interest"], 14000.0)
        self.assertEqual(res["current_payoff_balance"], 114000.0)

    def test_user_formula_ramesh_jan1_to_oct31(self):
        """User formula test: 1 lakh invested on 01-01-2026 @ 24% as of 31-10-2026 (300 days) = Rs. 20,000."""
        res = calculate_compound_interest(
            principal=100000.0,
            start_date=date(2026, 1, 1),
            as_of_date=date(2026, 10, 31),
            annual_rate=24.0,
        )
        self.assertEqual(res["days_elapsed"], 300)
        self.assertEqual(res["gross_accrued_interest"], 20000.0)
        self.assertEqual(res["gross_compound_amount"], 120000.0)
        self.assertEqual(res["current_payoff_balance"], 120000.0)


class TestAnnualCapitalization30360(unittest.TestCase):
    """Tests apply_annual_capitalization under 30/360 milestones."""

    def test_zero_days(self):
        res = apply_annual_capitalization(
            principal=100000.0,
            start_date=date(2025, 1, 1),
            as_of_date=date(2025, 1, 1),
            annual_rate=24.0,
        )
        self.assertEqual(res["days_elapsed"], 0)
        self.assertEqual(res["completed_milestones"], 0)
        self.assertEqual(res["active_principal"], 100000.0)

    def test_milestone_1(self):
        res = apply_annual_capitalization(
            principal=100000.0,
            start_date=date(2025, 1, 1),
            as_of_date=date(2025, 12, 31),
            annual_rate=24.0,
        )
        self.assertEqual(res["days_elapsed"], 360)
        self.assertEqual(res["completed_milestones"], 1)
        self.assertEqual(res["active_principal"], 124000.0)
        self.assertEqual(res["total_capitalized_interest"], 24000.0)
        self.assertEqual(res["current_payoff_balance"], 124000.0)


class TestOfficeExpenseReallocation(unittest.TestCase):
    """Tests expense distribution."""

    def test_paise_discrepancy_balancing(self):
        groups = [
            {"group_id": "G1", "group_name": "Group 1", "days": 10},
            {"group_id": "G2", "group_name": "Group 2", "days": 10},
            {"group_id": "G3", "group_name": "Group 3", "days": 10},
        ]
        res = calculate_office_expense_reallocation(100.0, groups)
        shares = [g["allocated_expense"] for g in res]
        self.assertEqual(sum(shares), 100.0)


class TestWaterfallWithdrawal(unittest.TestCase):
    """Tests 3-tier withdrawal waterfall."""

    def test_tier1_principal_covered(self):
        shares = [{"investor_id": "inv1", "share_pct": 100.0}]
        res = calculate_withdrawal_waterfall(
            withdrawn_amount=50000.0,
            principal_owed=100000.0,
            interest_owed=20000.0,
            shares=shares,
        )
        self.assertEqual(res["tier1_principal_covered"], 50000.0)
        self.assertEqual(res["tier2_interest_covered"], 0.0)
        self.assertEqual(res["tier3_profit_surplus"], 0.0)

    def test_all_tiers_covered(self):
        shares = [{"investor_id": "inv1", "share_pct": 100.0}]
        res = calculate_withdrawal_waterfall(
            withdrawn_amount=130000.0,
            principal_owed=100000.0,
            interest_owed=20000.0,
            shares=shares,
        )
        self.assertEqual(res["tier1_principal_covered"], 100000.0)
        self.assertEqual(res["tier2_interest_covered"], 20000.0)
        self.assertEqual(res["tier3_profit_surplus"], 10000.0)


class TestFormattingUtilities(unittest.TestCase):
    """Tests formatting."""

    def test_round_currency(self):
        self.assertEqual(round_currency(123.456), 123.0)
        self.assertEqual(round_currency(123.5), 124.0)

    def test_format_currency_inr(self):
        self.assertEqual(format_currency_inr(1245670.0), "₹12,45,670")


if __name__ == "__main__":
    unittest.main()
