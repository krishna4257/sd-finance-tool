import os
import unittest
from datetime import datetime, date
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()
os.environ["DISABLE_SECURE_COOKIE"] = "1"
os.environ["FLASK_ENV"] = "testing"

from app import app
from db import get_pg_connection

class TestRowsAndWithdrawnTile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "Admin"
            sess["role"] = "superadmin"

    def test_cashbag_rows_to_load_and_withdrawn_tile(self):
        """Verify that limit parameter works and Amount Withdrawn tile renders."""
        # 1. Test GET /cashbag?emp1=5 with limit=1000
        response = self.client.get("/cashbag?emp1=5&limit=1000")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # Check Rows to Load input has value 1000
        self.assertIn('name="limit" value="1000"', html)

        # Check Amount Withdrawn card is present
        self.assertIn("Amount Withdrawn", html)
        self.assertIn("openCapitalWithdrawnModal()", html)
        self.assertIn("capitalWithdrawnModal", html)

        # Check Amount Withdrawn shows ₹100,000
        self.assertIn("₹100,000", html)

    def test_cashbag_breakdown_api_withdrawn(self):
        """Verify breakdown API handles capital_withdrawn."""
        response = self.client.get("/api/cashbag/breakdown?emp1=5&type=capital_withdrawn")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        tree = data.get("tree", [])
        self.assertGreater(len(tree), 0)
        # Check total amount in tree
        total_tree_amt = sum(m["total_amount"] for m in tree)
        self.assertEqual(abs(total_tree_amt), 100000.0)

    def test_village_bank_withdrawn_tile_and_ledger_modal(self):
        """Verify that Village Bank detail page renders Amount Withdrawn KPI card and modal."""
        bank_id = "40481968-2a6d-4b65-92d9-dc3cbd54a41f"
        response = self.client.get(f"/banking/groups/{bank_id}")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")

        # Check Amount Withdrawn KPI card is present
        self.assertIn("Amount Withdrawn", html)
        self.assertIn("openWithdrawalsLedgerModal()", html)
        self.assertIn("withdrawalsLedgerModal", html)
        self.assertIn("waterfallWithdrawalsSection", html)

        # Check Amount Withdrawn shows ₹100,000
        self.assertIn("₹100,000", html)
        self.assertIn("Withdrawals Ledger", html)

if __name__ == "__main__":
    unittest.main()
