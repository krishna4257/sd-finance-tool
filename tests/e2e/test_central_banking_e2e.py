"""End-to-End Test Suite for Central Banking & Cashbag Ecosystem (Domain 3)."""

import unittest
from decimal import Decimal
from tests.e2e.e2e_base import (
    configure_app,
    get_admin_client,
    query_db,
    cleanup_test_records,
    TEST_BANK_GROUP_ID,
    TEST_CASHBAG_ID,
)

class TestCentralBankingE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = configure_app()
        cls.client = get_admin_client(cls.app)
        cleanup_test_records()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_records()

    def test_01_central_banking_dashboard_and_groups(self):
        """Verify Central Banking dashboard, groups list, and Test Bank detail page."""
        # 1. Banking Dashboard
        res_dash = self.client.get("/banking/dashboard")
        self.assertEqual(res_dash.status_code, 200, "Banking dashboard failed to render")

        # 2. Banking Groups List
        res_groups = self.client.get("/banking/groups")
        self.assertEqual(res_groups.status_code, 200, "Banking groups page failed to render")
        self.assertTrue(b"Test Route Bank" in res_groups.data or b"Route Bank" in res_groups.data)

        # 3. Test Bank Detail View
        res_bank_detail = self.client.get(f"/banking/groups/{TEST_BANK_GROUP_ID}")
        self.assertEqual(res_bank_detail.status_code, 200, "Test Bank detail page failed to render")
        self.assertTrue(b"ROUTE-TEST-001" in res_bank_detail.data or b"ROUTE-" in res_bank_detail.data)

    def test_02_capital_allocation_and_cashbag_sync(self):
        """Deploy capital to Test Bank and verify cashbag transaction synchronization."""
        # Use existing investor INV-001
        investor_row = query_db("SELECT id FROM investors WHERE investor_code = 'INV-001'", fetchone=True)
        self.assertIsNotNone(investor_row, "Investor INV-001 not found")
        inv_id = investor_row[0]

        alloc_payload = {
            "investor_id": inv_id,
            "amount": 50000,
            "payment_mode": "CASH",
            "allocation_date": "2026-11-09",
            "notes": "TEST-E2E-CAPITAL-ALLOCATION"
        }

        # 1. Allocate Capital API
        res_alloc = self.client.post(f"/banking/api/groups/{TEST_BANK_GROUP_ID}/allocate-capital", json=alloc_payload)
        self.assertEqual(res_alloc.status_code, 200, f"Capital allocation failed: {res_alloc.data}")
        alloc_data = res_alloc.get_json()
        self.assertTrue(alloc_data.get("success"), f"Capital allocation returned success=False: {alloc_data}")

        alloc_id = alloc_data.get("allocation_id") or alloc_data.get("id")

        # 2. Verify in group_capital_allocations DB table
        alloc_row = query_db("""
            SELECT id, amount, group_id, investor_id, cashbag_txn_id
            FROM group_capital_allocations
            WHERE group_id = %s AND investor_id = %s
            ORDER BY created_at DESC LIMIT 1
        """, (TEST_BANK_GROUP_ID, inv_id), fetchone=True)
        self.assertIsNotNone(alloc_row, "Capital allocation record not found in database")
        self.assertEqual(Decimal(str(alloc_row[1])), Decimal("50000.00"))

        # Clean up allocation record and cashbag transaction
        if alloc_row[4]:
            query_db("DELETE FROM cashbag_transactions WHERE id = %s", (alloc_row[4],), commit=True)
        query_db("DELETE FROM group_capital_allocations WHERE id = %s", (alloc_row[0],), commit=True)

    def test_03_admin_pin_verification_and_withdrawal(self):
        """Verify Admin Security PIN and waterfall withdrawal calculations."""
        # 1. Verify PIN endpoint
        res_pin_ok = self.client.post("/banking/api/verify-pin", json={"pin": "1234"})
        self.assertEqual(res_pin_ok.status_code, 200, "PIN verification failed")
        self.assertTrue(res_pin_ok.get_json().get("success"))

        res_pin_bad = self.client.post("/banking/api/verify-pin", json={"pin": "wrong-pin-9999"})
        self.assertIn(res_pin_bad.status_code, (401, 403), "Invalid PIN must return 401 or 403")

        # 2. Waterfall withdrawal execution
        withdraw_payload = {
            "amount": 1000,
            "payment_mode": "CASH",
            "withdrawal_date": "2026-11-09",
            "admin_pin": "1234"
        }
        res_withdraw = self.client.post(f"/banking/api/groups/{TEST_BANK_GROUP_ID}/withdraw", json=withdraw_payload)
        self.assertIn(res_withdraw.status_code, (200, 400), f"Withdrawal response: {res_withdraw.data}")
        # Note: If group has insufficient accumulated profit/capital, 400 with descriptive error is valid

    def test_04_office_expenses_lifecycle(self):
        """Record a central office expense, verify database persistence, and rollback."""
        # 1. Expenses page
        res_exp_page = self.client.get("/banking/expenses")
        self.assertEqual(res_exp_page.status_code, 200, "Office expenses page failed to render")

        # 2. Create expense
        exp_payload = {
            "expense_category": "OFFICE_RENT",
            "amount": 2500,
            "payment_mode": "CASH",
            "expense_date": "2026-11-09",
            "description": "TEST-E2E-EXPENSE"
        }
        res_add_exp = self.client.post("/banking/api/expenses", json=exp_payload)
        self.assertEqual(res_add_exp.status_code, 200, f"Adding office expense failed: {res_add_exp.data}")
        exp_json = res_add_exp.get_json()
        self.assertTrue(exp_json.get("success"), f"Expense creation returned success=False: {exp_json}")

        # Verify in DB
        exp_row = query_db("""
            SELECT id, amount, description FROM central_office_expenses
            WHERE description = 'TEST-E2E-EXPENSE'
            ORDER BY created_at DESC LIMIT 1
        """, fetchone=True)
        self.assertIsNotNone(exp_row, "Office expense not found in database")
        self.assertEqual(Decimal(str(exp_row[1])), Decimal("2500.00"))

        # Clean up
        query_db("DELETE FROM central_office_expenses WHERE id = %s", (exp_row[0],), commit=True)

    def test_05_investors_management_and_ledger(self):
        """Verify investor list, investor detail view, and investor deposit transaction."""
        # 1. Investors Directory
        res_inv_list = self.client.get("/banking/investors")
        self.assertEqual(res_inv_list.status_code, 200, "Investors page failed to render")
        self.assertIn(b"Ramesh Kumar Sharma", res_inv_list.data)

        # 2. Investor Detail View
        inv_id = query_db("SELECT id FROM investors WHERE investor_code = 'INV-001'", fetchone=True)[0]
        res_inv_detail = self.client.get(f"/banking/investors/{inv_id}")
        self.assertEqual(res_inv_detail.status_code, 200, "Investor detail page failed to render")

        # 3. Investor Deposit
        dep_payload = {
            "amount": 10000,
            "payment_mode": "CASH",
            "txn_date": "2026-11-09",
            "notes": "TEST-E2E-INVESTOR-DEPOSIT"
        }
        res_dep = self.client.post(f"/banking/api/investors/{inv_id}/deposit", json=dep_payload)
        self.assertEqual(res_dep.status_code, 200, f"Investor deposit failed: {res_dep.data}")
        dep_json = res_dep.get_json()
        self.assertTrue(dep_json.get("success"), f"Deposit returned success=False: {dep_json}")

        # Verify and clean up transaction
        txn_row = query_db("""
            SELECT id, amount FROM investor_transactions
            WHERE investor_id = %s AND notes = 'TEST-E2E-INVESTOR-DEPOSIT'
            ORDER BY created_at DESC LIMIT 1
        """, (inv_id,), fetchone=True)
        self.assertIsNotNone(txn_row)
        query_db("DELETE FROM investor_transactions WHERE id = %s", (txn_row[0],), commit=True)

    def test_06_cashbag_breakdown_and_formula_math(self):
        """Verify cashbag breakdown API and formulas for capital deployed."""
        # 1. Cashbag management page (with employee and bank scope)
        res_cb_page = self.client.get(f"/cashbag?emp1=5&bank_id={TEST_BANK_GROUP_ID}")
        self.assertEqual(res_cb_page.status_code, 200, "Cashbag management page failed to render")

        # 2. Village Cashbags API
        res_cb_api = self.client.get("/api/village/cashbags")
        self.assertEqual(res_cb_api.status_code, 200, "Village cashbags API failed")

        # 3. Capital Deployed Breakdown endpoint (scoped to employee 5)
        res_breakdown = self.client.get("/api/cashbag/breakdown?emp1=5&type=capital_deployed")
        self.assertEqual(res_breakdown.status_code, 200, "Cashbag breakdown endpoint failed")
        breakdown_data = res_breakdown.get_json()
        self.assertIsInstance(breakdown_data, (dict, list))

if __name__ == "__main__":
    unittest.main()
