"""
Automated PyUnit Test Suite for Phase 6 (Phase 2): Infrastructure Daemons & Configuration
File: SD_Accounting_Tool/tests/test_phase6_chat_phase2.py

Tests:
1. Centrifugo configuration schema and namespace validity.
2. Nginx reverse proxy configuration directives.
3. Setup script syntax validation (bash -n).
4. Health check sentinel socket & HTTP parsing logic.
"""

import os
import sys
import json
import unittest
import subprocess
from unittest.mock import patch, MagicMock

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from scripts.check_chat_services import check_port, check_http_endpoint, check_media_storage


class TestPhase6ChatPhase2(unittest.TestCase):

    def setUp(self):
        self.scripts_dir = os.path.join(APP_ROOT, "scripts")

    def test_centrifugo_config_json_validity(self):
        """Verify centrifugo.json is valid JSON with mandatory port, origins, and namespaces."""
        config_path = os.path.join(self.scripts_dir, "centrifugo.json")
        self.assertTrue(os.path.isfile(config_path), f"Missing {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.assertEqual(cfg.get("port"), 8001)
        self.assertEqual(cfg.get("address"), "127.0.0.1")
        origins = cfg.get("client", {}).get("allowed_origins") or cfg.get("allowed_origins", [])
        self.assertIn("https://sivadurga.in", origins)

        namespaces_list = cfg.get("channel", {}).get("namespaces") or cfg.get("namespaces", [])
        namespaces = {ns["name"]: ns for ns in namespaces_list}
        self.assertIn("chat", namespaces)
        self.assertIn("broadcast", namespaces)

        chat_ns = namespaces["chat"]
        self.assertTrue(chat_ns.get("presence"))
        self.assertTrue(chat_ns.get("history_size") >= 50)

    def test_nginx_chat_conf_directives(self):
        """Verify nginx_chat.conf contains proper timeout, buffering, and WebSocket directives."""
        nginx_path = os.path.join(self.scripts_dir, "nginx_chat.conf")
        self.assertTrue(os.path.isfile(nginx_path), f"Missing {nginx_path}")

        with open(nginx_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("client_max_body_size 15M;", content)
        self.assertIn("location /connection/websocket", content)
        self.assertIn("proxy_pass http://127.0.0.1:8001/connection/websocket;", content)
        self.assertIn("proxy_read_timeout 3600s;", content)
        self.assertIn("proxy_buffering off;", content)
        self.assertIn("location /chat-media/", content)

    def test_setup_phase2_daemons_bash_syntax(self):
        """Verify setup_phase2_daemons.sh is free of bash syntax errors."""
        script_path = os.path.join(self.scripts_dir, "setup_phase2_daemons.sh")
        self.assertTrue(os.path.isfile(script_path), f"Missing {script_path}")

        result = subprocess.run(["bash", "-n", script_path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Bash syntax error: {result.stderr}")

    @patch("socket.create_connection")
    def test_check_port_success_and_failure(self, mock_create_connection):
        """Verify socket health check returns latency on success and error on failure."""
        mock_conn = MagicMock()
        mock_create_connection.return_value.__enter__.return_value = mock_conn

        ok, msg = check_port("127.0.0.1", 6379)
        self.assertTrue(ok)
        self.assertIn("ms", msg)

        # Test failure
        mock_create_connection.side_effect = ConnectionRefusedError("Connection refused")
        ok, msg = check_port("127.0.0.1", 6379)
        self.assertFalse(ok)
        self.assertIn("Connection refused", msg)

    @patch("urllib.request.urlopen")
    def test_check_http_endpoint_parsing(self, mock_urlopen):
        """Verify HTTP endpoint check parses status codes and latency."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok, msg = check_http_endpoint("http://127.0.0.1:8001/health")
        self.assertTrue(ok)
        self.assertIn("HTTP 200", msg)


if __name__ == "__main__":
    unittest.main()
