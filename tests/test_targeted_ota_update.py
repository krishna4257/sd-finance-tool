import unittest
import json
import os
from unittest.mock import patch, MagicMock
from app import app, _write_version_json_atomic, _read_version_json, generate_mobile_token

class TestTargetedOtaUpdate(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self._orig_version_data = _read_version_json()

    def tearDown(self):
        if self._orig_version_data:
            _write_version_json_atomic(self._orig_version_data)

    def test_targeted_ota_filtering(self):
        # 1. Setup version.json with targeted scope
        test_payload = {
            "latest_version": "1.2.0",
            "latest_version_code": 25,
            "min_supported_version_code": 10,
            "force_update": True,
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "url": "https://sivadurga.in/api/mobile/app/download/1.2.0",
            "release_notes": "Test targeted pilot build",
            "released_at": "2026-11-05T20:00:00Z",
            "published_by": "admin",
            "target_scope": "targeted",
            "target_employee_ids": [42, "EMP042"],
            "target_employee_names": ["Target Pilot User (@pilot)"]
        }
        _write_version_json_atomic(test_payload)

        # 2. Mock token verification and DB active checks
        token_pilot = generate_mobile_token(42, "EMP042")
        token_regular = generate_mobile_token(99, "EMP099")

        with patch("app.get_pg_connection") as mock_conn:
            mock_cur = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cur
            # Employee and user are active
            mock_cur.fetchone.return_value = (True,)

            # Test A: Non-targeted user checking version (current_version_code=5)
            # Should NOT receive upgrade_required or force_update_required
            res_reg = self.client.get(
                "/api/mobile/app/version?current_version_code=5",
                headers={"X-Mobile-Token": token_regular},
                base_url="https://localhost"
            )
            self.assertEqual(res_reg.status_code, 200)
            data_reg = json.loads(res_reg.data)
            self.assertFalse(data_reg["upgrade_required"])
            self.assertFalse(data_reg["force_update_required"])

            # Test B: Targeted user checking version (current_version_code=5)
            # SHOULD receive upgrade_required and force_update_required
            res_pilot = self.client.get(
                "/api/mobile/app/version?current_version_code=5",
                headers={"X-Mobile-Token": token_pilot},
                base_url="https://localhost"
            )
            self.assertEqual(res_pilot.status_code, 200)
            data_pilot = json.loads(res_pilot.data)
            self.assertTrue(data_pilot["upgrade_required"])
            self.assertTrue(data_pilot["force_update_required"])

    def test_admin_update_target_endpoint(self):
        with self.client.session_transaction() as sess:
            sess['role'] = 'admin'
            sess['username'] = 'admin'

        res = self.client.post(
            "/api/admin/app/update_target",
            json={
                "target_scope": "targeted",
                "target_employee_ids": [101, 102],
                "target_employee_names": ["Agent 101", "Agent 102"]
            },
            base_url="https://localhost"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["target_scope"], "targeted")
        self.assertEqual(data["target_employee_ids"], [101, 102])

        # Verify disk version.json updated
        disk_ver = _read_version_json()
        self.assertEqual(disk_ver["target_scope"], "targeted")
        self.assertEqual(disk_ver["target_employee_ids"], [101, 102])

        # Now reset back to global
        res_reset = self.client.post(
            "/api/admin/app/update_target",
            json={"target_scope": "all"},
            base_url="https://localhost"
        )
        self.assertEqual(res_reset.status_code, 200)
        disk_ver2 = _read_version_json()
        self.assertEqual(disk_ver2["target_scope"], "all")

    def test_admin_auth_with_level_attribute_only(self):
        """Verifies admin web sessions with level='admin' (and without role) are authorized."""
        with self.client.session_transaction() as sess:
            sess.clear()
            sess['user_id'] = 2
            sess['username'] = 'chinna'
            sess['level'] = 'admin'  # level is set by login, role was not set

        res = self.client.get(
            "/api/admin/app/releases",
            base_url="https://localhost"
        )
        self.assertEqual(res.status_code, 200)

        res_target = self.client.post(
            "/api/admin/app/update_target",
            json={"target_scope": "all"},
            base_url="https://localhost"
        )
        self.assertEqual(res_target.status_code, 200)

if __name__ == '__main__':
    unittest.main()
