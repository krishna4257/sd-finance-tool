import unittest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app import app
from routes.mobile_api_routes import mobile_bp


class TestPostingUpdateAndDuplicates(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def test_mobile_ping(self):
        """Verify /api/mobile/ping returns 200 and status ok."""
        res = self.client.get("/api/mobile/ping")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("timestamp", data)

    @patch("app.get_pg_connection")
    @patch("app.invalidate_village_health_cache")
    def test_update_payment_date_bulk(self, mock_invalidate, mock_get_conn):
        """Verify update_payment_date_bulk updates payment_date, updated_at and payment_feed_items."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [] # no duplicate conflicts

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["employee_id"] = 10
            sess["vid"] = 101
            sess["village_code"] = "V101"
            sess["village_name"] = "Village 101"

        payload = {
            "find_date": "14-11-2026",
            "replace_date": "10-11-2026"
        }
        res = self.client.post("/update_payment_date_bulk", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

        # Verify SQL statements executed
        executed_sqls = [call[0][0] for call in mock_cur.execute.call_args_list]
        self.assertTrue(any("UPDATE payment" in sql and "updated_at = NOW()" in sql for sql in executed_sqls))
        self.assertTrue(any("UPDATE payment_feed_items" in sql for sql in executed_sqls))
        mock_conn.commit.assert_called_once()
        mock_invalidate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
