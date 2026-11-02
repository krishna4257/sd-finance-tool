"""
Unit Tests for Unified Interest Calculation Engine
SD Finance System: Smart Counting, Chit Fund, and Central Bank
"""

import unittest
from datetime import date

import interest_calc_engine as ice
import banking_calc_engine as bce
from chit_controller import calculate_loan_compound_interest


class TestUnifiedDayCount30360(unittest.TestCase):
    """Verifies strict 30/360 Indian commercial day count."""

    def test_zero_days(self):
        self.assertEqual(ice.calculate_days_30_360(date(2026, 1, 1), date(2026, 1, 1)), 0)
        self.assertEqual(ice.calculate_days_30_360(date(2026, 5, 10), date(2026, 5, 1)), 0)

    def test_user_formula_jan1_to_oct31(self):
        """User formula: Jan 1 to Oct 31 = (9 months * 30) + 30 = 300 days."""
        days = ice.calculate_days_30_360(date(2026, 1, 1), date(2026, 10, 31))
        self.assertEqual(days, 300)

    def test_single_month(self):
        """Jan 1 to Jan 31 = 30 days."""
        self.assertEqual(ice.calculate_days_30_360(date(2026, 1, 1), date(2026, 1, 31)), 30)

    def test_feb_end_of_month(self):
        """Jan 1 to Feb 28 = 60 days (strict 30 days per month)."""
        self.assertEqual(ice.calculate_days_30_360(date(2026, 1, 1), date(2026, 2, 28)), 60)

    def test_full_year(self):
        """Jan 1 to Dec 31 = 360 days."""
        self.assertEqual(ice.calculate_days_30_360(date(2026, 1, 1), date(2026, 12, 31)), 360)

    def test_mid_month(self):
        """Jan 15 to Feb 15 = 30 days."""
        self.assertEqual(ice.calculate_days_30_360(date(2026, 1, 15), date(2026, 2, 15)), 30)


class TestUnifiedInterestFormulas(unittest.TestCase):
    """Verifies user's exact linear 30/360 commercial daily interest formula."""

    def test_ramesh_1_lakh_300_days(self):
        """
        User Test Case:
        Principal = 1,00,000, Rate = 24%, Days = 300
        Interest = ((100000 * 24%) / 360) * 300 = 20,000.00
        """
        res = ice.calculate_simple_interest_30_360(100000.0, 24.0, date(2026, 1, 1), date(2026, 10, 31))
        self.assertEqual(res["days_elapsed"], 300)
        self.assertEqual(res["interest"], 20000.0)
        self.assertEqual(res["total"], 120000.0)

    def test_all_test_village_investor_tiers(self):
        """Checks multiple capital amounts and date milestones."""
        # 75,000 @ 24% for 240 days (01-Mar to 31-Oct): 75000 * 0.24 / 360 * 240 = 12,000
        r1 = ice.calculate_accrued_interest_30_360(75000.0, 24.0, date(2026, 3, 1), date(2026, 10, 31))
        self.assertEqual(r1["days_elapsed"], 240)
        self.assertEqual(r1["gross_interest"], 12000.0)

        # 60,000 @ 24% for 240 days: 60000 * 0.24 / 360 * 240 = 9,600
        r2 = ice.calculate_accrued_interest_30_360(60000.0, 24.0, date(2026, 3, 1), date(2026, 10, 31))
        self.assertEqual(r2["gross_interest"], 9600.0)

        # 50,000 @ 24% for 165 days (15-May to 31-Oct): 50000 * 0.24 / 360 * 165 = 5,500
        r3 = ice.calculate_accrued_interest_30_360(50000.0, 24.0, date(2026, 5, 15), date(2026, 10, 31))
        self.assertEqual(r3["days_elapsed"], 165)
        self.assertEqual(r3["gross_interest"], 5500.0)

        # 50,000 @ 24% for 90 days (01-Aug to 31-Oct): 50000 * 0.24 / 360 * 90 = 3,000
        r4 = ice.calculate_accrued_interest_30_360(50000.0, 24.0, date(2026, 8, 1), date(2026, 10, 31))
        self.assertEqual(r4["days_elapsed"], 90)
        self.assertEqual(r4["gross_interest"], 3000.0)


class TestBranchIntegrations(unittest.TestCase):
    """Verifies all 3 branches delegate to the unified interest engine."""

    def test_branch_central_bank_delegation(self):
        """Central Bank (banking_calc_engine) delegates to interest_calc_engine."""
        res = bce.calculate_compound_interest(100000.0, date(2026, 1, 1), date(2026, 10, 31), 24.0)
        self.assertEqual(res["days_elapsed"], 300)
        self.assertEqual(res["gross_accrued_interest"], 20000.0)
        self.assertEqual(res["current_payoff_balance"], 120000.0)

    def test_branch_chit_fund_delegation(self):
        """Chit Fund (chit_controller.calculate_loan_compound_interest) delegates to interest_calc_engine."""
        res = calculate_loan_compound_interest(100000.0, 24.0, date(2026, 1, 1), date(2026, 10, 31))
        self.assertEqual(res["days_elapsed"], 300)
        self.assertEqual(res["accrued_interest"], 20000.0)
        self.assertEqual(res["total_payoff"], 120000.0)

    def test_branch_smart_counting_loan_split(self):
        """Smart Counting flat upfront commission & cutting calculation."""
        split = ice.calculate_smart_counting_loan_split(10000.0, 10.0, 3.0)
        self.assertEqual(split["interest_amount"], 1000.0)
        self.assertEqual(split["cutting_amount"], 300.0)
        self.assertEqual(split["base_amount"], 8700.0)

    def test_branch_smart_counting_discount_validation(self):
        """Smart Counting interest discount validation rules."""
        # Valid discount: balance <= interest_amount
        valid, _ = ice.validate_interest_discount(balance_amount=500.0, interest_amount=1000.0, discount_amount=500.0)
        self.assertTrue(valid)

        # Invalid discount: balance > interest_amount (cannot discount principal base)
        invalid, err = ice.validate_interest_discount(balance_amount=1200.0, interest_amount=1000.0, discount_amount=500.0)
        self.assertFalse(invalid)
        self.assertIn("greater than interest amount", err)

        # Invalid: discount exceeds balance
        invalid2, err2 = ice.validate_interest_discount(balance_amount=500.0, interest_amount=1000.0, discount_amount=600.0)
        self.assertFalse(invalid2)
        self.assertIn("cannot exceed", err2)


if __name__ == "__main__":
    unittest.main()
