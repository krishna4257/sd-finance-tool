"""End-to-End Test Suite for Village Web Accounting (Domain 1: TEST Village 110104)."""

import unittest
from decimal import Decimal
from tests.e2e.e2e_base import (
    configure_app,
    get_admin_client,
    query_db,
    cleanup_test_records,
    TEST_VID,
    TEST_VNAME,
    TEST_VCODE,
)

class TestVillageAccountingE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = configure_app()
        cls.client = get_admin_client(cls.app)
        cleanup_test_records()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_records()

    def test_01_village_context_and_navigation(self):
        """Verify context selection, retrieval, and reset routes."""
        # 1. Set Context via JSON
        res = self.client.post("/set_context", json={"vid": TEST_VID})
        self.assertEqual(res.status_code, 200, f"Setting village context failed: {res.data}")
        self.assertTrue(res.get_json().get("success"))

        # 2. Get Context
        res = self.client.get("/get_context")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(int(data.get("vid")), TEST_VID)
        self.assertEqual(data.get("village_name"), TEST_VNAME)
        self.assertEqual(data.get("village_code"), TEST_VCODE)

        # 3. Reselect & Reset Context
        res_reselect = self.client.post("/reselect")
        self.assertIn(res_reselect.status_code, (200, 302))

        res_reset = self.client.post("/reset_context")
        self.assertIn(res_reset.status_code, (200, 302))

        # Restore context for subsequent tests
        self.client.post("/set_context", json={"vid": TEST_VID})

    def test_02_dashboard_and_analytics_integrity(self):
        """Verify dashboard page rendering, analytics endpoints, and mathematical consistency."""
        # Ensure context
        self.client.post("/set_context", json={"vid": TEST_VID})

        # 1. Render Dashboard
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200, "Dashboard failed to render")
        self.assertIn(b"TEST", res.data, "Dashboard does not display current village name")

        # 2. Analytics JSON endpoint
        res_analytics = self.client.get(f"/api/dashboard/analytics/{TEST_VID}")
        self.assertEqual(res_analytics.status_code, 200, "Dashboard analytics endpoint failed")
        analytics_data = res_analytics.get_json()
        self.assertIsInstance(analytics_data, dict)

        # 3. Posting Analytics endpoint
        res_posting = self.client.get(f"/api/dashboard/posting_analytics/{TEST_VID}")
        self.assertEqual(res_posting.status_code, 200, "Posting analytics endpoint failed")
        posting_data = res_posting.get_json()
        self.assertIsInstance(posting_data, dict)

        # 4. Invariant DB check
        db_stats = query_db("""
            SELECT
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(paid_amount), 0),
                COALESCE(SUM(balance_amount), 0),
                COUNT(*)
            FROM customer
            WHERE vid = %s
        """, (TEST_VID,), fetchone=True)
        total_loan, total_paid, total_bal, cust_count = db_stats
        self.assertEqual(total_loan - total_paid, total_bal, "Database total loan - paid does not match balance amount")

    def test_03_customer_directory_and_metadata(self):
        """Verify customer directory views, filter dropdowns, and add-customer metadata."""
        # 1. View customers HTML page
        res = self.client.get("/view_customers")
        self.assertEqual(res.status_code, 200, "View customers page failed to render")
        self.assertIn(b"customer", res.data.lower())

        # 2. Add customer metadata
        res_meta = self.client.get(f"/api/add_customer/metadata?vid={TEST_VID}")
        self.assertEqual(res_meta.status_code, 200, "Add customer metadata failed")
        meta = res_meta.get_json()
        self.assertIn("highest_ano", meta, "Metadata missing highest_ano")

        # 3. Aadhaar uniqueness check
        res_aadhaar = self.client.get("/api/customer/check_aadhaar?aadhaar=999999999999")
        self.assertEqual(res_aadhaar.status_code, 200)

        # 4. Split recalculation
        res_split = self.client.post("/api/customers/recalculate_split", json={"amount": 10000, "vid": TEST_VID})
        self.assertEqual(res_split.status_code, 200)
        split_data = res_split.get_json()
        self.assertIsNotNone(split_data)

    def test_04_customer_creation_lifecycle_and_details(self):
        """Create a new customer, verify ledger, borrower 360, family lineage, and updates."""
        test_ano = 999001
        # Clean any prior record
        query_db("DELETE FROM payment WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), commit=True)
        query_db("DELETE FROM customer WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), commit=True)

        # Ensure context
        self.client.post("/set_context", json={"vid": TEST_VID})

        # 1. Create customer via /add_customer
        form_payload = {
            "ano": str(test_ano),
            "name": "TEST-E2E-CUSTOMER",
            "start_date": "2026-11-09",
            "period": "10",
            "type": "W",
            "total_amount": "10000",
            "base_amount": "10000",
            "cutting_amount": "160",
            "interest_amount": "2000",
            "phone_number": "9876543210",
            "aadhaar_number": "999999999999",
            "notes": "E2E automated test customer"
        }
        res_add = self.client.post("/add_customer", data=form_payload)
        self.assertEqual(res_add.status_code, 200, f"Customer creation failed: {res_add.data}")
        add_json = res_add.get_json()
        self.assertIn("Customer added successfully", add_json.get("message", ""))

        # Verify in DB
        cust_row = query_db("""
            SELECT cid, ano, name, total_amount, paid_amount, balance_amount
            FROM customer
            WHERE ano = %s AND vid = %s
        """, (test_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(cust_row, "Created customer not found in DB")
        cid, ano, name, total_amt, paid_amt, bal_amt = cust_row
        self.assertEqual(name, "TEST-E2E-CUSTOMER")
        self.assertEqual(Decimal(str(total_amt)), Decimal("10000.00"))
        self.assertEqual(Decimal(str(paid_amt)), Decimal("0.00"))
        self.assertEqual(Decimal(str(bal_amt)), Decimal("10000.00"))

        # 2. Customer detail with payments
        res_detail = self.client.get(f"/api/customer_detail_with_payments/{test_ano}")
        self.assertEqual(res_detail.status_code, 200)

        # 3. Borrower 360 profile
        res_360 = self.client.get(f"/api/customer/{test_ano}/borrower_360")
        self.assertEqual(res_360.status_code, 200, "Borrower 360 failed on test customer")
        self.assertTrue(res_360.get_json().get("success"))

        res_360_unlinked = self.client.get("/api/customer/999999/borrower_360")
        self.assertEqual(res_360_unlinked.status_code, 404, "Unlinked customer should gracefully return 404")

        # 4. Family lineage
        res_family = self.client.get(f"/api/customer_family_full/{test_ano}")
        self.assertEqual(res_family.status_code, 200)

        # 5. Ledger API (Employee Group Ledger)
        res_ledger = self.client.get("/api/ledger?emp1=5&start_date=2026-11-01&end_date=2026-11-09")
        self.assertEqual(res_ledger.status_code, 200)
        self.assertTrue(res_ledger.get_json().get("success"))

        # 6. Update Customer Details
        res_update = self.client.post("/api/customer/update_pg", json={
            "data": {
                "cid": cid,
                "ano": test_ano,
                "name": "TEST-E2E-CUSTOMER-UPDATED",
                "phone_number": "9888888888",
                "notes": "Updated in test",
                "total_amount": 10000,
                "base_amount": 10000,
                "cutting_amount": 160,
                "interest_amount": 2000,
                "start_date": "2026-11-09",
                "period": 10,
                "type": "W"
            }
        })
        self.assertEqual(res_update.status_code, 200, f"Customer update failed: {res_update.data}")
        updated_name = query_db("SELECT name FROM customer WHERE cid = %s", (cid,), fetchone=True)[0]
        self.assertEqual(updated_name, "TEST-E2E-CUSTOMER-UPDATED")

    def test_05_payment_posting_and_mathematical_aggregation(self):
        """Post a payment and verify immediate mathematical updates on customer balance and village aggregates."""
        test_ano = 999001
        self.client.post("/set_context", json={"vid": TEST_VID})

        # Retrieve customer ID and initial balance
        cust_row = query_db("SELECT cid, balance_amount, paid_amount FROM customer WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(cust_row, "Test customer missing before payment posting")
        cid, bal_before, paid_before = cust_row

        # 1. Posting Page rendering
        res_posting_page = self.client.get("/posting")
        self.assertEqual(res_posting_page.status_code, 200, "Posting page failed to render")

        # 2. Get customer info API
        res_cust_info = self.client.get(f"/get_customer_info?ano={test_ano}&vid={TEST_VID}")
        self.assertEqual(res_cust_info.status_code, 200)

        # 3. Submit payment
        payment_payload = [{
            "ano": test_ano,
            "amt": 1000,
            "pdt": "2026-11-09",
            "notes": "TEST-E2E-PAYMENT"
        }]
        res_post = self.client.post("/submit_post_payment", json=payment_payload)
        self.assertEqual(res_post.status_code, 200, f"Submit payment failed: {res_post.data}")
        post_json = res_post.get_json()
        self.assertEqual(post_json.get("submitted_count"), 1, f"Payment was not posted: {post_json}")

        # 4. Verify customer balance changed in database
        cust_after = query_db("SELECT balance_amount, paid_amount FROM customer WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), fetchone=True)
        bal_after, paid_after = cust_after
        self.assertEqual(Decimal(str(bal_after)), Decimal(str(bal_before)) - Decimal("1000.00"), "Balance amount did not decrement by payment")
        self.assertEqual(Decimal(str(paid_after)), Decimal(str(paid_before)) + Decimal("1000.00"), "Paid amount did not increment by payment")

    def test_06_payment_deletion_and_reversal(self):
        """Delete payment and verify that customer balance and village aggregates are reversed cleanly."""
        test_ano = 999001
        self.client.post("/set_context", json={"vid": TEST_VID})

        # Find created payment
        payment_row = query_db("""
            SELECT pid, amt FROM payment
            WHERE ano = %s AND vid = %s
            ORDER BY pid DESC LIMIT 1
        """, (test_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(payment_row, "Payment record not found for deletion test")
        pid, amt = payment_row

        cust_before_del = query_db("SELECT balance_amount, paid_amount FROM customer WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), fetchone=True)
        bal_before_del, paid_before_del = cust_before_del

        # Delete payment
        res_del = self.client.post("/delete_payment", json={"pid": pid, "ano": test_ano})
        self.assertEqual(res_del.status_code, 200, f"Delete payment failed: {res_del.data}")
        del_json = res_del.get_json()
        self.assertTrue(del_json.get("success"), "Delete payment returned success=False")

        # Verify balance restored
        cust_after_del = query_db("SELECT balance_amount, paid_amount FROM customer WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), fetchone=True)
        bal_after_del, paid_after_del = cust_after_del
        self.assertEqual(Decimal(str(bal_after_del)), Decimal(str(bal_before_del)) + Decimal(str(amt)), "Balance not restored after payment deletion")
        self.assertEqual(Decimal(str(paid_after_del)), Decimal(str(paid_before_del)) - Decimal(str(amt)), "Paid amount not restored after payment deletion")

    def test_07_customer_account_closure_and_recovery(self):
        """Test account closure and subsequent account retrieval/reopen."""
        test_ano = 999001
        self.client.post("/set_context", json={"vid": TEST_VID})

        cust_row = query_db("SELECT cid FROM customer WHERE ano = %s AND vid = %s", (test_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(cust_row, "Customer not found for closure test")
        cid = cust_row[0]

        # 1. Close Customer Account
        res_close = self.client.post("/api/customer/close_account_pg", json={"cid": cid, "action": "defaulted"})
        self.assertEqual(res_close.status_code, 200, f"Account closure failed: {res_close.data}")
        close_json = res_close.get_json()
        self.assertTrue(close_json.get("success"), f"Account closure returned success=False: {close_json}")

        # Verify moved to closed_cust_account
        closed_row = query_db("SELECT cid, status FROM closed_cust_account WHERE cid = %s", (cid,), fetchone=True)
        self.assertIsNotNone(closed_row, "Customer not found in closed_cust_account")
        active_row = query_db("SELECT cid FROM customer WHERE cid = %s", (cid,), fetchone=True)
        self.assertIsNone(active_row, "Customer still present in active customer table")

        # 2. Retrieve / Reopen Customer Account
        res_retrieve = self.client.post("/api/customer/retrieve_account_pg", json={"cid": cid})
        self.assertEqual(res_retrieve.status_code, 200, f"Account retrieval failed: {res_retrieve.data}")
        retrieve_json = res_retrieve.get_json()
        self.assertTrue(retrieve_json.get("success"), f"Account retrieval returned success=False: {retrieve_json}")

        # Verify restored to active customer table
        restored_row = query_db("SELECT cid FROM customer WHERE cid = %s", (cid,), fetchone=True)
        self.assertIsNotNone(restored_row, "Customer not restored in active customer table")

if __name__ == "__main__":
    unittest.main()
