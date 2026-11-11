"""Base test fixtures, helpers, and cryptographic utilities for SD Finance E2E testing."""

import os
import sys
import uuid
import json
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["TESTING"] = "True"
os.environ["DISABLE_SECURE_COOKIE"] = "1"
os.environ["WTF_CSRF_ENABLED"] = "False"
if not os.environ.get("MOBILE_QUEUE_HMAC_SECRET"):
    os.environ["MOBILE_QUEUE_HMAC_SECRET"] = "dev-mobile-queue-secret"

import app as flask_app_mod
from app import app
from db import get_pg_connection
from security.mobile_auth import (
    generate_mobile_token,
    get_mobile_queue_hmac_secret,
    compute_canonical_envelope_hmac,
)

# Test village constants
TEST_VID = 110102
TEST_VNAME = "TEST"
TEST_VCODE = "TST"
ADMIN_USER_ID = 4  # user: chinna
ADMIN_EID = 5      # employee: 5 (Karri Chinna Reddy)
TEST_CHIT_GROUP_ID = "987b8c46-d51b-4289-82e9-501a730f9e3d"
TEST_BANK_GROUP_ID = "4a42da05-6570-4a5c-9bef-b76eec0a564f"
TEST_CASHBAG_ID = "3faccb2c-f3a1-41cd-8a7e-c484dc8771e9"


def configure_app():
    """Ensure app is configured cleanly for end-to-end testing."""
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost",
    })
    return app


def get_admin_client(app_instance=None):
    """Return a Flask test client with an authenticated admin session."""
    if app_instance is None:
        app_instance = configure_app()
    client = app_instance.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = ADMIN_USER_ID
        sess["username"] = "chinna"
        sess["employee_id"] = ADMIN_EID
        sess["level"] = "admin"
        sess["role"] = "admin"
        sess["villages"] = [TEST_VID]
        sess["vid"] = TEST_VID
        sess["village_name"] = TEST_VNAME
        sess["village_code"] = TEST_VCODE
    return client


def get_mobile_token_and_headers(user_id=ADMIN_USER_ID, eid=ADMIN_EID):
    """Generate mobile bearer token and headers."""
    token = generate_mobile_token(user_id, eid)
    return {
        "X-Mobile-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_signed_mobile_envelope(msg_type, payload_dict, vid=TEST_VID, eid=ADMIN_EID):
    """Generate a canonical HMAC signed envelope compliant with security.mobile_auth."""
    secret = get_mobile_queue_hmac_secret()
    nonce = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    idempotency_key = str(uuid.uuid4())

    signed_payload = {
        "type": msg_type,
        "eid": int(eid),
        "vid": int(vid),
        "nonce": nonce,
        "timestamp": ts,
        "idempotency_key": idempotency_key,
        "payload": payload_dict,
    }

    sig = compute_canonical_envelope_hmac(signed_payload, secret)
    envelope = dict(signed_payload)
    envelope["signature"] = sig
    return envelope


def query_db(sql, params=None, fetchone=False, fetchall=False, commit=False):
    """Execute raw query against PostgreSQL."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        res = None
        if fetchone:
            res = cur.fetchone()
        elif fetchall:
            res = cur.fetchall()
        if commit:
            conn.commit()
        cur.close()
        return res
    finally:
        conn.close()


def cleanup_test_records():
    """Clean up test entities generated with 'TEST-E2E-' prefixes."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        # Clean payment_feed_items (where payload contains test ano 999001 or TEST-E2E)
        cur.execute("DELETE FROM payment_feed_items WHERE payload::text LIKE '%%999001%%' OR payload::text LIKE '%%TEST-E2E%%'")
        # Clean customer_feed
        cur.execute("DELETE FROM customer_feed WHERE vid = %s AND (payload::text LIKE '%%TEST-E2E%%' OR payload::text LIKE '%%999001%%')", (TEST_VID,))
        # Clean account_closure_feed
        cur.execute("DELETE FROM account_closure_feed WHERE vid = %s AND ano >= 900000", (TEST_VID,))
        # Clean live payment
        cur.execute("DELETE FROM payment WHERE vid = %s AND ano >= 900000", (TEST_VID,))
        # Clean live customer
        cur.execute("DELETE FROM customer WHERE vid = %s AND (name LIKE '%%TEST-E2E%%' OR ano >= 900000)", (TEST_VID,))
        # Clean closed_cust_account
        cur.execute("DELETE FROM closed_cust_account WHERE vid = %s AND (name LIKE '%%TEST-E2E%%' OR ano >= 900000)", (TEST_VID,))
        # Clean chit test payments
        cur.execute("DELETE FROM chit_payments WHERE notes LIKE '%%TEST-E2E%%'")
        conn.commit()
        cur.close()
    finally:
        conn.close()
