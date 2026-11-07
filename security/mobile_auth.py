import os
import json
import hmac
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, g, jsonify, current_app, has_app_context
from itsdangerous import URLSafeTimedSerializer
from db import get_pg_connection

logger = logging.getLogger(__name__)

_serializer_instance = None


def _resolve_func(name, default_func):
    """
    Allow backwards-compatible mock patching where tests or callers patch `app.<name>`.
    If `app.<name>` exists and was replaced (e.g. by a MagicMock), use it instead.
    """
    try:
        import sys
        app_mod = sys.modules.get("app")
        if app_mod is not None and hasattr(app_mod, name):
            val = getattr(app_mod, name)
            if val is not default_func:
                return val
    except Exception:
        pass
    return default_func


def set_serializer(s):
    """Explicitly register a serializer instance (called by app initialization)."""
    global _serializer_instance
    _serializer_instance = s


def get_serializer():
    """Retrieve the URLSafeTimedSerializer using the application config or environment."""
    if _serializer_instance is not None:
        return _serializer_instance

    secret = None
    if has_app_context():
        secret = current_app.config.get("SECRET_KEY")

    if not secret:
        try:
            import app as flask_app_mod
            secret = getattr(flask_app_mod, "app", None).config.get("SECRET_KEY")
        except Exception:
            pass

    if not secret:
        secret = os.environ.get("SECRET_KEY", "sd-accounting-secret-fallback")

    return URLSafeTimedSerializer(secret)


def generate_mobile_token(user_id, eid):
    """Generate a signed mobile bearer token with user_id and eid."""
    payload = {
        "user_id": user_id,
        "eid": eid
    }
    return get_serializer().dumps(payload)


def verify_mobile_token(token):
    """Verify and decode a signed mobile bearer token."""
    try:
        data = get_serializer().loads(token, max_age=86400 * 30)
        return data
    except Exception:
        return None


def get_active_mobile_user(token_data, cur=None):
    """
    Validates that user_id and eid in token_data correspond to an existing,
    active user and active employee in PostgreSQL.
    Returns user dict or None if invalid/inactive/revoked.
    """
    if not token_data or not isinstance(token_data, dict):
        return None
    user_id = token_data.get("user_id")
    eid = token_data.get("eid")
    if not user_id:
        return None

    should_close = False
    if cur is None:
        get_conn_fn = _resolve_func("get_pg_connection", get_pg_connection)
        conn = get_conn_fn()
        cur = conn.cursor()
        should_close = True

    try:
        cur.execute("""
            SELECT u.id, u.username, u.is_active, u.employee_id, e.level, e.status
            FROM users u
            LEFT JOIN employee e ON e.eid = u.employee_id
            WHERE u.id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return None

        u_id, username, is_active, emp_id, level, emp_status = row
        if not is_active:
            return None

        if emp_status and emp_status.strip().lower() not in ("active", "a"):
            return None

        if eid and emp_id and str(eid) != str(emp_id):
            return None

        clean_level = (level or "").strip().lower()
        return {
            "user_id": u_id,
            "username": username,
            "eid": emp_id or eid,
            "level": clean_level,
            "is_active": is_active
        }
    except Exception as e:
        logger.error("Error verifying active mobile user: %s", e)
        return None
    finally:
        if should_close:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass


def check_user_village_access(user_id, eid, user_level, vid, cur=None):
    """
    Checks if the user has permission to access the specified village (vid).
    - Admin, superadmin, management roles have global access to all villages.
    - Other users must have an entry in user_village_access OR be assigned to the village (emp1/emp2).
    """
    if not vid:
        return False

    clean_level = (user_level or "").strip().lower()
    if clean_level in ("admin", "superadmin", "mgmt", "management"):
        return True

    try:
        vid_int = int(vid)
    except (ValueError, TypeError):
        return False

    should_close = False
    if cur is None:
        get_conn_fn = _resolve_func("get_pg_connection", get_pg_connection)
        conn = get_conn_fn()
        cur = conn.cursor()
        should_close = True

    try:
        # 1. Check explicit user_village_access assignment
        cur.execute("""
            SELECT 1 FROM user_village_access
            WHERE user_id = %s AND village_id = %s
            LIMIT 1
        """, (user_id, vid_int))
        if cur.fetchone():
            return True

        # 2. Check employee village assignment (emp1 or emp2)
        if eid:
            try:
                eid_int = int(eid)
                cur.execute("""
                    SELECT 1 FROM village
                    WHERE vid = %s AND (emp1 = %s OR emp2 = %s)
                    LIMIT 1
                """, (vid_int, eid_int, eid_int))
                if cur.fetchone():
                    return True
            except (ValueError, TypeError):
                pass

        return False
    except Exception as e:
        logger.error("Error checking user village access: %s", e)
        return False
    finally:
        if should_close:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass


def mobile_auth_required(allowed_levels=None, verify_village=False):
    """
    Enforces that incoming request has a valid X-Mobile-Token,
    that the corresponding user is active in the database,
    optionally verifies allowed user levels,
    and optionally verifies that the village (vid from query, json, or form) is authorized.
    Sets g.mobile_user and g.mobile_token_data.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get("X-Mobile-Token")
            if not token:
                return jsonify({"error": "missing token"}), 401

            token_data = verify_mobile_token(token)
            if not token_data:
                return jsonify({"error": "invalid token"}), 401

            get_user_fn = _resolve_func("get_active_mobile_user", get_active_mobile_user)
            user = get_user_fn(token_data)
            if not user:
                return jsonify({"error": "user inactive or token revoked"}), 401

            if allowed_levels:
                normalized_allowed = [lvl.strip().lower() for lvl in allowed_levels]
                if user["level"] not in normalized_allowed:
                    return jsonify({"error": "unauthorized access level"}), 403

            if verify_village:
                vid = request.args.get("vid")
                if vid is None and request.is_json:
                    body = request.get_json(silent=True) or {}
                    vid = body.get("vid")
                if vid is None and request.form:
                    vid = request.form.get("vid")

                if vid is not None and str(vid).strip():
                    check_village_fn = _resolve_func("check_user_village_access", check_user_village_access)
                    if not check_village_fn(user["user_id"], user["eid"], user["level"], vid):
                        return jsonify({"error": f"Access denied: Village {vid} is not assigned to this account"}), 403

            g.mobile_token_data = token_data
            g.mobile_user = user
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def parse_mobile_timestamp(ts):
    if not ts:
        return None
    try:
        # Mobile sends IST but without timezone -> force IST
        dt = datetime.fromisoformat(ts)

        # If no timezone -> assume IST
        if dt.tzinfo is None:
            ist_offset = timedelta(hours=5, minutes=30)
            dt = dt.replace(tzinfo=timezone(ist_offset))

        # Convert to UTC (Postgres compares internally in UTC)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def get_mobile_queue_hmac_secret():
    secret = os.environ.get("MOBILE_QUEUE_HMAC_SECRET")
    is_prod = (
        os.environ.get("FLASK_ENV", "").strip().lower() == "production"
        or os.environ.get("ENV", "").strip().lower() == "production"
        or os.environ.get("ENVIRONMENT", "").strip().lower() == "production"
        or os.environ.get("PRODUCTION", "").strip().lower() in ("1", "true")
    )
    if not secret:
        if is_prod:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "MOBILE_QUEUE_HMAC_SECRET must be defined in production environment!"
            )
        secret = os.environ.get("SECRET_KEY") or "dev-mobile-queue-secret"
        logger.warning("Using fallback development HMAC secret. Please configure MOBILE_QUEUE_HMAC_SECRET.")
    return secret


