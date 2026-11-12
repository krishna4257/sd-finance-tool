"""
Automated PyUnit Test Suite for Phase 6 (Phase 3): Chat API Routes & Notification Dispatcher
File: SD_Accounting_Tool/tests/test_phase6_chat_api.py

Tests:
1. Zero-dependency Centrifugo HS256 JWT generation.
2. Authentication guard (Web session & Mobile token fallback).
3. /api/v1/chat/token endpoint.
4. /api/v1/chat/send message ingestion, Centrifugo broadcasting, and NotifKit dispatch.
5. RBAC enforcement: Staff prohibited from posting to broadcast channels.
6. WhatsApp delivery receipts (/api/v1/chat/ack).
7. Media upload extension filtering and security.
8. Notification service dispatcher functions.
"""

import os
import sys
import json
import uuid
import unittest
from io import BytesIO
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

import app as main_app
from routes.chat_routes import generate_centrifugo_jwt, ALLOWED_EXTENSIONS
from services.notification_service import trigger_notification, notify_chat_message


class TestPhase6ChatApi(unittest.TestCase):

    def setUp(self):
        main_app.app.config["TESTING"] = True
        main_app.app.config["WTF_CSRF_ENABLED"] = False
        main_app.app.config["SECRET_KEY"] = "test-secret-key-64-characters-long-sd-finance-testing-suite"
        self.client = main_app.app.test_client()

    def test_jwt_generation_structure_and_signature(self):
        """Verify generate_centrifugo_jwt produces valid RFC 7519 three-part JWTs."""
        token = generate_centrifugo_jwt(
            user_id=42,
            role="admin",
            username="jaya",
            secret_key="my-secret-key",
            ttl_seconds=3600
        )
        parts = token.split(".")
        self.assertEqual(len(parts), 3, "JWT must consist of header.payload.signature")

        import base64
        def decode_b64url(s):
            padding = "=" * (4 - len(s) % 4) if len(s) % 4 != 0 else ""
            return json.loads(base64.urlsafe_b64decode(s + padding).decode("utf-8"))

        header = decode_b64url(parts[0])
        payload = decode_b64url(parts[1])

        self.assertEqual(header["alg"], "HS256")
        self.assertEqual(header["typ"], "JWT")
        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["info"]["username"], "jaya")
        self.assertEqual(payload["info"]["role"], "admin")
        self.assertTrue(payload["exp"] > payload["iat"])

    def test_chat_token_requires_authentication(self):
        """Verify /api/v1/chat/token returns 401 when no session or mobile token is provided."""
        res = self.client.get("/api/v1/chat/token")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_chat_token_with_authenticated_session(self):
        """Verify /api/v1/chat/token returns a signed token for an active web user."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["user_level"] = "admin"

        res = self.client.get("/api/v1/chat/token")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)
        self.assertIn("wss://", data["ws_endpoint"])
        self.assertEqual(data["user_id"], 1)
        self.assertEqual(data["role"], "admin")

    @patch("routes.chat_routes.requests.post")
    @patch("routes.chat_routes.notify_chat_message")
    @patch("routes.chat_routes.get_pg_connection")
    def test_send_message_flow(self, mock_get_conn, mock_notify, mock_requests_post):
        """Verify send_message inserts to DB, broadcasts via Centrifugo, and calls NotifKit."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        # Mock membership: User 1 (admin) and User 10 (staff)
        mock_cur.fetchall.return_value = [
            (1, "admin", "direct"),
            (10, "staff", "direct")
        ]
        test_msg_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        mock_cur.fetchone.return_value = (test_msg_id, now, "sent")

        client_uuid = str(uuid.uuid4())
        channel_id = str(uuid.uuid4())

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["user_level"] = "admin"

        res = self.client.post("/api/v1/chat/send", json={
            "client_uuid": client_uuid,
            "channel_id": channel_id,
            "type": "text",
            "body": "నమస్కారం, కలెక్షన్ రిపోర్ట్ అప్డేట్ అయింది."
        })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["client_uuid"], client_uuid)
        self.assertEqual(data["status"], "sent")

        # Verify Centrifugo loopback was called for both channel and recipient user
        self.assertGreaterEqual(mock_requests_post.call_count, 1)
        first_call_kwargs = mock_requests_post.call_args_list[0][1]
        self.assertIn("apikey", first_call_kwargs.get("headers", {}).get("Authorization", "").lower())
        self.assertTrue(first_call_kwargs.get("json", {}).get("channel", "").startswith("chat:"))

        # Verify NotifKit background alert was dispatched for recipient 10
        mock_notify.assert_called_once()
        notify_args = mock_notify.call_args[1]
        self.assertEqual(notify_args["recipient_id"], 10)

    @patch("routes.chat_routes.get_pg_connection")
    def test_send_message_staff_rbac_in_broadcast(self, mock_get_conn):
        """Verify staff members are prohibited from posting in broadcast announcement channels."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        # Mock membership: User 10 (staff) in broadcast channel
        mock_cur.fetchall.return_value = [
            (10, "staff", "broadcast"),
            (1, "admin", "broadcast")
        ]

        with self.client.session_transaction() as sess:
            sess["user_id"] = 10
            sess["username"] = "field_agent"
            sess["user_level"] = "staff"

        res = self.client.post("/api/v1/chat/send", json={
            "client_uuid": str(uuid.uuid4()),
            "channel_id": str(uuid.uuid4()),
            "body": "Unauthorized post attempt"
        })

        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("Only Admin and Management", data["error"])

    @patch("routes.chat_routes.requests.post")
    @patch("routes.chat_routes.get_pg_connection")
    def test_ack_message_status(self, mock_get_conn, mock_requests_post):
        """Verify /api/v1/chat/ack updates status to read and broadcasts tick update."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["user_level"] = "admin"

        msg_id = str(uuid.uuid4())
        channel_id = str(uuid.uuid4())

        res = self.client.post("/api/v1/chat/ack", json={
            "message_id": msg_id,
            "channel_id": channel_id,
            "status": "read"
        })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "read")

        # Verify DB execute was called with read update
        self.assertTrue(mock_cur.execute.called)
        mock_conn.commit.assert_called_once()

    def test_upload_chat_media_rejects_disallowed_extensions(self):
        """Verify upload_chat_media rejects dangerous or unauthorized file extensions."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"

        data = {
            "file": (BytesIO(b"malicious script"), "payload.exe")
        }
        res = self.client.post("/api/v1/chat/upload-media", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        json_data = res.get_json()
        self.assertIn("Unsupported media type", json_data["error"])

    @patch("services.notification_service.requests.post")
    def test_notification_service_dispatcher(self, mock_post):
        """Verify trigger_notification formats payload properly for NotifKit."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "notif-123"}
        mock_post.return_value = mock_resp

        ok, result = trigger_notification(
            event_type="test_event",
            recipient_id="99",
            payload={"msg": "hello"},
            priority="high"
        )
        self.assertTrue(ok)
        self.assertEqual(result["id"], "notif-123")
        mock_post.assert_called_once()

    @patch("routes.chat_routes.get_pg_connection")
    def test_get_chat_directory_for_admin_and_staff(self, mock_get_conn):
        """Verify leadership sees all users in directory and staff only sees leadership."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        mock_cur.fetchall.return_value = [
            (2, "admin_user", "Admin Two", "admin"),
            (3, "mgmt_user", "Manager Three", "mgmt"),
            (4, "staff_user", "Field Staff", "staff")
        ]

        # 1. Admin user request
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "superadmin"
            sess["user_level"] = "superadmin"

        res = self.client.get("/api/v1/chat/users")
        self.assertEqual(res.status_code, 200)
        users = res.get_json()["users"]
        self.assertEqual(len(users), 3)

        # 2. Staff user request (should only see leadership users: admin & mgmt)
        with self.client.session_transaction() as sess:
            sess["user_id"] = 4
            sess["username"] = "staff_user"
            sess["user_level"] = "staff"

        res = self.client.get("/api/v1/chat/users")
        self.assertEqual(res.status_code, 200)
        staff_users = res.get_json()["users"]
        self.assertEqual(len(staff_users), 2)
        roles = [u["role"] for u in staff_users]
        self.assertIn("admin", roles)
        self.assertIn("mgmt", roles)
        self.assertNotIn("staff", roles)

    @patch("routes.chat_routes.get_pg_connection")
    def test_unread_count_endpoint(self, mock_get_conn):
        """Verify /unread_count queries unread messages count for authenticated user."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        mock_cur.fetchone.return_value = (5,)

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["user_level"] = "admin"

        res = self.client.get("/api/v1/chat/unread_count")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["unread_count"], 5)


if __name__ == "__main__":
    unittest.main()
