import os
import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify, g, request
from werkzeug.security import generate_password_hash

import app as main_app
from app import (
    verify_mobile_token,
    generate_mobile_token,
    get_active_mobile_user,
    check_user_village_access,
    mobile_auth_required,
    get_mobile_queue_hmac_secret,
    verify_queue_integrity,
)


class TestPhase1Security(unittest.TestCase):
    def setUp(self):
        main_app.app.config["TESTING"] = True
        main_app.app.config["WTF_CSRF_ENABLED"] = False
        self.app = main_app.app.test_client()

    def test_mobile_token_encoding_and_decoding(self):
        """Verify token generation and decoding works for valid payloads."""
        token = generate_mobile_token(user_id=10, eid=5)
        self.assertIsNotNone(token)

        data = verify_mobile_token(token)
        self.assertIsNotNone(data)
        self.assertEqual(data.get("user_id"), 10)
        self.assertEqual(data.get("eid"), 5)

        # Invalid or tampered token returns None
        self.assertIsNone(verify_mobile_token("invalid.token.structure"))
        self.assertIsNone(verify_mobile_token(token + "tampered"))

    def test_get_active_mobile_user_success(self):
        """Active user and active employee returns user dict."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (10, "john_doe", True, 5, "staff", True)

        user = get_active_mobile_user({"user_id": 10, "eid": 5}, cur=mock_cur)
        self.assertIsNotNone(user)
        self.assertEqual(user["user_id"], 10)
        self.assertEqual(user["username"], "john_doe")
        self.assertEqual(user["eid"], 5)
        self.assertEqual(user["level"], "staff")
        self.assertTrue(user["is_active"])

    def test_get_active_mobile_user_revoked_or_inactive(self):
        """Deactivated user (is_active=False) or inactive employee status is rejected immediately."""
        mock_cur = MagicMock()
        # Case 1: user is_active is False
        mock_cur.fetchone.return_value = (10, "john_doe", False, 5, "staff", True)
        self.assertIsNone(get_active_mobile_user({"user_id": 10, "eid": 5}, cur=mock_cur))

        # Case 2: employee is inactive
        mock_cur.fetchone.return_value = (10, "john_doe", True, 5, "staff", False)
        self.assertIsNone(get_active_mobile_user({"user_id": 10, "eid": 5}, cur=mock_cur))

        # Case 3: User row not found
        mock_cur.fetchone.return_value = None
        self.assertIsNone(get_active_mobile_user({"user_id": 10, "eid": 5}, cur=mock_cur))

    def test_check_user_village_access_admin_mgmt(self):
        """Admin and management users have global access to any village."""
        self.assertTrue(check_user_village_access(user_id=1, eid=1, user_level="admin", vid=999))
        self.assertTrue(check_user_village_access(user_id=2, eid=2, user_level="mgmt", vid=123))
        self.assertTrue(check_user_village_access(user_id=3, eid=3, user_level="superadmin", vid=456))

    def test_check_user_village_access_staff_permissions(self):
        """Staff users only have access if assigned in user_village_access or village(emp1/emp2)."""
        mock_cur = MagicMock()
        # Case 1: Has record in user_village_access
        mock_cur.fetchone.side_effect = [(1,), None]
        self.assertTrue(check_user_village_access(user_id=10, eid=5, user_level="staff", vid=42, cur=mock_cur))

        # Case 2: No record in user_village_access, but assigned via emp1 in village
        mock_cur.fetchone.side_effect = [None, (1,)]
        self.assertTrue(check_user_village_access(user_id=10, eid=5, user_level="staff", vid=42, cur=mock_cur))

        # Case 3: Neither record exists -> Denied
        mock_cur.fetchone.side_effect = [None, None]
        self.assertFalse(check_user_village_access(user_id=10, eid=5, user_level="staff", vid=42, cur=mock_cur))

    @patch("app.get_active_mobile_user")
    @patch("app.check_user_village_access")
    def test_mobile_auth_required_decorator_enforcement(self, mock_check_village, mock_get_user):
        """Verify decorator blocks missing tokens, revoked users, and unauthorized villages."""
        # 1. Missing token -> 401
        res = self.app.get("/api/mobile/customers?vid=1")
        self.assertEqual(res.status_code, 401)
        self.assertIn("missing token", res.get_json().get("error", "").lower())

        valid_token = generate_mobile_token(user_id=10, eid=5)
        headers = {"X-Mobile-Token": valid_token}

        # 2. Inactive / revoked user -> 401
        mock_get_user.return_value = None
        res = self.app.get("/api/mobile/customers?vid=1", headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertIn("user inactive or token revoked", res.get_json().get("error", "").lower())

        # 3. Active user, but unauthorized village -> 403
        mock_get_user.return_value = {
            "user_id": 10,
            "username": "john_doe",
            "eid": 5,
            "level": "staff",
            "is_active": True
        }
        mock_check_village.return_value = False
        res = self.app.get("/api/mobile/customers?vid=999", headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access denied", res.get_json().get("error", ""))

    @patch.dict(os.environ, {"FLASK_ENV": "production"})
    def test_reset_database_blocked_in_production(self):
        """Database reset must be completely blocked in production environment."""
        valid_token = generate_mobile_token(user_id=1, eid=1)
        with patch("app.get_active_mobile_user") as mock_user:
            mock_user.return_value = {
                "user_id": 1,
                "username": "admin",
                "eid": 1,
                "level": "admin",
                "is_active": True
            }
            res = self.app.post(
                "/api/mobile/reset_database",
                headers={"X-Mobile-Token": valid_token},
                json={"password": "any_password"}
            )
            self.assertEqual(res.status_code, 403)
            self.assertIn("strictly disabled in production", res.get_json().get("error", ""))

    @patch.dict(os.environ, {"FLASK_ENV": "development"})
    @patch("app.get_pg_connection")
    @patch("app.get_active_mobile_user")
    def test_reset_database_requires_password_in_dev(self, mock_user, mock_conn):
        """In development, reset_database requires and validates the admin's password."""
        valid_token = generate_mobile_token(user_id=1, eid=1)
        mock_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "eid": 1,
            "level": "admin",
            "is_active": True
        }

        # Case 1: No password provided -> 400
        res = self.app.post(
            "/api/mobile/reset_database",
            headers={"X-Mobile-Token": valid_token},
            json={}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Admin password required", res.get_json().get("error", ""))

        # Case 2: Wrong password provided -> 401
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (generate_password_hash("correct_password", method="pbkdf2:sha256"),)
        mock_conn.return_value.cursor.return_value = mock_cur

        res = self.app.post(
            "/api/mobile/reset_database",
            headers={"X-Mobile-Token": valid_token},
            json={"password": "wrong_password"}
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("Incorrect admin password", res.get_json().get("error", ""))

    def test_hmac_secret_production_enforcement(self):
        """In production environment, a missing secret raises RuntimeError."""
        with patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=True):
            if "MOBILE_QUEUE_HMAC_SECRET" in os.environ:
                del os.environ["MOBILE_QUEUE_HMAC_SECRET"]
            with self.assertRaises(RuntimeError):
                get_mobile_queue_hmac_secret()

        # In development, it falls back gracefully
        with patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=True):
            if "MOBILE_QUEUE_HMAC_SECRET" in os.environ:
                del os.environ["MOBILE_QUEUE_HMAC_SECRET"]
            secret = get_mobile_queue_hmac_secret()
            self.assertEqual(secret, "dev-mobile-queue-secret")


if __name__ == "__main__":
    unittest.main()
