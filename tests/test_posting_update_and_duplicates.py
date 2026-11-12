import unittest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app import app
from routes.mobile_api_routes import mobile_bp


class TestPostingUpdateAndDuplicates(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_mobile_ping(self):
        """Verify /api/mobile/ping returns 200 and status ok."""
        res = self.client.get("/api/mobile/ping")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
