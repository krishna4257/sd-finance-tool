import unittest
import os
import sys

# Ensure project root is in python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app, get_dashboard_totals


class TestDashboardInterestDiscount(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_dashboard_totals_includes_interest_discount(self):
        # SUNNIPENTA3 vid 110013 has known interest discounts in closed_cust_account
        totals = get_dashboard_totals(110013)
        self.assertIn("sum_interest_discount", totals)
        self.assertEqual(totals["sum_interest_discount"], 22910.0)

    def test_dashboard_ssr_renders_interest_discount(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["level"] = "admin"
            sess["username"] = "admin"
            sess["vid"] = 110013

        res = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn('id="lblTotalInterestDiscount">₹22,910</span>', html)
        self.assertIn('id="lblInterestDiscountWaived">₹22,910</strong>', html)

    def test_api_dashboard_analytics_contains_interest_discount(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["level"] = "admin"
            sess["username"] = "admin"
            sess["vid"] = 110013

        res = self.client.get("/api/dashboard/analytics/110013?view=active", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        db_data = data.get("data", {})

        # Current snapshot validation
        current = db_data.get("current", {})
        self.assertIn("interest_discount", current)
        disc = current["interest_discount"]
        self.assertEqual(disc["total"], 22910.0)
        self.assertEqual(disc["accounts"], 17)
        self.assertAlmostEqual(disc["avg"], 1347.65, places=1)
        self.assertGreater(disc["pct_of_interest"], 0)

        # Trends validation
        trends = db_data.get("trends", {})
        self.assertIn("interest_discount", trends)
        self.assertIn("total", trends["interest_discount"])

        # History validation
        history = db_data.get("history", {})
        self.assertIn("weekly", history)
        self.assertIn("monthly", history)
        self.assertIn("yearly", history)
        for h in history["weekly"]:
            self.assertIn("interest_discount", h)
            self.assertIn("total", h["interest_discount"])


if __name__ == "__main__":
    unittest.main()
