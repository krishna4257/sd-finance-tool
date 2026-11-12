"""
Automated PyUnit Test Suite for Phase 6 (Phase 5): Web Management Portal & Template Rendering
File: SD_Accounting_Tool/tests/test_phase6_chat_web.py

Tests:
1. Unauthenticated access redirect/block for web chat.
2. Authenticated rendering of templates/chat.html (HTTP 200).
3. DOM structure, Telugu font support, and attachment controls in chat.html.
4. Navigation bar integration in templates/base.html.
"""

import os
import sys
import unittest

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

import app as main_app


class TestPhase6ChatWeb(unittest.TestCase):

    def setUp(self):
        main_app.app.config["TESTING"] = True
        main_app.app.config["WTF_CSRF_ENABLED"] = False
        main_app.app.config["SECRET_KEY"] = "test-secret-key-64-characters-long-sd-finance-testing-suite"
        self.client = main_app.app.test_client()

    def test_unauthenticated_web_chat_access(self):
        """Verify unauthenticated user cannot access /api/v1/chat/web."""
        res = self.client.get("/api/v1/chat/web")
        # Should return 401 JSON or redirect to login
        self.assertIn(res.status_code, (401, 302))

    def test_authenticated_web_chat_rendering(self):
        """Verify authenticated admin user can render /api/v1/chat/web successfully."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["user_level"] = "admin"
            sess["role"] = "admin"

        res = self.client.get("/api/v1/chat/web")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check core layout elements
        self.assertIn("Internal Staff Messaging", html)
        self.assertIn("chat-sidebar", html)
        self.assertIn("chat-viewport", html)
        self.assertIn("conversation-messages", html)
        self.assertIn("chat-text-input", html)
        self.assertIn("chat.js", html)
        self.assertIn("chat.css", html)
        self.assertIn("Noto+Sans+Telugu", html)

    def test_chat_shortcut_redirect(self):
        """Verify /chat shortcut redirects to /api/v1/chat."""
        res = self.client.get("/chat")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/api/v1/chat", res.headers.get("Location", ""))

    def test_base_html_has_messages_nav_link(self):
        """Verify templates/base.html contains the Messages link."""
        base_path = os.path.join(APP_ROOT, "templates", "base.html")
        self.assertTrue(os.path.isfile(base_path))

        with open(base_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('href="/chat"', content)
        self.assertIn("fa-comments", content)
        self.assertIn("Messages", content)


if __name__ == "__main__":
    unittest.main()
