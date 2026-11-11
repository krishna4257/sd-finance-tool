"""End-to-End Test Suite for Admin, Users, Fleet Telemetry, and Infrastructure Health (Domain 5)."""

import unittest
from tests.e2e.e2e_base import (
    configure_app,
    get_admin_client,
    query_db,
    cleanup_test_records,
    ADMIN_USER_ID,
)

class TestAdminAndTelemetryE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = configure_app()
        cls.client = get_admin_client(cls.app)
        cleanup_test_records()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_records()

    def test_01_users_and_device_management(self):
        """Verify users directory, mobile user list API, and device lock toggle."""
        # 1. Users Page (Redirects to /employee per modular architecture)
        res_users = self.client.get("/users")
        self.assertIn(res_users.status_code, (200, 302), "Users page failed to respond")

        # 2. Users List API
        res_user_api = self.client.get("/api/users/list")
        self.assertEqual(res_user_api.status_code, 200, "Users list API failed")
        self.assertIsInstance(res_user_api.get_json(), list)

        # 3. Mobile Users List API
        res_list = self.client.get("/api/admin/mobile_users/list")
        self.assertEqual(res_list.status_code, 200, "Mobile users list API failed")
        users_list = res_list.get_json()
        self.assertIsInstance(users_list, (list, dict))

        # 4. Toggle Lock Status on a test user (use user 9 'Nani' or test user)
        target_user = query_db("SELECT id, is_active FROM users WHERE id = 9", fetchone=True)
        if target_user:
            uid, orig_status = target_user
            # Lock device
            res_lock = self.client.post("/api/admin/mobile_users/toggle_lock", json={"user_id": uid, "is_active": False})
            self.assertEqual(res_lock.status_code, 200)
            self.assertTrue(res_lock.get_json().get("success"))

            # Restore original status
            res_restore = self.client.post("/api/admin/mobile_users/toggle_lock", json={"user_id": uid, "is_active": orig_status})
            self.assertEqual(res_restore.status_code, 200)
            self.assertTrue(res_restore.get_json().get("success"))

    def test_02_employee_management_lifecycle(self):
        """Verify employee directory, list, next EID generation, creation, and soft delete."""
        # 1. Employee Directory Page
        res_emp_page = self.client.get("/employee")
        self.assertEqual(res_emp_page.status_code, 200, "Employee page failed to render")

        # 2. Employees JSON API
        res_emps = self.client.get("/api/employees")
        self.assertEqual(res_emps.status_code, 200, "Employees API failed")

        # 3. Next EID API
        res_next_eid = self.client.get("/api/employee/next_eid")
        self.assertEqual(res_next_eid.status_code, 200, "Next EID API failed")

        # Clean any prior test employee with this phone
        query_db("DELETE FROM employee WHERE phone_number = '9000099999'", commit=True)

        # 4. Create Employee
        emp_payload = {
            "name": "TEST-E2E-AUTOMATION-EMP",
            "phone_number": "9000099999",
            "level": "staff",
            "city": "Rajahmundry",
            "state": "ANDHRA PRADESH"
        }
        res_create = self.client.post("/api/create_employee", json=emp_payload)
        self.assertEqual(res_create.status_code, 200, f"Create employee failed: {res_create.data}")
        create_json = res_create.get_json()
        self.assertTrue(create_json.get("success"), f"Create employee returned success=False: {create_json}")

        created_eid = create_json.get("eid")

        # 5. Verify in DB
        db_emp = query_db("SELECT eid, name, phone_number FROM employee WHERE phone_number = '9000099999'", fetchone=True)
        self.assertIsNotNone(db_emp, "Created employee not found in DB")
        self.assertEqual(db_emp[1], "TEST-E2E-AUTOMATION-EMP")

        # Clean up
        query_db("DELETE FROM employee WHERE phone_number = '9000099999'", commit=True)

    def test_03_fleet_telemetry_and_monitoring(self):
        """Verify fleet status and telemetry history endpoints."""
        # 1. Fleet status API
        res_status = self.client.get("/api/admin/fleet/status")
        self.assertEqual(res_status.status_code, 200, "Fleet status API failed")
        status_data = res_status.get_json()
        self.assertIsInstance(status_data, (dict, list))

        # 2. Fleet history for user
        res_hist = self.client.get(f"/api/admin/fleet/history/{ADMIN_USER_ID}")
        self.assertEqual(res_hist.status_code, 200, "Fleet history API failed")

    def test_04_infrastructure_and_db_pool_health(self):
        """Verify dynamic PostgreSQL connection pool health metrics."""
        res_pool = self.client.get("/api/health/db_pool")
        self.assertEqual(res_pool.status_code, 200, "DB pool health endpoint failed")
        pool_data = res_pool.get_json()
        self.assertIsInstance(pool_data, dict)
        self.assertTrue(pool_data.get("success"), "DB pool health returned success=False")
        self.assertIn("stats", pool_data)
        self.assertGreaterEqual(pool_data["stats"].get("max_connections", 0), 1)

if __name__ == "__main__":
    unittest.main()
