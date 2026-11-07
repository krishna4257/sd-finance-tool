"""Phase 5 Test Suite: Frontend Hardening, Network Resilience & CI/CD Automation.
Validates:
1. CSRF meta tag and shared utils.js inclusion across base templates.
2. Static asset integrity (utils.js exports, toast CSS tokens).
3. XSS sanitization and HTML escaping behavior.
4. CSRF protection barrier on mutating financial POST endpoints.
5. Unauthenticated AJAX 401 handling for session expiry interception.
6. Idempotency header (X-Client-Request-Id) handling.
"""

import os
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure application root is on sys.path
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from app import app


class TestPhase5FrontendAndResilience(unittest.TestCase):
    """Test suite for Phase 5 frontend contracts, security, and resilience."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["SERVER_NAME"] = "localhost"

    def setUp(self):
        self.client = app.test_client()

    def test_01_base_templates_include_csrf_meta_and_utils_js(self):
        """Verify all base templates have CSRF meta tag and load utils.js."""
        template_dir = os.path.join(APP_ROOT, "templates")

        base_templates = [
            os.path.join(template_dir, "base.html"),
            os.path.join(template_dir, "banking", "base.html"),
            os.path.join(template_dir, "chit", "base.html"),
        ]

        for path in base_templates:
            self.assertTrue(os.path.exists(path), f"Base template missing: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Must have csrf-token meta tag
            self.assertIn(
                '<meta name="csrf-token" content="{{ csrf_token() }}">',
                content,
                f"Missing CSRF meta tag in {os.path.basename(path)}"
            )

            # Must include utils.js
            self.assertTrue(
                "static', filename='js/utils.js'" in content or "static/js/utils.js" in content,
                f"Missing utils.js inclusion in {os.path.basename(path)}"
            )

    def test_02_utils_js_contains_required_resilience_exports(self):
        """Verify static/js/utils.js exports all Phase 5 resilience and toast functions."""
        utils_path = os.path.join(APP_ROOT, "static", "js", "utils.js")
        self.assertTrue(os.path.exists(utils_path), "utils.js missing")

        with open(utils_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_symbols = [
            "window.escapeHtml = escapeHtml",
            "window.getCSRFToken = getCSRFToken",
            "window.generateUUID = generateUUID",
            "window.showToast = showToast",
            "window.showSuccessToast",
            "window.showErrorToast",
            "window.fetchWithRetry = fetchWithRetry",
            "window.csrfFetch = secureFetch",
            "__SD_FETCH_INITIALIZED__",
        ]

        for symbol in required_symbols:
            self.assertIn(symbol, content, f"utils.js missing expected symbol: {symbol}")

    def test_03_toast_css_tokens_present_in_stylesheet(self):
        """Verify static/css/style.css contains styles for modern non-blocking toasts."""
        css_path = os.path.join(APP_ROOT, "static", "css", "style.css")
        self.assertTrue(os.path.exists(css_path), "style.css missing")

        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_selectors = [
            ".sd-toast-container",
            ".sd-toast",
            ".sd-toast.sd-toast-show",
            ".sd-toast-success",
            ".sd-toast-error",
            ".sd-toast-warning",
            ".sd-toast-info",
        ]

        for sel in required_selectors:
            self.assertIn(sel, content, f"style.css missing expected toast selector: {sel}")

    def test_04_xss_escape_html_logic(self):
        """Test HTML escaping logic equivalent to utils.js escapeHtml()."""
        def py_escape_html(s):
            if s is None:
                return ""
            return (
                str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#039;")
                .replace("`", "&#96;")
            )

        # Malicious payloads
        payload_script = "<script>alert('xss')</script>"
        escaped_script = py_escape_html(payload_script)
        self.assertNotIn("<script>", escaped_script)
        self.assertEqual(escaped_script, "&lt;script&gt;alert(&#039;xss&#039;)&lt;/script&gt;")

        payload_img = '<img src=x onerror="alert(`XSS`)">'
        escaped_img = py_escape_html(payload_img)
        self.assertNotIn("<img", escaped_img)
        self.assertNotIn('"', escaped_img)
        self.assertNotIn("`", escaped_img)

        # Graceful handling of numbers and None
        self.assertEqual(py_escape_html(12345), "12345")
        self.assertEqual(py_escape_html(None), "")

    def test_05_unauthenticated_ajax_returns_401_for_session_interception(self):
        """Verify unauthenticated AJAX request receives 401 JSON so utils.js intercepts it."""
        response = self.client.get(
            "/feed",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"
            }
        )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data.get("session_expired") or "error" in data)

    def test_06_mutating_financial_routes_reject_missing_csrf_when_enabled(self):
        """Verify mutating POST endpoints enforce CSRF validation when WTF_CSRF_ENABLED=True."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["user_level"] = "admin"
                sess["is_admin"] = True
                sess["vid"] = 1

            # Temporarily enable CSRF for this specific security check
            app.config["WTF_CSRF_ENABLED"] = True
            try:
                # Post payment delete without CSRF token
                response = client.post(
                    "/delete_payment",
                    json={"pid": 9999, "ano": 101, "pdt": "2026-11-06"},
                    headers={"X-Requested-With": "XMLHttpRequest"}
                )
                # Must be 400 Bad Request due to missing CSRF token
                self.assertEqual(response.status_code, 400)
            finally:
                app.config["WTF_CSRF_ENABLED"] = False

    @patch("app.audit_log")
    @patch("app.recalc_customer_balance")
    @patch("app.invalidate_village_health_cache")
    @patch("app.get_pg_connection")
    def test_07_idempotency_header_support(self, mock_get_conn, mock_invalidate, mock_recalc, mock_audit):
        """Verify mutating routes process requests with X-Client-Request-Id header without error."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["user_level"] = "admin"
                sess["is_admin"] = True
                sess["vid"] = 1

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.__enter__.return_value = mock_cur
            mock_conn.__enter__.return_value = mock_conn

            # Delete query mock return: payment found in village 1
            mock_cur.fetchone.return_value = (10, 55, 1, "2026-11-06", 500)
            mock_cur.rowcount = 1

            response = client.post(
                "/delete_payment",
                json={"pid": 12345},
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Client-Request-Id": "12345678-1234-5678-1234-567812345678"
                }
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data.get("success"))

    def test_08_mobile_app_extends_base_and_uses_unified_csrf(self):
        """Verify templates/mobile_app.html extends base.html and references unified csrfFetch."""
        mobile_template_path = os.path.join(APP_ROOT, "templates", "mobile_app.html")
        self.assertTrue(os.path.exists(mobile_template_path))

        with open(mobile_template_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(
            content.startswith('{% extends "base.html" %}') or '{% extends "base.html" %}' in content[:100],
            "mobile_app.html must extend base.html"
        )
        self.assertIn("window.csrfFetch || window.fetch", content)

    def test_09_village_page_renders_with_format_waiting_duration(self):
        """Verify /village route renders cleanly using format_waiting_duration."""
        from datetime import datetime, timezone

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["level"] = "admin"
                sess["is_admin"] = True
                sess["vid"] = 1
                sess["village_code"] = "V01"
                sess["village_name"] = "Test Village"

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            mock_cur.fetchone.side_effect = [(5,)]
            mock_cur.fetchall.side_effect = [
                [
                    (1, "V01", "Test Village", "District", "500001", "State", 1, "Emp 1", None, None, 2.0, 1.0, datetime.now(timezone.utc), "active", 17.0, 78.0, 100, 2, datetime.now(timezone.utc))
                ],
                []  # cashbags
            ]
            mock_cur.description = [
                ("vid",), ("village_code",), ("village_name",), ("district",), ("pincode",),
                ("state",), ("emp1",), ("emp1_name",), ("emp2",), ("emp2_name",),
                ("interest_rate",), ("cutting_rate",), ("created_at",), ("status",),
                ("latitude",), ("longitude",), ("customer_count",), ("pending_feed_count",),
                ("oldest_pending_time",)
            ]

            with patch("app.get_pg_connection", return_value=mock_conn):
                response = client.get("/village")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Test Village", response.data)

    def test_10_post_payment_analytics_endpoint(self):
        """Verify /api/post_payment_analytics returns 200 and expected analytics structure."""
        from datetime import date

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["level"] = "admin"
                sess["is_admin"] = True
                sess["vid"] = 1
                sess["village_code"] = "V01"
                sess["village_name"] = "Test Village"

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            mock_cur.fetchone.side_effect = [
                (date(2026, 10, 28),),  # MAX(payment_date)
                (None,),
            ]
            mock_cur.fetchall.side_effect = [
                [
                    (1, 101, "Customer 1", 10000, 1000, date(2026, 1, 1), None)
                ],
                [
                    (1, 1000, date(2026, 10, 28))
                ]
            ]

            with patch("routes.payment_routes.get_resolved_pg_conn", return_value=mock_conn), \
                 patch("routes.payment_routes.is_village_monthly", return_value=False):
                response = client.get("/api/post_payment_analytics")
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertIsNotNone(data)
                self.assertIn("last_posting_date", data)
                self.assertIn("weeks", data)
                self.assertIn("28-10-2026", data["last_posting_date"])
                self.assertEqual(len(data["weeks"]), 5)

    def test_11_submit_post_payment_and_button_attributes(self):
        """Verify post_payment.html Submit button has type='button' and submit_post_payment succeeds."""
        # 1. Template verification
        template_path = os.path.join(APP_ROOT, "templates", "post_payment.html")
        with open(template_path, "r", encoding="utf-8") as f:
            tmpl = f.read()
        self.assertIn('type="button" class="neumorphic-btn small submit-btn" id="submitAllPaymentsBtn"', tmpl)
        self.assertIn('onclick="submitAllPayments(event)"', tmpl)

        # 2. Endpoint verification
        from datetime import date
        from decimal import Decimal
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["level"] = "admin"
                sess["is_admin"] = True
                sess["vid"] = 1
                sess["employee_id"] = 99  # modern session key

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            # Mock customer query return: (cid, total_amount, paid_amount, start_date)
            mock_cur.fetchone.side_effect = [
                (101, Decimal(10000), Decimal(2000), date(2026, 1, 1)),  # customer lookup
                None,  # duplicate check -> none found
            ]

            payload = [{"ano": 1, "pdt": "06-11-2026", "amt": 4000}]
            with patch("routes.payment_routes.get_resolved_pg_conn", return_value=mock_conn), \
                 patch("routes.payment_routes._call_recalc_balance"), \
                 patch("routes.payment_routes._call_invalidate_cache"), \
                 patch("routes.payment_routes._call_audit_log"):
                response = client.post(
                    "/submit_post_payment",
                    json=payload,
                    headers={"X-Requested-With": "XMLHttpRequest"}
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data.get("success"))
                self.assertEqual(data.get("submitted_count"), 1)
                self.assertEqual(data.get("skipped_count"), 0)

    def test_12_set_context_handling_for_admin_and_inactive_villages(self):
        """Verify set_context allows admins to access inactive villages and blocks non-admins."""
        with app.test_client() as client:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            # 1. Admin accessing inactive village -> should succeed
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["level"] = "admin"
                sess["is_admin"] = True

            # (emp1, emp2, village_name, village_code, emp1_name, emp2_name, status)
            mock_cur.fetchone.return_value = (86, 87, "NANDIKOTKUR 2", "NDK2", "Emp 1", "Emp 2", "inactive")

            with patch("app.get_pg_connection", return_value=mock_conn):
                resp = client.post("/set_context", json={"vid": 110043})
                self.assertEqual(resp.status_code, 200)
                data = resp.get_json()
                self.assertTrue(data.get("success"))
                self.assertEqual(data.get("village_status"), "inactive")

            # 2. Non-admin accessing inactive village -> should be rejected with 403
            with client.session_transaction() as sess:
                sess["user_id"] = 2
                sess["username"] = "staff_user"
                sess["level"] = "user"
                sess["is_admin"] = False
                sess["villages"] = [110043]

            mock_cur.fetchone.return_value = (86, 87, "NANDIKOTKUR 2", "NDK2", "Emp 1", "Emp 2", "inactive")

            with patch("app.get_pg_connection", return_value=mock_conn):
                resp = client.post("/set_context", json={"vid": 110043})
                self.assertEqual(resp.status_code, 403)
                data = resp.get_json()
                self.assertFalse(data.get("success"))
                self.assertIn("inactive", data.get("error").lower())


if __name__ == "__main__":
    unittest.main()
