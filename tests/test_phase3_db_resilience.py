import os
import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date, datetime

import app as main_app
import db
from db import get_pool_stats, DB_POOL_MIN, DB_POOL_MAX, PooledConnection
from app import audit_log


class TestPhase3DbResilience(unittest.TestCase):
    def setUp(self):
        main_app.app.config["TESTING"] = True
        main_app.app.config["WTF_CSRF_ENABLED"] = False
        self.app = main_app.app.test_client()

    def _set_test_session(self, user_id=1, username="admin", level="admin", vid=1):
        """Helper to set authenticated session with village context."""
        with self.app.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["level"] = level
            sess["vid"] = vid
            sess["village_code"] = f"V{vid}"
            sess["village_name"] = f"Village {vid}"

    def test_pool_configuration_defaults(self):
        """Verify connection pool defaults: min=2, max=12."""
        self.assertEqual(DB_POOL_MIN, 2)
        self.assertEqual(DB_POOL_MAX, 12)

    def test_pool_configuration_env_override(self):
        """Verify pool limits can be customized via environment variables."""
        with patch.dict(os.environ, {"DB_POOL_MIN": "4", "DB_POOL_MAX": "16"}):
            with patch("db.ThreadedConnectionPool") as mock_pool_cls:
                # Force pool re-initialization by resetting _pg_pool
                db._pg_pool = None
                db._pool_pid = None
                db.get_pool()
                mock_pool_cls.assert_called_once()
                _, kwargs = mock_pool_cls.call_args
                self.assertEqual(kwargs.get("minconn"), 4)
                self.assertEqual(kwargs.get("maxconn"), 16)
        # Restore pool state
        db._pg_pool = None
        db._pool_pid = None

    def test_pool_stats_reporting(self):
        """Verify get_pool_stats returns accurate dictionary structure."""
        mock_pool = MagicMock()
        mock_pool._used = {"c1": 1, "c2": 2}
        mock_pool._pool = [3, 4, 5]
        mock_pool.maxconn = 12

        with patch("db.get_pool", return_value=mock_pool):
            stats = get_pool_stats()
            self.assertEqual(stats["pid"], os.getpid())
            self.assertEqual(stats["used_connections"], 2)
            self.assertEqual(stats["available_connections"], 3)
            self.assertEqual(stats["max_connections"], 12)
            self.assertEqual(stats["utilization_pct"], 16.7)

    @patch("app.get_pg_connection")
    def test_audit_log_atomic_with_cursor(self, mock_get_conn):
        """When cur is provided, audit_log writes to cur directly without taking a new connection."""
        mock_cur = MagicMock()

        audit_log(
            action="delete_payment",
            entity_type="payment",
            entity_id="101",
            details={"ano": 10, "amt": "500.00"},
            status="success",
            cur=mock_cur
        )

        # Must execute on the passed cursor
        mock_cur.execute.assert_called_once()
        sql, params = mock_cur.execute.call_args[0]
        self.assertIn("INSERT INTO audit_log", sql)
        self.assertEqual(params[0], "delete_payment")
        self.assertEqual(params[1], "payment")
        self.assertEqual(params[2], "101")

        # Must NOT acquire a new database connection from the pool!
        mock_get_conn.assert_not_called()

    @patch("app.get_pg_connection")
    def test_audit_log_standalone_without_cursor(self, mock_get_conn):
        """When cur is None, audit_log acquires an independent connection, commits, and closes."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        audit_log(
            action="login",
            entity_type="user",
            entity_id=1,
            details={"username": "admin"},
            status="success",
            cur=None
        )

        mock_get_conn.assert_called_once()
        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_audit_log_handles_decimals_dates_and_nested_objects(self):
        """Verify audit_log safely serializes complex objects (Decimal, date, datetime) without crash."""
        mock_cur = MagicMock()

        details_payload = {
            "amount": Decimal("1500.50"),
            "due_date": date(2026, 11, 6),
            "timestamp": datetime(2026, 11, 6, 12, 0, 0),
            "items": [{"id": 1, "balance": Decimal("500.00")}]
        }

        # Should execute cleanly without raising TypeError
        audit_log(
            action="complex_tx",
            entity_type="account",
            entity_id=99,
            details=details_payload,
            cur=mock_cur
        )

        mock_cur.execute.assert_called_once()
        sql, params = mock_cur.execute.call_args[0]
        details_json_str = params[10]
        self.assertIn('"amount": "1500.50"', details_json_str)
        self.assertIn('"due_date": "2026-11-06"', details_json_str)
        self.assertIn('"balance": "500.00"', details_json_str)

    def test_pooled_connection_context_manager_cleanup(self):
        """Verify PooledConnection resets state via rollback and puts connection back into pool upon exit."""
        mock_raw_conn = MagicMock()
        mock_pool = MagicMock()

        with PooledConnection(mock_raw_conn, mock_pool) as conn:
            self.assertIsNotNone(conn)

        # Upon exiting context manager:
        # 1. Rollback must be called so no dirty transaction leaks
        mock_raw_conn.rollback.assert_called_once()
        # 2. Connection returned to pool
        mock_pool.putconn.assert_called_once_with(mock_raw_conn)

    def test_phase3_performance_indexes_sql_syntax(self):
        """Verify SQL migration script exists and defines idempotent indexes on all required tables."""
        sql_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sql_scripts",
            "phase3_performance_indexes.sql"
        )
        self.assertTrue(os.path.exists(sql_path), "Missing phase3_performance_indexes.sql")

        with open(sql_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_indexes = [
            "idx_payment_cid",
            "idx_payment_vid_ano_date",
            "idx_payment_date",
            "idx_closed_payment_cid",
            "idx_historic_payment_cid",
            "idx_customer_vid_ano",
            "idx_customer_vid_status",
            "idx_closed_customer_vid_ano",
            "idx_historic_customer_vid_ano",
            "idx_loan_link_cid_tier",
            "idx_loan_link_ucid",
            "idx_audit_log_created_at"
        ]

        for idx_name in required_indexes:
            self.assertIn(f"CREATE INDEX IF NOT EXISTS {idx_name}", content)

    @patch("app.get_pool_stats")
    def test_health_db_pool_endpoint_permissions(self, mock_stats):
        """Verify /api/health/db_pool allows admin/mgmt and rejects staff with 403."""
        mock_stats.return_value = {
            "pid": 1234,
            "used_connections": 2,
            "available_connections": 10,
            "max_connections": 12,
            "utilization_pct": 16.7
        }

        # 1. Staff access denied (403)
        self._set_test_session(level="staff")
        res = self.app.get("/api/health/db_pool")
        self.assertEqual(res.status_code, 403)
        self.assertFalse(res.get_json()["success"])

        # 2. Admin access granted (200)
        self._set_test_session(level="admin")
        res = self.app.get("/api/health/db_pool")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["stats"]["max_connections"], 12)
        self.assertEqual(data["stats"]["used_connections"], 2)


if __name__ == "__main__":
    unittest.main()
