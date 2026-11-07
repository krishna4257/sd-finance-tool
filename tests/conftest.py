"""Shared pytest fixtures and test harness for SD Finance Tool.
Supports isolated testing of Flask routes, security decorators, and frontend contracts.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Ensure application root is on sys.path
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

try:
    import pytest
except ImportError:
    pytest = None

from app import app as flask_app


def get_mock_db_connection():
    """Build a compliant mock psycopg2 connection and cursor for testing."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.__enter__.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    return mock_conn, mock_cur


if pytest is not None:
    @pytest.fixture(scope="session")
    def app():
        """Session-scoped Flask application instance configured for testing."""
        flask_app.config.update({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost",
        })
        return flask_app

    @pytest.fixture
    def client(app):
        """Standard Flask test client."""
        return app.test_client()

    @pytest.fixture
    def authenticated_client(app):
        """Test client with an active admin session."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["user_level"] = "admin"
                sess["is_admin"] = True
                sess["vid"] = 1
                sess["village_name"] = "Test Village"
            yield client

    @pytest.fixture
    def mock_db():
        """Fixture that patches get_pg_connection with a MagicMock cursor."""
        mock_conn, mock_cur = get_mock_db_connection()
        with patch("app.get_pg_connection", return_value=mock_conn), \
             patch("db.get_pg_connection", return_value=mock_conn):
            yield mock_conn, mock_cur