def compute_canonical_envelope_hmac(signed_payload, secret):
    return hmac.new(
        secret.encode("utf-8"),
        _canonical_json(signed_payload).encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def verify_queue_integrity(data, token_data):
    if not isinstance(data, dict):
        return False, "invalid envelope"

    required_fields = [
        "type",
        "eid",
        "vid",
        "nonce",
        "timestamp",
        "idempotency_key",
        "payload",
        "signature",
    ]
    missing = [field for field in required_fields if data.get(field) in (None, "")]
    if missing:
        return False, f"missing integrity fields: {', '.join(missing)}"

    try:
        eid_val = data.get("eid")
        vid_val = data.get("vid")
        token_eid_val = token_data.get("eid")

        if eid_val is None or vid_val is None or token_eid_val is None:
            return False, "invalid identity fields"

        envelope_eid = int(eid_val)
        envelope_vid = int(vid_val)
        token_eid = int(token_eid_val)
    except Exception:
        return False, "invalid identity fields"

    if envelope_eid != token_eid:
        return False, "eid mismatch"

    ts = parse_mobile_timestamp(data.get("timestamp"))
    if ts is None:
        return False, "invalid timestamp"

    age_seconds = abs((datetime.now(timezone.utc) - ts).total_seconds())
    if age_seconds > 900:
        return False, "stale timestamp"

    signing_secret = get_mobile_queue_hmac_secret()

    signed_payload = {
        "type": data.get("type"),
        "eid": envelope_eid,
        "vid": envelope_vid,
        "nonce": data.get("nonce"),
        "timestamp": data.get("timestamp"),
        "idempotency_key": data.get("idempotency_key"),
        "payload": data.get("payload"),
    }

    expected_signature = compute_canonical_envelope_hmac(signed_payload, signing_secret)

    provided_signature = str(data.get("signature") or "")
    if not hmac.compare_digest(provided_signature, expected_signature):
        return False, "invalid signature"

    return True, None


def register_mobile_request_integrity(
    cur,
    *,
    endpoint,
    eid,
    vid,
    local_uuid,
    idempotency_key,
    nonce,
    request_signature,
    request_timestamp,
):
    cur.execute("""
        INSERT INTO mobile_request_integrity
        (
            endpoint,
            eid,
            vid,
            local_uuid,
            idempotency_key,
            nonce,
            request_signature,
            request_timestamp
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (endpoint, idempotency_key) DO NOTHING
        RETURNING id
    """, (
        endpoint,
        eid,
        vid,
        local_uuid,
        idempotency_key,
        nonce,
        request_signature,
        request_timestamp,
    ))

    row = cur.fetchone()
    if row:
        return True, "accepted"

    cur.execute("""
        SELECT idempotency_key, nonce
        FROM mobile_request_integrity
        WHERE endpoint = %s
          AND (idempotency_key = %s OR nonce = %s)
        LIMIT 1
    """, (endpoint, idempotency_key, nonce))

    existing = cur.fetchone()
    if not existing:
        return False, "duplicate request"

    existing_idempotency_key, existing_nonce = existing
    if existing_nonce == nonce:
        return False, "duplicate nonce"
    if existing_idempotency_key == idempotency_key:
        return False, "duplicate idempotency key"

    return False, "duplicate request"
