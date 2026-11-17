"""
Unit tests for the official SD Finance iOS / Mobile PWA routes.
"""
import unittest
from app import app


class TestPWARoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_pwa_index_returns_200(self):
        response = self.client.get("/pwa/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Smart Counting", response.data)
        self.assertIn("text/html", response.headers.get("Content-Type", ""))

    def test_pwa_manifest_returns_json(self):
        response = self.client.get("/pwa/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Smart Counting", response.data)
        self.assertIn("application/manifest+json", response.headers.get("Content-Type", ""))

    def test_pwa_service_worker_returns_js_with_headers(self):
        response = self.client.get("/pwa/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Service-Worker-Allowed"), "/pwa/")
        self.assertIn("javascript", response.headers.get("Content-Type", ""))

    def test_ios_shortcut_redirects_to_pwa(self):
        response = self.client.get("/ios")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/pwa/")

    def test_mobile_shortcut_redirects_to_pwa(self):
        response = self.client.get("/mobile")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/pwa/")


if __name__ == "__main__":
    unittest.main()
