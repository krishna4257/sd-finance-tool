"""End-to-End Test Suite for Chit Fund System (Domain 4: Test Chit Group 987b8c46-d51b-4289-82e9-501a730f9e3d)."""

import unittest
from decimal import Decimal
from tests.e2e.e2e_base import (
    configure_app,
    get_admin_client,
    query_db,
    cleanup_test_records,
    TEST_CHIT_GROUP_ID,
)

class TestChitFundE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = configure_app()
        cls.client = get_admin_client(cls.app)
        cleanup_test_records()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_records()

    def test_01_chit_dashboard_and_views(self):
        """Verify chit fund dashboard, group lists, members, auctions, and accounting pages."""
        # 1. Chit Dashboard
        res_dash = self.client.get("/chit/dashboard")
        self.assertEqual(res_dash.status_code, 200, "Chit dashboard failed to render")

        # 2. Chit Groups Directory
        res_groups = self.client.get("/chit/groups")
        self.assertEqual(res_groups.status_code, 200, "Chit groups page failed to render")
        self.assertIn(b"Chit Groups", res_groups.data)

        # 3. Test Chit Group Edit Page
        res_edit = self.client.get(f"/chit/groups/{TEST_CHIT_GROUP_ID}/edit")
        self.assertEqual(res_edit.status_code, 200, "Chit group edit page failed to render")

        # 4. Members Directory
        res_members = self.client.get("/chit/members")
        self.assertEqual(res_members.status_code, 200, "Chit members page failed to render")

        # 5. Auctions, Schedules, Reports, and Accounting Pages
        for route in ("/chit/auctions", "/chit/reports", "/chit/accounting"):
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Page {route} failed to render")

    def test_02_chit_group_apis_and_schedules(self):
        """Verify chit groups listing, month schedules, and payouts summary APIs."""
        # 1. Groups JSON API
        res_groups = self.client.get("/chit/api/chitgroups")
        self.assertEqual(res_groups.status_code, 200, "Chit groups API failed")
        groups_data = res_groups.get_json()
        self.assertIsInstance(groups_data, (list, dict))

        # 2. Months Schedule for Test Chit Group
        res_months = self.client.get(f"/chit/api/chitgroups/{TEST_CHIT_GROUP_ID}/months")
        self.assertEqual(res_months.status_code, 200, "Chit months API failed")
        months_data = res_months.get_json()
        self.assertIsInstance(months_data, (list, dict))

        # 3. Payouts Summary
        res_payouts = self.client.get(f"/chit/api/chitgroups/{TEST_CHIT_GROUP_ID}/payouts-summary")
        self.assertEqual(res_payouts.status_code, 200, "Chit payouts summary API failed")

    def test_03_member_profile_and_folio(self):
        """Verify member detail page, folio, commitments, and default toggle."""
        # Target existing member in Test group
        member_row = query_db("""
            SELECT m.id, m.full_name FROM chit_members m
            JOIN chit_memberships ms ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s LIMIT 1
        """, (TEST_CHIT_GROUP_ID,), fetchone=True)
        self.assertIsNotNone(member_row, "No member found in Test Chit Group")
        member_id, full_name = member_row

        # 1. Member Detail View
        res_mem_page = self.client.get(f"/chit/members/{member_id}")
        self.assertEqual(res_mem_page.status_code, 200, "Member detail page failed to render")

        # 2. Member Folio API
        res_folio = self.client.get(f"/chit/api/members/{member_id}/folio")
        self.assertEqual(res_folio.status_code, 200, "Member folio API failed")

        # 3. Member Summary API
        res_summary = self.client.get(f"/chit/api/members/{member_id}/summary")
        self.assertEqual(res_summary.status_code, 200, "Member summary API failed")

        # 4. Toggle Default Status and Revert
        res_def_on = self.client.post(f"/chit/api/members/{member_id}/toggle-default", json={"is_defaulted": True, "reason": "E2E Test"})
        self.assertEqual(res_def_on.status_code, 200)
        self.assertTrue(res_def_on.get_json().get("success"))

        res_def_off = self.client.post(f"/chit/api/members/{member_id}/toggle-default", json={"is_defaulted": False})
        self.assertEqual(res_def_off.status_code, 200)
        self.assertTrue(res_def_off.get_json().get("success"))

    def test_04_chit_quick_payment_and_receipt(self):
        """Record quick installment payment, verify database insertion, receipt endpoint, and rollback."""
        # Locate membership in Test Chit Group
        ms_row = query_db("SELECT id FROM chit_memberships WHERE chit_group_id = %s LIMIT 1", (TEST_CHIT_GROUP_ID,), fetchone=True)
        self.assertIsNotNone(ms_row, "No membership found for quick payment test")
        membership_id = ms_row[0]

        payment_payload = {
            "membership_id": membership_id,
            "amount": 5000,
            "payment_mode": "Cash",
            "payment_date": "2026-11-09",
            "notes": "TEST-E2E-CHIT-PAYMENT"
        }

        # 1. Record quick payment
        res_pay = self.client.post("/chit/api/payments/quick-pay", json=payment_payload)
        self.assertEqual(res_pay.status_code, 200, f"Quick pay failed: {res_pay.data}")
        pay_json = res_pay.get_json()
        self.assertTrue(pay_json.get("success"), f"Quick pay returned success=False: {pay_json}")

        payment_id = pay_json.get("payment_id") or pay_json.get("id")

        # 2. Verify in DB by payment_id
        self.assertIsNotNone(payment_id, "Quick pay did not return payment_id")
        db_pay = query_db("""
            SELECT id, amount, notes FROM chit_payments
            WHERE id = %s
        """, (payment_id,), fetchone=True)
        self.assertIsNotNone(db_pay, "Chit payment not found in DB")
        self.assertEqual(Decimal(str(db_pay[1])), Decimal("5000.00"))

        # 3. Receipt Details API
        res_receipt = self.client.get(f"/chit/api/receipts/payment/{payment_id}")
        self.assertEqual(res_receipt.status_code, 200, "Receipt details API failed")

        # Clean up payment record
        query_db("DELETE FROM chit_payments WHERE id = %s", (payment_id,), commit=True)

    def test_05_chit_accounting_and_reports(self):
        """Verify chit accounting overview, trend, and reports data APIs."""
        # 1. Accounting Overview API
        res_acc = self.client.get("/chit/api/accounting/overview")
        self.assertEqual(res_acc.status_code, 200, "Accounting overview API failed")
        acc_data = res_acc.get_json()
        self.assertIsInstance(acc_data, dict)

        # 2. Reports Data API
        res_rep = self.client.get("/chit/api/reports/data")
        self.assertEqual(res_rep.status_code, 200, "Reports data API failed")

        # 3. Dashboard Trend API
        res_trend = self.client.get("/chit/api/dashboard/trend")
        self.assertEqual(res_trend.status_code, 200, "Dashboard trend API failed")

if __name__ == "__main__":
    unittest.main()
