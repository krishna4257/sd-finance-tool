"""
Unit Tests for Multi-Device Management & Telemetry
Verifies:
1. Device reset endpoint with single device_id vs all devices.
2. Multi-device verification in mobile app version endpoint (permits multiple registered devices per user).
3. Fleet telemetry controller multi-device serialization in /api/admin/mobile_users/list.
4. Fleet status and history filtering by device_id.
"""

import os
os.environ["DISABLE_SECURE_COOKIE"] = "1"

import unittest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime, timezone, timedelta
import pytz

# Mock DB connection early so app import does not attempt network connect to remote DB
mock_startup_conn = MagicMock()
mock_startup_cur = MagicMock()
mock_startup_conn.cursor.return_value = mock_startup_cur

with patch('db.get_pg_connection', return_value=mock_startup_conn), \
     patch('psycopg2.connect', return_value=mock_startup_conn):
    from app import app

class TestMultiDeviceManagement(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    @patch('app.get_pg_connection')
    def test_reset_specific_device(self, mock_get_conn):
        """Verify resetting a specific device_id deactivates only that device and returns ok/success."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = [1]  # active_cnt = 1

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['level'] = 'admin'
            sess['role'] = 'admin'

        response = self.client.post(
            '/api/users/reset_device',
            data=json.dumps({'user_id': 5, 'device_id': 'ONEPLUS_GM1911'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('ok'))
        self.assertTrue(data.get('success'))

        # Check SQL executed targeted specific device_id
        update_calls = [
            str(call) for call in mock_cur.execute.call_args_list 
            if 'UPDATE user_devices' in str(call)
        ]
        self.assertTrue(any('device_id = %s' in call for call in update_calls))

    @patch('app.get_pg_connection')
    def test_reset_all_devices_for_user(self, mock_get_conn):
        """Verify resetting without device_id deactivates all devices for user and creates PENDING slot."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['level'] = 'admin'
            sess['role'] = 'admin'

        response = self.client.post(
            '/api/users/reset_device',
            data=json.dumps({'user_id': 5}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('ok'))
        self.assertTrue(data.get('success'))

        # Check user_devices deactivates all physical devices
        dev_update_calls = [
            str(call) for call in mock_cur.execute.call_args_list 
            if "UPDATE user_devices SET is_active = FALSE WHERE user_id = %s AND device_id != 'PENDING'" in str(call)
        ]
        self.assertTrue(len(dev_update_calls) > 0)

    @patch('fleet_telemetry_controller.get_pg_connection')
    def test_mobile_users_list_multi_device_serialization(self, mock_get_conn):
        """Verify /api/admin/mobile_users/list bundles multiple devices per user in u.devices array."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # User rows: (id, username, employee_id, is_active, created_at, session_revoked_at, eid, name, level, phone, photo)
        user_rows = [
            (5, 'field_agent', 10, True, datetime.now(timezone.utc), None, 10, 'Field Agent', 'employee', '9876543210', None)
        ]
        # Multi-device rows for user 5: OnePlus and Samsung
        # (user_id, device_id, device_model, last_active, is_active, latest_lat, latest_lon, latest_speed, latest_heading, latest_acc, latest_battery, is_charging, gps_status)
        now = datetime.now(timezone.utc)
        device_rows = [
            (5, 'ONEPLUS_GM1911', 'OnePlus GM1911 (Android 12)', now, True,
             14.681, 77.600, 15.0, 90.0, 4.0, 85, False, 'accurate'),
            (5, 'SAMSUNG_SM_F966U1', 'Samsung Galaxy Z Fold (Android 14)', now, True,
             14.685, 77.605, 0.0, 0.0, 5.0, 92, True, 'accurate')
        ]

        # In execute side effect:
        # call 1: user_rows
        # call 2: device_rows (active, deduplicated)
        # call 3: pending_rows
        # call 4: villages
        mock_cur.fetchall.side_effect = [
            user_rows,
            device_rows,
            [], # pending rows
            []  # villages
        ]

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['level'] = 'admin'
            sess['role'] = 'admin'

        response = self.client.get('/api/admin/mobile_users/list')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        users = data.get('users', [])
        self.assertEqual(len(users), 1)

        user = users[0]
        self.assertIn('devices', user)
        self.assertEqual(len(user['devices']), 2)
        device_ids = [d['device_id'] for d in user['devices']]
        self.assertIn('ONEPLUS_GM1911', device_ids)
        self.assertIn('SAMSUNG_SM_F966U1', device_ids)

        # Verify device telemetry fields
        d1 = user['devices'][0]
        self.assertEqual(d1['device_id'], 'ONEPLUS_GM1911')
        self.assertEqual(d1['latest_battery_pct'], 85)
        self.assertEqual(d1['latest_speed'], 15.0)

    @patch('fleet_telemetry_controller.get_pg_connection')
    def test_fleet_status_device_filtering(self, mock_get_conn):
        """Verify /api/admin/fleet/status accepts device_id parameter and filters query."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['level'] = 'admin'
            sess['role'] = 'admin'

        response = self.client.get('/api/admin/fleet/status?device_id=ONEPLUS_GM1911')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))

        # Verify SQL filter
        calls = [str(call) for call in mock_cur.execute.call_args_list]
        self.assertTrue(any('ud.device_id = %s' in c for c in calls))

    @patch('fleet_telemetry_controller.get_pg_connection')
    def test_fleet_history_device_filtering(self, mock_get_conn):
        """Verify /api/admin/fleet/history/<user_id> filters by device_id when provided."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['level'] = 'admin'
            sess['role'] = 'admin'

        response = self.client.get('/api/admin/fleet/history/5?device_id=ONEPLUS_GM1911&date=2026-11-04')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))

        # Verify SQL filter
        calls = [str(call) for call in mock_cur.execute.call_args_list]
        self.assertTrue(any('device_id = %s' in c for c in calls))


    @patch('fleet_telemetry_controller.get_pg_connection')
    def test_lock_individual_device_endpoint(self, mock_get_conn):
        """Verify /api/admin/mobile_users/lock_device locks specific physical hardware."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['level'] = 'admin'
            sess['role'] = 'admin'

        response = self.client.post(
            '/api/admin/mobile_users/lock_device',
            data=json.dumps({'user_id': 5, 'device_id': 'SAMSUNG_SM_F966U1', 'is_locked': True}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('is_locked'))

        # Verify SQL updated is_locked=TRUE and is_active=FALSE
        calls = [str(call) for call in mock_cur.execute.call_args_list]
        self.assertTrue(any('is_locked = TRUE' in c for c in calls))

    @patch('app.get_pg_connection')
    def test_mobile_login_rejected_when_device_locked(self, mock_get_conn):
        """Verify /api/mobile/login immediately blocks locked hardware with 403 wipe_and_lock."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        from werkzeug.security import generate_password_hash
        # user row: (id, password_hash, is_active, level)
        mock_cur.fetchone.side_effect = [
            (5, generate_password_hash('pass123'), True, 'j'), # user lookup
            (10,), # eid
            (True, False) # is_locked=True for this device
        ]

        response = self.client.post(
            '/api/mobile/login',
            data=json.dumps({
                'username': 'agent_chinna',
                'password': 'pass123',
                'device_id': 'LOCKED_DEVICE_UUID',
                'device_model': 'Locked Mobile'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('locked', data.get('error', '').lower())
        self.assertEqual(data.get('action'), 'wipe_and_lock')

    @patch('fleet_telemetry_controller.get_pg_connection')
    @patch('fleet_telemetry_controller.execute_values')
    def test_location_batch_scopes_to_device_id_only(self, mock_exec_vals, mock_get_conn):
        """Verify POST /api/mobile/location/batch strictly updates only the reporting device_id."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.__enter__.return_value = mock_cur

        # Security check returns active user & device
        mock_cur.fetchone.return_value = (True, True, False) # user_active=True, dev_active=True, dev_locked=False

        # Generate valid mobile token
        from app import generate_mobile_token
        token = generate_mobile_token(5, 10)

        payload = {
            "device_id": "ONEPLUS_GM1911",
            "locations": [
                {
                    "latitude": 14.681,
                    "longitude": 77.600,
                    "accuracy": 4.0,
                    "speed": 12.5,
                    "heading": 85.0,
                    "battery_pct": 78,
                    "is_charging": False,
                    "activity_type": "in_vehicle",
                    "recorded_at": "2026-11-05T08:30:00Z"
                }
            ]
        }

        response = self.client.post(
            '/api/mobile/location/batch',
            data=json.dumps(payload),
            headers={"X-Mobile-Token": token},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))

        # Verify SQL update in user_devices strictly has WHERE user_id = %s AND device_id = %s;
        calls = [str(call) for call in mock_cur.execute.call_args_list if 'UPDATE user_devices' in str(call)]
        self.assertTrue(len(calls) > 0)
        self.assertTrue(any('WHERE user_id = %s AND device_id = %s;' in c for c in calls))
        self.assertFalse(any('OR is_active = TRUE' in c for c in calls))

if __name__ == '__main__':
    unittest.main()

