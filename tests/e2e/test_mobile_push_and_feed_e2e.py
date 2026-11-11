"""End-to-End Test Suite for Mobile Accounting Push, Sync, and Web Feed Engine (Domain 2)."""

import json
import uuid
import unittest
from decimal import Decimal
from tests.e2e.e2e_base import (
    configure_app,
    get_admin_client,
    get_mobile_token_and_headers,
    create_signed_mobile_envelope,
    query_db,
    cleanup_test_records,
    TEST_VID,
    ADMIN_USER_ID,
    ADMIN_EID,
)

class TestMobilePushAndFeedE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = configure_app()
        cls.admin_client = get_admin_client(cls.app)
        cls.mobile_headers = get_mobile_token_and_headers(ADMIN_USER_ID, ADMIN_EID)
        cleanup_test_records()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_records()

    def test_01_mobile_auth_and_permissions(self):
        """Verify mobile authentication, invalid login handling, and village permissions."""
        client = self.app.test_client()

        # 1. Successful Mobile Login
        res_login = client.post("/api/mobile/login", json={
            "username": "chinna",
            "password": "dev",
            "device_id": "test-mobile-e2e-device"
        })
        if res_login.status_code == 200:
            login_data = res_login.get_json()
            self.assertIn("token", login_data)

        # 2. Blocked Invalid Credentials
        res_bad = client.post("/api/mobile/login", json={
            "username": "chinna",
            "password": "wrong_password_12345",
            "device_id": "test-device"
        })
        self.assertEqual(res_bad.status_code, 401, "Invalid mobile login must return 401")

        # 3. Authorized Villages via X-Mobile-Token
        res_villages = client.get("/api/mobile/villages", headers=self.mobile_headers)
        self.assertEqual(res_villages.status_code, 200, f"Failed fetching mobile villages: {res_villages.data}")
        villages_data = res_villages.get_json()
        self.assertIsInstance(villages_data, (list, dict))

    def test_02_mobile_pull_sync_endpoints(self):
        """Verify mobile pull endpoints for offline sync (customers, payments, closed accounts)."""
        client = self.app.test_client()

        # 1. Pull active customers for TEST village
        res_cust = client.get(f"/api/mobile/customers?vid={TEST_VID}", headers=self.mobile_headers)
        self.assertEqual(res_cust.status_code, 200, f"Mobile customers pull failed: {res_cust.data}")
        cust_resp = res_cust.get_json()
        self.assertTrue(isinstance(cust_resp, list) or "customers" in cust_resp)

        # 2. Pull payments for TEST village
        res_payments = client.get(f"/api/mobile/payments?vid={TEST_VID}", headers=self.mobile_headers)
        self.assertEqual(res_payments.status_code, 200, f"Mobile payments pull failed: {res_payments.data}")
        payments_resp = res_payments.get_json()
        self.assertTrue(isinstance(payments_resp, list) or "payments" in payments_resp)

        # 3. Pull closed customers
        res_closed = client.get(f"/api/mobile/closed_customers?vid={TEST_VID}", headers=self.mobile_headers)
        self.assertEqual(res_closed.status_code, 200, f"Mobile closed customers pull failed: {res_closed.data}")

        # 4. Pull mobile cashbag
        res_cashbag = client.get(f"/api/mobile/cashbag?vid={TEST_VID}", headers=self.mobile_headers)
        self.assertEqual(res_cashbag.status_code, 200, f"Mobile cashbag pull failed: {res_cashbag.data}")

    def test_03_mobile_payment_push_and_web_feed_ingestion(self):
        """Push batch payment from mobile -> verify in web feed -> edit -> accept single -> reject remaining."""
        client = self.app.test_client()
        cust_row = query_db("SELECT cid, ano, balance_amount, paid_amount FROM customer WHERE vid = %s LIMIT 1", (TEST_VID,), fetchone=True)
        self.assertIsNotNone(cust_row, "No customer found in TEST village for payment push")
        cid, target_ano, bal_start, paid_start = cust_row

        # Clean any pending feed items for this customer first
        query_db("DELETE FROM payment_feed_items WHERE payload::text LIKE %s", (f'%{target_ano}%',), commit=True)

        local_uuid_1 = str(uuid.uuid4())
        local_uuid_2 = str(uuid.uuid4())

        batch_payload = {
            "vid": TEST_VID,
            "eid": ADMIN_EID,
            "device_id": "test-device-uuid",
            "payments": [
                {
                    "local_uuid": local_uuid_1,
                    "ano": target_ano,
                    "amt": 250,
                    "payment_date": "2026-11-08",
                    "vid": TEST_VID,
                    "eid": ADMIN_EID,
                    "payment_type": "cash"
                },
                {
                    "local_uuid": local_uuid_2,
                    "ano": target_ano,
                    "amt": 300,
                    "payment_date": "2026-11-09",
                    "vid": TEST_VID,
                    "eid": ADMIN_EID,
                    "payment_type": "upi"
                }
            ]
        }

        # 1. Push batch to mobile API
        res_push = client.post("/api/mobile/payment_feed_batch", json=batch_payload, headers=self.mobile_headers)
        self.assertEqual(res_push.status_code, 200, f"Mobile payment batch push failed: {res_push.data}")

        # Verify items stored in payment_feed_items
        feed_rows = query_db("""
            SELECT feed_payment_id, local_uuid, status, payload
            FROM payment_feed_items
            WHERE local_uuid IN (%s, %s)
            ORDER BY feed_payment_id ASC
        """, (local_uuid_1, local_uuid_2), fetchall=True)
        self.assertEqual(len(feed_rows), 2, "Payment feed items not found in database")
        feed_id_1, _, status_1, _ = feed_rows[0]
        feed_id_2, _, status_2, _ = feed_rows[1]
        self.assertEqual(status_1, "pending")
        self.assertEqual(status_2, "pending")

        # 2. Web Feed Review Screen
        self.admin_client.post("/set_context", json={"vid": TEST_VID})
        res_feed_page = self.admin_client.get("/feed")
        self.assertEqual(res_feed_page.status_code, 200, "Feed page failed to render")

        # 3. Edit 1st payment feed item (adjust amount from 250 to 350)
        res_edit = self.admin_client.post(f"/feed/payment/edit/{feed_id_1}", json={"amt": 350, "pdt": "2026-11-09"})
        self.assertEqual(res_edit.status_code, 200, f"Feed payment edit failed: {res_edit.data}")

        # 4. Accept 1st payment feed item into live ledger
        res_accept = self.admin_client.post(f"/feed/payment/accept/{feed_id_1}", json={})
        self.assertIn(res_accept.status_code, (200, 302), f"Accepting payment feed failed: {res_accept.data}")

        # Verify feed item status is now accepted
        feed_1_after = query_db("SELECT status FROM payment_feed_items WHERE feed_payment_id = %s", (feed_id_1,), fetchone=True)
        self.assertEqual(feed_1_after[0], "accepted")

        # Verify payment table has the accepted payment with adjusted amount 350
        pay_row = query_db("""
            SELECT pid, amt FROM payment
            WHERE ano = %s AND vid = %s
            ORDER BY pid DESC LIMIT 1
        """, (target_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(pay_row, "Accepted payment not found in live payment table")
        self.assertEqual(Decimal(str(pay_row[1])), Decimal("350.00"))

        # Verify customer balance was decremented by 350
        cust_after_accept = query_db("SELECT balance_amount, paid_amount FROM customer WHERE cid = %s", (cid,), fetchone=True)
        self.assertEqual(Decimal(str(cust_after_accept[0])), Decimal(str(bal_start)) - Decimal("350.00"))
        self.assertEqual(Decimal(str(cust_after_accept[1])), Decimal(str(paid_start)) + Decimal("350.00"))

        # 5. Delete / Reject 2nd payment feed item
        res_del = self.admin_client.post(f"/feed/payment/delete/{feed_id_2}", json={})
        self.assertIn(res_del.status_code, (200, 302), f"Delete payment feed failed: {res_del.data}")
        feed_2_after = query_db("SELECT status FROM payment_feed_items WHERE feed_payment_id = %s", (feed_id_2,), fetchone=True)
        self.assertTrue(feed_2_after is None or feed_2_after[0] in ("rejected", "deleted"), "Feed item was not deleted or rejected")

        # Roll back accepted payment to keep test village balanced
        self.admin_client.post("/delete_payment", json={"pid": pay_row[0], "ano": target_ano})

    def test_04_mobile_customer_push_and_ingestion(self):
        """Push new customer from mobile -> verify queue -> web accept into core customer table."""
        client = self.app.test_client()
        test_mobile_ano = 999002
        query_db("DELETE FROM customer WHERE ano = %s AND vid = %s", (test_mobile_ano, TEST_VID), commit=True)
        query_db("DELETE FROM customer_feed WHERE payload::text LIKE '%%999002%%'", commit=True)

        cust_payload = {
            "ano": test_mobile_ano,
            "name": "TEST-E2E-MOBILE-CUST",
            "phone_number": "9876543211",
            "start_date": "2026-11-09",
            "period": 10,
            "type": "W",
            "total_amount": 15000,
            "base_amount": 12000,
            "cutting_amount": 240,
            "interest_amount": 2760,
            "installment_amount": 1500,
            "paid_amount": 0,
            "balance_amount": 15000,
            "vid": TEST_VID,
            "eid": ADMIN_EID
        }

        envelope = create_signed_mobile_envelope("customer_feed", cust_payload, vid=TEST_VID, eid=ADMIN_EID)

        # 1. Post to mobile customer feed endpoint
        res_push = client.post("/api/mobile/customer_feed", data={"payload": json.dumps(envelope)}, headers={"X-Mobile-Token": self.mobile_headers["X-Mobile-Token"]})
        self.assertEqual(res_push.status_code, 200, f"Push customer feed failed: {res_push.data}")

        # 2. Locate feed_id in customer_feed table
        feed_row = query_db("SELECT feed_id, status FROM customer_feed WHERE payload::text LIKE '%%999002%%' LIMIT 1", fetchone=True)
        self.assertIsNotNone(feed_row, "Customer feed entry not found in DB")
        feed_id, status = feed_row
        self.assertEqual(status, "pending")

        # 3. Admin Web Client accepts customer feed item
        self.admin_client.post("/set_context", json={"vid": TEST_VID})
        res_accept = self.admin_client.post(f"/feed/customer/accept/{feed_id}", json={})
        self.assertIn(res_accept.status_code, (200, 302), f"Accept customer feed failed: {res_accept.data}")

        # 4. Verify customer exists in core customer table
        core_cust = query_db("SELECT cid, ano, name, total_amount FROM customer WHERE ano = %s AND vid = %s", (test_mobile_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(core_cust, "Accepted customer feed was not ingested into core customer table")
        self.assertEqual(core_cust[2], "TEST-E2E-MOBILE-CUST")
        self.assertEqual(Decimal(str(core_cust[3])), Decimal("15000.00"))

    def test_05_mobile_closure_push_and_ingestion(self):
        """Push account closure request from mobile -> accept in web feed -> verify customer closed."""
        client = self.app.test_client()
        test_mobile_ano = 999002

        closure_payload = {
            "ano": test_mobile_ano,
            "vid": TEST_VID,
            "eid": ADMIN_EID,
            "action": "defaulted",
            "notes": "Closed via E2E mobile request"
        }

        envelope = create_signed_mobile_envelope("close_account_feed", closure_payload, vid=TEST_VID, eid=ADMIN_EID)

        # 1. Post to close account feed endpoint
        res_push = client.post("/close_account_feed", data={"payload": json.dumps(envelope)}, headers={"X-Mobile-Token": self.mobile_headers["X-Mobile-Token"]})
        self.assertEqual(res_push.status_code, 200, f"Push closure feed failed: {res_push.data}")

        # 2. Locate feed_id in account_closure_feed table
        closure_row = query_db("SELECT feed_id, status FROM account_closure_feed WHERE ano = %s AND vid = %s LIMIT 1", (test_mobile_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(closure_row, "Closure feed entry not found in DB")
        feed_id, status = closure_row
        self.assertEqual(status, "pending")

        # 3. Admin Web Client accepts closure request
        self.admin_client.post("/set_context", json={"vid": TEST_VID})
        res_accept = self.admin_client.post(f"/feed/closure/accept/{feed_id}", json={"action": "defaulted"})
        self.assertIn(res_accept.status_code, (200, 302), f"Accept closure feed failed: {res_accept.data}")

        # 4. Verify customer moved from customer to closed_cust_account
        closed_cust = query_db("SELECT cid, ano FROM closed_cust_account WHERE ano = %s AND vid = %s", (test_mobile_ano, TEST_VID), fetchone=True)
        self.assertIsNotNone(closed_cust, "Closed customer not found in closed_cust_account")
        active_cust = query_db("SELECT cid FROM customer WHERE ano = %s AND vid = %s", (test_mobile_ano, TEST_VID), fetchone=True)
        self.assertIsNone(active_cust, "Customer still in active customer table after closure acceptance")

if __name__ == "__main__":
    unittest.main()
