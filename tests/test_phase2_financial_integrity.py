import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date

import app as main_app
from app import (
    to_decimal,
    normalize_mobile_customer_payload,
    normalize_mobile_payment_payload,
)


class TestPhase2FinancialIntegrity(unittest.TestCase):
    def setUp(self):
        main_app.app.config["TESTING"] = True
        main_app.app.config["WTF_CSRF_ENABLED"] = False
        self.app = main_app.app.test_client()

    def _set_test_session(self, user_id=1, username="admin", employee_id=10, vid=1):
        """Helper to set authenticated session with village context."""
        with self.app.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["employee_id"] = employee_id
            sess["vid"] = vid
            sess["village_code"] = f"V{vid}"
            sess["village_name"] = f"Village {vid}"

    def test_to_decimal_precision(self):
        """Verify to_decimal handles floats, ints, decimals, and formatted currency strings."""
        # Standard values
        self.assertEqual(to_decimal(100), Decimal("100"))
        self.assertEqual(to_decimal(100.5), Decimal("100.5"))
        self.assertEqual(to_decimal(Decimal("42.99")), Decimal("42.99"))

        # Empty / None handling
        self.assertEqual(to_decimal(None), Decimal("0.00"))
        self.assertEqual(to_decimal(""), Decimal("0.00"))
        self.assertEqual(to_decimal(None, default="10.00"), Decimal("10.00"))

        # Formatted currency strings (commas, currency symbols, whitespace)
        self.assertEqual(to_decimal(" ₹1,50,000.75 "), Decimal("150000.75"))
        self.assertEqual(to_decimal("$2,500.00"), Decimal("2500.00"))
        self.assertEqual(to_decimal("1,234.56"), Decimal("1234.56"))

        # Invalid fallback
        self.assertEqual(to_decimal("invalid-num"), Decimal("0.00"))

    def test_normalize_mobile_customer_payload_decimals(self):
        """Verify customer payload amounts are parsed as Decimals without float drift."""
        raw_payload = {
            "ano": "101",
            "vid": "1",
            "eid": "2",
            "name": "Ravi Kumar",
            "base_amount": "10000.00",
            "cutting_amount": "500.00",
            "interest_amount": "1500.00",
            "total_amount": "12000.00",
            "paid_amount": "2000.00",
            "type": "weekly"
        }
        normalized = normalize_mobile_customer_payload(raw_payload)

        self.assertIsInstance(normalized["base_amount"], Decimal)
        self.assertIsInstance(normalized["cutting_amount"], Decimal)
        self.assertIsInstance(normalized["interest_amount"], Decimal)
        self.assertIsInstance(normalized["total_amount"], Decimal)
        self.assertIsInstance(normalized["paid_amount"], Decimal)
        self.assertIsInstance(normalized["balance_amount"], Decimal)

        self.assertEqual(normalized["total_amount"], Decimal("12000.00"))
        self.assertEqual(normalized["balance_amount"], Decimal("10000.00"))
        self.assertEqual(normalized["type"], "W")

    def test_normalize_mobile_payment_payload_decimals(self):
        """Verify payment payload amounts are parsed as Decimals."""
        # 1. Cash payment
        cash_payload = {
            "ano": 10,
            "vid": 1,
            "eid": 2,
            "payment_type": "cash",
            "amt": "500.50",
            "payment_date": "2026-11-06"
        }
        norm_cash = normalize_mobile_payment_payload(cash_payload)
        self.assertIsInstance(norm_cash["amt"], Decimal)
        self.assertEqual(norm_cash["amt"], Decimal("500.50"))
        self.assertEqual(norm_cash["cash_amount"], Decimal("500.50"))
        self.assertEqual(norm_cash["upi_amount"], Decimal("0.00"))

        # 2. Partial payment
        partial_payload = {
            "ano": 10,
            "vid": 1,
            "eid": 2,
            "payment_type": "partial",
            "cash_amount": "300.00",
            "upi_amount": "200.00",
            "payment_date": "2026-11-06"
        }
        norm_partial = normalize_mobile_payment_payload(partial_payload)
        self.assertIsInstance(norm_partial["amt"], Decimal)
        self.assertEqual(norm_partial["amt"], Decimal("500.00"))
        self.assertEqual(norm_partial["cash_amount"], Decimal("300.00"))
        self.assertEqual(norm_partial["upi_amount"], Decimal("200.00"))

    @patch("app.audit_log")
    @patch("app.recalc_customer_balance")
    @patch("app.invalidate_village_health_cache")
    @patch("app.get_pg_connection")
    def test_delete_payment_by_pid_isolation(self, mock_get_conn, mock_invalidate, mock_recalc, mock_audit):
        """Deleting by primary key (pid) deletes strictly that payment and recalculates balance."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Mock: payment with pid=501 found in payment table
        mock_cur.fetchone.return_value = (10, 55, 1, date(2026, 11, 6), Decimal("500.00"))
        mock_cur.rowcount = 1

        self._set_test_session(vid=1)

        res = self.app.post("/delete_payment", json={"pid": 501})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Check that DELETE was called with pid = 501
        delete_call_found = False
        for call_args in mock_cur.execute.call_args_list:
            sql, params = call_args[0]
            if "DELETE FROM payment WHERE pid = %s" in sql:
                self.assertEqual(params, (501,))
                delete_call_found = True
        self.assertTrue(delete_call_found, "Expected DELETE FROM payment WHERE pid = %s")

        # Balance was recalculated for customer 10
        mock_recalc.assert_called_once_with(mock_cur, 10)
        mock_invalidate.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("app.audit_log")
    @patch("app.get_pg_connection")
    def test_delete_payment_legacy_multi_date_rejection(self, mock_get_conn, mock_audit):
        """Calling /delete_payment without pid when multiple payments exist returns 400."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Mock: 2 payments found on this date for (vid=1, ano=55)
        mock_cur.fetchall.return_value = [
            (501, 10, 55, 1, date(2026, 11, 6), Decimal("500.00")),
            (502, 10, 55, 1, date(2026, 11, 6), Decimal("300.00")),
        ]

        self._set_test_session(vid=1)

        res = self.app.post("/delete_payment", json={
            "ano": 55,
            "pdt": "2026-11-06"
        })
        self.assertEqual(res.status_code, 400)
        json_data = res.get_json()
        self.assertFalse(json_data["success"])
        self.assertIn("Multiple payments exist", json_data["error"])
        self.assertIn("pid", json_data["error"])

    @patch("app.audit_log")
    @patch("app.recalc_customer_balance")
    @patch("app.invalidate_village_health_cache")
    @patch("app.get_pg_connection")
    def test_delete_payment_legacy_single_date_fallback(self, mock_get_conn, mock_invalidate, mock_recalc, mock_audit):
        """Calling /delete_payment without pid when exactly 1 payment exists succeeds."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Mock: exactly 1 payment found
        mock_cur.fetchall.return_value = [
            (501, 10, 55, 1, date(2026, 11, 6), Decimal("500.00")),
        ]
        mock_cur.rowcount = 1

        self._set_test_session(vid=1)

        res = self.app.post("/delete_payment", json={
            "ano": 55,
            "pdt": "2026-11-06"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Primary key deletion executed for the resolved single pid
        delete_call_found = False
        for call_args in mock_cur.execute.call_args_list:
            sql, params = call_args[0]
            if "DELETE FROM payment WHERE pid = %s" in sql:
                self.assertEqual(params, (501,))
                delete_call_found = True
        self.assertTrue(delete_call_found)

    @patch("app.audit_log")
    @patch("app.get_pg_connection")
    def test_delete_payment_village_context_protection(self, mock_get_conn, mock_audit):
        """Attempting to delete a payment belonging to a different village context returns 403."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Payment belongs to vid=2, but user session is vid=1
        mock_cur.fetchone.return_value = (10, 55, 2, date(2026, 11, 6), Decimal("500.00"))

        self._set_test_session(vid=1)

        res = self.app.post("/delete_payment", json={"pid": 501})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Different village context", res.get_json()["error"])

    @patch("app.audit_log")
    @patch("app.broadcast_submission_event")
    @patch("app.invalidate_village_health_cache")
    @patch("app.recalc_customer_balance")
    @patch("app.execute_values")
    @patch("app.get_pg_connection")
    def test_accept_payment_batch_composite_keys_multi_village(
        self, mock_get_conn, mock_exec_values, mock_recalc, mock_invalidate, mock_broadcast, mock_audit
    ):
        """Batch containing payments from multiple villages with the same account number are both accepted cleanly."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Feed items:
        # Row 1: Village 1, Account 10, Amount 500
        # Row 2: Village 2, Account 10, Amount 700 (same ano, different vid!)
        mock_cur.fetchall.side_effect = [
            # 1. payment_feed_items
            [
                (1, "uuid-1", '{"vid": 1, "eid": 10, "ano": 10, "amt": 500, "payment_date": "2026-11-06", "payment_type": "cash"}', "pending"),
                (2, "uuid-2", '{"vid": 2, "eid": 10, "ano": 10, "amt": 700, "payment_date": "2026-11-06", "payment_type": "cash"}', "pending"),
            ],
            # 2. payment_feed_edits
            [],
            # 3. Customer query using composite pairs: returns both distinct customers
            [
                (101, 1, 10, Decimal("10000.00"), Decimal("0.00"), Decimal("10000.00"), date(2026, 1, 1)),
                (202, 2, 10, Decimal("15000.00"), Decimal("0.00"), Decimal("15000.00"), date(2026, 1, 1)),
            ],
        ]

        # Duplicate checks in DB (fetchone for COUNT(*)) -> return 0 (no DB duplicates)
        mock_cur.fetchone.return_value = (0,)

        self._set_test_session(vid=1)

        res = self.app.post("/feed/payment/accept_batch", json={"ids": [1, 2]})
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["accepted_count"], 2)
        self.assertEqual(data["failed_count"], 0)

        # Invalidate cache must be called for BOTH Village 1 and Village 2!
        invalidated_vids = {call[0][1] for call in mock_invalidate.call_args_list}
        self.assertIn(1, invalidated_vids)
        self.assertIn(2, invalidated_vids)

        # Broadcast events must be dispatched to their respective villages
        broadcast_vids = {call[0][0] for call in mock_broadcast.call_args_list}
        self.assertIn(1, broadcast_vids)
        self.assertIn(2, broadcast_vids)

    @patch("app.audit_log")
    @patch("app.broadcast_submission_event")
    @patch("app.invalidate_village_health_cache")
    @patch("app.recalc_customer_balance")
    @patch("app.execute_values")
    @patch("app.get_pg_connection")
    def test_accept_payment_batch_intra_batch_duplicate_handling(
        self, mock_get_conn, mock_exec_values, mock_recalc, mock_invalidate, mock_broadcast, mock_audit
    ):
        """Intra-batch duplicates for same (vid, ano, date) are caught, while different vids are allowed."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Feed items:
        # Row 1: Village 1, Account 10, Date 2026-11-06
        # Row 2: Village 1, Account 10, Date 2026-11-06 (DUPLICATE)
        # Row 3: Village 2, Account 10, Date 2026-11-06 (Same ano & date, but DIFFERENT Village!)
        mock_cur.fetchall.side_effect = [
            # 1. payment_feed_items
            [
                (1, "uuid-1", '{"vid": 1, "eid": 10, "ano": 10, "amt": 500, "payment_date": "2026-11-06", "payment_type": "cash"}', "pending"),
                (2, "uuid-2", '{"vid": 1, "eid": 10, "ano": 10, "amt": 500, "payment_date": "2026-11-06", "payment_type": "cash"}', "pending"),
                (3, "uuid-3", '{"vid": 2, "eid": 10, "ano": 10, "amt": 500, "payment_date": "2026-11-06", "payment_type": "cash"}', "pending"),
            ],
            # 2. payment_feed_edits
            [],
            # 3. Customer query
            [
                (101, 1, 10, Decimal("10000.00"), Decimal("0.00"), Decimal("10000.00"), date(2026, 1, 1)),
                (202, 2, 10, Decimal("15000.00"), Decimal("0.00"), Decimal("15000.00"), date(2026, 1, 1)),
            ],
        ]

        mock_cur.fetchone.return_value = (0,)

        self._set_test_session(vid=1)

        res = self.app.post("/feed/payment/accept_batch", json={"ids": [1, 2, 3]})
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["accepted_count"], 2)  # Row 1 and Row 3 accepted
        self.assertEqual(data["failed_count"], 1)    # Row 2 rejected as intra-batch duplicate
        self.assertIn("Multiple payments for date", data["failed_items"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
