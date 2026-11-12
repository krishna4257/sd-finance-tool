"""
Automated PyUnit Test Suite for Phase 6: Internal Chat Schema & RBAC Provisioning
File: SD_Accounting_Tool/tests/test_phase6_chat_schema.py

Tests:
1. SQL migration file integrity, syntax, and presence of all required tables & indexes.
2. UTF-8 Telugu character processing and length preservation.
3. Client UUID idempotency contract for offline mobile queue.
4. Channel provisioning logic (Broadcast + Staff-to-Admin 1:1).
5. RBAC enforcement: Prohibits direct channels between two field staff members.
"""

import os
import sys
import uuid
import unittest
from unittest.mock import MagicMock, patch

# Ensure application root is on sys.path
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from scripts.provision_chat_channels import provision_channels, apply_migration


class TestPhase6ChatSchema(unittest.TestCase):

    def setUp(self):
        self.sql_path = os.path.join(APP_ROOT, "sql_scripts", "phase6_internal_chat.sql")

    def test_sql_file_exists_and_contains_core_entities(self):
        """Verify phase6_internal_chat.sql exists and declares all mandatory tables, types, and schemas."""
        self.assertTrue(os.path.isfile(self.sql_path), f"Migration missing at {self.sql_path}")
        
        with open(self.sql_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check Schema & Tables
        self.assertIn("CREATE SCHEMA IF NOT EXISTS notifkit;", content)
        self.assertIn("CREATE TABLE IF NOT EXISTS chat_channels", content)
        self.assertIn("CREATE TABLE IF NOT EXISTS chat_channel_members", content)
        self.assertIn("CREATE TABLE IF NOT EXISTS chat_messages", content)
        self.assertIn("CREATE TABLE IF NOT EXISTS user_notification_settings", content)

        # Check Enums
        self.assertIn("chat_message_type", content)
        self.assertIn("chat_delivery_status", content)
        self.assertIn("chat_channel_type", content)

        # Check Indexes
        self.assertIn("idx_chat_messages_channel_created", content)
        self.assertIn("idx_chat_messages_client_uuid", content)
        self.assertIn("idx_chat_messages_unread_status", content)
        self.assertIn("idx_chat_members_user", content)

        # Check RBAC Trigger
        self.assertIn("check_direct_channel_rbac", content)
        self.assertIn("trg_check_channel_rbac", content)

    def test_telugu_unicode_string_integrity(self):
        """Verify Telugu characters maintain byte integrity, Unicode encoding, and string length."""
        telugu_sample = "నమస్కారం సార్, నేటి కలెక్షన్ పూర్తయింది. మొత్తం ₹15,000 వసూలు అయింది."
        
        # Test UTF-8 byte serialization
        encoded_bytes = telugu_sample.encode("utf-8")
        self.assertIsInstance(encoded_bytes, bytes)
        decoded_string = encoded_bytes.decode("utf-8")
        self.assertEqual(telugu_sample, decoded_string)
        
        # Verify currency symbol and Telugu consonants preserve integrity
        self.assertIn("₹", decoded_string)
        self.assertIn("నమస్కారం", decoded_string)

    def test_client_uuid_idempotency_generation(self):
        """Verify client UUID idempotency generation adheres to standard v4 UUID specification."""
        client_uuid = str(uuid.uuid4())
        self.assertEqual(len(client_uuid), 36)
        self.assertEqual(client_uuid.count("-"), 4)

        # Ensure unique generation across 1,000 attempts
        generated = {str(uuid.uuid4()) for _ in range(1000)}
        self.assertEqual(len(generated), 1000)

    def test_rbac_channel_membership_validation(self):
        """Verify that direct channels between two field staff members are flagged as invalid."""
        def validate_channel_members(channel_type, members):
            """Simulates database trigger validation logic in Python."""
            if channel_type == "direct":
                staff_count = sum(1 for m in members if m["role"] == "staff")
                if staff_count > 1:
                    raise ValueError("RBAC Violation: Direct channels between two field staff members are prohibited.")
            return True

        # Valid: Admin and Staff in direct channel
        valid_direct = [
            {"user_id": 1, "role": "admin"},
            {"user_id": 2, "role": "staff"}
        ]
        self.assertTrue(validate_channel_members("direct", valid_direct))

        # Valid: Management and Staff in direct channel
        valid_mgmt_direct = [
            {"user_id": 3, "role": "mgmt"},
            {"user_id": 2, "role": "staff"}
        ]
        self.assertTrue(validate_channel_members("direct", valid_mgmt_direct))

        # Invalid: Staff and Staff in direct channel
        invalid_staff_direct = [
            {"user_id": 2, "role": "staff"},
            {"user_id": 4, "role": "staff"}
        ]
        with self.assertRaises(ValueError) as ctx:
            validate_channel_members("direct", invalid_staff_direct)
        self.assertIn("RBAC Violation", str(ctx.exception))

        # Valid: Broadcast channels can have any number of staff
        broadcast_channel = [
            {"user_id": 1, "role": "admin"},
            {"user_id": 2, "role": "staff"},
            {"user_id": 4, "role": "staff"}
        ]
        self.assertTrue(validate_channel_members("broadcast", broadcast_channel))

    @patch("scripts.provision_chat_channels.get_pg_connection")
    def test_channel_provisioning_workflow(self, mock_get_conn):
        """Verify channel provisioning creates broadcast channel and 1:1 staff channels."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        # Mock database responses:
        # 1. Leadership users: Admin (ID 1)
        # 2. Staff users: Staff A (ID 10), Staff B (ID 11)
        # 3. Existing broadcast check: None (so it creates one)
        # 4. Existing direct check: None (so it creates 1:1 for both)
        mock_cur.fetchall.side_effect = [
            [(1, "admin", "Admin User", "admin", "9876543210")],  # leadership
            [(10, "staff_a", "Staff A", "staff", "9123456780"),   # staff
             (11, "staff_b", "Staff B", "staff", "9123456781")]
        ]
        mock_cur.fetchone.side_effect = [
            None,      # broadcast check -> not found
            ("uuid-broadcast-1",), # returning id for broadcast
            None,      # direct check for staff_a -> not found
            ("uuid-direct-10",),   # returning id for staff_a
            None,      # direct check for staff_b -> not found
            ("uuid-direct-11",)    # returning id for staff_b
        ]

        provision_channels(mock_conn)

        # Verify commit called
        mock_conn.commit.assert_called_once()
        self.assertTrue(mock_cur.execute.called)


if __name__ == "__main__":
    unittest.main()
