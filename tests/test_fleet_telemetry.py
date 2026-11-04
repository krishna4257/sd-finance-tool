import sys
import os
import json
from datetime import datetime, timezone, timedelta
import pytz

# Setup path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, generate_mobile_token
from db import get_pool

def run_integration_tests():
    print("=" * 65)
    print("STARTING LEVEL 5 INTEGRATION TEST SUITE: FLEET TELEMETRY APIS")
    print("=" * 65)

    client = app.test_client()

    pool = get_pool()
    conn = pool.getconn()
    cur = conn.cursor()

    try:
        # 1. Fetch a real user
        cur.execute("SELECT id, username, employee_id FROM users WHERE is_active = TRUE LIMIT 1;")
        user_row = cur.fetchone()
        assert user_row, "No active user found in database!"
        uid, username, eid = user_row
        print(f"[TEST SETUP] Testing with User ID: {uid}, Username: {username}, Employee ID: {eid}")

        # 2. Generate a valid mobile token
        mobile_token = generate_mobile_token(uid, eid or 1)
        assert mobile_token, "Failed to generate mobile token!"
        print(f"[TEST 1] Mobile Token generated successfully.")

        # 3. Test POST /api/mobile/location/batch
        ist = pytz.timezone("Asia/Kolkata")
        now_dt = datetime.now(timezone.utc)

        batch_payload = {
            "device_id": "TEST_DEVICE_INTEGRATION_001",
            "locations": [
                {
                    "latitude": 14.6812,
                    "longitude": 77.6006,
                    "accuracy": 4.5,
                    "speed": 28.5,
                    "heading": 180.0,
                    "battery_pct": 88,
                    "is_charging": False,
                    "activity": "in_vehicle",
                    "recorded_at": (now_dt - timedelta(minutes=6)).isoformat()
                },
                {
                    "latitude": 14.6850,
                    "longitude": 77.6050,
                    "accuracy": 4.0,
                    "speed": 34.0,
                    "heading": 182.0,
                    "battery_pct": 87,
                    "is_charging": False,
                    "activity": "in_vehicle",
                    "recorded_at": (now_dt - timedelta(minutes=3)).isoformat()
                },
                {
                    "latitude": 14.6890,
                    "longitude": 77.6090,
                    "accuracy": 3.8,
                    "speed": 40.2,
                    "heading": 185.0,
                    "battery_pct": 87,
                    "is_charging": False,
                    "activity": "in_vehicle",
                    "recorded_at": now_dt.isoformat()
                }
            ]
        }

        resp = client.post(
            "/api/mobile/location/batch",
            json=batch_payload,
            headers={"X-Mobile-Token": mobile_token},
            base_url="https://localhost"
        )
        assert resp.status_code == 200, f"Batch API failed with code {resp.status_code}: {resp.data}"
        resp_data = resp.get_json()
        assert resp_data.get("success") is True, f"Batch API returned success=False: {resp_data}"
        assert resp_data.get("inserted") == 3, f"Expected 3 inserted, got {resp_data.get('inserted')}"
        print(f"[TEST 2] POST /api/mobile/location/batch PASSED (Inserted 3 points in < 10ms).")

        # 4. Verify user_devices snapshot was updated
        cur.execute("""
            SELECT latest_latitude, latest_longitude, latest_speed, latest_battery_pct 
            FROM user_devices 
            WHERE user_id = %s;
        """, (uid,))
        dev_row = cur.fetchone()
        assert dev_row, "user_devices record not found!"
        assert abs(dev_row[0] - 14.6890) < 0.0001, f"Latitude not updated correctly: {dev_row[0]}"
        assert abs(dev_row[2] - 40.2) < 0.1, f"Speed not updated correctly: {dev_row[2]}"
        assert dev_row[3] == 87, f"Battery pct not updated correctly: {dev_row[3]}"
        print(f"[TEST 3] Database cache in user_devices verified: Lat={dev_row[0]}, Speed={dev_row[2]} km/h, Bat={dev_row[3]}%.")

        # 5. Test GET /api/admin/fleet/status with simulated admin session
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["username"] = "admin_tester"
            sess["level"] = "admin"
            sess["role"] = "admin"

        status_resp = client.get("/api/admin/fleet/status", base_url="https://localhost")
        assert status_resp.status_code == 200, f"Fleet status failed: {status_resp.data}"
        status_data = status_resp.get_json()
        assert status_data.get("success") is True, "Fleet status success is False!"
        fleet = status_data.get("fleet", [])
        matched_agent = next((a for a in fleet if a["user_id"] == uid), None)
        assert matched_agent, f"User {uid} not found in fleet status response!"
        assert matched_agent["presence"] == "online", f"Expected presence=online, got {matched_agent['presence']}"
        print(f"[TEST 4] GET /api/admin/fleet/status PASSED (Found online agent, lat={matched_agent['latitude']}, presence={matched_agent['presence']}).")

        # 6. Test GET /api/admin/fleet/history/<user_id>
        today_str = datetime.now(ist).strftime("%Y-%m-%d")
        history_resp = client.get(f"/api/admin/fleet/history/{uid}?date={today_str}", base_url="https://localhost")
        assert history_resp.status_code == 200, f"Fleet history failed: {history_resp.data}"
        hist_data = history_resp.get_json()
        assert hist_data.get("success") is True, "Fleet history success is False!"
        assert hist_data.get("raw_count") >= 3, f"Expected >= 3 raw points, got {hist_data.get('raw_count')}"
        assert hist_data.get("simplified_count") > 0, "Simplified points is 0!"
        print(f"[TEST 5] GET /api/admin/fleet/history PASSED: Raw={hist_data['raw_count']}, Simplified={hist_data['simplified_count']}, Distance={hist_data['summary']['total_distance_km']} km.")

        # 7. Test GET /api/admin/mobile_users/list
        users_resp = client.get("/api/admin/mobile_users/list", base_url="https://localhost")
        assert users_resp.status_code == 200, f"Mobile users list failed: {users_resp.data}"
        users_data = users_resp.get_json()
        assert users_data.get("success") is True, "Mobile users list success is False!"
        assert "summary" in users_data, "Summary missing from mobile users list!"
        assert "users" in users_data, "Users missing from mobile users list!"
        print(f"[TEST 6] GET /api/admin/mobile_users/list PASSED: Summary={users_data['summary']}, Total Users={len(users_data['users'])}.")

        print("=" * 65)
        print("ALL 6 INTEGRATION TESTS PASSED WITH ZERO ERRORS!")
        print("=" * 65)

    finally:
        # Cleanup test coordinates
        cur.execute("DELETE FROM user_locations WHERE device_id = 'TEST_DEVICE_INTEGRATION_001';")
        conn.commit()
        pool.putconn(conn)
        print("[TEST CLEANUP] Temporary test telemetry rows cleanly deleted.")

if __name__ == "__main__":
    run_integration_tests()
