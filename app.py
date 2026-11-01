import os
import re
import pytz
import requests
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import]
import time as pytime
import calendar
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
import traceback
import logging
import uuid
import base64
import hashlib
import hmac
import json
from functools import wraps
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from dateutil.relativedelta import relativedelta
import secrets
import threading
import queue
import io
import socket
from flask import (
    Flask, render_template, request, redirect,
    session, jsonify, flash, url_for, send_file, Response
)
from db import get_pg_connection
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError
from psycopg2.extras import execute_values
from chit_calc_engine import round_curr
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------
# AUDIT LOGGING SYSTEM
# ----------------------------------------------------
def audit_log(
    action,
    entity_type=None,
    entity_id=None,
    details=None,
    status="success"
):
    conn = None
    cur = None

    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        user_id = session.get("user_id")
        employee_id = session.get("employee_id") or session.get("eid")
        username = session.get("username")

        cur.execute("""
            INSERT INTO audit_log (
                action,
                entity_type,
                entity_id,
                user_id,
                employee_id,
                username,
                ip_address,
                request_method,
                request_path,
                user_agent,
                details,
                status
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s
            )
        """, (
            action,
            entity_type,
            str(entity_id) if entity_id is not None else None,
            user_id,
            employee_id,
            username,
            request.remote_addr,
            request.method,
            request.path,
            request.headers.get("User-Agent"),
            json.dumps(details or {}),
            status
        ))

        conn.commit()

    except Exception as e:
        logger.warning("Audit log failed: %s", e)

        if conn:
            conn.rollback()

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()

# Helper: Log DB pool stats
# CENTRALIZED DATE UTILITIES
def parse_date_input(value):
    """Parse a date from any common format into a Python date object.
    Accepts: 'yyyy-mm-dd' (ISO), 'dd-mm-yyyy', 'dd/mm/yyyy', date, datetime.
    Returns: datetime.date or None if parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    # Try ISO first (yyyy-mm-dd)
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        pass
    # Try dd-mm-yyyy (hyphens)
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError:
        pass
    # Try dd/mm/yyyy (slashes)
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        pass
    return None


def format_date_display(value):
    """Format a date for frontend display as dd-mm-yyyy.
    Accepts: date, datetime, or ISO string.
    Returns: 'dd-mm-yyyy' string or '' if None/invalid.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        value = parse_date_input(value)
        if value is None:
            return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")


def format_date_iso(value):
    """Format a date for HTML5 <input type='date'> as yyyy-mm-dd.
    Accepts: date, datetime, or date string (iso, dd-mm-yyyy, dd/mm/yyyy).
    Returns: 'yyyy-mm-dd' string or '' if None/invalid.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            return value
        parsed = parse_date_input(value)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
        return value
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return ""


def ensure_feed_tables_exist(cur):
    """Ensure customer_feed_edits and payment_feed_edits tables exist."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_feed_edits (
            edit_id SERIAL PRIMARY KEY,
            local_uuid TEXT NOT NULL,
            edited_payload JSONB NOT NULL,
            eid INTEGER,
            vid INTEGER,
            edit_status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_feed_edits (
            edit_id SERIAL PRIMARY KEY,
            local_uuid TEXT NOT NULL,
            edited_payload JSONB NOT NULL,
            eid INTEGER,
            vid INTEGER,
            edit_status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feed_rejections (
            rejection_id SERIAL PRIMARY KEY,
            feed_type TEXT NOT NULL,
            local_uuid TEXT,
            ano INTEGER,
            vid INTEGER,
            eid INTEGER,
            action_type TEXT DEFAULT 'rejected_deleted',
            deleted_by TEXT,
            reason TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_feed_rejections_vid ON feed_rejections (vid);
        CREATE INDEX IF NOT EXISTS idx_feed_rejections_uuid ON feed_rejections (local_uuid);
    """)
    # Ensure payment.payment_type check constraint includes 'partial'
    try:
        cur.execute("""
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'payment' AND c.conname = 'payment_payment_type_chk'
        """)
        chk_row = cur.fetchone()
        if chk_row and "'partial'" not in chk_row[0]:
            cur.execute("""
                ALTER TABLE payment DROP CONSTRAINT IF EXISTS payment_payment_type_chk;
                ALTER TABLE payment ADD CONSTRAINT payment_payment_type_chk 
                    CHECK (lower(payment_type) = ANY (ARRAY['cash', 'upi', 'partial', 'mixed']));
            """)
    except Exception:
        pass


# ----------------------------------------------------
# REAL-TIME SUBMISSION STATUS SYSTEM (SAFE NO-OP STUBS)
# ----------------------------------------------------
# Note: Persistent in-memory SSE pub-sub was deprecated because Gunicorn pre-forked
# worker processes have isolated memory spaces, and long-lived streams starved Gunicorn
# threads. Statuses are authoritatively recorded in PostgreSQL and retrieved via
# lightweight status polling (/api/mobile/submissions/status).

def add_sse_subscriber(vid, q):
    pass

def remove_sse_subscriber(vid, q):
    pass

def broadcast_submission_event(vid, event_data):
    """Deprecated: Status updates are written to PostgreSQL and fetched via polling."""
    pass



def ensure_user_devices_table(cur):
    """Ensure user_devices table has device_model column and unique index on (user_id, device_id)."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_devices (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            device_model TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            last_active TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        ALTER TABLE user_devices ADD COLUMN IF NOT EXISTS device_model TEXT
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_devices_user_device 
        ON user_devices (user_id, device_id)
    """)


def generate_mobile_token(user_id, eid):
    payload = {
        "user_id": user_id,
        "eid": eid
    }

    token = serializer.dumps(payload)
    return token

def verify_mobile_token(token):
    try:
        data = serializer.loads(token, max_age=86400*30)
        return data
    except Exception:
        return None
    

def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def get_mobile_queue_hmac_secret():
    secret = os.environ.get("MOBILE_QUEUE_HMAC_SECRET") or os.environ.get("SECRET_KEY") or "dev-mobile-queue-secret"
    return secret


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

    expected_signature = hmac.new(
    signing_secret.encode("utf-8"),
    _canonical_json(signed_payload).encode("utf-8"),
    hashlib.sha256).hexdigest()


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


def parse_mobile_timestamp(ts):
    if not ts:
        return None
    try:
        # Mobile sends IST but without timezone → force IST
        dt = datetime.fromisoformat(ts)

        # If no timezone → assume IST
        if dt.tzinfo is None:
            ist_offset = timedelta(hours=5, minutes=30)
            dt = dt.replace(tzinfo=timezone(ist_offset))

        # Convert to UTC (Postgres compares internally in UTC)
        return dt.astimezone(timezone.utc)

    except Exception as e:
        logger.warning("Timestamp parse error: %s", e)
        return None
    
def normalize_account_number(value):
    if value is None:
        return None
    try:
        return int(str(value).replace(".0", "").strip())
    except Exception:
        return None


def merge_edit_payload(original, edited):
    """Helper to merge edited fields into original payload."""
    if not isinstance(original, dict) or not isinstance(edited, dict):
        return original
    res = dict(original)
    if "payload" in res and isinstance(res["payload"], dict):
        res["payload"] = dict(res["payload"])
        res["payload"].update(edited)
    else:
        res.update(edited)
    return res


def normalize_mobile_customer_payload(payload):
    """Normalize customer payload from mobile app to match DB column names."""
    if not isinstance(payload, dict):
        raise ValueError("Invalid customer payload")

    source = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    normalized = dict(source) # type: ignore

    normalized["ano"] = normalize_account_number(normalized.get("ano")) # type: ignore
    normalized["vid"] = normalize_account_number(normalized.get("vid")) # type: ignore
    normalized["eid"] = normalize_account_number(normalized.get("eid")) # type: ignore
    normalized["pano"] = normalize_account_number(normalized.get("pano")) # type: ignore

    base_amount = Decimal(str(normalized.get("base_amount") or 0)) # type: ignore
    cutting_amount = Decimal(str(normalized.get("cutting_amount") or 0)) # type: ignore
    interest_amount = Decimal(str(normalized.get("interest_amount") or 0)) # type: ignore
    total_amount = Decimal(str(normalized.get("total_amount") or 0)) # type: ignore

    normalized["base_amount"] = float(base_amount) # type: ignore
    normalized["cutting_amount"] = float(cutting_amount) # type: ignore
    normalized["interest_amount"] = float(interest_amount) # type: ignore

    if total_amount > 0:
        component_sum = base_amount + cutting_amount + interest_amount
        if component_sum > 0 and component_sum != total_amount:
            logger.warning(
                "Customer ano=%s total_amount=%s does not equal base+cutting+interest=%s",
                normalized.get("ano"), # type: ignore
                total_amount,
                component_sum,
            )

    loan_type = normalized.get("type") # type: ignore
    if loan_type == "weekly":
        normalized["type"] = "W" # type: ignore
    elif loan_type == "monthly":
        normalized["type"] = "M" # type: ignore

    normalized["paid_amount"] = float(normalized.get("paid_amount") or 0) # type: ignore
    if normalized.get("balance_amount") is None and total_amount > 0: # type: ignore
        normalized["balance_amount"] = float( # type: ignore
            total_amount - Decimal(str(normalized["paid_amount"])) # type: ignore
        )

    return normalized


def normalize_mobile_payment_payload(payload):
    """Normalize payment payload from mobile app to match DB column names."""
    if not isinstance(payload, dict):
        raise ValueError("Invalid payment payload")

    normalized = dict(payload)

    payment_type = (normalized.get("payment_type") or "cash").lower().strip()
    if payment_type not in ("cash", "upi", "partial"):
        payment_type = "cash"

    amt = Decimal(str(normalized.get("amt") or 0))

    cash_raw = normalized.get("cash_amount", normalized.get("cash_amt"))
    upi_raw = normalized.get("upi_amount", normalized.get("upi_amt"))

    if payment_type == "cash":
        cash_amount = amt
        upi_amount = Decimal("0")
    elif payment_type == "upi":
        cash_amount = Decimal("0")
        upi_amount = amt
    else:
        cash_amount = Decimal(str(cash_raw or 0))
        upi_amount = Decimal(str(upi_raw or 0))
        if cash_amount <= 0 or upi_amount <= 0:
            raise ValueError(
                "Partial payment requires cash_amount and upi_amount greater than zero"
            )
        amt = cash_amount + upi_amount

    if amt <= 0:
        raise ValueError("Payment amount must be greater than zero")

    payment_date_raw = normalized.get("payment_date") or normalized.get("pdate")
    if not payment_date_raw:
        raise ValueError("Payment date is required")

    payment_date = datetime.fromisoformat(str(payment_date_raw)[:10]).date()

    ano = normalize_account_number(normalized.get("ano"))
    vid = normalize_account_number(normalized.get("vid"))
    eid = normalize_account_number(normalized.get("eid"))
    if ano is None or vid is None or eid is None:
        raise ValueError("Payment requires ano, vid, and eid")

    normalized["ano"] = ano
    normalized["vid"] = vid
    normalized["eid"] = eid
    normalized["payment_type"] = payment_type
    normalized["amt"] = float(amt)
    normalized["cash_amount"] = float(cash_amount)
    normalized["upi_amount"] = float(upi_amount)
    normalized["payment_date"] = payment_date.isoformat()
    normalized.pop("pdate", None)
    normalized.pop("cash_amt", None)
    normalized.pop("upi_amt", None)

    return normalized
# ----------------------------------------------------
# FLASK APP SETUP
# ----------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")

# Fix: Running behind nginx reverse proxy — ProxyFix makes Flask correctly
# read X-Forwarded-Proto and X-Forwarded-For so HTTPS is detected properly.
# Without this, SESSION_COOKIE_SECURE cookies are silently dropped on
# any request that Flask thinks arrived over HTTP.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.after_request
def debug_session_writer(response):

    try:
        set_cookie = response.headers.getlist("Set-Cookie")

        for hdr in set_cookie:
            if "sivadurga_session" in hdr:
                logger.warning(
                    f"SESSION_COOKIE_WRITTEN "
                    f"path={request.path} "
                    f"status={response.status_code} "
                    f"cookie={hdr[:200]}"
                )
    except Exception:
        pass

    return response

@app.after_request
def debug_session_cookie(response):
    try:
        for hdr in response.headers.getlist("Set-Cookie"):
            if "sivadurga_session" in hdr:
                logger.warning(
                    f"SESSION_COOKIE_WRITE "
                    f"path={request.path} "
                    f"status={response.status_code}"
                )
    except Exception:
        pass

    return response

def sync_unlinked_customer_accounts(cur):
    """
    Finds newly created accounts in `customer` that are not yet in `customer_loan_link`,
    links repeat borrowers via (vid, pano) to their parent's UCID, and provisions new
    UCIDs in `customer_master` for brand-new borrowers.
    """
    # 1. Link repeat borrowers via pano match
    cur.execute("""
        WITH repeat_matches AS (
            SELECT DISTINCT ON (c.cid)
                parent.ucid,
                c.cid,
                c.vid,
                c.ano,
                c.pano,
                'active'::text AS record_tier,
                COALESCE(parent.cycle_number, 1) + 1 AS cycle_number,
                c.start_date,
                c.end_date,
                c.total_amount,
                c.paid_amount,
                c.balance_amount,
                c.status
            FROM customer c
            JOIN v_all_customers parent 
              ON c.vid = parent.vid 
             AND CAST(parent.ano AS TEXT) = TRIM(c.pano) 
             AND parent.ucid IS NOT NULL
            LEFT JOIN customer_loan_link cll ON c.cid = cll.cid
            WHERE cll.cid IS NULL AND c.pano IS NOT NULL AND TRIM(c.pano) != ''
            ORDER BY c.cid, parent.cycle_number DESC
        )
        INSERT INTO customer_loan_link (ucid, cid, vid, ano, pano, record_tier, cycle_number, start_date, end_date, total_amount, paid_amount, balance_amount, status, created_at)
        SELECT 
            rm.ucid, rm.cid, rm.vid, rm.ano, rm.pano, rm.record_tier, rm.cycle_number, rm.start_date, rm.end_date, rm.total_amount, rm.paid_amount, rm.balance_amount, rm.status, NOW()
        FROM repeat_matches rm
        ON CONFLICT (cid, record_tier) DO NOTHING;
    """)
    repeat_linked = cur.rowcount

    # 2. For remaining unlinked active accounts (new borrowers), create master entries and link as cycle 1
    cur.execute("""
        WITH unlinked_new AS (
            SELECT DISTINCT ON (c.vid, c.name)
                c.cid, c.name, c.vid, c.ano, c.pano, c.phone_number, c.aadhaar_number, c.start_date, c.end_date, c.total_amount, c.paid_amount, c.balance_amount, c.status
            FROM customer c
            LEFT JOIN customer_loan_link cll ON c.cid = cll.cid
            WHERE cll.cid IS NULL
            ORDER BY c.vid, c.name, c.ano ASC
        ),
        inserted_masters AS (
            INSERT INTO customer_master (
                primary_name, primary_vid, phone_number, aadhaar_number,
                total_loan_cycles, first_loan_date, latest_loan_date,
                lifetime_borrowed, lifetime_repaid, current_active_balance,
                customer_risk_tier, lifetime_credit_score, lifetime_on_time_ratio, total_cycles_completed
            )
            SELECT 
                un.name, un.vid, un.phone_number, un.aadhaar_number,
                1, un.start_date, un.start_date,
                un.total_amount, 0.0, un.balance_amount,
                'standard', 100.0, 100.0, 0
            FROM unlinked_new un
            RETURNING ucid, primary_vid, primary_name
        )
        INSERT INTO customer_loan_link (ucid, cid, vid, ano, pano, record_tier, cycle_number, start_date, end_date, total_amount, paid_amount, balance_amount, status, created_at)
        SELECT 
            im.ucid, un.cid, un.vid, un.ano, un.pano, 'active', 1, un.start_date, un.end_date, un.total_amount, un.paid_amount, un.balance_amount, un.status, NOW()
        FROM inserted_masters im
        JOIN unlinked_new un ON im.primary_vid = un.vid AND im.primary_name = un.name
        ON CONFLICT (cid, record_tier) DO NOTHING;
    """)
    new_linked = cur.rowcount

    return repeat_linked, new_linked


def execute_daily_rating_recalculation():
    logger.info("Scheduler task triggered: checking for advisory lock...")
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT pg_try_advisory_lock(55555)")
        lock_acquired = cur.fetchone()[0]
        
        if not lock_acquired:
            logger.info("Advisory lock not acquired. Another worker is already executing the daily recalculation.")
            return

        logger.info("Advisory lock acquired. Running daily rating recalculation for active customers...")

        # 0. Sync and link any newly added accounts to customer_master
        try:
            repeat_c, new_c = sync_unlinked_customer_accounts(cur)
            if repeat_c or new_c:
                logger.info(f"Auto-linked {repeat_c} repeat loans and {new_c} new borrowers.")
                conn.commit()
        except Exception as ex:
            logger.error(f"Failed to auto-link new accounts: {ex}")
            conn.rollback()
        
        cur.execute("""
            SELECT cid
            FROM customer
            WHERE balance_amount > 0
        """)
        cids = [row[0] for row in cur.fetchall()]
        
        logger.info(f"Found {len(cids)} active customers to evaluate.")
        for cid in cids:
            try:
                recalc_customer_repayment_score(cur, cid, force_recalc=True)
            except Exception as ex:
                logger.error(f"Failed to recalculate rating for customer cid={cid}: {ex}")
                
        conn.commit()
        logger.info("Daily rating recalculation completed successfully.")

        # Recalculate lifetime credit scores for all borrowers
        try:
            cur.execute("""
                WITH borrower_stats AS (
                    SELECT 
                        ucid,
                        COUNT(*) AS total_cycles,
                        COUNT(*) FILTER (WHERE balance_amount <= 0 OR status = 'closed') AS completed_cycles,
                        BOOL_OR(status IN ('defaulted', 'written_off') OR (balance_amount > 0 AND record_tier IN ('closed', 'historic'))) AS has_default,
                        ROUND(AVG(COALESCE(customer_rating, 100.0)), 1) AS on_time_ratio,
                        ROUND(
                            LEAST(100.0, GREATEST(0.0,
                                AVG(COALESCE(customer_rating, 100.0))
                                + LEAST(10.0, COUNT(*) FILTER (WHERE balance_amount <= 0 OR status = 'closed') * 2.0)
                                - CASE WHEN BOOL_OR(status IN ('defaulted', 'written_off') OR (balance_amount > 0 AND record_tier IN ('closed', 'historic'))) THEN 25.0 ELSE 0.0 END
                            )), 1
                        ) AS lifetime_score
                    FROM v_all_customers
                    WHERE ucid IS NOT NULL
                    GROUP BY ucid
                )
                UPDATE customer_master cm
                SET 
                    total_loan_cycles = bs.total_cycles,
                    total_cycles_completed = bs.completed_cycles,
                    lifetime_on_time_ratio = bs.on_time_ratio,
                    lifetime_credit_score = bs.lifetime_score,
                    customer_risk_tier = CASE 
                        WHEN bs.has_default THEN 'default_risk'
                        WHEN bs.lifetime_score >= 85.0 THEN 'low'
                        WHEN bs.lifetime_score >= 65.0 THEN 'standard'
                        WHEN bs.lifetime_score >= 45.0 THEN 'elevated'
                        ELSE 'high'
                    END,
                    updated_at = NOW()
                FROM borrower_stats bs
                WHERE cm.ucid = bs.ucid;
            """)
            conn.commit()
            logger.info("Daily lifetime credit score recalculation completed successfully.")
        except Exception as ex:
            conn.rollback()
            logger.error(f"Failed daily lifetime credit score recalculation: {ex}")

        # Warm up default dashboard cache for active villages (non-blocking, only if not cached)
        try:
            cur.execute("""
                SELECT DISTINCT vid
                FROM customer
                WHERE balance_amount > 0
            """)
            active_vids = [row[0] for row in cur.fetchall()]
            logger.info(f"Validating dashboard cache for {len(active_vids)} active villages...")
            for vid in active_vids:
                try:
                    with app.test_request_context(query_string={"view": "active", "sub_view": "active_only", "force_recalc": "false"}):
                        session["user_id"] = "scheduler"
                        session["level"] = "admin"
                        api_village_behavioral_analytics(vid)
                except Exception as ex:
                    logger.debug(f"Dashboard cache warming error vid={vid}: {ex}")
            logger.info("Daily active village dashboard cache check completed.")
        except Exception as cache_ex:
            logger.error(f"Error checking active village dashboard cache: {cache_ex}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in daily scheduler run: {e}")
    finally:
        try:
            cur.execute("SELECT pg_advisory_unlock(55555)")
            conn.commit()
        except Exception as unlock_err:
            logger.warning(f"Error releasing advisory lock: {unlock_err}")
        cur.close()
        conn.close()

def init_scheduler():
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        KOLKATA = pytz.timezone('Asia/Kolkata')
        scheduler = BackgroundScheduler(timezone=KOLKATA)
        scheduler.add_job(execute_daily_rating_recalculation, 'cron', hour=5, minute=0)
        scheduler.start()
        logger.info("APScheduler initialized for 5:00 AM IST daily recalculations.")

init_scheduler()

secret_key = os.environ.get("SECRET_KEY")

if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set")

app.secret_key = secret_key

mobile_queue_hmac_secret = get_mobile_queue_hmac_secret()

app.config["WTF_CSRF_ENABLED"] = True
# Disable CSRF token time expiry — the default 3600s (1 hour) was causing
# sudden logouts when employees kept a page open for over an hour and then
# refreshed or navigated. The session cookie itself provides auth security.
app.config["WTF_CSRF_TIME_LIMIT"] = None
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
# SESSION_REFRESH_EACH_REQUEST = False is critical.
# With 8 gunicorn workers × 4 threads = 32 concurrent handlers, setting this
# to True means EVERY response (including 302 redirects with empty sessions from
# login_required) writes a Set-Cookie. A stale/empty cookie from a slow or failed
# concurrent request then overwrites the browser's valid session → sudden logout.
# With False, Flask only writes Set-Cookie when the session data actually changed.
app.config["SESSION_REFRESH_EACH_REQUEST"] = False
# Secure session cookie settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Always enforce Secure cookie — the site is always served over HTTPS at
# sivadurga.in. ProxyFix above ensures Flask sees the correct protocol.
# Set DISABLE_SECURE_COOKIE=1 only for local http:// development.
is_local_run = (__name__ == "__main__")
app.config["SESSION_COOKIE_SECURE"] = (os.environ.get("DISABLE_SECURE_COOKIE") != "1") and not is_local_run
app.config["SESSION_COOKIE_NAME"] = "sivadurga_session"
app.config["SESSION_COOKIE_DOMAIN"] = None

csrf = CSRFProtect(app)
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ChitBase Blueprint Registration
from chit_controller import chit_bp
app.register_blueprint(chit_bp)

# Custom mobile rate limit key function
def mobile_rate_limit_key():
    token = request.headers.get("X-Mobile-Token")

    if token:
        data = verify_mobile_token(token)

        if data:
            eid = data.get("eid")
            user_id = data.get("user_id")

            if eid:
                return f"mobile-eid:{eid}"

            if user_id:
                return f"mobile-user:{user_id}"

    return get_remote_address()


limiter = Limiter(
    key_func=mobile_rate_limit_key,
    app=app
)


def ensure_customer_docs_feed_table():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_docs_feed (
                docs_feed_id BIGSERIAL PRIMARY KEY,
                local_uuid TEXT UNIQUE,
                device_id TEXT,
                eid INTEGER,
                vid INTEGER NOT NULL,
                ano INTEGER NOT NULL,
                cid INTEGER,
                aadhaar_front_pic BYTEA,
                aadhaar_back_pic BYTEA,
                house_photo BYTEA,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_docs_feed_vid_status
            ON customer_docs_feed (vid, status)
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def ensure_device_wipe_audit_table():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS device_wipe_audit (
                id SERIAL PRIMARY KEY,
                user_id INT,
                device_id TEXT NOT NULL,
                triggered_at TIMESTAMPTZ DEFAULT NOW(),
                reason TEXT,
                ip_address TEXT
            )
        """)
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def ensure_account_closure_feed_table():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS account_closure_feed (
                feed_id BIGSERIAL PRIMARY KEY,
                local_uuid TEXT UNIQUE,
                device_id TEXT,
                eid INTEGER,
                vid INTEGER NOT NULL,
                ano INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_account_closure_feed_vid_status
            ON account_closure_feed (vid, status)
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()


try:
    ensure_customer_docs_feed_table()
    ensure_device_wipe_audit_table()
    ensure_account_closure_feed_table()
except Exception as exc:
    logger.warning("Could not ensure startup tables: %s", exc)


# Set security headers after each request
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # HSTS only when running over HTTPS
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Prevent caching of dynamic resources (HTML and API responses)
    # to avoid stale session/village context on navigation, unless a custom Cache-Control is set.
    if response.mimetype in ["text/html", "application/json"]:
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    return response



# ----------------------------------------------------
# Session timeout and activity tracking
@app.before_request
def redirect_www_and_force_https():
    # Skip for static assets
    if request.path.startswith("/static/"):
        return

    # Force HTTPS in production to prevent Secure cookies from being blocked/discarded
    is_https = request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"
    if not is_https and os.environ.get("DISABLE_SECURE_COOKIE") != "1" and not is_local_run:
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)

    host = request.headers.get("Host", "")
    if host.startswith("www."):
        new_host = host[4:]
        scheme = "https" if is_https else "http"
        return redirect(f"{scheme}://{new_host}{request.full_path}", code=301)

# Auto-recover village context fields if missing (runs on every request for logged-in users)
@app.before_request
def restore_village_context():
    if request.path.startswith("/static/"):
        return
    if "user_id" not in session:
        return
    if "vid" in session and ("village_code" not in session or "village_name" not in session):
        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("SELECT village_code, village_name FROM village WHERE vid = %s", (session["vid"],))
            row = cur.fetchone()
            if row:
                session["village_code"] = row[0]
                session["village_name"] = row[1]
            cur.close()
            conn.close()
        except Exception:
            pass


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)
# ----------------------------------------------------
# Decorators
# ----------------------------------------------------
def is_ajax_request():
    # If Sec-Fetch-Mode is present, verify if it is not a document navigation
    fetch_mode = request.headers.get("Sec-Fetch-Mode")
    if fetch_mode:
        return fetch_mode != "navigate"

    # Fallback for older browsers, custom API clients, and crawlers
    return (
        request.path.startswith("/api/")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
        or "application/json" in request.headers.get("Accept", "")
    )

@app.errorhandler(CSRFError)
def csrf_error_response(e):
    reason = getattr(e, 'description', str(e))
    if is_ajax_request() or request.path.startswith("/chit/api/"):
        return jsonify(success=False, error=f"CSRF token missing or invalid: {reason}", csrf_error=True), 400
    return f"CSRF validation failed: {reason}", 400

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            # --- SESSION DIAGNOSTIC LOG ---
            try:
                import datetime as _dt
                _ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _ip = request.headers.get("X-Forwarded-For", request.remote_addr)
                _ua = request.headers.get("User-Agent", "unknown")
                _url = request.url
                _method = request.method
                _cookie_hdr = request.headers.get("Cookie", "")
                _has_session_cookie = "sivadurga_session" in _cookie_hdr
                _session_keys = list(session.keys())
                _log_line = (
                    f"[{_ts}] UNEXPECTED_LOGOUT "
                    f"ip={_ip} method={_method} url={_url} "
                    f"cookie_present={_has_session_cookie} "
                    f"session_keys={_session_keys} "
                    f"ua={_ua}\n"
                )
                log_path = "/tmp/sd_session_debug.log"
                with open(log_path, "a") as _lf:
                    _lf.write(_log_line)
                logger.warning(_log_line.strip())
            except Exception:
                pass
            # --- END DIAGNOSTIC LOG ---
            # IMPORTANT: Mark session as unmodified so Flask does NOT send a
            # Set-Cookie header in this redirect response.
            session.modified = False

            # API / AJAX / Fetch requests should receive 401 Unauthorized instead of a 302
            # redirect to /login. This prevents the browser fetch engine from fetching
            # /login in the background and generating a sparse session cookie that
            # overwrites the user's valid session cookie.
            if is_ajax_request():
                return jsonify(success=False, error="Session expired. Please login again.", session_expired=True), 401

            return redirect("/login")

        user_level = session.get("level")
        if user_level in ("j", "m", "s"):
            allowed_paths = ("/app/portal", "/app/download-action", "/logout")
            if request.path not in allowed_paths:
                if session.get("download_authorized") == True:
                    return redirect("/app/portal")
                else:
                    session.clear()
                    flash("Access denied.")
                    return redirect("/login")

        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        level = session.get("level")

        if not user_id:
            session.modified = False
            if is_ajax_request():
                return jsonify(success=False, error="Session expired. Please login again.", session_expired=True), 401
            flash("Please login", "danger")
            return redirect(url_for("login"))

        # Only admin and mgmt allowed
        if level not in ["admin", "mgmt"]:
            if is_ajax_request():
                return jsonify(success=False, error="Access denied."), 403
            flash("Access denied", "danger")
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)
    return wrapper


class TTLMemoryCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                val, expires_at = self._cache[key]
                if pytime.time() < expires_at:
                    return val
                else:
                    del self._cache[key]
            return None

    def set(self, key, val, ttl_seconds):
        with self._lock:
            self._cache[key] = (val, pytime.time() + ttl_seconds)

    def clear(self):
        with self._lock:
            self._cache.clear()

global_ttl_cache = TTLMemoryCache()

def ttl_cache(ttl_seconds=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                body_data = request.get_json(silent=True)
                if body_data:
                    body_key = json.dumps(body_data, sort_keys=True)
                else:
                    body_key = ""
            except Exception:
                body_key = ""

            query_key = tuple(sorted(request.args.items()))
            session_vid = session.get("vid")
            session_uid = session.get("user_id")
            
            cache_key = (
                f.__name__,
                args,
                tuple(sorted(kwargs.items())),
                query_key,
                body_key,
                session_vid,
                session_uid
            )

            cached_val = global_ttl_cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            response = f(*args, **kwargs)

            is_cacheable = True
            if isinstance(response, tuple):
                if len(response) > 1 and isinstance(response[1], int) and response[1] != 200:
                    is_cacheable = False
            
            if is_cacheable:
                global_ttl_cache.set(cache_key, response, ttl_seconds)

            return response
        return wrapper
    return decorator


# ----------------------------------------------------
# CONTEXT SELECTION APIs (Postgres) - top bar dropdowns
# ----------------------------------------------------



@app.route("/api/employees")
@login_required
def api_employees():

    conn = get_pg_connection()
    cur = conn.cursor()

    user_level = session.get("level")
    allowed_villages = session.get("villages", [])

    try:
        # Admin & mgmt → full access
        if user_level in ["admin", "mgmt"]:
            cur.execute("""
                SELECT eid, name
                FROM employee
                WHERE is_active = TRUE
                ORDER BY name
            """)

        # s / m / j → only employees linked to their villages
        else:
            if not allowed_villages:
                return jsonify([])

            cur.execute("""
                SELECT DISTINCT e.eid, e.name
                FROM village v
                JOIN employee e
                  ON e.eid = v.emp1 OR e.eid = v.emp2
                WHERE v.vid = ANY(%s)
                  AND v.status = 'active'
                  AND e.is_active = TRUE
                ORDER BY e.name
            """, (allowed_villages,))

        rows = cur.fetchall()

        return jsonify([
            {"eid": r[0], "name": r[1]}
            for r in rows
        ])

    finally:
        cur.close()
        conn.close()
@app.route("/api/employee/toggle_status", methods=["POST"])
@login_required
@admin_required
def toggle_employee_status():
    data = request.get_json()
    eid = data.get("eid")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # prevent deactivate if assigned to village
        cur.execute("""
            SELECT 1 FROM village
            WHERE emp1 = %s OR emp2 = %s
            LIMIT 1
        """, (eid, eid))

        assigned = cur.fetchone()

        cur.execute("""
            SELECT is_active FROM employee WHERE eid = %s
        """, (eid,))
        current = cur.fetchone()

        if not current:
            return jsonify(success=False, error="Employee not found")

        is_active = current[0]

        if is_active and assigned:
            return jsonify(success=False, error="Employee assigned to village")

        cur.execute("""
            UPDATE employee
            SET is_active = NOT is_active
            WHERE eid = %s
            RETURNING is_active
        """, (eid,))

        new_status = cur.fetchone()[0] # type: ignore

        conn.commit()

        audit_log(
            action="toggle_employee_status",
            entity_type="employee",
            entity_id=eid,
            details={
                "new_status": "active" if new_status else "inactive"
            }
        )

        return jsonify(success=True, status="active" if new_status else "inactive")

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e))

    finally:
        cur.close()
        conn.close()


@app.route("/api/villages")
@login_required
def api_villages():
    eid = request.args.get("eid")
    if not eid or eid == "undefined":
        eid = None
    user_level = session.get("level")
    user_villages = session.get("villages", [])

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Admin & mgmt → full access
        if user_level in ["admin", "mgmt"]:
            if eid:
                cur.execute("""
                    SELECT vid, village_code, village_name
                    FROM village
                    WHERE (emp1 = %s OR emp2 = %s)
                      AND status = 'active'
                    ORDER BY village_name
                """, (eid, eid))
            else:
                cur.execute("""
                    SELECT vid, village_code, village_name
                    FROM village WHERE status = 'active'
                    ORDER BY village_name
                """)

        # s / m / j → only assigned villages
        else:
            if not user_villages:
                return jsonify([])
 
            cur.execute("""
                SELECT vid, village_code, village_name
                FROM village
                WHERE vid = ANY(%s)
                  AND status = 'active'
                ORDER BY village_name
            """, (user_villages,))

        rows = cur.fetchall()

        return jsonify([
            {"vid": r[0], "code": r[1], "name": r[2], "display_name": f"{r[1]} - {r[2]}"}
            for r in rows
        ])
    finally:
        cur.close()
        conn.close()

@app.route("/api/village/employees")
@login_required
def api_village_employees():
    vid = request.args.get("vid")
    if not vid:
        return jsonify([])

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT e.eid, e.name
        FROM village v
        JOIN employee e ON e.eid = v.emp1 OR e.eid = v.emp2
        WHERE v.vid = %s
          AND e.is_active = TRUE
        ORDER BY e.name
    """, (vid,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"eid": r[0], "name": r[1]}
        for r in rows
    ])

@app.route("/api/employee_level")
@login_required
@admin_required
def api_employee_level():
    eid = request.args.get("eid")

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("SELECT level FROM employee WHERE eid = %s", (eid,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return jsonify({"level": row[0] if row else ""})

@app.route("/api/villages_by_employee")
@login_required
@admin_required
def api_villages_by_employee():
    eid = request.args.get("eid")

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.vid, v.village_name
        FROM village v
        JOIN employee e ON e.eid = %s
        WHERE (v.emp1 = %s OR v.emp2 = %s)
          AND v.status = 'active'
          AND e.is_active = TRUE
        ORDER BY v.village_name
    """, (eid, eid, eid))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {"vid": r[0], "name": r[1]}
        for r in rows
    ])
# ------------------------------
# GET CONTEXT API (missing)
# ------------------------------
@app.route("/get_context")
@login_required
def get_context():
    return jsonify({
        "vid": session.get("vid"),
        "eid": session.get("eid"),
        "eid2": session.get("eid2"),
        "village_name": session.get("village_name"),
        "village_code": session.get("village_code"),
        "employee_name": session.get("employee_name"),
        "employee_name2": session.get("employee_name2"),
        "username": session.get("username")
    })


@app.route("/set_context", methods=["POST"])
@login_required
def set_context():
    data = request.get_json()
    vid = int(data.get("vid"))
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])

    if user_level not in ["admin", "mgmt"]:
        if vid not in allowed_villages:
           return jsonify(success=False, error="Unauthorized village"), 403

    conn = get_pg_connection()
    cur = conn.cursor()

    # fetch eid + village_name together
    cur.execute("""
        SELECT v.emp1, v.emp2, v.village_name, v.village_code, e1.name, e2.name
        FROM village v
        LEFT JOIN employee e1 ON e1.eid = v.emp1
        LEFT JOIN employee e2 ON e2.eid = v.emp2
        WHERE v.vid = %s
          AND v.status = 'active'
    """, (vid,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify(success=False, error="Inactive or invalid village"), 400

    eid1 = row[0]
    eid2 = row[1]
    village_name = row[2]
    village_code = row[3]
    employee_name1 = row[4] or "Unknown"
    employee_name2 = row[5]

    # store session
    session["vid"] = vid
    session["eid"] = eid1
    session["village_name"] = village_name
    session["village_code"] = village_code
    session["employee_name"] = employee_name1
    if eid2 and employee_name2:
        session["eid2"] = eid2
        session["employee_name2"] = employee_name2
    else:
        session.pop("eid2", None)
        session.pop("employee_name2", None)
    
    cur.close()
    conn.close()
    return jsonify(success=True)

@app.route("/reset_context", methods=["POST"])
@login_required
def reset_context():
    session.pop("eid", None)
    session.pop("eid2", None)
    session.pop("vid", None)
    session.pop("village_name", None)
    session.pop("village_code", None)
    session.pop("employee_name", None)
    session.pop("employee_name2", None)
    return jsonify(success=True)

@app.route("/api/employee/check")
@login_required
def check_employee():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify(found=False)

    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT eid FROM employee WHERE LOWER(name)=LOWER(%s)", (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify(found=bool(row))

# ------------------ New API: Get next available Employee ID ------------------
@app.route("/api/employee/next_eid")
@login_required
def api_next_employee_eid():
    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT COALESCE(MAX(eid), 0) + 1 FROM employee")
        result = cur.fetchone()
        next_eid = result[0] if result else 1

        return jsonify({"next_eid": next_eid})

    finally:
        cur.close()
        conn.close()

STATE_CODE_MAP = {
    "ANDHRA PRADESH": 11,
    "TELANGANA": 12,
    "KARNATAKA": 13,
    "MAHARASHTRA": 14,
    "ODISHA": 15,
    "GUJARAT": 16,
}

@app.route("/api/create_village", methods=["POST"])
@login_required
@admin_required
def api_create_village():
    data = request.json
    
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON or empty request body"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()

        # -------------------------
    # DUPLICATE CHECK
    # -------------------------
    village_code = (data.get("village_code") or "").strip().upper()
    village_name = (data.get("village_name") or "").strip().upper()

    cur.execute("""
        SELECT village_code, village_name
        FROM village
        WHERE
            LOWER(village_code) = LOWER(%s)
            OR LOWER(village_name) = LOWER(%s)
        LIMIT 1
    """, (
        village_code,
        village_name
    ))

    existing = cur.fetchone()

    if existing:
        existing_code, existing_name = existing

        # Same code + same name
        if (
            existing_code
            and existing_name
            and existing_code.strip().lower() == village_code.lower()
            and existing_name.strip().lower() == village_name.lower()
        ):
            cur.close()
            conn.close()

            return jsonify({
                "success": False,
                "error": "Village already exists with same code and village name"
            })

        # Same village code
        if (
            existing_code
            and existing_code.strip().lower() == village_code.lower()
        ):
            cur.close()
            conn.close()

            return jsonify({
                "success": False,
                "error": f"Village code '{village_code}' already exists"
            })

        # Same village name
        if (
            existing_name
            and existing_name.strip().lower() == village_name.lower()
        ):
            cur.close()
            conn.close()

            return jsonify({
                "success": False,
                "error": f"Village name '{village_name}' already exists"
            })

    # -------------------------
    # STATE-BASED VID GENERATION
    # -------------------------
    state = (data.get("state") or "").strip().upper()

    if state not in STATE_CODE_MAP:
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "error": "Invalid state selected"
        }), 400

    state_code = STATE_CODE_MAP[state]  # e.g. 13 for KARNATAKA

    vid_start = state_code * 10000
    vid_end = (state_code + 1) * 10000 - 1

    cur.execute("""
        SELECT COALESCE(MAX(vid), %s - 1)
        FROM village
        WHERE vid BETWEEN %s AND %s
    """, (vid_start, vid_start, vid_end))

    result = cur.fetchone()
    last_vid = result[0] if result else vid_start - 1
    vid = last_vid + 1

    # -------------------------
    # INSERT
    # -------------------------
    cur.execute("""
        INSERT INTO village (
            vid, village_code, village_name,
            district, pincode, state,
            emp1, emp2,
            interest_rate, cutting_rate,
            latitude, longitude,
            created_at, source_file, status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NULL,'active')
    """, (
        vid,
        data["village_code"],
        data["village_name"],
        data["district"],
        data["pincode"],
        state,
        data["emp1_eid"],
        data.get("emp2_eid"),
        float(data.get("interest_rate") or 0.0),
        float(data.get("cutting_rate") or 0.0),
        float(data["latitude"]) if data.get("latitude") is not None and str(data.get("latitude")).strip() != "" else None,
        float(data["longitude"]) if data.get("longitude") is not None and str(data.get("longitude")).strip() != "" else None
    ))

    conn.commit()
    audit_log(
        action="create_village",
        entity_type="village",
        entity_id=vid,
        details={
            "village_name": data["village_name"],
            "village_code": data["village_code"],
            "emp1": data["emp1_eid"],
            "emp2": data.get("emp2_eid"),
            "state": state
        }
    )
    cur.close()
    conn.close()

    return jsonify({"success": True, "vid": vid})

@app.route("/api/create_employee", methods=["POST"])
@login_required
def api_create_employee():
    data = request.get_json()

    name = data.get("name", "").strip()
    if not name:
        return jsonify(success=False, error="Employee name is required")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # 1ï¸âƒ£ Get next EID
        cur.execute("SELECT COALESCE(MAX(eid), 0) + 1 FROM employee")
        result = cur.fetchone()
        if not result:
            return jsonify(success=False, error="Failed to generate EID"), 500
        new_eid = result[0]

        phone_number = (data.get("phone_number") or "").strip()

        # ðŸ”’ Prevent duplicate employee name + phone combinations
        cur.execute(
            """
            SELECT name, phone_number
            FROM employee
            WHERE LOWER(name) = LOWER(%s)
               OR phone_number = %s
            LIMIT 1
            """,
            (name, phone_number)
        )

        existing_employee = cur.fetchone()

        if existing_employee:
            existing_name, existing_phone = existing_employee

            # Same name + same phone
            if (
                existing_name
                and existing_phone
                and existing_name.strip().lower() == name.lower()
                and str(existing_phone).strip() == phone_number
            ):
                return jsonify(
                    success=False,
                    error="Employee already exists with same name and mobile number"
                )

            # Same employee name
            if (
                existing_name
                and existing_name.strip().lower() == name.lower()
            ):
                return jsonify(
                    success=False,
                    error=f"Employee name '{name}' already exists"
                )

            # Same phone number
            if (
                existing_phone
                and str(existing_phone).strip() == phone_number
            ):
                return jsonify(
                    success=False,
                    error=f"Mobile number '{phone_number}' is already assigned to another employee"
                )

        cur.execute("""
            INSERT INTO employee (eid, name, phone_number, city, joining_date, level, state, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING eid
        """, (
            new_eid,
            name,
            phone_number,
            data.get("city"),
            data.get("joining_date"),
            data.get("level").strip().lower() if data.get("level") else None,
            data.get("state")
        ))

        result = cur.fetchone()
        if not result:
            return jsonify(success=False, error="Failed to create employee"), 500
        
        conn.commit()
        audit_log(
            action="create_employee",
            entity_type="employee",
            entity_id=new_eid,
            details={
                "name": name,
                "level": data.get("level"),
                "state": data.get("state")
            }
        )

        return jsonify(success=True, eid=new_eid, name=name)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@app.route("/api/village/check")
@login_required
def api_check_village():
    code = request.args.get("code")
    name = request.args.get("name")
    emp1 = request.args.get("emp1")
    vid = request.args.get("vid")

    conn = get_pg_connection()
    cur = conn.cursor()

    if vid:
        cur.execute("""
            SELECT 1
            FROM village
            WHERE (
                LOWER(village_code) = LOWER(%s)
                OR LOWER(village_name) = LOWER(%s)
            )
              AND vid != %s
            LIMIT 1
        """, (code, name, vid))
    else:
        cur.execute("""
            SELECT 1
            FROM village
            WHERE (
                LOWER(village_code) = LOWER(%s)
                OR LOWER(village_name) = LOWER(%s)
            )
            LIMIT 1
        """, (code, name))

    exists = cur.fetchone() is not None
    cur.close()

    return jsonify({"exists": exists})
# ----------------------------------------------------
# HELPER FUNCTIONS - postgre
# ----------------------------------------------------


@app.route("/check_parent_link")
@login_required
def check_parent_link():

    pano = request.args.get("pano", "").strip()
    vid = session.get("vid")

    if not pano or not vid:
        return jsonify({
            "found": False,
            "accounts": []
        })

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT ano
            FROM customer
            WHERE pano = %s
              AND vid = %s
            ORDER BY ano
        """, (pano, vid))

        rows = cur.fetchall()

        accounts = [str(r[0]) for r in rows]

        return jsonify({
            "found": len(accounts) > 0,
            "accounts": accounts
        })

    except Exception as e:
        return jsonify({
            "found": False,
            "accounts": [],
            "error": str(e)
        })

    finally:
        cur.close()
        conn.close()


@app.route("/get_parent_details")
@login_required
def get_parent_details():
    pano = request.args.get("pano", "").strip()
    vid = session.get("vid")

    if not pano or not vid:
        return jsonify({"found": False, "error": "Missing pano or village context"})

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        ano_int = int(pano) if pano.isdigit() else None
        if ano_int is not None:
            cur.execute("""
                SELECT name, phone_number, aadhaar_number, latitude, longitude, status, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND ano = %s
                ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
                LIMIT 1
            """, (vid, ano_int))
        else:
            cur.execute("""
                SELECT name, phone_number, aadhaar_number, latitude, longitude, status, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND CAST(ano AS TEXT) = %s
                ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
                LIMIT 1
            """, (vid, pano))

        row = cur.fetchone()
        if not row:
            return jsonify({"found": False})

        return jsonify({
            "found": True,
            "name": row[0] or "",
            "phone_number": row[1] or "",
            "aadhaar_number": row[2] or "",
            "latitude": float(row[3]) if row[3] is not None else "",
            "longitude": float(row[4]) if row[4] is not None else "",
            "ucid": row[6] if len(row) > 6 and row[6] is not None else None,
            "cycle_number": row[7] if len(row) > 7 and row[7] is not None else 1
        })
    except Exception as e:
        logger.error(f"Error in get_parent_details: {e}")
        return jsonify({"found": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


def get_highest_ano_by_vid(vid):
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(MAX(CAST(ano AS INTEGER)), 0)
        FROM customer
        WHERE vid = %s
    """, (vid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 0

def ano_exists(ano, vid):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM customer
                WHERE ano = %s AND vid = %s
                LIMIT 1
            """, (ano, vid))
            return cur.fetchone() is not None

def is_village_monthly(vid, cur=None):
    """
    Check if a village operates on a monthly installment schedule ('M').
    Criteria:
      1. Village name or village code ends with '-M' or contains '-M'.
      2. OR majority of active customers in the village are type 'M'.
    """
    if not vid:
        return False
    
    close_cur = False
    conn = None
    if cur is None:
        conn = get_pg_connection()
        cur = conn.cursor()
        close_cur = True
        
    try:
        cur.execute("SELECT village_name, village_code FROM village WHERE vid = %s", (vid,))
        row = cur.fetchone()
        if not row:
            return False
        v_name, v_code = (row[0] or "").upper(), (row[1] or "").upper()
        if "-M" in v_name or "-M" in v_code:
            return True
            
        cur.execute("""
            SELECT COUNT(*) FILTER (WHERE type = 'M'), COUNT(*)
            FROM customer
            WHERE vid = %s
        """, (vid,))
        c_row = cur.fetchone()
        if c_row and c_row[1] and c_row[1] > 0:
            if (c_row[0] / c_row[1]) >= 0.5:
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error checking if village {vid} is monthly: {e}")
        return False
    finally:
        if close_cur and cur is not None:
            cur.close()
            if conn is not None:
                conn.close()

def insert_customer(data):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO customer (
                    ano, name, pano, vid, eid,
                    start_date, end_date,
                    total_amount, base_amount, cutting_amount, interest_amount,
                    paid_amount, balance_amount, installment_amount,
                    type, period,
                    aadhaar_number, notes,
                    latitude, longitude,phone_number,
                    status
                )
                VALUES (
                    %(ano)s, %(name)s, %(pano)s, %(vid)s, %(eid)s,
                    %(start_date)s, %(end_date)s,
                    %(total_amount)s, %(base_amount)s, %(cutting_amount)s, %(interest_amount)s,
                    %(paid_amount)s, %(balance_amount)s, %(installment_amount)s,
                    %(type)s, %(period)s,
                    %(aadhaar_number)s, %(notes)s,
                    %(latitude)s, %(longitude)s, %(phone_number)s,
                    'open'
                )
                RETURNING cid
            """, data)

            result = cur.fetchone()
            if result is None:
                conn.close()
                return None
            cid = result[0]
            recalc_customer_repayment_score(cur, cid, force_recalc=True)
            # Invalidate cache for this village
            invalidate_village_health_cache(cur, data["vid"], data["start_date"])
            conn.commit()
            return cid


def customer_exists_by_ano_and_vid(ano, vid):
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM customer
        WHERE ano = %s AND vid = %s
        LIMIT 1
    """, (ano, vid))

    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def calculate_customer_rating_details(start_date, end_date, installment_amount, period, payments, balance_amount, loan_type="W", today=None):
    KOLKATA = pytz.timezone('Asia/Kolkata')
    
    if not today:
        today = datetime.now(KOLKATA).date()
        
    start_date = parse_date_input(start_date)
    end_date = parse_date_input(end_date)
    today = parse_date_input(today)

    if not start_date or not end_date or not installment_amount or not period or installment_amount <= 0 or period <= 0:
        return 100.0, "Excellent", 0.0, []

    # Filter out future-dated payments
    valid_payments = []
    for p in payments:
        p_date = p.get("payment_date")
        if not p_date:
            continue
        p_date = parse_date_input(p_date)
        
        if p_date <= today: # type: ignore
            valid_payments.append({
                "amt": Decimal(str(p.get("amt", 0))),
                "payment_date": p_date
            })

    # Day aggregation: multiple payments on the same calendar day for the same customer will be aggregated into a single amount.
    aggregated_payments = {}
    for p in valid_payments:
        d = p["payment_date"]
        aggregated_payments[d] = aggregated_payments.get(d, Decimal("0")) + p["amt"]
        
    # Generate rolling sequential due windows, expanding beyond period if customer is overdue
    max_eval_date = end_date
    if today > max_eval_date: # type: ignore
        max_eval_date = today
    for p in valid_payments:
        if p["payment_date"] > max_eval_date:
            max_eval_date = p["payment_date"]

    if loan_type == "M":
        total_periods_cap = int(period) + 36
    elif loan_type == "D":
        total_periods_cap = int(period) + 1095
    else:
        total_periods_cap = int(period) + 156

    due_dates = []
    w = 1
    while True:
        if loan_type == "M":
            due = start_date + relativedelta(months=w) + timedelta(days=1)
        elif loan_type == "D":
            due = start_date + timedelta(days=w)
        else:
            due = start_date + timedelta(days=7 * w + 1)
        due_dates.append(due)
        if w >= int(period):
            if due >= max_eval_date or w >= total_periods_cap: # type: ignore
                break
        w += 1
    total_weeks = len(due_dates)

    # Determine how many weeks to evaluate
    num_weeks_to_evaluate = 0
    for w in range(1, total_weeks + 1):
        window_start = start_date if w == 1 else due_dates[w-2] + timedelta(days=1)
        if window_start <= today: # type: ignore
            num_weeks_to_evaluate = w
        else:
            break

    # Sum of valid payments
    total_paid = sum(p["amt"] for p in valid_payments)
    rem_balance = Decimal(str(balance_amount or 0)) + total_paid
    inst_amt = Decimal(str(installment_amount))

    # Allocation state
    payments_by_week = {}
    for w in range(1, num_weeks_to_evaluate + 1):
        window_start = start_date if w == 1 else due_dates[w-2] + timedelta(days=1)
        window_end = due_dates[w-1]
        
        week_p_sum = Decimal("0")
        for p_date, p_amt in list(aggregated_payments.items()):
            if window_start <= p_date <= window_end:
                week_p_sum += p_amt
                
        payments_by_week[w] = week_p_sum

    # Allocation algorithm
    virtual_paid = {w: Decimal("0") for w in range(1, num_weeks_to_evaluate + 1)}
    initial_status = {}
    
    carry_forward = Decimal("0")
    
    for w in range(1, num_weeks_to_evaluate + 1):
        current_inst = inst_amt if w <= int(period) else Decimal("0")
        available = payments_by_week.get(w, Decimal("0")) + carry_forward
        
        if current_inst > 0:
            if available >= current_inst:
                initial_status[w] = "SUCCESS"
                allocated = current_inst
                excess = available - current_inst
                virtual_paid[w] = allocated
                
                # 1. Repair oldest MISSED first
                if excess > 0:
                    for j in range(1, w):
                        if j <= int(period) and virtual_paid[j] == 0:
                            needed = inst_amt
                            if excess >= needed:
                                virtual_paid[j] = inst_amt
                                excess -= needed
                            else:
                                virtual_paid[j] = excess
                                excess = Decimal("0")
                                break
                                
                # 2. Repair oldest PARTIAL second
                if excess > 0:
                    for j in range(1, w):
                        if j <= int(period) and 0 < virtual_paid[j] < inst_amt:
                            needed = inst_amt - virtual_paid[j]
                            if excess >= needed:
                                virtual_paid[j] = inst_amt
                                excess -= needed
                            else:
                                virtual_paid[j] += excess
                                excess = Decimal("0")
                                break
                                
                carry_forward = excess
            else:
                if available > 0:
                    initial_status[w] = "PARTIAL"
                else:
                    initial_status[w] = "MISSED"
                virtual_paid[w] = available
                carry_forward = Decimal("0")
        else:
            # Week is beyond the original period (overdue window).
            # These payments are just late regular installments, NOT surplus.
            # They must NOT repair earlier missed/partial weeks.
            initial_status[w] = "OVERDUE"
            virtual_paid[w] = available
            carry_forward = Decimal("0")

    # Score calculation loop
    score = 100.0
    consecutive_success = 0
    week_details = []
    total_excess_payments = Decimal("0")
    
    for w in range(1, num_weeks_to_evaluate + 1):
        if rem_balance <= 0:
            break
            
        p_actual = payments_by_week.get(w, Decimal("0"))
        rem_balance -= p_actual
        due_dt = due_dates[w-1]
        
        window_start = start_date if w == 1 else due_dates[w-2] + timedelta(days=1)
        window_end = due_dates[w-1]
        
        # Calculate excess payments throughout lifecycle (using base inst_amt)
        if p_actual > inst_amt:
            total_excess_payments += (p_actual - inst_amt)
        
        # Find all actual payments in this window
        week_payment_dates = []
        for p_date in sorted(aggregated_payments.keys()):
            if window_start <= p_date <= window_end:
                week_payment_dates.append(p_date.isoformat())
        
        paid_date_val = ", ".join(week_payment_dates) if week_payment_dates else None
        
        if w <= int(period):
            init_stat = initial_status[w]
            v_paid = virtual_paid[w]
            is_current_due_window = (due_dt >= today)
            
            if is_current_due_window:
                if v_paid >= inst_amt:
                    consecutive_success += 1
                    if consecutive_success > 1:
                        score = min(100.0, score + 3.0)
                    penalty = 0.0
                    display_status = "SUCCESS"
                else:
                    consecutive_success = 0
                    penalty = 0.0
                    display_status = "PENDING"
            else:
                if init_stat == "SUCCESS":
                    consecutive_success += 1
                    if consecutive_success > 1:
                        score = min(100.0, score + 3.0)
                    penalty = 0.0
                    display_status = "SUCCESS"
                elif v_paid >= inst_amt:
                    consecutive_success = 0
                    score = max(0.0, score - 3.0)
                    penalty = 3.0
                    display_status = init_stat
                else:
                    consecutive_success = 0
                    unpaid_percentage = float((inst_amt - v_paid) / inst_amt)
                    penalty = unpaid_percentage * 10.0
                    score = max(0.0, score - penalty)
                    display_status = init_stat
            
            allocated_val = float(v_paid)
        else:
            # Overdue weeks beyond period - display only, no repair
            display_status = "OVERDUE"
            
            # Apply overdue penalty period-by-period
            # Only apply if payment is NOT made (p_actual == 0) and past the grace period
            penalty = 0.0
            if p_actual == 0:
                periods_past = w - int(period)
                grace_threshold = 2 if loan_type == "M" else (3 if loan_type == "W" else 3)
                if periods_past >= grace_threshold:
                    if due_dt <= today:
                        penalty = 5.0
                        score = max(0.0, score - penalty)
            
            allocated_val = float(p_actual)
            
        week_details.append({
            "week": w,
            "due_date": due_dt.isoformat(),
            "paid_date": paid_date_val,
            "status": display_status,
            "allocated": allocated_val,
            "penalty": float(round_curr(penalty)),
            "score_after": float(round_curr(score))
        })

    # Apply Closure Recovery Bonus ONLY if balance_amount <= 0
    if balance_amount is not None and balance_amount <= 0:
        bonus_installments = float(total_excess_payments / inst_amt) if inst_amt > 0 else 0.0
        closure_bonus = bonus_installments * 5.0
        score = min(100.0, score + closure_bonus)
        if week_details:
            week_details[-1]["score_after"] = float(round_curr(score))

    # Score must always be clamped
    score = min(max(score, 0.0), 100.0)

    # Overdue end date penalties are already applied period-by-period inside the loop above.
    # Calculate overdue_penalty for return value only (informational), do NOT subtract again.
    overdue_penalty = 0.0
    if rem_balance > 0 and today > end_date: # type: ignore
        days_overdue = (today - end_date).days # type: ignore
        if loan_type == "M":
            if days_overdue >= 30:
                overdue_months = ((days_overdue - 30) // 30) + 1
                overdue_penalty = overdue_months * 5.0
        elif loan_type == "D":
            if days_overdue >= 3:
                overdue_days = ((days_overdue - 3) // 1) + 1
                overdue_penalty = overdue_days * 5.0
        else:
            if days_overdue >= 21:
                overdue_weeks = ((days_overdue - 21) // 7) + 1
                overdue_penalty = overdue_weeks * 5.0

    rounded_score = int(round(score))
    if rounded_score >= 90:
        risk_level = "Excellent"
    elif rounded_score >= 75:
        risk_level = "Good"
    elif rounded_score >= 60:
        risk_level = "Risky"
    else:
        risk_level = "Critical"

    return float(round_curr(score)), risk_level, overdue_penalty, week_details


def calculate_behavioral_analytics(start_date, end_date, installment_amount, period, payments, balance_amount, week_details, loan_type="W", today=None):
    KOLKATA = pytz.timezone('Asia/Kolkata')
    
    if not today:
        today = datetime.now(KOLKATA).date()
        
    start_date = parse_date_input(start_date)
    end_date = parse_date_input(end_date)
    today = parse_date_input(today)

    if not start_date or not end_date or not installment_amount or not period or installment_amount <= 0 or period <= 0:
        actual_end = end_date or start_date or today
        predicted_end = actual_end
        return {
            "status": "OnTrack",
            "predicted_end_date": predicted_end.isoformat() if hasattr(predicted_end, "isoformat") else str(predicted_end), # type: ignore
            "actual_end_date": actual_end.isoformat() if hasattr(actual_end, "isoformat") else str(actual_end), # type: ignore
            "diff_badge": "On Time",
            "net_weeks": 0,
            "discipline": {
                "on_time": 0,
                "delayed": 0,
                "partial": 0,
                "missed": 0
            },
            "stability": {
                "score": 100.0,
                "label": "Stable"
            },
            "predicted_next_risk": "Low"
        }

    inst_amt = Decimal(str(installment_amount or 0))
    bal_amt = Decimal(str(balance_amount or 0))
    
    # 1. Reconstruct payments_by_week
    valid_payments = []
    for p in payments:
        p_date = p.get("payment_date")
        if not p_date:
            continue
        p_date = parse_date_input(p_date)
        
        if p_date <= today: # type: ignore
            valid_payments.append({
                "amt": Decimal(str(p.get("amt", 0))),
                "payment_date": p_date
            })

    aggregated_payments = {}
    for p in valid_payments:
        d = p["payment_date"]
        aggregated_payments[d] = aggregated_payments.get(d, Decimal("0")) + p["amt"]
        
    due_dates = []
    w = 1
    if loan_type == "M":
        total_periods_cap = int(period) + 36
    elif loan_type == "D":
        total_periods_cap = int(period) + 1095
    else:
        total_periods_cap = int(period) + 156
    max_eval_date = end_date
    if today > max_eval_date:# type: ignore
        max_eval_date = today
    for p in valid_payments:
        if p["payment_date"] > max_eval_date:
            max_eval_date = p["payment_date"]
            
    while True:
        if loan_type == "M":
            due = start_date + relativedelta(months=w) + timedelta(days=1)
        elif loan_type == "D":
            due = start_date + timedelta(days=w)
        else:
            due = start_date + timedelta(days=7 * w + 1)
        due_dates.append(due)
        if w >= int(period):
            if due >= max_eval_date or w >= total_periods_cap:# type: ignore
                break
        w += 1
    total_weeks = len(due_dates)

    num_weeks_to_evaluate = 0
    for w in range(1, total_weeks + 1):
        window_start = start_date if w == 1 else due_dates[w-2] + timedelta(days=1)
        if window_start <= today:# type: ignore
            num_weeks_to_evaluate = w
        else:
            break

    payments_by_week = {}
    for w in range(1, num_weeks_to_evaluate + 1):
        window_start = start_date if w == 1 else due_dates[w-2] + timedelta(days=1)
        window_end = due_dates[w-1]
        week_p_sum = Decimal("0")
        for p_date, p_amt in list(aggregated_payments.items()):
            if window_start <= p_date <= window_end:
                week_p_sum += p_amt
        payments_by_week[w] = week_p_sum

    # 2. Run allocation logic
    virtual_paid = {w: Decimal("0") for w in range(1, num_weeks_to_evaluate + 1)}
    initial_status = {}
    carry_forward = Decimal("0")
    
    for w in range(1, num_weeks_to_evaluate + 1):
        current_inst = inst_amt if w <= int(period) else Decimal("0")
        available = payments_by_week.get(w, Decimal("0")) + carry_forward
        
        if current_inst > 0:
            if available >= current_inst:
                initial_status[w] = "SUCCESS"
                allocated = current_inst
                excess = available - current_inst
                virtual_paid[w] = allocated
                
                # Repair oldest MISSED first
                if excess > 0:
                    for j in range(1, w):
                        if j <= int(period) and virtual_paid[j] == 0:
                            needed = inst_amt
                            if excess >= needed:
                                virtual_paid[j] = inst_amt
                                excess -= needed
                            else:
                                virtual_paid[j] = excess
                                excess = Decimal("0")
                                break
                                
                # Repair oldest PARTIAL second
                if excess > 0:
                    for j in range(1, w):
                        if j <= int(period) and 0 < virtual_paid[j] < inst_amt:
                            needed = inst_amt - virtual_paid[j]
                            if excess >= needed:
                                virtual_paid[j] = inst_amt
                                excess -= needed
                            else:
                                virtual_paid[j] += excess
                                excess = Decimal("0")
                                break
                                
                carry_forward = excess
            else:
                if available > 0:
                    initial_status[w] = "PARTIAL"
                else:
                    initial_status[w] = "MISSED"
                virtual_paid[w] = available
                carry_forward = Decimal("0")
        else:
            initial_status[w] = "OVERDUE"
            virtual_paid[w] = available
            carry_forward = Decimal("0")

    # 3. Calculate status
    status = "OnTrack"
    if bal_amt <= 0:
        status = "Settled"
    else:
        if today > end_date:# type: ignore
            days_overdue = (today - end_date).days# type: ignore
            default_threshold_days = 180 if loan_type == "M" else (42 if loan_type == "W" else 30)
            if days_overdue >= default_threshold_days:
                status = "To Be Defaulted"
            else:
                status = "Overdue"
        else:
            has_overdue_weeks = False
            for w in range(1, num_weeks_to_evaluate + 1):
                if w <= int(period):
                    due_dt = due_dates[w-1]
                    if due_dt < today:
                        if virtual_paid.get(w, Decimal("0")) < inst_amt:
                            has_overdue_weeks = True
                            break
            if has_overdue_weeks:
                status = "Overdue"

    # 4. Calculate Predicted End Date
    if bal_amt <= 0:
        predicted_end = end_date
        net_weeks = 0
        diff_badge = "On Time"
    else:
        if loan_type == "M":
            period_days = 30.0
            period_name = "month"
        elif loan_type == "D":
            period_days = 1.0
            period_name = "day"
        else:
            period_days = 7.0
            period_name = "week"

        unpaid_equivalents = float(bal_amt / inst_amt) if inst_amt > 0 else 0.0
        if today < end_date:# type: ignore
            scheduled_remaining_periods = (end_date - today).days / period_days # type: ignore
            delay_periods = max(0.0, unpaid_equivalents - scheduled_remaining_periods)
            predicted_end = end_date + timedelta(days=int(round(delay_periods * period_days)))
        else:
            predicted_end = today + timedelta(days=int(round(unpaid_equivalents * period_days)))# type: ignore
        
        net_weeks = int(round((predicted_end - end_date).days / period_days))

        if net_weeks > 0:
            diff_badge = f"+{net_weeks} {period_name}{'s' if net_weeks > 1 else ''} late"
        elif net_weeks < 0:
            diff_badge = f"{abs(net_weeks)} {period_name}{'s' if abs(net_weeks) > 1 else ''} early"
        else:
            diff_badge = "On Time"

    # 5. Discipline profile counts
    on_time_count = 0
    delayed_count = 0
    partial_count = 0
    missed_count = 0
    
    unrepaired_missed = 0
    unrepaired_partial = 0
    
    for w in range(1, num_weeks_to_evaluate + 1):
        if w > int(period):
            continue
        due_dt = due_dates[w-1]
        is_past = (due_dt < today)
        
        init_stat = initial_status[w]
        v_paid = virtual_paid[w]
        
        if init_stat == "SUCCESS":
            on_time_count += 1
        elif is_past:
            if init_stat == "MISSED":
                missed_count += 1
                if v_paid >= inst_amt:
                    delayed_count += 1
                else:
                    unrepaired_missed += 1
            elif init_stat == "PARTIAL":
                partial_count += 1
                if v_paid >= inst_amt:
                    delayed_count += 1
                else:
                    unrepaired_partial += 1

    # 6. Payment Stability
    stability_score = 100.0
    stability_score -= (unrepaired_missed * 10.0 + unrepaired_partial * 5.0 + delayed_count * 3.0)
    stability_score = min(max(stability_score, 0.0), 100.0)
    
    if stability_score >= 90:
        stability = "Very Stable"
    elif stability_score >= 75:
        stability = "Stable"
    elif stability_score >= 50:
        stability = "Medium"
    elif stability_score >= 30:
        stability = "Unstable"
    else:
        stability = "Highly Unstable"

    # 7. Predicted Next Risk
    curr_score = 100.0
    if week_details:
        curr_score = week_details[-1]["score_after"]
        
    next_risk = "Low"
    if status == "To Be Defaulted" or curr_score < 50.0:
        next_risk = "Critical"
    elif status == "Overdue":
        last_w = num_weeks_to_evaluate
        if last_w > 0 and virtual_paid.get(last_w, Decimal("0")) == 0:
            next_risk = "High"
        else:
            next_risk = "Medium"
    elif status == "Settled":
        next_risk = "Low"
    else:
        recent_issues = 0
        for w in range(max(1, num_weeks_to_evaluate - 2), num_weeks_to_evaluate + 1):
            if w <= int(period):
                due_dt = due_dates[w-1]
                if due_dt < today:
                    if virtual_paid.get(w, Decimal("0")) < inst_amt:
                        recent_issues += 1
        if recent_issues >= 2:
            next_risk = "High"
        elif recent_issues == 1:
            next_risk = "Medium"
        else:
            next_risk = "Low"
            
        if curr_score < 75.0:
            if next_risk == "Low":
                next_risk = "Medium"
            elif next_risk == "Medium":
                next_risk = "High"
            elif next_risk == "High":
                next_risk = "Critical"

    return {
        "status": status,
        "predicted_end_date": predicted_end.isoformat(),
        "actual_end_date": end_date.isoformat(),
        "diff_badge": diff_badge,
        "net_weeks": net_weeks,
        "discipline": {
            "on_time": on_time_count,
            "delayed": delayed_count,
            "partial": partial_count,
            "missed": missed_count
        },
        "stability": {
            "score": float(stability_score),
            "label": stability
        },
        "predicted_next_risk": next_risk
    }


def format_customer_ratings_with_trends(cur, data):
    if not data:
        return data
        
    cids = [c["cid"] for c in data]
    
    # Fetch all payments for these customers
    cur.execute("""
        SELECT cid, ano, payment_date, amt, pid
        FROM v_all_payments
        WHERE cid = ANY(%s)
        ORDER BY payment_date, pid
    """, (cids,))
    prows = cur.fetchall()
    
    payments_by_cid = {}

    for prow in prows:
        cid = prow[0]
        if cid not in payments_by_cid:
            payments_by_cid[cid] = []
        payments_by_cid[cid].append({
            "ano": prow[1],
            "payment_date": prow[2].isoformat() if hasattr(prow[2], "isoformat") else str(prow[2]),
            "amt": float(prow[3] or 0),
            "pid": prow[4]
        })
        
    for c in data:
        cid = c["cid"]
        payments = payments_by_cid.get(cid, [])
        
        # Run calculation
        score, risk_level, overdue_penalty, week_details = calculate_customer_rating_details(
            c["start_date"], c["end_date"], c["installment_amount"], c["period"], payments, c["balance_amount"], loan_type=c.get("type", "W")
        )
        
        # Filter out future in-progress weeks for trend calculation
        KOLKATA = pytz.timezone('Asia/Kolkata')
        today = datetime.now(KOLKATA).date()

        completed_weeks = []
        for w in week_details:
            w_due_str = w["due_date"]
            if isinstance(w_due_str, str):
                w_due = parse_date_input(w_due_str)
            else:
                w_due = w_due_str
                
            if w_due > today:# type: ignore
                continue
            completed_weeks.append(w)

        trend = "flat"
        if len(completed_weeks) >= 2:
            last_score = completed_weeks[-1]["score_after"]
            prev_score = completed_weeks[-2]["score_after"]
            if last_score > prev_score:
                trend = "up"
            elif last_score < prev_score:
                trend = "down"
                
        rating = score
        if rating is not None:
            try:
                rating_val = int(round(float(rating)))
                c["customer_rating_raw"] = rating_val
                c["trend"] = trend
                
                prev_rating_val = 100
                if len(completed_weeks) >= 2:
                    try:
                        prev_rating_val = int(round(float(completed_weeks[-2]["score_after"])))
                    except (ValueError, TypeError):
                        prev_rating_val = 100
                c["customer_rating_prev_raw"] = prev_rating_val

                if trend == "up":
                    c["customer_rating"] = f"{rating_val} ↑"
                elif trend == "down":
                    c["customer_rating"] = f"{rating_val} ↓"
                else:
                    c["customer_rating"] = f"{rating_val} →"
            except (ValueError, TypeError):
                c["customer_rating_raw"] = None
                c["customer_rating_prev_raw"] = 100
                c["customer_rating"] = str(rating)
                c["trend"] = "flat"
        else:
            c["customer_rating_raw"] = None
            c["customer_rating_prev_raw"] = 100
            c["customer_rating"] = ""
            c["trend"] = "flat"
            
    return data


def recalc_customer_repayment_score(cur, cid, force_recalc=False):
    cur.execute("""
        SELECT start_date, end_date, installment_amount, period, balance_amount, 
               customer_rating, final_frozen_rating, final_risk_level, freeze_date, 
               status, record_tier AS source_table, type
        FROM v_all_customers
        WHERE cid = %s
        LIMIT 1
    """, (cid,))
    row = cur.fetchone()
    if not row:
        return None

    start_date, end_date, installment_amount, period, balance_amount, customer_rating, final_frozen_rating, final_risk_level, freeze_date, status, source_table, loan_type = row
    
    # Freeze logic:
    if balance_amount is not None and balance_amount <= 0 and freeze_date is not None and not force_recalc:
        return {
            "score": float(customer_rating),
            "risk_level": final_risk_level,
            "freeze_date": freeze_date.isoformat() if freeze_date else None
        }

    # Fetch payments from unified view
    cur.execute("SELECT amt, payment_date FROM v_all_payments WHERE cid = %s ORDER BY payment_date, pid", (cid,))
    prows = cur.fetchall()
    payments = [{"amt": prow[0], "payment_date": prow[1]} for prow in prows]

    score, risk_level, overdue_penalty, week_details = calculate_customer_rating_details(
        start_date, end_date, installment_amount, period, payments, balance_amount, loan_type=loan_type
    )

    if source_table == "active":
        table_name = "customer"
    elif source_table == "closed":
        table_name = "closed_cust_account"
    elif source_table == "historic":
        table_name = "historic_customer_data"
    else:
        table_name = source_table
    
    KOLKATA = pytz.timezone('Asia/Kolkata')
    
    new_freeze_date = freeze_date
    new_final_frozen_rating = final_frozen_rating
    new_final_risk_level = final_risk_level
    
    if balance_amount is not None and balance_amount <= 0:
        if new_freeze_date is None:
            new_freeze_date = datetime.now(KOLKATA)
        new_final_frozen_rating = score
        new_final_risk_level = risk_level
    else:
        new_freeze_date = None
        new_final_frozen_rating = None
        new_final_risk_level = None

    cur.execute(f"""
        UPDATE {table_name}
        SET customer_rating = %s,
            final_frozen_rating = %s,
            final_risk_level = %s,
            freeze_date = %s
        WHERE cid = %s
    """, (score, new_final_frozen_rating, new_final_risk_level, new_freeze_date, cid))

    # Update borrower master lifetime metrics if linked to UCID
    cur.execute("SELECT ucid FROM customer_loan_link WHERE cid = %s LIMIT 1", (cid,))
    ucid_row = cur.fetchone()
    lifetime_summary = None
    if ucid_row and ucid_row[0]:
        lifetime_summary = update_borrower_lifetime_metrics(cur, ucid_row[0])

    return {
        "score": float(score),
        "risk_level": risk_level,
        "freeze_date": new_freeze_date.isoformat() if new_freeze_date else None,
        "week_details": week_details,
        "lifetime_summary": lifetime_summary
    }


def update_borrower_lifetime_metrics(cur, ucid):
    if not ucid:
        return None
    cur.execute("""
        WITH borrower_stats AS (
            SELECT 
                ucid,
                COUNT(*) AS total_cycles,
                COUNT(*) FILTER (WHERE balance_amount <= 0 OR status = 'closed') AS completed_cycles,
                BOOL_OR(status IN ('defaulted', 'written_off') OR (balance_amount > 0 AND record_tier IN ('closed', 'historic'))) AS has_default,
                ROUND(AVG(COALESCE(customer_rating, 100.0)), 1) AS on_time_ratio,
                ROUND(
                    LEAST(100.0, GREATEST(0.0,
                        AVG(COALESCE(customer_rating, 100.0))
                        + LEAST(10.0, COUNT(*) FILTER (WHERE balance_amount <= 0 OR status = 'closed') * 2.0)
                        - CASE WHEN BOOL_OR(status IN ('defaulted', 'written_off') OR (balance_amount > 0 AND record_tier IN ('closed', 'historic'))) THEN 25.0 ELSE 0.0 END
                    )), 1
                ) AS lifetime_score,
                SUM(total_amount) AS lifetime_borrowed,
                SUM(paid_amount) AS lifetime_repaid,
                SUM(CASE WHEN balance_amount > 0 AND record_tier = 'active' THEN balance_amount ELSE 0.0 END) AS active_balance
            FROM v_all_customers
            WHERE ucid = %s
            GROUP BY ucid
        )
        UPDATE customer_master cm
        SET 
            total_loan_cycles = bs.total_cycles,
            total_cycles_completed = bs.completed_cycles,
            lifetime_on_time_ratio = bs.on_time_ratio,
            lifetime_credit_score = bs.lifetime_score,
            lifetime_borrowed = COALESCE(bs.lifetime_borrowed, 0.0),
            lifetime_repaid = COALESCE(bs.lifetime_repaid, 0.0),
            current_active_balance = COALESCE(bs.active_balance, 0.0),
            customer_risk_tier = CASE 
                WHEN bs.has_default THEN 'default_risk'
                WHEN bs.lifetime_score >= 85.0 THEN 'low'
                WHEN bs.lifetime_score >= 65.0 THEN 'standard'
                WHEN bs.lifetime_score >= 45.0 THEN 'elevated'
                ELSE 'high'
            END,
            updated_at = NOW()
        FROM borrower_stats bs
        WHERE cm.ucid = bs.ucid
        RETURNING cm.ucid, cm.lifetime_credit_score, cm.customer_risk_tier, cm.total_loan_cycles, cm.lifetime_on_time_ratio, cm.total_cycles_completed;
    """, (ucid,))
    row = cur.fetchone()
    if row:
        return {
            "ucid": row[0],
            "lifetime_credit_score": float(row[1]) if row[1] is not None else 100.0,
            "customer_risk_tier": row[2],
            "total_cycles": row[3],
            "lifetime_on_time_ratio": float(row[4]) if row[4] is not None else 100.0,
            "total_cycles_completed": row[5] or 0
        }
    return None


def invalidate_village_health_cache(cur, vid, invalidation_date=None):
    if invalidation_date:
        if isinstance(invalidation_date, datetime):
            invalidation_date = invalidation_date.date()
        cur.execute("""
            DELETE FROM village_health_cache 
            WHERE vid = %s AND (date_key >= %s OR time_range = 'dashboard')
        """, (vid, invalidation_date))
    else:
        cur.execute("DELETE FROM village_health_cache WHERE vid = %s", (vid,))


def recalc_customer_balance(cur, cid):
    cur.execute("SELECT record_tier, total_amount, COALESCE(interest_discount, 0) FROM v_all_customers WHERE cid = %s LIMIT 1", (cid,))
    cust_row = cur.fetchone()
    if not cust_row:
        return

    tier, total_amt, interest_discount = cust_row
    if tier == "active":
        table_customer = "customer"
    elif tier == "closed":
        table_customer = "closed_cust_account"
    elif tier == "historic":
        table_customer = "historic_customer_data"
    else:
        table_customer = "customer"

    cur.execute("SELECT COALESCE(SUM(amt), 0) FROM v_all_payments WHERE cid = %s", (cid,))
    paid_amt = cur.fetchone()[0]
    balance_amt = total_amt - paid_amt - interest_discount

    if table_customer == "customer":
        cur.execute(f"""
            UPDATE {table_customer}
            SET paid_amount = %s,
                balance_amount = %s,
                updated_at = NOW()
            WHERE cid = %s
        """, (paid_amt, balance_amt, cid))
    else:
        cur.execute(f"""
            UPDATE {table_customer}
            SET paid_amount = %s,
                balance_amount = %s
            WHERE cid = %s
        """, (paid_amt, balance_amt, cid))

    recalc_customer_repayment_score(cur, cid, force_recalc=True)
# ----------------------------------------------------
# ROUTES - mobile app
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("5 per minute")
@app.post("/api/mobile/login")
def mobile_login():

    data = request.json
    if not data:
        return {"error": "invalid"}, 401
    
    username = data.get("username")
    password = data.get("password")

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT u.id, u.password_hash, u.is_active, e.level
            FROM users u
            JOIN employee e ON e.eid = u.employee_id
            WHERE u.username=%s
        """,(username,))

        user = cur.fetchone()

        if not user:
            return {"error":"invalid"},401

        user_id,password_hash,is_active,level = user

        if not is_active:
            return {"error":"inactive"},403

        if not check_password_hash(password_hash,password):
            return {"error":"invalid"},401
        
        cur.execute("SELECT eid FROM employee WHERE eid IN (SELECT employee_id FROM users WHERE id = %s)", (user_id,))
        result = cur.fetchone()
        if not result:
            return {"error":"employee not found"},401
        eid = result[0]

        # ---------------------------
        # Multi-Device Installation Tracking & Lock Check
        # ---------------------------
        device_id = data.get("device_id")
        device_model = data.get("device_model") or data.get("device_name") or "Mobile Device"

        if device_id and device_id != 'PENDING':
            ensure_user_devices_table(cur)
            # Record/Upsert this device for the user account (including admins)
            cur.execute("""
                INSERT INTO user_devices (user_id, device_id, device_model, is_active, last_active, created_at)
                VALUES (%s, %s, %s, TRUE, NOW(), NOW())
                ON CONFLICT (user_id, device_id)
                DO UPDATE SET
                    last_active = NOW(),
                    device_model = COALESCE(EXCLUDED.device_model, user_devices.device_model),
                    is_active = TRUE
            """, (user_id, device_id, device_model))
            conn.commit()

        if level and level.strip().lower() in ("j", "m", "s"):
            if not device_id:
                return {"error": "device_id required"}, 400

            cur.execute("""
                SELECT is_active 
                FROM user_devices 
                WHERE user_id = %s AND device_id = %s
            """, (user_id, device_id))
            dev_row = cur.fetchone()

            if dev_row and not dev_row[0]:
                return {"error": "Device disabled. Contact administrator."}, 403

        token = generate_mobile_token(user_id, eid)

        audit_log(
          action="mobile_login",
          entity_type="user",
          entity_id=user_id,
          details={
              "eid": eid,
              "username": username,
              "level": level
            }
        )

        return {
            "token":token,
            "user_id":user_id,
            "username":username,
            "eid": eid,
            "level": level
        }
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@app.get("/api/mobile/villages")
def mobile_villages():

    token = request.headers.get("X-Mobile-Token")

    if not token:
        return {"error": "missing token"}, 401

    data = verify_mobile_token(token)

    if not data:
        return {"error": "invalid token"}, 401

    user_id = data["user_id"]
    eid = data["eid"]

    # Fetch employee name
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM employee WHERE eid = %s", (eid,))
        emp_row = cur.fetchone()
        employee_name = emp_row[0] if emp_row else ""

        # 🔹 Fetch villages from user_village_access
        cur.execute("""
            SELECT v.vid, v.village_name, v.village_code, v.district, v.interest_rate, v.cutting_rate
            FROM user_village_access uva
            JOIN village v ON v.vid = uva.village_id
            WHERE uva.user_id = %s
            ORDER BY v.village_name
        """, (user_id,))

        villages = cur.fetchall()

        if not villages:
            # Fallback 1: Check if user is admin or management
            cur.execute("SELECT level FROM users WHERE id = %s", (user_id,))
            user_level_row = cur.fetchone()
            user_level = (user_level_row[0] if user_level_row else "").lower()
            if user_level in ["admin", "superadmin", "mgmt"]:
                cur.execute("""
                    SELECT vid, village_name, village_code, district, interest_rate, cutting_rate
                    FROM village
                    ORDER BY village_name
                """)
                villages = cur.fetchall()
            elif eid:
                # Fallback 2: Check employee village assignment (emp1 or emp2)
                cur.execute("""
                    SELECT vid, village_name, village_code, district, interest_rate, cutting_rate
                    FROM village
                    WHERE emp1 = %s OR emp2 = %s
                    ORDER BY village_name
                """, (eid, eid))
                villages = cur.fetchall()
                if villages:
                    try:
                        for v_row in villages:
                            cur.execute("""
                                INSERT INTO user_village_access (user_id, village_id)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, (user_id, v_row[0]))
                        conn.commit()
                    except Exception:
                        conn.rollback()

        return {
            "villages": [
                {
                    "vid": v[0],
                    "village_name": v[1],
                    "village_code": v[2] or "",
                    "district": v[3],
                    "interest_rate": float(v[4]) if v[4] is not None else 0.0,
                    "cutting_rate": float(v[5]) if v[5] is not None else 0.0,
                    "employee_name": employee_name
                }
                for v in villages
            ]
        }
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@app.get("/api/mobile/cashbag")
def mobile_cashbag_get():
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return {"error": "missing token"}, 401

    token_data = verify_mobile_token(token)
    if not token_data:
        return {"error": "invalid token"}, 401

    eid = token_data.get("eid")
    if not eid:
        return {"error": "invalid token data"}, 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Resolve emp1, emp2 from village or default to eid
        cur.execute("SELECT emp1, emp2 FROM village WHERE emp1 = %s OR emp2 = %s LIMIT 1", (eid, eid))
        row = cur.fetchone()
        if row:
            emp1, emp2 = row[0], row[1]
        else:
            emp1, emp2 = eid, None

        # Fetch names
        cur.execute("SELECT name FROM employee WHERE eid = %s", (emp1,))
        row_e1 = cur.fetchone()
        emp1_name = row_e1[0] if row_e1 else f"Employee {emp1}"

        emp2_name = None
        if emp2:
            cur.execute("SELECT name FROM employee WHERE eid = %s", (emp2,))
            row_e2 = cur.fetchone()
            emp2_name = row_e2[0] if row_e2 else f"Employee {emp2}"

        # Fetch villages in the group
        if emp2:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND emp2 = %s AND status = 'active'
                ORDER BY village_code
            """, (emp1, emp2))
        else:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
                ORDER BY village_code
            """, (emp1,))
        rows_v = cur.fetchall()
        group_villages = [{"id": r[0], "name": r[1], "code": r[2]} for r in rows_v]
        vids = [r[0] for r in rows_v]

        # Consolidated Manual Transactions
        if emp2:
            pair_filter = "emp1 = %s AND emp2 = %s"
            pair_params_single = (emp1, emp2)
        else:
            pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
            pair_params_single = (emp1,)

        cur.execute(f"""
            SELECT id, txn, txn_sub, txn_type, amount, notes, created_by, created_at
            FROM cashbag_transactions
            WHERE {pair_filter}
            ORDER BY created_at DESC, id DESC
        """, pair_params_single)
        manual_rows = cur.fetchall()

        office_cash = 0.0
        expenses = 0.0
        adjustments_add = 0.0
        adjustments_minus = 0.0

        for tid, txn, txn_sub, txn_type, amount_db, notes, created_by, created_at in manual_rows:
            amt = float(amount_db or 0)
            if txn == 'OFFICE_CASH':
                office_cash += amt
            elif txn == 'EXPENSE':
                expenses += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    adjustments_add += amt
                elif txn_sub == 'MINUS':
                    adjustments_minus += amt

        # Installment Collections
        if vids:
            cur.execute("""
                SELECT COALESCE(SUM(amt), 0)
                FROM payment
                WHERE vid = ANY(%s)
            """, (vids,))
            installments = float(cur.fetchone()[0] or 0)
        else:
            installments = 0.0

        # Loans & Commissions
        loans_disbursed = 0.0
        loan_commission = 0.0
        if vids:
            cur.execute("""
                SELECT c.base_amount, c.cutting_amount, c.total_amount,
                       v.interest_rate, v.cutting_rate
                FROM customer c
                JOIN village v ON c.vid = v.vid
                WHERE c.vid = ANY(%s) AND c.status != 'deleted'
            """, (vids,))
            loan_rows = cur.fetchall()

            for base_amt_db, cutting_amt_db, total_amt_db, ir_db, cr_db in loan_rows:
                base_amt = float(base_amt_db or 0)
                cutting_amt = float(cutting_amt_db or 0)
                total_amt = float(total_amt_db or 0)

                if base_amt <= 0.0:
                    ir = float(ir_db or 0)
                    cr = float(cr_db or 0)
                    interest = round_curr(total_amt * (ir / 100.0))
                    cutting_amt = round_curr(total_amt * (cr / 100.0))
                    base_amt = round_curr(total_amt - interest - cutting_amt)

                loans_disbursed += base_amt
                loan_commission += cutting_amt

        cashbag_total = (
            office_cash
            + installments
            + loan_commission
            + adjustments_add
            - loans_disbursed
            - expenses
            - adjustments_minus
        )

        # UNIFIED LEDGER
        transactions = []
        if vids:
            query = f"""
                SELECT 
                    id,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by,
                    TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH12:MI AM') AS created_at
                FROM (
                    -- Manual entries
                    SELECT 
                        id::text AS id,
                        txn,
                        txn_sub,
                        txn_type,
                        amount,
                        notes,
                        created_by,
                        created_at
                    FROM cashbag_transactions
                    WHERE {pair_filter}
                      AND txn IN ('OFFICE_CASH', 'EXPENSE', 'ADJUSTMENT')

                    UNION ALL

                    -- Customer Loans
                    SELECT 
                        'loan_' || c.cid::text AS id,
                        'LOAN' AS txn,
                        NULL AS txn_sub,
                        'CASH' AS txn_type,
                        CASE 
                            WHEN c.base_amount > 0 THEN c.base_amount
                            ELSE ROUND(c.total_amount - (c.total_amount * (v.interest_rate / 100.0)) - (c.total_amount * (v.cutting_rate / 100.0)), 2)
                        END AS amount,
                        'Loan issued to ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                        'System' AS created_by,
                        c.start_date::timestamp WITH time zone AS created_at
                    FROM customer c
                    JOIN village v ON c.vid = v.vid
                    WHERE c.vid = ANY(%s) AND c.status != 'deleted'

                    UNION ALL

                    -- Customer Loan Commission
                    SELECT 
                        'comm_' || c.cid::text AS id,
                        'LOAN_COMMISION' AS txn,
                        NULL AS txn_sub,
                        'CASH' AS txn_type,
                        CASE 
                            WHEN c.cutting_amount > 0 THEN c.cutting_amount
                            ELSE ROUND(c.total_amount * (v.cutting_rate / 100.0), 2)
                        END AS amount,
                        'Rusum - ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                        'System' AS created_by,
                        c.start_date::timestamp WITH time zone AS created_at
                    FROM customer c
                    JOIN village v ON c.vid = v.vid
                    WHERE c.vid = ANY(%s) AND c.status != 'deleted'

                    UNION ALL

                    -- Customer Payments
                    SELECT 
                        'pay_' || p.pid::text AS id,
                        'INSTALLMENT_AMOUNT' AS txn,
                        NULL AS txn_sub,
                        p.payment_type AS txn_type,
                        p.amt AS amount,
                        'Collection from ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                        'System' AS created_by,
                        p.created_at AS created_at
                    FROM payment p
                    JOIN customer c ON p.cid = c.cid
                    WHERE c.vid = ANY(%s)
                ) AS combined
                ORDER BY combined.created_at DESC, id DESC
            """
            if emp2:
                params = (emp1, emp2, vids, vids, vids)
            else:
                params = (emp1, vids, vids, vids)
            cur.execute(query, params)
        else:
            query = f"""
                SELECT 
                    id::text AS id,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by,
                    TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH12:MI AM') AS created_at
                FROM cashbag_transactions
                WHERE {pair_filter}
                  AND txn IN ('OFFICE_CASH', 'EXPENSE', 'ADJUSTMENT')
                ORDER BY created_at DESC, id DESC
            """
            cur.execute(query, pair_params_single)

        rows = cur.fetchall()
        for row in rows:
            transactions.append({
                "id":         row[0],
                "txn":        row[1],
                "txn_sub":    row[2],
                "txn_type":   row[3],
                "amount":     float(row[4] or 0),
                "notes":      row[5],
                "created_by": row[6],
                "created_at": row[7]
            })

        return {
            "emp1": emp1,
            "emp2": emp2,
            "emp1_name": emp1_name,
            "emp2_name": emp2_name,
            "group_villages": group_villages,
            "cashbag_total": cashbag_total,
            "office_cash": office_cash,
            "installments": installments,
            "loans_disbursed": loans_disbursed,
            "loan_commission": loan_commission,
            "expenses": expenses,
            "adjustments_add": adjustments_add,
            "adjustments_minus": adjustments_minus,
            "transactions": transactions
        }
    finally:
        cur.close()
        conn.close()

@app.get("/api/mobile/ledger")
def mobile_ledger_get():
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return {"error": "missing token"}, 401

    token_data = verify_mobile_token(token)
    if not token_data:
        return {"error": "invalid token"}, 401

    eid = token_data.get("eid")
    if not eid:
        return {"error": "invalid token data"}, 400

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        return {"error": "Missing start_date or end_date"}, 400

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format"}, 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT emp1, emp2 FROM village WHERE emp1 = %s OR emp2 = %s LIMIT 1", (eid, eid))
        row = cur.fetchone()
        if row:
            emp1, emp2 = row[0], row[1]
        else:
            emp1, emp2 = eid, None

        if emp2:
            pair_filter = "emp1 = %s AND emp2 = %s"
            pair_params_single = (emp1, emp2)
        else:
            pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
            pair_params_single = (emp1,)

        if emp2:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND emp2 = %s AND status = 'active'
            """, (emp1, emp2))
        else:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
            """, (emp1,))
        
        village_rows = cur.fetchall()
        vids = [r[0] for r in village_rows]

        if not vids:
            return {
                "success": True,
                "opening_balance": 0.0,
                "dates": {},
                "dates_list": []
            }

        cur.execute(f"""
            SELECT txn, txn_sub, amount
            FROM cashbag_transactions
            WHERE {pair_filter} AND created_at::date < %s
        """, pair_params_single + (start_date,))
        hist_manual = cur.fetchall()

        office_cash_h = 0.0
        expenses_h = 0.0
        adj_add_h = 0.0
        adj_minus_h = 0.0

        for txn, txn_sub, amount in hist_manual:
            amt = float(amount or 0)
            if txn == 'OFFICE_CASH':
                office_cash_h += amt
            elif txn == 'EXPENSE':
                expenses_h += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    adj_add_h += amt
                elif txn_sub == 'MINUS':
                    adj_minus_h += amt

        cur.execute("""
            SELECT COALESCE(SUM(amt), 0)
            FROM payment p
            JOIN customer c ON p.cid = c.cid
            WHERE c.vid = ANY(%s) AND p.payment_date < %s
        """, (vids, start_date))
        installments_h = float(cur.fetchone()[0] or 0)

        cur.execute("""
            SELECT c.base_amount, c.cutting_amount, c.total_amount,
                   v.interest_rate, v.cutting_rate
            FROM customer c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted' AND c.start_date < %s
        """, (vids, start_date))
        hist_loans = cur.fetchall()

        loans_disbursed_h = 0.0
        loan_commission_h = 0.0

        for base_amt_db, cutting_amt_db, total_amt_db, ir_db, cr_db in hist_loans:
            base_amt = float(base_amt_db or 0)
            cutting_amt = float(cutting_amt_db or 0)
            total_amt = float(total_amt_db or 0)

            if base_amt <= 0.0:
                ir = float(ir_db or 0)
                cr = float(cr_db or 0)
                interest = round_curr(total_amt * (ir / 100.0))
                cutting_amt = round_curr(total_amt * (cr / 100.0))
                base_amt = round_curr(total_amt - interest - cutting_amt)

            loans_disbursed_h += base_amt
            loan_commission_h += cutting_amt

        opening_balance = (
            office_cash_h
            + installments_h
            + loan_commission_h
            + adj_add_h
            - loans_disbursed_h
            - expenses_h
            - adj_minus_h
        )

        cur.execute("""
            SELECT c.cid, c.ano, c.name, c.base_amount, c.cutting_amount, c.total_amount, c.start_date,
                   v.village_code, v.interest_rate, v.cutting_rate
            FROM customer c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted'
              AND c.start_date >= %s AND c.start_date <= %s
            ORDER BY c.start_date ASC, c.cid ASC
        """, (vids, start_date, end_date))
        loans_rows = cur.fetchall()

        cur.execute("""
            SELECT p.pid, c.ano, c.name, p.amt, p.payment_date, v.village_code
            FROM payment p
            JOIN customer c ON p.cid = c.cid
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s)
              AND p.payment_date >= %s AND p.payment_date <= %s
            ORDER BY p.payment_date ASC, p.pid ASC
        """, (vids, start_date, end_date))
        payments_rows = cur.fetchall()

        cur.execute(f"""
            SELECT id, txn, txn_sub, txn_type, amount, notes, created_at
            FROM cashbag_transactions
            WHERE {pair_filter}
              AND created_at::date >= %s AND created_at::date <= %s
            ORDER BY created_at ASC, id ASC
        """, pair_params_single + (start_date, end_date))
        manual_rows = cur.fetchall()

        dates_in_range = []
        curr = start_date
        while curr <= end_date:
            dates_in_range.append(curr)
            curr += timedelta(days=1)

        dates_data = {}
        for d in dates_in_range:
            d_str = d.strftime("%Y-%m-%d")
            dates_data[d_str] = {
                "date_label": d.strftime("%d-%m-%Y"),
                "villages": [],
                "loans": [],
                "loans_total": {"commission": 0.0, "amount": 0.0, "interest": 0.0},
                "payments": [],
                "payments_total": 0.0,
                "expenses": [],
                "expenses_total": 0.0,
                "office_cash": [],
                "office_cash_total": 0.0,
                "adjustments_add": [],
                "adjustments_total_add": 0.0,
                "adjustments_minus": [],
                "adjustments_total_minus": 0.0
            }

        for cid, ano, name, base_amt_db, cutting_amt_db, total_amt_db, start_dt, v_code, ir_db, cr_db in loans_rows:
            d_str = start_dt.strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            base_amt = float(base_amt_db or 0)
            cutting_amt = float(cutting_amt_db or 0)
            total_amt = float(total_amt_db or 0)

            ir = float(ir_db or 0)
            cr = float(cr_db or 0)
            interest = round_curr(total_amt * (ir / 100.0))
            if base_amt <= 0.0:
                cutting_amt = round_curr(total_amt * (cr / 100.0))
                base_amt = round_curr(total_amt - interest - cutting_amt)

            dates_data[d_str]["loans"].append({
                "ano": ano,
                "name": name,
                "amount": base_amt,
                "interest": interest,
                "commission": cutting_amt,
                "village_code": v_code
            })
            dates_data[d_str]["loans_total"]["amount"] += base_amt
            dates_data[d_str]["loans_total"]["interest"] += interest
            dates_data[d_str]["loans_total"]["commission"] += cutting_amt
            if v_code not in dates_data[d_str]["villages"]:
                dates_data[d_str]["villages"].append(v_code)

        for pid, ano, name, amt, payment_date, v_code in payments_rows:
            d_str = payment_date.strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            dates_data[d_str]["payments"].append({
                "ano": ano,
                "name": name,
                "amount": float(amt or 0),
                "village_code": v_code
            })
            dates_data[d_str]["payments_total"] += float(amt or 0)
            if v_code not in dates_data[d_str]["villages"]:
                dates_data[d_str]["villages"].append(v_code)

        for tid, txn, txn_sub, txn_type, amount_db, notes, created_at in manual_rows:
            d_str = created_at.date().strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            amt = float(amount_db or 0)
            if txn == 'OFFICE_CASH':
                dates_data[d_str]["office_cash"].append({
                    "notes": notes or "Office Cash",
                    "amount": amt,
                    "txn_type": txn_type
                })
                dates_data[d_str]["office_cash_total"] += amt
            elif txn == 'EXPENSE':
                dates_data[d_str]["expenses"].append({
                    "notes": notes or "Expense",
                    "amount": amt,
                    "txn_type": txn_type
                })
                dates_data[d_str]["expenses_total"] += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    dates_data[d_str]["adjustments_add"].append({
                        "notes": notes or "Adjustment Add",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_add"] += amt
                elif txn_sub == 'MINUS':
                    dates_data[d_str]["adjustments_minus"].append({
                        "notes": notes or "Adjustment Minus",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_minus"] += amt

        dates_list = [d.strftime("%Y-%m-%d") for d in dates_in_range]

        return {
            "success": True,
            "opening_balance": opening_balance,
            "dates": dates_data,
            "dates_list": dates_list
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}, 500
    finally:
        cur.close()
        conn.close()


@csrf.exempt
@app.post("/api/mobile/cashbag/add")
def mobile_cashbag_add():
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return {"error": "missing token"}, 401

    token_data = verify_mobile_token(token)
    if not token_data:
        return {"error": "invalid token"}, 401

    eid = token_data.get("eid")
    if not eid:
        return {"error": "invalid token data"}, 400

    body = request.json or {}
    txn = body.get("txn", "").strip().upper()
    txn_sub = body.get("txn_sub", "").strip().upper()
    txn_type = body.get("txn_type", "CASH").strip().upper()
    amount_raw = body.get("amount")
    notes = body.get("notes", "").strip()

    allowed_txn = ["OFFICE_CASH", "EXPENSE", "ADJUSTMENT"]
    if txn not in allowed_txn:
        return {"error": f"Invalid transaction category: {txn}"}, 400

    if txn == "OFFICE_CASH":
        txn_sub = ""

    allowed_txn_type = ["CASH", "UPI"]
    if txn_type not in allowed_txn_type:
        txn_type = "CASH"

    try:
        amount = float(amount_raw or 0)
        if amount <= 0:
            return {"error": "Amount must be greater than zero"}, 400
    except Exception:
        return {"error": "Invalid amount format"}, 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Get username
        cur.execute("SELECT username FROM users WHERE employee_id = %s LIMIT 1", (eid,))
        user_row = cur.fetchone()
        username = user_row[0] if user_row else f"Employee {eid}"

        # Resolve emp1, emp2
        cur.execute("SELECT emp1, emp2 FROM village WHERE emp1 = %s OR emp2 = %s LIMIT 1", (eid, eid))
        row = cur.fetchone()
        if row:
            emp1, emp2 = row[0], row[1]
        else:
            emp1, emp2 = eid, None

        cur.execute("""
            INSERT INTO cashbag_transactions (
                emp1,
                emp2,
                eid,
                txn,
                txn_sub,
                txn_type,
                amount,
                notes,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            emp1,
            emp2,
            eid,
            txn,
            txn_sub or None,
            txn_type,
            amount,
            notes or None,
            username
        ))

        conn.commit()

        audit_log(
            action="mobile_cashbag_transaction_added",
            entity_type="cashbag_transaction",
            entity_id=emp1,
            details={
                "emp1":     emp1,
                "emp2":     emp2,
                "txn":      txn,
                "txn_sub":  txn_sub,
                "txn_type": txn_type,
                "amount":   amount,
                "notes":    notes
            }
        )

        return {"success": True, "message": "Cashbag entry added successfully"}
    except Exception as e:
        return {"error": f"Failed to add cashbag entry: {str(e)}"}, 500
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@app.get("/api/mobile/customers")
def mobile_customers():

    token = request.headers.get("X-Mobile-Token")
    if not token:
        return {"error": "missing token"}, 401

    data = verify_mobile_token(token)
    if not data:
        return {"error": "invalid token"}, 401

    vid = request.args.get("vid")
    updated_after_raw = request.args.get("updated_after")
    updated_after = parse_mobile_timestamp(updated_after_raw)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SET TIME ZONE 'UTC'")

        if updated_after:
            cur.execute("""
                SELECT *
                FROM customer
                WHERE vid = %s
                  AND (
                    created_at > %s
                    OR COALESCE(updated_at, created_at) > %s
                  )
            """, (vid, updated_after, updated_after))
        else:
            cur.execute("""
                SELECT *
                FROM customer
                WHERE vid = %s
            """, (vid,))

        columns = [desc[0] for desc in cur.description] if cur.description else []

        rows = cur.fetchall()

        customers = []

        for r in rows:
            customers.append(dict(zip(columns, r)))

        return {"customers": customers}
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@app.get("/api/mobile/payments")
def mobile_payments():

    token = request.headers.get("X-Mobile-Token")
    if not token:
        return {"error": "missing token"}, 401

    data = verify_mobile_token(token)
    if not data:
        return {"error": "invalid token"}, 401

    vid = request.args.get("vid")
    updated_after_raw = request.args.get("updated_after")
    updated_after = parse_mobile_timestamp(updated_after_raw)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SET TIME ZONE 'UTC'")

        if updated_after:
            cur.execute("""
                SELECT *
                FROM payment
                WHERE vid = %s
                  AND (
                    created_at > %s
                    OR updated_at > %s
                  )
            """, (vid, updated_after, updated_after))
        else:
            cur.execute("""
                SELECT *
                FROM payment
                WHERE vid = %s
            """, (vid,))

        columns = [desc[0] for desc in cur.description] if cur.description else []

        rows = cur.fetchall()

        payments = []

        for r in rows:
            payments.append(dict(zip(columns, r)))

        return {"payments": payments}
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@app.get("/api/mobile/closed_customers")
def mobile_closed_customers():

    token = request.headers.get("X-Mobile-Token")
    if not token:
        return {"error": "missing token"}, 401

    data = verify_mobile_token(token)
    if not data:
        return {"error": "invalid token"}, 401

    vid = request.args.get("vid")
    updated_after_raw = request.args.get("updated_after")
    updated_after = parse_mobile_timestamp(updated_after_raw)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SET TIME ZONE 'UTC'")

        if updated_after:
            cur.execute("""
                SELECT
                    cid,
                    ano,
                    name,
                    vid,
                    status,
                    balance_amount,
                    closed_at,
                    closed_at AS updated_at
                FROM closed_cust_account
                WHERE vid = %s
                  AND closed_at > %s
            """, (vid, updated_after))
        else:
            cur.execute("""
                SELECT
                    cid,
                    ano,
                    name,
                    vid,
                    status,
                    balance_amount,
                    closed_at,
                    closed_at AS updated_at
                FROM closed_cust_account
                WHERE vid = %s
            """, (vid,))

        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        customers = [dict(zip(columns, r)) for r in rows]

        return {"customers": customers}
    finally:
        cur.close()
        conn.close()

@csrf.exempt
@limiter.limit("200 per minute")
@app.route("/api/mobile/customer_feed", methods=["POST"])
def customer_feed():
    conn = None
    cur = None
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return {"error": "missing token"}, 401

        data_token = verify_mobile_token(token)
        if not data_token:
            return {"error": "invalid token"}, 401

        payload_json = request.form.get("payload")
        if not payload_json:
            return jsonify({"error": "missing payload"}), 400

        try:
            data = json.loads(payload_json)  # queue envelope from mobile
        except Exception:
            return jsonify({"error": "invalid payload json"}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "invalid envelope"}), 400

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
            return jsonify({
                "error": f"missing integrity fields: {', '.join(missing)}"
            }), 400

        def _canonical_json(value):
            return json.dumps(value, sort_keys=True, separators=(",", ":"))

        try:
            # use defaults to satisfy type checkers; presence/emptiness validated above
            envelope_eid = int(data.get("eid", 0))
            envelope_vid = int(data.get("vid", 0))
            token_eid = int(data_token.get("eid", 0))
        except Exception:
            return jsonify({"error": "invalid identity fields"}), 400

        if envelope_eid != token_eid:
            return jsonify({"error": "eid mismatch"}), 403

        parsed_ts = parse_mobile_timestamp(data.get("timestamp"))
        if parsed_ts is None:
            return jsonify({"error": "invalid timestamp"}), 400

        age_seconds = abs((datetime.now(timezone.utc) - parsed_ts).total_seconds())
        if age_seconds > 900:
            return jsonify({"error": "stale timestamp"}), 400

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

        expected_signature = hmac.new(
            signing_secret.encode("utf-8"),
            _canonical_json(signed_payload).encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        provided_signature = str(data.get("signature") or "")
        if not hmac.compare_digest(provided_signature, expected_signature):
            audit_log(
                action="mobile_customer_upload_rejected",
                entity_type="customer_feed",
                entity_id=data.get("local_uuid"),
                details={
                    "reason": "invalid signature",
                    "eid": data.get("eid"),
                    "vid": data.get("vid"),
                    "nonce": data.get("nonce"),
                    "idempotency_key": data.get("idempotency_key"),
                },
                status="failed"
            )
            return jsonify({"error": "invalid signature"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC'")

        # Optional replay protection if you create a dedicated table:
        # cur.execute(
        #     "SELECT 1 FROM mobile_request_integrity WHERE idempotency_key = %s OR nonce = %s LIMIT 1",
        #     (data.get("idempotency_key"), data.get("nonce"))
        # )
        # if cur.fetchone():
        #     return jsonify({"error": "duplicate request"}), 409

        local_uuid = data.get("local_uuid")
        device_id = data.get("device_id", "mobile")
        eid = envelope_eid
        vid = envelope_vid
        status = data.get("status", "pending")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        gps_accuracy = data.get("gps_accuracy")

        ok, reason = register_mobile_request_integrity(
            cur,
            endpoint="/api/mobile/customer_feed",
            eid=eid,
            vid=vid,
            local_uuid=local_uuid,
            idempotency_key=data.get("idempotency_key"),
            nonce=data.get("nonce"),
            request_signature=provided_signature,
            request_timestamp=parsed_ts,
        )
        if not ok:
            conn.rollback()
            audit_log(
                action="mobile_customer_upload_rejected",
                entity_type="customer_feed",
                entity_id=local_uuid,
                details={
                    "reason": reason,
                    "eid": eid,
                    "vid": vid,
                    "nonce": data.get("nonce"),
                    "idempotency_key": data.get("idempotency_key"),
                },
                status="failed"
            )
            return jsonify({"error": reason}), 409

        customer_payload = data.get("payload")

        if isinstance(customer_payload, str):
            customer_payload = json.loads(customer_payload)

        if not isinstance(customer_payload, dict):
            return jsonify({"error": "invalid customer payload"}), 400

        try:
            customer_payload = normalize_mobile_customer_payload(customer_payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        ano = customer_payload.get("ano") # type: ignore
        payload = json.dumps(customer_payload)

        logger.debug(
            "Customer feed received for vid=%s ano=%s nonce=%s idempotency_key=%s",
            vid,
            ano,
            data.get("nonce"),
            data.get("idempotency_key"),
        )

        cur.execute("""
            INSERT INTO customer_feed
            (
                local_uuid,
                device_id,
                eid,
                vid,
                status,
                payload,
                latitude,
                longitude,
                gps_accuracy
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (local_uuid) DO NOTHING
        """, (
            local_uuid,
            device_id,
            eid,
            vid,
            status,
            payload,
            latitude,
            longitude,
            gps_accuracy
        ))

        # 2️⃣ Read images
        aadhaar_front_file = request.files.get("aadhaar_front_pic")
        aadhaar_back_file = request.files.get("aadhaar_back_pic")
        house_file = request.files.get("house_photo")

        aadhaar_front_bytes = aadhaar_front_file.read() if aadhaar_front_file else None
        aadhaar_back_bytes = aadhaar_back_file.read() if aadhaar_back_file else None
        house_bytes = house_file.read() if house_file else None

        # 3️⃣ Insert into customer_docs
        if aadhaar_front_bytes or aadhaar_back_bytes or house_bytes:
            cur.execute("""
                INSERT INTO customer_docs (vid, ano, aadhaar_front_pic, aadhaar_back_pic, house_photo)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (vid, ano)
                DO UPDATE SET
                    aadhaar_front_pic = COALESCE(EXCLUDED.aadhaar_front_pic, customer_docs.aadhaar_front_pic),
                    aadhaar_back_pic = COALESCE(EXCLUDED.aadhaar_back_pic, customer_docs.aadhaar_back_pic),
                    house_photo = COALESCE(EXCLUDED.house_photo, customer_docs.house_photo)
            """, (
                vid,
                ano,
                aadhaar_front_bytes,
                aadhaar_back_bytes,
                house_bytes
            ))

        # Optional replay ledger insert if you create the table:
        # cur.execute("""
        #     INSERT INTO mobile_request_integrity
        #     (idempotency_key, nonce, eid, vid, endpoint, local_uuid, created_at)
        #     VALUES (%s, %s, %s, %s, %s, %s, NOW())
        # """, (
        #     data.get("idempotency_key"),
        #     data.get("nonce"),
        #     eid,
        #     vid,
        #     "/api/mobile/customer_feed",
        #     local_uuid,
        # ))

        conn.commit()
        audit_log(
            action="mobile_customer_upload",
            entity_type="customer_feed",
            entity_id=local_uuid,
            details={
                "eid": eid,
                "vid": vid,
                "ano": ano,
                "device_id": device_id,
                "status": status,
                "nonce": data.get("nonce"),
                "idempotency_key": data.get("idempotency_key"),
            }
        )

        return jsonify({"status": "ok"})

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("Customer feed processing failed")
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


# ----------------------------------------------------
# /api/mobile/close_account_feed
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("200 per minute")
@app.route("/api/mobile/close_account_feed", methods=["POST"])
@app.route("/close_account_feed", methods=["POST"])
def close_account_feed():
    conn = None
    cur = None
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return {"error": "missing token"}, 401

        data_token = verify_mobile_token(token)
        if not data_token:
            return {"error": "invalid token"}, 401

        payload_json = request.form.get("payload")
        if not payload_json:
            return jsonify({"error": "missing payload"}), 400

        try:
            data = json.loads(payload_json)  # queue envelope from mobile
        except Exception:
            return jsonify({"error": "invalid payload json"}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "invalid envelope"}), 400

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
            return jsonify({
                "error": f"missing integrity fields: {', '.join(missing)}"
            }), 400

        def _canonical_json(value):
            return json.dumps(value, sort_keys=True, separators=(",", ":"))

        try:
            envelope_eid = int(data.get("eid", 0))
            envelope_vid = int(data.get("vid", 0))
            token_eid = int(data_token.get("eid", 0))
        except Exception:
            return jsonify({"error": "invalid identity fields"}), 400

        if envelope_eid != token_eid:
            return jsonify({"error": "eid mismatch"}), 403

        parsed_ts = parse_mobile_timestamp(data.get("timestamp"))
        if parsed_ts is None:
            return jsonify({"error": "invalid timestamp"}), 400

        age_seconds = abs((datetime.now(timezone.utc) - parsed_ts).total_seconds())
        if age_seconds > 900:
            return jsonify({"error": "stale timestamp"}), 400

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

        expected_signature = hmac.new(
            signing_secret.encode("utf-8"),
            _canonical_json(signed_payload).encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        provided_signature = str(data.get("signature") or "")
        if not hmac.compare_digest(provided_signature, expected_signature):
            return jsonify({"error": "invalid signature"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC'")

        local_uuid = data.get("local_uuid")
        device_id = data.get("device_id", "mobile")
        eid = envelope_eid
        vid = envelope_vid

        ok, reason = register_mobile_request_integrity(
            cur,
            endpoint="/api/mobile/close_account_feed",
            eid=eid,
            vid=vid,
            local_uuid=local_uuid,
            idempotency_key=data.get("idempotency_key"),
            nonce=data.get("nonce"),
            request_signature=provided_signature,
            request_timestamp=parsed_ts,
        )
        if not ok:
            conn.rollback()
            return jsonify({"error": reason}), 409

        closure_payload = data.get("payload")
        if isinstance(closure_payload, str):
            closure_payload = json.loads(closure_payload)

        ano = int(closure_payload.get("ano", 0)) # type: ignore

        cur.execute("""
            INSERT INTO account_closure_feed
            (
                local_uuid,
                device_id,
                eid,
                vid,
                ano,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (local_uuid) DO NOTHING
        """, (local_uuid, device_id, eid, vid, ano, 'pending'))

        conn.commit()
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Account closure feed processing failed")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ----------------------------------------------------
# REAL-TIME SUBMISSION STATUS & STREAMING API
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("300 per minute")
@app.route("/api/mobile/submissions/status", methods=["GET"])
def get_submission_statuses():
    token = request.headers.get("X-Mobile-Token")
    if not token or not verify_mobile_token(token):
        return jsonify({"error": "unauthorized"}), 401

    vid = request.args.get("vid", type=int)
    if not vid:
        return jsonify({"error": "vid required"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        ensure_feed_tables_exist(cur)
        statuses = []

        # 1. Customer feed items for vid
        cur.execute("""
            SELECT cf.local_uuid, cf.status, cf.payload, cfe.edit_status, cfe.edited_payload
            FROM customer_feed cf
            LEFT JOIN customer_feed_edits cfe ON cfe.local_uuid = cf.local_uuid
            WHERE cf.vid = %s AND cf.local_uuid IS NOT NULL
        """, (vid,))
        for lu, st, pl, est, epl in cur.fetchall():
            effective_status = st
            if st == 'pending' and est == 'pending':
                effective_status = 'rejected_edit'
            statuses.append({
                "local_uuid": lu,
                "feed_type": "customer",
                "status": effective_status,
                "edited_payload": epl if effective_status == 'rejected_edit' else None
            })

        # 2. Payment feed items for vid
        cur.execute("""
            SELECT pfi.local_uuid, pfi.status, pfi.payload, pfe.edit_status, pfe.edited_payload
            FROM payment_feed_items pfi
            LEFT JOIN payment_feed_edits pfe ON pfe.local_uuid = pfi.local_uuid
            WHERE (pfi.payload->>'vid')::int = %s AND pfi.local_uuid IS NOT NULL
        """, (vid,))
        for lu, st, pl, est, epl in cur.fetchall():
            effective_status = st
            if st == 'pending' and est == 'pending':
                effective_status = 'rejected_edit'
            statuses.append({
                "local_uuid": lu,
                "feed_type": "payment",
                "status": effective_status,
                "edited_payload": epl if effective_status == 'rejected_edit' else None
            })

        # 3. Account closure feed items for vid
        cur.execute("""
            SELECT local_uuid, status
            FROM account_closure_feed
            WHERE vid = %s AND local_uuid IS NOT NULL
        """, (vid,))
        for lu, st in cur.fetchall():
            statuses.append({
                "local_uuid": lu,
                "feed_type": "closure",
                "status": st
            })

        # 4. Feed rejections for vid
        cur.execute("""
            SELECT local_uuid, feed_type, action_type, reason
            FROM feed_rejections
            WHERE vid = %s AND local_uuid IS NOT NULL
        """, (vid,))
        for lu, ft, at, rsn in cur.fetchall():
            statuses.append({
                "local_uuid": lu,
                "feed_type": ft,
                "status": at or "rejected_deleted",
                "reason": rsn
            })

        return jsonify({"success": True, "statuses": statuses}), 200
    except Exception as e:
        logger.error(f"Error fetching submission statuses: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@csrf.exempt
@app.route("/api/mobile/submissions/stream", methods=["GET"])
def submission_events_stream():
    token = request.headers.get("X-Mobile-Token") or request.args.get("token")
    if not token or not verify_mobile_token(token):
        return jsonify({"error": "unauthorized"}), 401

    vid = request.args.get("vid", type=int)
    if not vid:
        return jsonify({"error": "vid required"}), 400

    # Deprecated endpoint: Return immediately so legacy clients do not pin Gunicorn threads.
    # Real-time status updates are authoritatively served via /api/mobile/submissions/status.
    def stream():
        yield ": stream_deprecated\n\n"
        yield f"data: {json.dumps({'type': 'stream_deprecated', 'message': 'Please poll /api/mobile/submissions/status'})}\n\n"

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "close",
            "X-Accel-Buffering": "no"
        }
    )


# ----------------------------------------------------
# /api/mobile/customer_docs_update
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("300 per minute")
@app.route("/api/mobile/customer_docs_update", methods=["POST"])
def customer_docs_update():
    conn = None
    cur = None
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return {"error": "missing token"}, 401

        data_token = verify_mobile_token(token)
        if not data_token:
            return {"error": "invalid token"}, 401

        local_uuid = (request.form.get("local_uuid") or "").strip()
        device_id = (request.form.get("device_id") or "mobile").strip()

        cid = normalize_account_number(request.form.get("cid"))
        ano = normalize_account_number(request.form.get("ano"))
        vid = normalize_account_number(request.form.get("vid"))
        eid = normalize_account_number(request.form.get("eid"))

        if not ano or not vid or not eid:
            return jsonify({"error": "ano, vid and eid are required"}), 400

        aadhaar_front_file = request.files.get("aadhaar_front_pic")
        aadhaar_back_file = request.files.get("aadhaar_back_pic")
        house_file = request.files.get("house_photo")
        logger.info(
            "customer_docs_update request: local_uuid=%s vid=%s ano=%s eid=%s has_aadhaar_front=%s has_aadhaar_back=%s has_house=%s",
            local_uuid,
            vid,
            ano,
            eid,
            bool(aadhaar_front_file),
            bool(aadhaar_back_file),
            bool(house_file),
        )

        aadhaar_front_bytes = aadhaar_front_file.read() if aadhaar_front_file else None
        aadhaar_back_bytes = aadhaar_back_file.read() if aadhaar_back_file else None
        house_bytes = house_file.read() if house_file else None

        if not aadhaar_front_bytes and not aadhaar_back_bytes and not house_bytes:
            logger.warning(
                "customer_docs_update no documents provided: local_uuid=%s vid=%s ano=%s",
                local_uuid,
                vid,
                ano,
            )
            return jsonify({"error": "no documents provided"}), 400

        if not local_uuid:
            local_uuid = str(uuid.uuid4())

        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT cid
            FROM customer
            WHERE vid = %s AND ano = %s
            LIMIT 1
        """, (vid, ano))
        customer_row = cur.fetchone()

        resolved_cid = None
        if customer_row:
            logger.info(
                "customer_docs_update matched existing customer: local_uuid=%s vid=%s ano=%s cid=%s",
                local_uuid,
                vid,
                ano,
                customer_row[0],
            )
            resolved_cid = cid or customer_row[0]
        else:
            # Allow docs while collecting payment for customers still pending
            # in customer_feed (added on mobile, not yet accepted), or when a
            # matching payment is already in the payment feed queue.
            cur.execute("""
                SELECT feed_id
                FROM customer_feed
                WHERE vid = %s
                  AND status = 'pending'
                  AND COALESCE(
                      (payload->'payload'->>'ano')::bigint,
                      (payload->>'ano')::bigint
                  ) = %s
                ORDER BY feed_id DESC
                LIMIT 1
            """, (vid, ano))
            feed_row = cur.fetchone()

            if feed_row:
                logger.info(
                    "customer_docs_update matched pending customer_feed: local_uuid=%s vid=%s ano=%s feed_id=%s",
                    local_uuid,
                    vid,
                    ano,
                    feed_row[0],
                )
            else:
                logger.warning(
                    "customer_docs_update no customer/customer_feed match yet: local_uuid=%s vid=%s ano=%s",
                    local_uuid,
                    vid,
                    ano,
                )
                cur.execute("""
                    SELECT 1
                    FROM payment_feed_items
                    WHERE status = 'pending'
                      AND (payload->>'ano')::bigint = %s
                      AND (payload->>'vid')::bigint = %s
                    LIMIT 1
                """, (ano, vid))
                payment_row = cur.fetchone()
                if payment_row:
                    logger.info(
                        "customer_docs_update matched pending payment_feed_items: local_uuid=%s vid=%s ano=%s",
                        local_uuid,
                        vid,
                        ano,
                    )
                else:
                    logger.warning(
                        "customer_docs_update customer not found: local_uuid=%s vid=%s ano=%s",
                        local_uuid,
                        vid,
                        ano,
                    )
                    return jsonify({"error": "customer not found"}), 404

            resolved_cid = cid or None

        cur.execute("""
            INSERT INTO customer_docs_feed (
                local_uuid,
                device_id,
                eid,
                vid,
                ano,
                cid,
                aadhaar_front_pic,
                aadhaar_back_pic,
                house_photo,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
            ON CONFLICT (local_uuid) DO UPDATE SET
                device_id = EXCLUDED.device_id,
                eid = EXCLUDED.eid,
                vid = EXCLUDED.vid,
                ano = EXCLUDED.ano,
                cid = EXCLUDED.cid,
                aadhaar_front_pic = COALESCE(EXCLUDED.aadhaar_front_pic, customer_docs_feed.aadhaar_front_pic),
                aadhaar_back_pic = COALESCE(EXCLUDED.aadhaar_back_pic, customer_docs_feed.aadhaar_back_pic),
                house_photo = COALESCE(EXCLUDED.house_photo, customer_docs_feed.house_photo),
                status = 'pending',
                reviewed_by = NULL,
                reviewed_at = NULL
            WHERE customer_docs_feed.status = 'pending'
        """, (
            local_uuid,
            device_id,
            eid,
            vid,
            ano,
            resolved_cid,
            aadhaar_front_bytes,
            aadhaar_back_bytes,
            house_bytes
        ))

        conn.commit()

        audit_log(
            action="mobile_customer_docs_update",
            entity_type="customer_docs_feed",
            entity_id=resolved_cid,
            details={
                "cid": resolved_cid,
                "ano": ano,
                "eid": eid,
                "vid": vid,
                "device_id": device_id,
                "local_uuid": local_uuid,
                "aadhaar_uploaded": (aadhaar_front_bytes is not None or aadhaar_back_bytes is not None),
                "house_uploaded": house_bytes is not None
            }
        )

        return jsonify({
            "status": "ok",
            "cid": resolved_cid,
            "ano": ano,
            "vid": vid,
            "local_uuid": local_uuid
        })

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("Existing customer docs update failed")
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


# ----------------------------------------------------
# /api/mobile/payment_feed_batch
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("300 per minute")
@app.route("/api/mobile/payment_feed_batch", methods=["POST"])
def payment_feed_batch():
    conn = None
    cur = None
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return {"error": "missing token"}, 401

        data_token = verify_mobile_token(token)
        if not data_token:
            return {"error": "invalid token"}, 401

        data = request.json # type: ignore

        payments = data.get("payments", []) # type: ignore
        vid = data.get("vid") # type: ignore
        eid = data.get("eid") # type: ignore
        device_id = data.get("device_id", "mobile") # type: ignore

        if not payments:
            return jsonify({"error": "no payments provided"}), 400

        normalized_payments = []
        for p in payments:
            try:
                normalized = normalize_mobile_payment_payload(p)
                if p.get("local_uuid"):
                    normalized["local_uuid"] = p.get("local_uuid")
                normalized_payments.append(normalized)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        conn = get_pg_connection()
        cur = conn.cursor()

        total_records = len(normalized_payments)

        # insert each payment as JSON payload
        for p in normalized_payments:
            p_ano = p.get("ano")
            p_vid = p.get("vid")
            p_date = p.get("payment_date")
            local_uuid = p.get("local_uuid")
            payload = json.dumps(p)

            # Prevent duplicate payment for the same ANO, VID, and payment_date
            if p_ano is not None and p_vid is not None and p_date:
                # 1. Check if already in accepted payment table
                cur.execute("""
                    SELECT 1 FROM payment 
                    WHERE vid = %s AND ano = %s AND payment_date = %s
                    LIMIT 1
                """, (p_vid, p_ano, p_date))
                if cur.fetchone():
                    logger.warning("Skipping duplicate payment feed item (already in payment table): ano=%s, vid=%s, date=%s", p_ano, p_vid, p_date)
                    continue

                # 2. Check if already pending in payment_feed_items
                cur.execute("""
                    SELECT 1 FROM payment_feed_items
                    WHERE (payload->>'vid')::int = %s 
                      AND (payload->>'ano')::int = %s 
                      AND (payload->>'payment_date') = %s
                      AND status IN ('pending', 'approved', 'synced')
                      AND (local_uuid != %s OR local_uuid IS NULL)
                    LIMIT 1
                """, (p_vid, p_ano, str(p_date), local_uuid or ''))
                if cur.fetchone():
                    logger.warning("Skipping duplicate payment feed item (already pending in feed): ano=%s, vid=%s, date=%s", p_ano, p_vid, p_date)
                    continue

            cur.execute("""
                INSERT INTO payment_feed_items (
                    local_uuid,
                    payload,
                    status,
                    created_at
                )
                VALUES (%s,%s,'pending',NOW())
                ON CONFLICT (local_uuid) DO NOTHING
            """, (
                local_uuid,
                payload
            ))

        conn.commit()
        audit_log(
            action="mobile_payment_upload",
            entity_type="payment_feed",
            entity_id=vid,
            details={
                "eid": eid,
                "vid": vid,
                "device_id": device_id,
                "payments_received": total_records
            }
        )

        return jsonify({
            "status": "ok",
            "payments_received": total_records
        })

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("Payment feed batch processing failed")
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()

# ----------------------------------------------------
# /api/mobile/customer_feed_edit
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("60 per minute")
@app.route("/api/mobile/customer_feed_edit", methods=["POST"])
def customer_feed_edit():
    """Receive an edit request for a pending customer feed item from mobile.
    Stores the edited payload alongside the original in customer_feed_edits table.
    The /feed page shows original (strikethrough) + edited data.
    """
    conn = None
    cur = None
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return jsonify({"error": "missing token"}), 401

        data_token = verify_mobile_token(token)
        if not data_token:
            return jsonify({"error": "invalid token"}), 401

        data = request.json
        if not data:
            return jsonify({"error": "missing body"}), 400

        local_uuid = (data.get("local_uuid") or "").strip()
        edited_payload = data.get("edited_payload")
        eid = data.get("eid")
        vid = data.get("vid")

        if not local_uuid:
            return jsonify({"error": "missing local_uuid"}), 400
        if not edited_payload or not isinstance(edited_payload, dict):
            return jsonify({"error": "missing or invalid edited_payload"}), 400

        token_eid = int(data_token.get("eid", 0))
        req_eid = int(eid or 0)
        if req_eid and req_eid != token_eid:
            return jsonify({"error": "eid mismatch"}), 403

        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_feed_edits (
                edit_id SERIAL PRIMARY KEY,
                local_uuid TEXT NOT NULL,
                edited_payload JSONB NOT NULL,
                eid INTEGER,
                vid INTEGER,
                edit_status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            SELECT edit_id FROM customer_feed_edits WHERE local_uuid = %s LIMIT 1
        """, (local_uuid,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE customer_feed_edits
                SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                WHERE local_uuid = %s
            """, (json.dumps(edited_payload), local_uuid))
        else:
            cur.execute("""
                INSERT INTO customer_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW())
            """, (local_uuid, json.dumps(edited_payload), token_eid, vid))

        conn.commit()
        audit_log(
            action="mobile_customer_feed_edit",
            entity_type="customer_feed_edit",
            entity_id=local_uuid,
            details={"eid": token_eid, "vid": vid, "local_uuid": local_uuid}
        )
        return jsonify({"status": "ok"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Customer feed edit failed")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ----------------------------------------------------
# /api/mobile/payment_feed_edit
# ----------------------------------------------------
@csrf.exempt
@limiter.limit("60 per minute")
@app.route("/api/mobile/payment_feed_edit", methods=["POST"])
def payment_feed_edit():
    """Receive an edit request for a pending payment feed item from mobile.
    Stores the edited payload in payment_feed_edits table.
    The /feed page shows original (strikethrough) + edited data.
    """
    conn = None
    cur = None
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return jsonify({"error": "missing token"}), 401

        data_token = verify_mobile_token(token)
        if not data_token:
            return jsonify({"error": "invalid token"}), 401

        data = request.json
        if not data:
            return jsonify({"error": "missing body"}), 400

        local_uuid = (data.get("local_uuid") or "").strip()
        edited_payload = data.get("edited_payload")
        eid = data.get("eid")
        vid = data.get("vid")

        if not local_uuid:
            return jsonify({"error": "missing local_uuid"}), 400
        if not edited_payload or not isinstance(edited_payload, dict):
            return jsonify({"error": "missing or invalid edited_payload"}), 400

        token_eid = int(data_token.get("eid", 0))
        req_eid = int(eid or 0)
        if req_eid and req_eid != token_eid:
            return jsonify({"error": "eid mismatch"}), 403

        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payment_feed_edits (
                edit_id SERIAL PRIMARY KEY,
                local_uuid TEXT NOT NULL,
                edited_payload JSONB NOT NULL,
                eid INTEGER,
                vid INTEGER,
                edit_status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            SELECT edit_id FROM payment_feed_edits WHERE local_uuid = %s LIMIT 1
        """, (local_uuid,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE payment_feed_edits
                SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                WHERE local_uuid = %s
            """, (json.dumps(edited_payload), local_uuid))
        else:
            cur.execute("""
                INSERT INTO payment_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW())
            """, (local_uuid, json.dumps(edited_payload), token_eid, vid))

        conn.commit()
        audit_log(
            action="mobile_payment_feed_edit",
            entity_type="payment_feed_edit",
            entity_id=local_uuid,
            details={"eid": token_eid, "vid": vid, "local_uuid": local_uuid}
        )
        return jsonify({"status": "ok"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Payment feed edit failed")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ----------------------------------------------------
# /api/mobile/payment_feed_edits_debug  (temp debug)
# ----------------------------------------------------
@csrf.exempt
@app.route("/api/mobile/payment_feed_edits_debug", methods=["GET"])
def payment_feed_edits_debug():
    """Temporary debug endpoint — returns all rows in payment_feed_edits."""
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return jsonify({"error": "missing token"}), 401
    data_token = verify_mobile_token(token)
    if not data_token:
        return jsonify({"error": "invalid token"}), 401
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT edit_id, local_uuid, edited_payload, eid, vid, edit_status, created_at::text
            FROM payment_feed_edits
            ORDER BY edit_id DESC
            LIMIT 20
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return jsonify({"edits": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------
# /api/mobile/parent_customer_info
# ----------------------------------------------------
@csrf.exempt
@app.route("/api/mobile/parent_customer_info")
def mobile_parent_customer_info():
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return jsonify({"error": "missing token"}), 401

    data = verify_mobile_token(token)
    if not data:
        return jsonify({"error": "invalid token"}), 401

    pano = request.args.get("pano")
    vid = request.args.get("vid")

    if not pano or not vid:
        return jsonify({"error": "Missing pano or vid"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT name, phone_number, aadhaar_number, notes, type, period, total_amount, base_amount, cutting_amount, interest_amount, ucid, cycle_number
            FROM v_all_customers
            WHERE vid = %s AND ano = %s
            ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
            LIMIT 1
        """, (int(vid), int(pano)))
        row = cur.fetchone()
        if not row:
            return jsonify({"found": False})
        
        return jsonify({
            "found": True,
            "name": row[0] or "",
            "phone_number": row[1] or "",
            "aadhaar_number": row[2] or "",
            "notes": row[3] or "",
            "type": row[4] or "",
            "period": row[5] or 0,
            "total_amount": row[6] or 0.0,
            "base_amount": row[7] or 0.0,
            "cutting_amount": row[8] or 0.0,
            "interest_amount": row[9] or 0.0,
            "ucid": row[10] if len(row) > 10 and row[10] is not None else None,
            "cycle_number": row[11] if len(row) > 11 and row[11] is not None else 1
        })
    except Exception as e:
        logger.error(f"Error in mobile_parent_customer_info: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------
# /api/mobile/reset_database
# ----------------------------------------------------
@csrf.exempt
@app.route("/api/mobile/reset_database", methods=["POST"])
def reset_database():
    try:
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return {"error": "missing token"}, 401

        data = verify_mobile_token(token)
        if not data:
            return {"error": "invalid token"}, 401

        eid = data.get("eid")

        user_id = data.get("user_id")

        # ðŸ” Validate user + employee mapping and active status
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.is_active, e.level
            FROM users u
            JOIN employee e ON e.eid = u.employee_id
            WHERE u.id = %s AND u.employee_id = %s
        """, (user_id, eid))

        user_row = cur.fetchone()

        if not user_row:
            return {"error": "invalid user mapping"}, 401

        is_active, level = user_row

        if not is_active:
            return {"error": "user inactive"}, 403

        if level not in ["admin", "mgmt"]:
            return {"error": "unauthorized"}, 403

        # ðŸš¨ DELETE ALL DATA (SAFE ORDER USING TRUNCATE CASCADE)
        cur.execute("""
            TRUNCATE TABLE
                payment,
                closed_cust_payment,
                customer,
                closed_cust_account,
                customer_docs,
                customer_docs_feed,
                customer_feed,
                payment_feed_items,
                user_devices,
                user_village_access,
                users,
                village,
                employee
            RESTART IDENTITY CASCADE
        """)
        
        conn.commit()
        audit_log(
            action="reset_database",
            entity_type="system",
            entity_id="full_database",
            details={
                "performed_by_user_id": user_id,
                "performed_by_eid": eid,
                "level": level
            }
        )

        return {"success": True, "message": "All data deleted successfully"}

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return {"error": str(e)}, 500

    finally:
        try:
            if cur:
                cur.close()

            if conn:
                conn.close()
        except:
            pass
# ----------------------------------------------------
# ROUTES - postgre
# ----------------------------------------------------

def get_dashboard_totals(vid):
    if not vid:
        return {
            "total_customers": 0,
            "sum_amt": 0.0,
            "sum_pamt": 0.0,
            "sum_bamt": 0.0,
        }
    conn = get_pg_connection()
    cur = conn.cursor()

    if vid:
        cur.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(c.total_amount), 0),
                COALESCE(SUM(c.paid_amount), 0),
                COALESCE(SUM(c.balance_amount), 0)
            FROM customer c
            WHERE c.vid = %s
        """, (vid,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        row = (0, 0, 0, 0)

    return {
        "total_customers": int(row[0]),
        "sum_amt": float(row[1]),
        "sum_pamt": float(row[2]),
        "sum_bamt": float(row[3]),
    }

# ----------------------------------------------------
# SERVER TELEMETRY & INFRASTRUCTURE MONITORING
# ----------------------------------------------------
TELEMETRY_SECRET_KEY = os.environ.get("TELEMETRY_SECRET_KEY") or os.environ.get("MOBILE_QUEUE_HMAC_SECRET") or os.environ.get("SECRET_KEY", "sdfinance-telemetry-default-key-2026")

def format_uptime(seconds):
    if not seconds or seconds < 0:
        return "0m"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def format_duration(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h {minutes % 60}m"
    days = int(hours // 24)
    return f"{days}d {hours % 24}h"

def ensure_server_telemetry_table(cur):
    """Ensure server_telemetry table exists and has default records."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS server_telemetry (
            server_id VARCHAR(64) PRIMARY KEY,
            server_name VARCHAR(128) NOT NULL,
            server_role VARCHAR(64) DEFAULT 'primary',
            location VARCHAR(128) DEFAULT 'Remote Office 1',
            hostname VARCHAR(128),
            ip_address VARCHAR(64),
            tailscale_ip VARCHAR(64),
            status VARCHAR(32) DEFAULT 'unknown',
            cpu_percent REAL DEFAULT 0.0,
            cpu_cores INTEGER DEFAULT 1,
            load_avg VARCHAR(64) DEFAULT '0.00, 0.00, 0.00',
            memory_percent REAL DEFAULT 0.0,
            memory_used_gb REAL DEFAULT 0.0,
            memory_total_gb REAL DEFAULT 0.0,
            disk_percent REAL DEFAULT 0.0,
            disk_used_gb REAL DEFAULT 0.0,
            disk_free_gb REAL DEFAULT 0.0,
            disk_total_gb REAL DEFAULT 0.0,
            uptime_seconds BIGINT DEFAULT 0,
            boot_time TIMESTAMPTZ,
            services JSONB DEFAULT '{}'::jsonb,
            power_status VARCHAR(64) DEFAULT 'AC Main Normal',
            last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("SELECT COUNT(*) FROM server_telemetry")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("""
            INSERT INTO server_telemetry 
            (server_id, server_name, server_role, location, status, disk_percent, disk_free_gb, disk_total_gb, memory_percent, memory_used_gb, memory_total_gb, cpu_percent, uptime_seconds, services, last_heartbeat)
            VALUES 
            ('main_server', 'Primary Core Server (sivadurga.in)', 'Core Web & Database', 'Primary Site', 'offline', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, '{"sd_app": "standby", "postgresql": "standby", "cloudflared": "standby"}'::jsonb, NOW() - INTERVAL '15 minutes'),
            ('backup_server', 'Secondary Disaster Recovery Machine', 'Database Replica & Cold Backup', 'Secondary Site', 'offline', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, '{"replication": "standby", "backup_agent": "standby"}'::jsonb, NOW() - INTERVAL '15 minutes')
        """)

_telemetry_cache = {}

def _get_default_telemetry():
    return [
        {
            "server_id": "main_server",
            "server_name": "Primary Core Server (sivadurga.in)",
            "server_role": "Core Web & Database",
            "location": "Primary Site",
            "hostname": "ubuntu-sivadurga",
            "ip_address": "192.168.1.48",
            "tailscale_ip": "100.110.107.116",
            "status": "offline",
            "status_msg": "Awaiting initial agent telemetry heartbeat",
            "cpu_percent": 0.0,
            "cpu_cores": 4,
            "load_avg": "0.0, 0.0, 0.0",
            "memory_percent": 0.0,
            "memory_used_gb": 0.0,
            "memory_total_gb": 16.0,
            "disk_percent": 0.0,
            "disk_used_gb": 0.0,
            "disk_free_gb": 0.0,
            "disk_total_gb": 500.0,
            "uptime_seconds": 0,
            "uptime_formatted": "0m",
            "boot_time": "N/A",
            "services": {"sd_app": "standby", "postgresql": "standby", "cloudflared": "standby"},
            "power_status": "Normal AC",
            "last_heartbeat": "Never",
            "seconds_since_ping": 999999,
            "is_active": False
        },
        {
            "server_id": "backup_server",
            "server_name": "Secondary Disaster Recovery Machine",
            "server_role": "Database Replica & Standby",
            "location": "Secondary Site",
            "hostname": "ubuntu-backup",
            "ip_address": "192.168.1.213",
            "tailscale_ip": "100.x.x.x",
            "status": "offline",
            "status_msg": "Awaiting initial agent telemetry heartbeat",
            "cpu_percent": 0.0,
            "cpu_cores": 4,
            "load_avg": "0.0, 0.0, 0.0",
            "memory_percent": 0.0,
            "memory_used_gb": 0.0,
            "memory_total_gb": 16.0,
            "disk_percent": 0.0,
            "disk_used_gb": 0.0,
            "disk_free_gb": 0.0,
            "disk_total_gb": 500.0,
            "uptime_seconds": 0,
            "uptime_formatted": "0m",
            "boot_time": "N/A",
            "services": {"replication": "standby", "backup_agent": "standby"},
            "power_status": "Normal AC",
            "last_heartbeat": "Never",
            "seconds_since_ping": 999999,
            "is_active": False
        }
    ]

def get_fleet_telemetry(cur=None):
    global _telemetry_cache
    close_conn = False
    if cur is None:
        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            close_conn = True
        except Exception as e:
            logger.error(f"[Telemetry] DB connection failed for telemetry: {e}")
            return list(_telemetry_cache.values()) if _telemetry_cache else _get_default_telemetry()
    try:
        ensure_server_telemetry_table(cur)
        cur.execute("""
            SELECT server_id, server_name, server_role, location, hostname, 
                   ip_address, tailscale_ip, status, cpu_percent, cpu_cores, 
                   load_avg, memory_percent, memory_used_gb, memory_total_gb, 
                   disk_percent, disk_used_gb, disk_free_gb, disk_total_gb, 
                   uptime_seconds, boot_time, services, power_status, 
                   last_heartbeat, updated_at
            FROM server_telemetry
            ORDER BY CASE WHEN server_id = 'main_server' THEN 1 ELSE 2 END
        """)
        rows = cur.fetchall()
        now = datetime.now(timezone.utc)
        results = []
        for r in rows:
            last_hb = r[22]
            if last_hb and last_hb.tzinfo is None:
                last_hb = last_hb.replace(tzinfo=timezone.utc)
            
            diff_seconds = (now - last_hb).total_seconds() if last_hb else 999999
            
            # Determine health status based on thresholds
            if diff_seconds > 120:
                calc_status = "offline"
                status_msg = f"Offline ({format_duration(diff_seconds)} since ping - Power/ISP out)"
            elif (r[14] or 0) >= 90:
                calc_status = "critical"
                status_msg = f"CRITICAL: Storage at {r[14]:.1f}%! Immediate crash risk"
            elif (r[14] or 0) >= 80 or (r[8] or 0) >= 90:
                calc_status = "warning"
                status_msg = "Warning: High Resource Utilization"
            else:
                calc_status = "healthy"
                status_msg = "Optimal & Active"

            uptime_formatted = format_uptime(r[18])
            boot_formatted = r[19].strftime("%Y-%m-%d %H:%M:%S") if r[19] else "N/A"
            last_hb_formatted = last_hb.strftime("%Y-%m-%d %H:%M:%S UTC") if last_hb else "Never"

            services_data = r[20] if isinstance(r[20], dict) else {}
            if isinstance(r[20], str):
                try:
                    services_data = json.loads(r[20])
                except Exception:
                    services_data = {}

            item = {
                "server_id": r[0],
                "server_name": r[1],
                "server_role": r[2],
                "location": r[3],
                "hostname": r[4] or "Unregistered Host",
                "ip_address": r[5] or "N/A",
                "tailscale_ip": r[6] or "N/A",
                "status": calc_status,
                "status_msg": status_msg,
                "cpu_percent": round(float(r[8] or 0), 1),
                "cpu_cores": int(r[9] or 1),
                "load_avg": r[10] or "0.0, 0.0, 0.0",
                "memory_percent": round(float(r[11] or 0), 1),
                "memory_used_gb": round(float(r[12] or 0), 2),
                "memory_total_gb": round(float(r[13] or 0), 2),
                "disk_percent": round(float(r[14] or 0), 1),
                "disk_used_gb": round(float(r[15] or 0), 2),
                "disk_free_gb": round(float(r[16] or 0), 2),
                "disk_total_gb": round(float(r[17] or 0), 2),
                "uptime_seconds": int(r[18] or 0),
                "uptime_formatted": uptime_formatted,
                "boot_time": boot_formatted,
                "services": services_data,
                "power_status": r[21] or "Normal AC",
                "last_heartbeat": last_hb_formatted,
                "seconds_since_ping": int(diff_seconds),
                "is_active": diff_seconds <= 120
            }
            results.append(item)
            _telemetry_cache[r[0]] = item
        return results
    except Exception as e:
        logger.error(f"[Telemetry] Error fetching telemetry: {e}")
        return list(_telemetry_cache.values()) if _telemetry_cache else _get_default_telemetry()
    finally:
        if close_conn and cur:
            cur.close()
            conn.close()

@app.route("/admin_control")
@login_required
@admin_required
def admin_control():
    conn = None
    cur = None
    telemetry_servers = []
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        telemetry_servers = get_fleet_telemetry(cur)
    except Exception as e:
        logger.error(f"[admin_control] DB query error: {e}")
        if not telemetry_servers:
            telemetry_servers = get_fleet_telemetry(None)
    finally:
        if cur: cur.close()
        if conn: conn.close()

    return render_template(
        "admin_control.html", 
        telemetry_servers=telemetry_servers,
        telemetry_secret_key=TELEMETRY_SECRET_KEY
    )

@csrf.exempt
@app.route("/api/v1/telemetry/heartbeat", methods=["POST"])
def ingest_telemetry():
    server_id = request.headers.get("X-Server-Id")
    timestamp = request.headers.get("X-Timestamp")
    signature = request.headers.get("X-Signature")

    if not server_id or not timestamp or not signature:
        return jsonify({"error": "Missing security authentication headers (X-Server-Id, X-Timestamp, X-Signature)"}), 401

    try:
        ts = int(timestamp)
        now_ts = int(pytime.time())
        if abs(now_ts - ts) > 300:
            return jsonify({"error": "Timestamp outside acceptable 5-minute replay window"}), 401
    except ValueError:
        return jsonify({"error": "Invalid timestamp format"}), 400

    raw_body = request.get_data(as_text=True)
    expected_msg = f"{timestamp}:{raw_body}".encode("utf-8")
    expected_sig = hmac.new(
        TELEMETRY_SECRET_KEY.encode("utf-8"),
        expected_msg,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return jsonify({"error": "Invalid HMAC-SHA256 signature - rejected"}), 403

    data = request.json or {}
    conn = None
    cur = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        ensure_server_telemetry_table(cur)
        cur.execute("""
            INSERT INTO server_telemetry (
                server_id, server_name, server_role, location, hostname,
                ip_address, tailscale_ip, status, cpu_percent, cpu_cores,
                load_avg, memory_percent, memory_used_gb, memory_total_gb,
                disk_percent, disk_used_gb, disk_free_gb, disk_total_gb,
                uptime_seconds, boot_time, services, power_status,
                last_heartbeat, updated_at
            ) VALUES (
                %(server_id)s, %(server_name)s, %(server_role)s, %(location)s, %(hostname)s,
                %(ip_address)s, %(tailscale_ip)s, %(status)s, %(cpu_percent)s, %(cpu_cores)s,
                %(load_avg)s, %(memory_percent)s, %(memory_used_gb)s, %(memory_total_gb)s,
                %(disk_percent)s, %(disk_used_gb)s, %(disk_free_gb)s, %(disk_total_gb)s,
                %(uptime_seconds)s, %(boot_time)s, %(services)s, %(power_status)s,
                NOW(), NOW()
            )
            ON CONFLICT (server_id) DO UPDATE SET
                server_name = COALESCE(EXCLUDED.server_name, server_telemetry.server_name),
                server_role = COALESCE(EXCLUDED.server_role, server_telemetry.server_role),
                location = COALESCE(EXCLUDED.location, server_telemetry.location),
                hostname = EXCLUDED.hostname,
                ip_address = EXCLUDED.ip_address,
                tailscale_ip = EXCLUDED.tailscale_ip,
                status = EXCLUDED.status,
                cpu_percent = EXCLUDED.cpu_percent,
                cpu_cores = EXCLUDED.cpu_cores,
                load_avg = EXCLUDED.load_avg,
                memory_percent = EXCLUDED.memory_percent,
                memory_used_gb = EXCLUDED.memory_used_gb,
                memory_total_gb = EXCLUDED.memory_total_gb,
                disk_percent = EXCLUDED.disk_percent,
                disk_used_gb = EXCLUDED.disk_used_gb,
                disk_free_gb = EXCLUDED.disk_free_gb,
                disk_total_gb = EXCLUDED.disk_total_gb,
                uptime_seconds = EXCLUDED.uptime_seconds,
                boot_time = EXCLUDED.boot_time,
                services = EXCLUDED.services,
                power_status = EXCLUDED.power_status,
                last_heartbeat = NOW(),
                updated_at = NOW()
        """, {
            "server_id": server_id,
            "server_name": data.get("server_name", "Remote Node"),
            "server_role": data.get("server_role", "Standby"),
            "location": data.get("location", "Remote Site"),
            "hostname": data.get("hostname", "Unknown"),
            "ip_address": data.get("ip_address", request.remote_addr),
            "tailscale_ip": data.get("tailscale_ip", ""),
            "status": "online",
            "cpu_percent": float(data.get("cpu_percent", 0)),
            "cpu_cores": int(data.get("cpu_cores", 1)),
            "load_avg": data.get("load_avg", "0.0, 0.0, 0.0"),
            "memory_percent": float(data.get("memory_percent", 0)),
            "memory_used_gb": float(data.get("memory_used_gb", 0)),
            "memory_total_gb": float(data.get("memory_total_gb", 0)),
            "disk_percent": float(data.get("disk_percent", 0)),
            "disk_used_gb": float(data.get("disk_used_gb", 0)),
            "disk_free_gb": float(data.get("disk_free_gb", 0)),
            "disk_total_gb": float(data.get("disk_total_gb", 0)),
            "uptime_seconds": int(data.get("uptime_seconds", 0)),
            "boot_time": data.get("boot_time"),
            "services": json.dumps(data.get("services", {})),
            "power_status": data.get("power_status", "Normal AC"),
        })
        conn.commit()
        return jsonify({"success": True, "server_id": server_id, "status": "heartbeat_recorded", "timestamp": now_ts})
    except Exception as e:
        logger.error(f"[Telemetry] Ingest error: {e}")
        return jsonify({"error": "Failed to record telemetry", "details": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/api/v1/telemetry/status")
@login_required
@admin_required
def telemetry_status_api():
    servers = get_fleet_telemetry()
    return jsonify({
        "success": True,
        "servers": servers,
        "checked_at": datetime.now(timezone.utc).isoformat()
    })

def get_customer_analytics(vid):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE CURRENT_DATE - start_date >= 0 AND CURRENT_DATE - start_date < 3) as today_count,
                COALESCE(SUM(total_amount) FILTER (WHERE CURRENT_DATE - start_date >= 0 AND CURRENT_DATE - start_date < 3), 0) as today_sum,
                COUNT(*) FILTER (WHERE CURRENT_DATE - start_date >= 0 AND CURRENT_DATE - start_date < 8) as week_count,
                COALESCE(SUM(total_amount) FILTER (WHERE CURRENT_DATE - start_date >= 0 AND CURRENT_DATE - start_date < 8), 0) as week_sum,
                COUNT(*) FILTER (WHERE CURRENT_DATE - start_date >= 0 AND CURRENT_DATE - start_date < 31) as month_count,
                COALESCE(SUM(total_amount) FILTER (WHERE CURRENT_DATE - start_date >= 0 AND CURRENT_DATE - start_date < 31), 0) as month_sum
            FROM (
                SELECT start_date, total_amount, vid FROM customer
                UNION ALL
                SELECT start_date, total_amount, vid FROM closed_cust_account
            ) c
            WHERE vid = %s
        """, (vid,))
        row = cur.fetchone()
        if row:
            t_count, t_sum, w_count, w_sum, m_count, m_sum = row
            return {
                "today": f"{t_count} - {int(round(t_sum)):,}",
                "week": f"{w_count} - {int(round(w_sum)):,}",
                "month": f"{m_count} - {int(round(m_sum)):,}"
            }
        return {"today": "0 - 0", "week": "0 - 0", "month": "0 - 0"}
    except Exception as e:
        logger.error(f"Error fetching customer analytics: {e}")
        return {"today": "0 - 0", "week": "0 - 0", "month": "0 - 0"}
    finally:
        cur.close()
        conn.close()

@app.route("/add_customer", methods=["GET", "POST"])
@login_required
def add_customer():
    vid = session.get("vid")
    eid = session.get("eid")

    if not vid:
        return redirect("/dashboard")

    if request.method == "POST":
        data = request.form

        ano = int(data["ano"])
        if ano_exists(ano, vid):
            return jsonify(error="Account number already exists"), 400

        fdt = parse_date_input(data["start_date"])
        period = int(data["period"])
        loan_type = data["type"]

        if loan_type == "M":
            tdt = fdt + relativedelta(months=period)# type: ignore
        elif loan_type == "D":
            tdt = fdt + timedelta(days=period)# type: ignore
        else:
            tdt = fdt + timedelta(weeks=period)# type: ignore

        raw_total = data.get("total_amount", "").strip()
        if not raw_total:
            return jsonify(error="Total amount is required"), 400
        try:
            total_amount = float(raw_total)
        except (ValueError, TypeError):
            return jsonify(error="Total amount must be a valid number"), 400
        installment_amount = round_curr(total_amount / period)
        paid_amount = 0.0
        balance_amount = total_amount
        payload = {
            "ano": ano,
            "name": data["name"].strip(),
            "pano": data.get("pano") or None,
            "phone_number": (data.get("phone_number") or "").strip() or None,
            "vid": vid,
            "eid": eid,
            "start_date": fdt,
            "end_date": tdt,
            "total_amount": total_amount,
            "base_amount": float(data.get("base_amount") or 0.0),
            "cutting_amount": float(data.get("cutting_amount") or 0.0),
            "interest_amount": float(data.get("interest_amount") or 0.0),
            "paid_amount": paid_amount,     
            "balance_amount": balance_amount,
            "installment_amount": installment_amount,
            "type": loan_type,
            "period": period,
            "aadhaar_number": data.get("aadhaar_number") or None,
            "notes": data.get("notes") or None,
            "latitude": data.get("latitude") or None,
            "longitude": data.get("longitude") or None,
        }

        cid = insert_customer(payload)
        
        audit_log(
            action="create_customer",
            entity_type="customer",
            entity_id=ano,
            details={
                "vid": vid,
                "eid": eid,
                "name": data["name"]
            }
        )

        return jsonify({
            "message": "Customer added successfully",
            "highest_ano": get_highest_ano_by_vid(vid),
            "new_ano": ano,
            "cid": cid,
            "analytics": get_customer_analytics(vid)
        })

    # GET
    # Fetch interest_rate and cutting_rate for the current village
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT interest_rate, cutting_rate FROM village WHERE vid = %s", (vid,))
        row = cur.fetchone()
        interest_rate = float(row[0]) if row and row[0] is not None else 0.0
        cutting_rate = float(row[1]) if row and row[1] is not None else 0.0
    except Exception as e:
        logger.error(f"Error fetching village rates in add_customer: {e}")
        interest_rate = 0.0
        cutting_rate = 0.0
    finally:
        cur.close()
        conn.close()

    return render_template(
        "add_customer.html",
        village_name=session.get("village_name"),
        employee_name=session.get("employee_name"),
        interest_rate=interest_rate,
        cutting_rate=cutting_rate
    )

@app.route("/api/add_customer/metadata")
@login_required
def api_add_customer_metadata():
    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="No active village context"), 400

    try:
        highest_ano = get_highest_ano_by_vid(vid)
        analytics = get_customer_analytics(vid)
        return jsonify(
            success=True,
            highest_ano=highest_ano,
            analytics=analytics
        )
    except Exception as e:
        logger.error(f"Error fetching add customer metadata: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route("/api/customer/check_aadhaar")
@login_required
def api_check_aadhaar():
    raw_aadhaar = request.args.get("aadhaar", "").strip()
    clean_aadhaar = "".join(ch for ch in raw_aadhaar if ch.isdigit())

    if len(clean_aadhaar) != 12:
        return jsonify({
            "duplicate": False,
            "count": 0,
            "aadhaar": clean_aadhaar,
            "accounts": []
        })

    exclude_ano = request.args.get("exclude_ano")
    exclude_vid = request.args.get("exclude_vid")

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT 
                c.cid,
                c.vid,
                COALESCE(v.village_name, 'Village ' || c.vid::text) AS village_name,
                c.ano,
                c.name,
                c.phone_number,
                c.start_date,
                c.end_date,
                c.total_amount,
                c.balance_amount,
                COALESCE(c.status, 'open') AS status
            FROM customer c
            LEFT JOIN village v ON v.vid = c.vid
            WHERE REPLACE(REPLACE(COALESCE(c.aadhaar_number, ''), ' ', ''), '-', '') = %s
        """
        params = [clean_aadhaar]
        if exclude_ano and exclude_vid:
            query += " AND NOT (c.ano = %s AND c.vid = %s)"
            params.extend([int(exclude_ano), int(exclude_vid)])

        query += """
            UNION ALL
            SELECT 
                ca.cid,
                ca.vid,
                COALESCE(v.village_name, 'Village ' || ca.vid::text) AS village_name,
                ca.ano,
                ca.name,
                ca.phone_number,
                ca.start_date,
                ca.end_date,
                ca.total_amount,
                ca.balance_amount,
                'closed' AS status
            FROM closed_cust_account ca
            LEFT JOIN village v ON v.vid = ca.vid
            WHERE REPLACE(REPLACE(COALESCE(ca.aadhaar_number, ''), ' ', ''), '-', '') = %s
        """
        params.append(clean_aadhaar)
        if exclude_ano and exclude_vid:
            query += " AND NOT (ca.ano = %s AND ca.vid = %s)"
            params.extend([int(exclude_ano), int(exclude_vid)])

        query += " ORDER BY cid DESC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        accounts = []
        for r in rows:
            accounts.append({
                "cid": r[0],
                "vid": r[1],
                "village_name": r[2] or f"Village {r[1]}",
                "ano": r[3],
                "name": r[4] or "Unnamed",
                "phone_number": r[5] or "",
                "start_date": format_date_display(str(r[6])) if r[6] else "",
                "end_date": format_date_display(str(r[7])) if r[7] else "",
                "total_amount": float(r[8] or 0),
                "balance_amount": float(r[9] or 0),
                "status": r[10] or "open"
            })

        return jsonify({
            "duplicate": len(accounts) > 0,
            "count": len(accounts),
            "aadhaar": clean_aadhaar,
            "accounts": accounts
        })
    except Exception as e:
        logger.error(f"Error checking duplicate aadhaar: {e}")
        return jsonify({"duplicate": False, "count": 0, "error": str(e), "accounts": []}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/view_customers")
@login_required
def view_customers():
    vid = session.get("vid")

    # 🚨 Enforce context
    if not vid:
        flash("Please select Village from Dashboard first", "warning")
        return redirect(url_for("dashboard"))

    mode = request.args.get("mode", "active")  # default = active

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT interest_rate, cutting_rate FROM village WHERE vid = %s", (vid,))
        rates_row = cur.fetchone()
        interest_rate = float(rates_row[0]) if rates_row and rates_row[0] is not None else 0.0
        cutting_rate = float(rates_row[1]) if rates_row and rates_row[1] is not None else 0.0
    except Exception as e:
        logger.error(f"Error fetching rates in view_customers: {e}")
        interest_rate = 0.0
        cutting_rate = 0.0
    finally:
        cur.close()
        conn.close()

    return render_template(
        "view_customers.html",
        interest_rate=interest_rate,
        cutting_rate=cutting_rate,
        current_mode=mode
    )

@app.route("/api/view_customers/data")
@login_required
def api_view_customers_data():
    vid = session.get("vid")
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])

    if not vid:
        return jsonify(success=False, error="No active village context"), 400

    if user_level not in ["admin", "mgmt"] and vid not in allowed_villages:
        return jsonify(success=False, error="Unauthorized village access"), 403

    mode = request.args.get("mode", "active")

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Fetch village rates
        cur.execute("SELECT interest_rate, cutting_rate FROM village WHERE vid = %s", (vid,))
        rates_row = cur.fetchone()
        interest_rate = float(rates_row[0]) if rates_row and rates_row[0] is not None else 0.0
        cutting_rate = float(rates_row[1]) if rates_row and rates_row[1] is not None else 0.0
        # Active Stats
        cur.execute("""
            SELECT 
                COALESCE(COUNT(*), 0),
                COALESCE(SUM(balance_amount), 0.0)
            FROM customer
            WHERE vid = %s
        """, (vid,))
        active_count, active_bal_sum = cur.fetchone()

        # Closed Stats
        cur.execute("""
            SELECT 
                COALESCE(COUNT(*) FILTER (WHERE balance_amount > 0), 0),
                COALESCE(SUM(balance_amount) FILTER (WHERE balance_amount > 0), 0.0),
                COALESCE(COUNT(*) FILTER (WHERE balance_amount <= 0), 0)
            FROM closed_cust_account
            WHERE vid = %s
        """, (vid,))
        defaulted_count, defaulted_bal_sum, closed_count = cur.fetchone()

        # Average Ratings
        cur.execute("""
            SELECT COALESCE(AVG(customer_rating), 100.0)
            FROM customer
            WHERE vid = %s
        """, (vid,))
        active_avg_score = float(cur.fetchone()[0])

        cur.execute("""
            SELECT COALESCE(AVG(customer_rating), 100.0)
            FROM (
                SELECT customer_rating FROM closed_cust_account WHERE vid = %s AND balance_amount > 0
                UNION ALL
                SELECT customer_rating FROM customer WHERE vid = %s
            ) defaulted_group
        """, (vid, vid))
        defaulted_avg_score = float(cur.fetchone()[0])

        cur.execute("""
            SELECT COALESCE(AVG(customer_rating), 100.0)
            FROM v_all_customers
            WHERE vid = %s
        """, (vid,))
        complete_avg_score = float(cur.fetchone()[0])

        # Fetch Table Rows based on mode
        if mode == "closed":
            cur.execute("""
                SELECT
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, pano, created_at, aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date, base_amount, cutting_amount, interest_amount,
                    interest_discount, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND record_tier = 'closed'
                ORDER BY ano DESC
            """, (vid,))
        elif mode == "historic":
            cur.execute("""
                SELECT
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, pano, created_at, aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date, base_amount, cutting_amount, interest_amount,
                    interest_discount, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND record_tier = 'historic'
                ORDER BY ano DESC
            """, (vid,))
        elif mode == "yearly":
            cur.execute("""
                SELECT
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, pano, created_at, aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date, base_amount, cutting_amount, interest_amount,
                    interest_discount, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND LOWER(TRIM(status)) NOT IN ('written_off', 'closed') AND balance_amount > 0
                ORDER BY ano DESC
            """, (vid,))
        else:  # default "active"
            cur.execute("""
                SELECT
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, pano, created_at, aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date, base_amount, cutting_amount, interest_amount,
                    interest_discount, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND record_tier = 'active'
                ORDER BY ano DESC
            """, (vid,))

        rows = cur.fetchall()
        headers = [desc[0] for desc in cur.description]
        data = [dict(zip(headers, r)) for r in rows]
        data = format_customer_ratings_with_trends(cur, data)

        # Format dates
        for d in data:
            for key in ['start_date', 'end_date', 'created_at', 'freeze_date', 'updated_at']:
                if key in d and d[key]:
                    val = d[key]
                    if isinstance(val, (date, datetime)):
                        d[f"{key}_raw"] = val.strftime("%Y-%m-%d")
                    elif isinstance(val, str):
                        parsed = parse_date_input(val)
                        d[f"{key}_raw"] = parsed.strftime("%Y-%m-%d") if parsed else val
                    else:
                        d[f"{key}_raw"] = str(val)
                    d[key] = format_date_display(d[key])
                else:
                    d[f"{key}_raw"] = ""

        # Global stats list across all tiers via unified view
        cur.execute("""
            SELECT cid, ano, name, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, period, pano, phone_number, record_tier AS source, COALESCE(interest_discount, 0.00) AS interest_discount,
                   COALESCE(base_amount, 0.00) AS base_amount, COALESCE(cutting_amount, 0.00) AS cutting_amount, COALESCE(interest_amount, 0.00) AS interest_amount
            FROM v_all_customers WHERE vid = %s
            ORDER BY ano DESC
        """, (vid,))
        all_stats_rows = cur.fetchall()
        all_cols = ['cid', 'ano', 'name', 'start_date', 'end_date', 'total_amount', 'paid_amount', 'balance_amount', 'installment_amount', 'period', 'pano', 'phone_number', 'source', 'interest_discount', 'base_amount', 'cutting_amount', 'interest_amount']
        all_stats_dicts = [dict(zip(all_cols, r)) for r in all_stats_rows]
        all_stats_list = format_customer_ratings_with_trends(cur, all_stats_dicts)

        def make_serializable(val):
            if isinstance(val, Decimal):
                return float(val)
            if isinstance(val, (datetime, date)):
                return val.isoformat()
            if isinstance(val, dict):
                return {k: make_serializable(v) for k, v in val.items()}
            if isinstance(val, list):
                return [make_serializable(v) for v in val]
            return val

        serializable_data = make_serializable(data)
        serializable_stats = make_serializable(all_stats_list)

        return jsonify(
            success=True,
            data=serializable_data,
            all_customers_stats=serializable_stats,
            interest_rate=interest_rate,
            cutting_rate=cutting_rate,
            summary={
                "active_customers": active_count,
                "defaulted_customers": defaulted_count,
                "closed_customers": closed_count,
                "active_balance_amount": float(active_bal_sum) if active_bal_sum is not None else 0.0,
                "defaulted_balance_amount": float(defaulted_bal_sum) if defaulted_bal_sum is not None else 0.0,
                "active_avg_score": active_avg_score,
                "defaulted_avg_score": defaulted_avg_score,
                "complete_avg_score": complete_avg_score,
            }
        )
    except Exception as e:
        logger.error(f"Error fetching view customers data: {e}")
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/balance_report")
@login_required
def api_balance_report():
    vid = session.get("vid")
    if not vid:
        return jsonify({"success": False, "error": "No village context selected"})
    
    conn = get_pg_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT
                cid,
                ano,
                name,
                vid,
                start_date,
                end_date,
                total_amount,
                paid_amount,
                balance_amount,
                installment_amount,
                type,
                period,
                pano,
                created_at,
                aadhaar_number,
                notes,
                latitude,
                longitude,
                eid,
                phone_number,
                CASE WHEN record_tier = 'active' THEN 'active' ELSE status END AS status,
                customer_rating,
                final_frozen_rating,
                final_risk_level,
                freeze_date,
                base_amount,
                cutting_amount,
                interest_amount,
                interest_discount,
                record_tier,
                ucid,
                cycle_number
            FROM v_all_customers
            WHERE vid = %s AND balance_amount > 0
            ORDER BY ano DESC
        """, (vid,))
        
        rows = cur.fetchall()
        headers = [desc[0] for desc in cur.description]
        data = [dict(zip(headers, r)) for r in rows]
        
        data = format_customer_ratings_with_trends(cur, data)
        
        serialized = []
        for c in data:
            serialized.append({
                "cid": c.get("cid"),
                "ano": str(c.get("ano")).strip() if c.get("ano") is not None else "",
                "name": c.get("name"),
                "vid": c.get("vid"),
                "start_date": c.get("start_date").isoformat() if hasattr(c.get("start_date"), "isoformat") else str(c.get("start_date")) if c.get("start_date") else None,
                "end_date": c.get("end_date").isoformat() if hasattr(c.get("end_date"), "isoformat") else str(c.get("end_date")) if c.get("end_date") else None,
                "total_amount": float(c.get("total_amount") or 0),
                "paid_amount": float(c.get("paid_amount") or 0),
                "balance_amount": float(c.get("balance_amount") or 0),
                "installment_amount": float(c.get("installment_amount") or 0),
                "type": c.get("type"),
                "period": c.get("period"),
                "pano": str(c.get("pano")).strip() if c.get("pano") is not None else "",
                "created_at": c.get("created_at").isoformat() if hasattr(c.get("created_at"), "isoformat") else str(c.get("created_at")) if c.get("created_at") else None,
                "aadhaar_number": c.get("aadhaar_number"),
                "notes": c.get("notes"),
                "latitude": c.get("latitude"),
                "longitude": c.get("longitude"),
                "eid": c.get("eid"),
                "phone_number": c.get("phone_number"),
                "status": c.get("status"),
                "customer_rating": c.get("customer_rating"),
                "final_frozen_rating": float(c.get("final_frozen_rating")) if c.get("final_frozen_rating") is not None else None,
                "final_risk_level": c.get("final_risk_level"),
                "freeze_date": c.get("freeze_date").isoformat() if hasattr(c.get("freeze_date"), "isoformat") else str(c.get("freeze_date")) if c.get("freeze_date") else None,
                "base_amount": float(c.get("base_amount") or 0.0),
                "cutting_amount": float(c.get("cutting_amount") or 0.0),
                "interest_amount": float(c.get("interest_amount") or 0.0),
                "interest_discount": float(c.get("interest_discount") or 0.0),
                "source": c.get("record_tier"),
                "ucid": c.get("ucid"),
                "cycle_number": c.get("cycle_number")
            })
            
        return jsonify({"success": True, "customers": serialized})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        cur.close()
        conn.close()

@app.route("/check_ano_exists")
@login_required
def check_ano_exists():
    ano = request.args.get("ano", "").strip()
    vid = session.get("vid")

    if not ano or not vid:
        return jsonify({"exists": False})

    exists = customer_exists_by_ano_and_vid(ano, vid)
    return jsonify({"exists": exists})

@app.route("/api/posting_report", methods=["GET", "QUERY"])
@login_required
@ttl_cache(ttl_seconds=300)
def api_posting_report():
    vid = session.get("vid")

    if not vid:
        return jsonify(success=False, error="Please select Village first"), 400

    if request.method == "QUERY" or request.is_json:
        data = request.get_json(silent=True) or {}
        view = data.get("view", "current")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        ano_val = str(data.get("ano", "")).strip()
    else:
        view = request.args.get("view", "current")
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        ano_val = request.args.get("ano", "").strip()

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        conditions = ["p.vid = %s"]
        params = [vid]

        if view == "historic":
            conditions.append("p.record_tier = 'historic'")
        elif view == "current":
            conditions.append("p.record_tier IN ('active', 'closed')")

        if start_date_str:
            try:
                start_date = parse_date_input(start_date_str)
                if start_date:
                    conditions.append("p.payment_date >= %s")
                    params.append(start_date)
            except Exception:
                pass

        if end_date_str:
            try:
                end_date = parse_date_input(end_date_str)
                if end_date:
                    conditions.append("p.payment_date <= %s")
                    params.append(end_date)
            except Exception:
                pass

        if ano_val and ano_val.isdigit():
            conditions.append("p.ano = %s")
            params.append(int(ano_val))

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT
                p.pid,
                p.ano,
                p.payment_date,
                p.amt,
                p.created_at,
                p.eid,
                p.cid,
                p.vid,
                p.record_tier AS payment_status,
                c.name AS customer_name
            FROM v_all_payments p
            LEFT JOIN v_all_customers c ON p.cid = c.cid
            WHERE {where_clause}
            ORDER BY p.payment_date DESC, p.pid DESC
        """
        cur.execute(query, tuple(params))

        rows = cur.fetchall()
        if cur.description:
            headers = [desc[0] for desc in cur.description]
        else:
            headers = ["pid", "ano", "payment_date", "amt", "created_at", "eid", "cid", "vid", "payment_status", "customer_name"]

        payments = []
        for r in rows:
            row_dict = dict(zip(headers, r))
            if row_dict.get("payment_date"):
                row_dict["payment_date"] = row_dict["payment_date"].isoformat()
            if row_dict.get("created_at"):
                row_dict["created_at"] = row_dict["created_at"].isoformat()
            if row_dict.get("amt") is not None:
                row_dict["amt"] = float(row_dict["amt"])
            payments.append(row_dict)

        resp_headers = {
            "Accept-Query": "application/json",
            "Cache-Control": "public, max-age=300"
        }
        return jsonify(success=True, headers=headers, payments=payments), 200, resp_headers

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/posting", methods=["GET"])
@login_required
def posting_page():
    vid = session.get("vid")

    if not vid:
        flash("Please select Village first", "warning")
        return redirect("/dashboard")

    return render_template("post_payment.html", customers=[])

@app.route("/api/posting/customers", methods=["GET"])
@login_required
def api_posting_customers():
    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="No active village context"), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                cid,
                ano,
                name,
                start_date,
                total_amount,
                paid_amount,
                balance_amount,
                installment_amount
            FROM customer
            WHERE vid = %s AND (status IS NULL OR status != 'closed')
        """, (vid,))

        customers = [
            dict(
                cid=r[0],
                ano=r[1],
                name=r[2],
                start_date=r[3].isoformat() if isinstance(r[3], (date, datetime)) else r[3],
                total_amount=float(r[4]) if r[4] is not None else 0.0,
                paid_amount=float(r[5]) if r[5] is not None else 0.0,
                balance_amount=float(r[6]) if r[6] is not None else 0.0,
                installment_amount=float(r[7]) if r[7] is not None else 0.0,
            )
            for r in cur.fetchall()
        ]
        return jsonify(success=True, customers=customers)
    except Exception as e:
        logger.error(f"Error fetching posting customers: {e}")
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/get_customer_info")
@login_required
def get_customer_info():
    ano = request.args.get("ano")
    vid = session.get("vid")

    if not ano or not vid:
        return jsonify({"error": "Missing context"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            cid,
            name,
            total_amount,
            paid_amount,
            balance_amount,
            installment_amount
        FROM customer
        WHERE vid = %s AND ano = %s
    """, (vid, ano))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Account number not found"})

    return jsonify({
        "cid": row[0],
        "name": row[1],
        "loan_amount": row[2],
        "total_repaid": row[3],
        "outstanding": row[4],
        "installment_amount": row[5],
    })

@app.route("/api/payment_day_stats")
@login_required
def payment_day_stats():

    vid = session.get("vid")

    if not vid:
        return jsonify({"error": "Missing village context"}), 400

    date_str = request.args.get("date")

    if not date_str:
        return jsonify({"error": "Missing date"}), 400

    try:
        payment_date = parse_date_input(date_str)
        if not payment_date:
            raise ValueError("bad date")
    except Exception:
        return jsonify({"error": "Invalid date"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:

        is_monthly = is_village_monthly(vid, cur)

        if is_monthly:
            cur.execute("""
                WITH eligible_customers AS (
                    SELECT
                        COUNT(*) AS expected_accounts
                    FROM v_all_customers c
                    WHERE c.vid = %s
                      AND (c.closed_at IS NULL OR c.closed_at::date > %s::date)
                      AND c.start_date <= %s::date
                ),
                actual_payments AS (
                    SELECT
                        COUNT(DISTINCT ano) AS paid_accounts
                    FROM v_all_payments all_p
                    WHERE vid = %s
                      AND payment_date = %s
                )
                SELECT
                    COALESCE(ec.expected_accounts, 0)
                        AS expected_accounts,
                    COALESCE(ap.paid_accounts, 0)
                        AS already_paid
                FROM eligible_customers ec
                CROSS JOIN actual_payments ap
            """, (
                vid,
                payment_date,
                payment_date,
                vid,
                payment_date
            ))
        else:
            cur.execute("""
                WITH village_collection_day AS (
                    SELECT DISTINCT ON (p.vid)
                        p.vid,
                        TRIM(TO_CHAR(p.payment_date, 'Day'))
                            AS collection_day,
                        COUNT(*) AS payment_count
                    FROM v_all_payments p
                    WHERE p.vid = %s
                    GROUP BY
                        p.vid,
                        collection_day
                    ORDER BY
                        p.vid,
                        payment_count DESC
                ),
                eligible_customers AS (
                    SELECT
                        COUNT(*) AS expected_accounts
                    FROM v_all_customers c
                    JOIN village_collection_day vcd
                        ON vcd.vid = c.vid
                    WHERE c.vid = %s
                      AND c.type = 'W'
                      AND (c.closed_at IS NULL OR c.closed_at::date > %s::date)
                      AND (
                            c.start_date + INTERVAL '7 days'
                          )::date <= %s
                      AND TRIM(TO_CHAR(%s::date, 'Day'))
                          = vcd.collection_day
                ),
                actual_payments AS (
                    SELECT
                        COUNT(DISTINCT ano) AS paid_accounts
                    FROM v_all_payments all_p
                    WHERE vid = %s
                      AND payment_date = %s
                )
                SELECT
                    COALESCE(ec.expected_accounts, 0)
                        AS expected_accounts,
                    COALESCE(ap.paid_accounts, 0)
                        AS already_paid
                FROM eligible_customers ec
                CROSS JOIN actual_payments ap
            """, (
                vid,
                vid,
                payment_date,
                payment_date,
                payment_date,
                vid,
                payment_date
            ))

        row = cur.fetchone()

        expected_accounts = int(row[0] or 0) if row else 0
        already_paid = int(row[1] or 0) if row else 0

        return jsonify({
            "expected_accounts": expected_accounts,
            "already_paid": already_paid
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route("/api/post_payment_analytics", methods=["GET"])
@login_required
def post_payment_analytics():
    KOLKATA = pytz.timezone('Asia/Kolkata')
    vid = session.get("vid")
    if not vid:
        return jsonify(error="Village context not set"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # 1. Get last posting date for the village
        cur.execute("""
            SELECT MAX(payment_date) FROM payment WHERE vid = %s
        """, (vid,))
        last_date = cur.fetchone()[0]

        if not last_date:
            last_date = datetime.today().date()
            last_date_str = format_date_display(last_date) + " (No postings yet)" # type: ignore
        else:
            days_ago = (datetime.now(KOLKATA).date() - last_date).days
            last_date_str = format_date_display(last_date) + f" ({days_ago} days ago)" # type: ignore

        # 2. Get all active or historically active customers for this village (both open and closed)
        cur.execute("""
            SELECT cid, ano, name, total_amount, installment_amount, start_date, closed_at
            FROM v_all_customers
            WHERE vid = %s
        """, (vid,))
        customers = []
        for r in cur.fetchall():
            customers.append({
                "cid": r[0],
                "ano": r[1],
                "name": r[2],
                "total_amount": float(r[3] or 0),
                "installment_amount": float(r[4] or 0),
                "start_date": r[5],
                "closed_at": r[6]
            })

        # 3. Get all payments (both active and closed) for this village
        cur.execute("""
            SELECT cid, amt, payment_date
            FROM v_all_payments
            WHERE vid = %s
        """, (vid,))
        payments = []
        payments_by_cid = {}
        for r in cur.fetchall():
            p = {
                "cid": r[0],
                "amt": float(r[1] or 0),
                "payment_date": r[2]
            }
            payments.append(p)
            
            cid = p["cid"]
            if cid not in payments_by_cid:
                payments_by_cid[cid] = []
            payments_by_cid[cid].append(p)

        is_monthly = is_village_monthly(vid, cur)

        if is_monthly:
            cur.execute("""
                SELECT DISTINCT payment_date 
                FROM v_all_payments
                WHERE vid = %s AND payment_date IS NOT NULL
                ORDER BY payment_date DESC
            """, (vid,))
            posting_dates = [r[0] for r in cur.fetchall()]
            target_dates = list(reversed(posting_dates[:5])) if posting_dates else [last_date]
            
            weeks = []
            for idx, p_dt in enumerate(target_dates):
                active_c = [
                    c for c in customers
                    if c["start_date"] and c["start_date"] <= p_dt
                    and (not c["closed_at"] or (c["closed_at"].date() if isinstance(c["closed_at"], datetime) else c["closed_at"]) > p_dt)
                ]
                expected = sum(c["installment_amount"] for c in active_c)
                
                pmts_at_dt = [p for p in payments if p["payment_date"] == p_dt]
                actual = sum(p["amt"] for p in pmts_at_dt)
                paying_cids = {p["cid"] for p in pmts_at_dt}
                
                paid_cnt = len(paying_cids)
                active_cnt = len(active_c)
                unpaid_cnt = max(0, active_cnt - paid_cnt)
                failed = max(0.0, expected - actual)
                
                offset = len(target_dates) - 1 - idx
                label = "This Month" if offset == 0 else (f"{offset} Mos Ago" if offset > 1 else "1 Mo Ago")
                
                weeks.append({
                    "label": label,
                    "start": p_dt,
                    "end": p_dt,
                    "active_customers": active_cnt,
                    "paid_customers": paid_cnt,
                    "unpaid_customers": unpaid_cnt,
                    "expected_collection": expected,
                    "actual_collection": actual,
                    "failed_to_collect": failed
                })
        else:
            # Calculate weeks: We generate 5 weeks ending at last_date
            # Week 0: [last_date - 6, last_date]
            # Week 1: [last_date - 13, last_date - 7]
            # Week 2: [last_date - 20, last_date - 14]
            # Week 3: [last_date - 27, last_date - 21]
            # Week 4: [last_date - 34, last_date - 28]
            weeks = []
            for i in range(4, -1, -1):
                w_end = last_date - timedelta(days=7 * i)
                w_start = w_end - timedelta(days=6)
                
                label = "This Week" if i == 0 else f"{i} Wk{'s' if i > 1 else ''} Ago"
                
                weeks.append({
                    "label": label,
                    "start": w_start,
                    "end": w_end,
                    "active_customers": 0,
                    "paid_customers": 0,
                    "unpaid_customers": 0,
                    "expected_collection": 0.0,
                    "actual_collection": 0.0,
                    "failed_to_collect": 0.0
                })

            for w in weeks:
                start_dt = w["start"]
                end_dt = w["end"]
                
                for c in customers:
                    # Check if customer loan started on or before the end of the week
                    if c["start_date"] and c["start_date"] <= end_dt:
                        # If customer was closed before start_dt, they are not active in this week
                        if c["closed_at"]:
                            cl_dt = c["closed_at"].date() if isinstance(c["closed_at"], datetime) else c["closed_at"]
                            if cl_dt < start_dt:
                                continue
                        cust_payments = payments_by_cid.get(c["cid"], [])
                        # Calculate total paid before this week
                        paid_before = sum(p["amt"] for p in cust_payments if p["payment_date"] < start_dt)
                        
                        # If loan balance at start of week was greater than 0, they were active
                        if c["total_amount"] - paid_before > 0.01:
                            w["active_customers"] += 1
                            w["expected_collection"] += c["installment_amount"]
                            
                            # Calculate paid during this week
                            paid_this_week = sum(p["amt"] for p in cust_payments if start_dt <= p["payment_date"] <= end_dt)
                            
                            if paid_this_week > 0.01:
                                w["paid_customers"] += 1
                                w["actual_collection"] += paid_this_week
                            else:
                                w["unpaid_customers"] += 1
                                w["failed_to_collect"] += c["installment_amount"]

        # Format and round data
        for w in weeks:
            w["expected_collection"] = round_curr(w["expected_collection"])
            w["actual_collection"] = round_curr(w["actual_collection"])
            w["failed_to_collect"] = round_curr(w["failed_to_collect"])
            w["start"] = format_date_display(w["start"])
            w["end"] = format_date_display(w["end"])

        return jsonify(
            last_posting_date=last_date_str,
            weeks=weeks,
            is_monthly=is_monthly
        )

    except Exception as e:
        logger.error(f"Error calculating post payment analytics: {e}")
        return jsonify(error="Internal server error"), 500
    finally:
        cur.close()
        conn.close()



# ----------------------------------------------------
# BULK LEDGER OCR EXTRACTION (GEMINI AI)
# ----------------------------------------------------
LEDGER_OCR_PROMPT = """You are an OCR extraction engine.
Your task is to extract handwritten ledger data from the attached images with maximum accuracy.
Do NOT summarize, explain, calculate totals, or reformat beyond what is requested.

Image Structure
Each image represents one page.
Each page contains three independent vertical sections (columns).
Each section contains rows.
Every row contains:
Account Number (left side of that section)
Amount (right side of that section)
Treat every section independently.
Read rows top to bottom.
Read sections left → middle → right.
When moving to the next image, start a new page.

Extraction Rules
For every row output exactly:
(AccountNumber,Amount)
Examples:
(1,500)
(25,1000)
(94,700)

Important Rules
1. Never skip rows
Every account number that appears in the image must appear exactly once in the output.

2. If amount is a dash
If the amount field contains only a dash, blank dash, horizontal line, or intentionally empty value, output
(account,-)
Example
Image:
24    —
Output
(24,-)

3. If the amount is unreadable
If you are less than 95% confident about the handwritten amount,
DO NOT guess.
Output
(account,N)
Examples
(15,N)
(43,N)
Never invent numbers.

4. If the account number is unreadable
If the account number itself cannot be read with at least 95% confidence,
skip that row completely.
Do not invent account numbers.

5. Preserve values exactly
Do not:
round numbers
correct handwriting
infer missing digits
calculate missing values
Only transcribe what is actually written.

6. Ignore everything except ledger rows
Ignore:
titles
dates
totals
page totals
notes
signatures
scribbles
headings
Only extract account-number/amount pairs.

7. Do NOT output totals
Ignore every total written at the bottom.
Never calculate totals.
Never mention totals.

Output Format
Separate every page.
Separate every section with one blank line.
Example:
Page 1

(1,500), (2,500), (3,300), (4,200), (5,200)

(21,400), (22,10000), (23,100), (24,-), (25,100)

(41,300), (42,100), (43,N), (44,100), (45,-)


Page 2

(61,150), (62,100), (63,200), (64,100)

(81,100), (82,500), (83,500), (84,100)

Accuracy Policy
Before producing the final output, verify:
Every section has been processed.
Rows are in the correct order.
No account numbers are duplicated.
No rows are skipped.
Every unreadable amount is replaced with N.
Every dash remains -.
No totals appear.
No explanations appear.
Output contains only the requested pairs.
Return nothing except the formatted extraction."""


@app.route("/api/ocr_extract_bulk", methods=["POST"])
@login_required
def api_ocr_extract_bulk():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify(
            success=False,
            error="Gemini API Key is not set in .env. Please set GEMINI_API_KEY in your .env file."
        ), 400

    uploaded_files = request.files.getlist("images")
    if not uploaded_files:
        return jsonify(success=False, error="No images uploaded."), 400

    valid_files = [f for f in uploaded_files if f and f.filename]
    if not valid_files:
        return jsonify(success=False, error="No valid images selected."), 400

    try:
        preferred_model = os.environ.get("GEMINI_OCR_MODEL", "gemini-3.7-flash").strip()
        candidate_models = [preferred_model, "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3-flash-preview", "gemini-3.6-flash"]
        seen_models = set()
        models_to_try = [m for m in candidate_models if not (m in seen_models or seen_models.add(m))]

        # Read images and prepare base64 parts
        image_data_list = []
        for file in valid_files:
            file_bytes = file.read()
            mime = file.mimetype or "image/jpeg"
            b64_str = base64.b64encode(file_bytes).decode("utf-8")
            image_data_list.append({"mime": mime, "b64": b64_str, "bytes": file_bytes})

        extracted_text = None
        last_error = None

        # Method A: Direct official Gemini REST API (zero SDK dependency / eliminates import conflicts)
        for m in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                parts = []
                for item in image_data_list:
                    parts.append({
                        "inline_data": {
                            "mime_type": item["mime"],
                            "data": item["b64"]
                        }
                    })
                parts.append({"text": LEDGER_OCR_PROMPT})

                payload = {"contents": [{"parts": parts}]}
                resp = requests.post(url, json=payload, timeout=45)

                if resp.status_code == 200:
                    resp_json = resp.json()
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        p_list = content.get("parts", [])
                        if p_list:
                            extracted_text = p_list[0].get("text", "").strip()
                            if extracted_text:
                                break
                else:
                    err_msg = resp.text
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error", {}).get("message", resp.text)
                    except Exception:
                        pass
                    last_error = RuntimeError(f"{m} (HTTP {resp.status_code}): {err_msg}")
                    logger.warning(f"REST Gemini model {m} returned {resp.status_code}: {err_msg}")

            except Exception as rest_err:
                last_error = rest_err
                logger.warning(f"REST Gemini model {m} failed: {rest_err}")

        # Method B: Secondary fallback to google-genai SDK if REST didn't extract
        if not extracted_text:
            try:
                from google import genai # type: ignore
                from google.genai import types # type: ignore

                client = genai.Client(api_key=api_key)
                sdk_contents = []
                for item in image_data_list:
                    part = types.Part.from_bytes(data=item["bytes"], mime_type=item["mime"])
                    sdk_contents.append(part)
                sdk_contents.append(LEDGER_OCR_PROMPT)

                for m in models_to_try:
                    try:
                        sdk_res = client.models.generate_content(model=m, contents=sdk_contents)
                        if sdk_res and sdk_res.text:
                            extracted_text = sdk_res.text.strip()
                            break
                    except Exception as sdk_err:
                        last_error = sdk_err
            except Exception as import_or_sdk_err:
                logger.warning(f"google-genai SDK fallback unavailable: {import_or_sdk_err}")

        if not extracted_text:
            raise last_error or RuntimeError("Could not extract ledger data from Gemini API.")

        return jsonify(
            success=True,
            text=extracted_text,
            pages_count=len(valid_files)
        )

    except Exception as e:
        logger.error(f"OCR Extraction Error: {e}", exc_info=True)
        return jsonify(success=False, error=str(e)), 500

# ----------------------------------------------------
# ----------------------------------------------------
# SMART COUNTING MOBILE SCANNER (STANDALONE WEB CAPTURE)
# ----------------------------------------------------
# Thread-safe in-memory session broker for live mobile scanner pairing
_BULK_CAPTURE_SESSIONS = {}
_BULK_CAPTURE_LOCK = threading.Lock()
_BULK_SESSION_TTL_SECONDS = 900  # 15 minutes

def _cleanup_bulk_capture_sessions():
    """Removes sessions older than TTL."""
    now = datetime.now(timezone.utc)
    with _BULK_CAPTURE_LOCK:
        expired = [
            sid for sid, sdata in _BULK_CAPTURE_SESSIONS.items()
            if (now - sdata.get("created_at", now)).total_seconds() > _BULK_SESSION_TTL_SECONDS
        ]
        for sid in expired:
            _BULK_CAPTURE_SESSIONS.pop(sid, None)

def _find_session_by_code(code_str):
    """Finds an active session matching the 6-digit sync code."""
    if not code_str:
        return None, None
    clean_code = str(code_str).replace("-", "").replace(" ", "").strip().upper()
    now = datetime.now(timezone.utc)
    with _BULK_CAPTURE_LOCK:
        for sid, sdata in _BULK_CAPTURE_SESSIONS.items():
            s_code = str(sdata.get("code", "")).replace("-", "").replace(" ", "").strip().upper()
            if s_code == clean_code:
                if (now - sdata.get("created_at", now)).total_seconds() <= _BULK_SESSION_TTL_SECONDS:
                    return sid, sdata
    return None, None


def _get_reachable_mobile_host(request):
    """
    Determines the best network host/IP so a phone scanning the QR code can reach the server.
    If the request is from localhost or 127.0.0.1, resolves the machine's actual LAN IP (e.g. 192.168.x.x)
    and keeps the correct port, allowing any phone on the Wi-Fi network to open the URL directly.
    """
    configured_base = os.environ.get("MOBILE_SCANNER_BASE_URL", "").strip()
    if configured_base:
        return configured_base.rstrip("/")

    req_host = request.host  # e.g. "localhost:8080" or "sivadurga.in"
    scheme = "https" if (request.is_secure or request.headers.get("X-Forwarded-Proto") == "https") else request.scheme

    # If domain or external address, use it directly
    if not any(local in req_host for local in ("localhost", "127.0.0.1", "0.0.0.0")):
        return f"{scheme}://{req_host}"

    # Local development: resolve LAN Wi-Fi IP so phones on the same network can load it
    port_part = ""
    if ":" in req_host:
        port_part = ":" + req_host.split(":")[1]
    
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "127.0.0.1"

    return f"{scheme}://{lan_ip}{port_part}"


@app.route("/api/bulk_capture/session/create", methods=["POST"])
@login_required
def api_bulk_capture_session_create():
    """
    Creates a new mobile pairing capture session.
    Returns session_id, upload_url, and high-compatibility QR code image.
    The QR code encodes a direct, standard HTTP/HTTPS web link.
    """
    _cleanup_bulk_capture_sessions()

    session_id = secrets.token_urlsafe(16)
    base_url = _get_reachable_mobile_host(request)
    mobile_capture_url = f"{base_url}/bulk_capture/{session_id}"

    qr_base64 = ""
    try:
        import qrcode # type: ignore
        qr = qrcode.QRCode(
            version=None,  # Auto-fit version based on URL length
            error_correction=qrcode.constants.ERROR_CORRECT_M, # type: ignore
            box_size=8,
            border=3,
        )
        qr.add_data(mobile_capture_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1a1a2e", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf, format="PNG") # type: ignore
        qr_base64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as qr_err:
        logger.warning(f"Could not generate QR code with qrcode lib: {qr_err}")

    session_data = {
        "session_id": session_id,
        "mobile_capture_url": mobile_capture_url,
        "qr_code": qr_base64,
        "status": "waiting",  # waiting | connected | completed
        "created_at": datetime.now(timezone.utc),
        "user_id": session.get("user_id"),
        "employee_id": session.get("employee_id") or session.get("eid"),
        "images": [],
        "device_info": None,
    }

    with _BULK_CAPTURE_LOCK:
        _BULK_CAPTURE_SESSIONS[session_id] = session_data

    logger.info(f"Bulk capture session created: {session_id} (URL: {mobile_capture_url})")

    return jsonify(
        success=True,
        session_id=session_id,
        mobile_capture_url=mobile_capture_url,
        qr_code=qr_base64,
        expires_in=_BULK_SESSION_TTL_SECONDS,
    )


@app.route("/bulk_capture/<session_id>", methods=["GET"])
def view_bulk_capture_mobile(session_id):
    """
    Mobile Web Document Scanner page.
    Opened directly when scanning the QR code from ANY mobile phone browser.
    Validates that the session is still active and valid.
    """
    _cleanup_bulk_capture_sessions()

    with _BULK_CAPTURE_LOCK:
        sdata = _BULK_CAPTURE_SESSIONS.get(session_id)

    if not sdata:
        return render_template(
            "bulk_capture_expired.html",
            title="Session Expired",
            error_message="This capture session has expired or was closed on desktop. Please scan a new QR code from the Bulk Payments window."
        ), 404

    # Mark as connected
    with _BULK_CAPTURE_LOCK:
        if sdata.get("status") == "waiting":
            sdata["status"] = "connected"
            sdata["device_info"] = {
                "name": "Mobile Browser",
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }

    return render_template(
        "bulk_capture_mobile.html",
        session_id=session_id,
        code=sdata.get("code", "")
    )


@csrf.exempt
@app.route("/api/bulk_capture/mobile_ping/<session_id>", methods=["POST"])
def api_bulk_capture_mobile_ping(session_id):
    """
    Notifies desktop that the mobile user has opened the scanner page.
    """
    with _BULK_CAPTURE_LOCK:
        sdata = _BULK_CAPTURE_SESSIONS.get(session_id)
        if not sdata:
            return jsonify(error="Session not found"), 404
        sdata["status"] = "connected"
        sdata["device_info"] = {
            "name": "Mobile Phone",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
    return jsonify(success=True)


@csrf.exempt
@app.route("/api/bulk_capture/mobile_upload", methods=["POST"])
def api_bulk_capture_mobile_upload():
    """
    Receives processed document page images from the mobile web page.
    Appends them to the capture session and updates status to 'completed'.
    """
    _cleanup_bulk_capture_sessions()

    session_id = request.form.get("session_id", "").strip()
    with _BULK_CAPTURE_LOCK:
        sdata = _BULK_CAPTURE_SESSIONS.get(session_id)
        if not sdata:
            return jsonify(error="Session expired or not found. Please scan a new QR code."), 404

    files = request.files.getlist("images")
    if not files and "image" in request.files:
        files = [request.files["image"]]

    if not files:
        return jsonify(error="No image files received"), 400

    saved_images = []
    for f in files:
        if f and f.filename:
            content = f.read()
            if len(content) > 0:
                saved_images.append({
                    "filename": f.filename,
                    "mimetype": f.mimetype or "image/jpeg",
                    "bytes": content,
                })

    if not saved_images:
        return jsonify(error="Uploaded images were empty"), 400

    with _BULK_CAPTURE_LOCK:
        sdata["images"].extend(saved_images)
        sdata["status"] = "completed"

    logger.info(
        f"Mobile web capture upload completed for session {session_id}: "
        f"{len(saved_images)} new images (Total: {len(sdata['images'])})"
    )

    return jsonify(
        success=True,
        session_id=session_id,
        uploaded_count=len(saved_images),
        total_images=len(sdata["images"]),
        status="completed",
    )


@app.route("/api/bulk_capture/session/status/<session_id>", methods=["GET"])
@login_required
def api_bulk_capture_session_status(session_id):
    """
    Polled by the desktop web browser to check capture session status.
    """
    _cleanup_bulk_capture_sessions()

    with _BULK_CAPTURE_LOCK:
        sdata = _BULK_CAPTURE_SESSIONS.get(session_id)

    if not sdata:
        return jsonify(success=False, error="Session expired or not found"), 404

    image_list = [
        {
            "index": idx,
            "filename": img.get("filename", f"page_{idx + 1}.jpg"),
            "size": len(img.get("bytes", b"")),
            "url": f"/api/bulk_capture/session/{session_id}/image/{idx}",
        }
        for idx, img in enumerate(sdata.get("images", []))
    ]

    return jsonify(
        success=True,
        session_id=session_id,
        code=sdata.get("code"),
        mobile_capture_url=sdata.get("mobile_capture_url"),
        status=sdata.get("status", "waiting"),
        image_count=len(image_list),
        images=image_list,
        device_info=sdata.get("device_info"),
    )


@app.route("/api/bulk_capture/session/<session_id>/image/<int:index>", methods=["GET"])
@login_required
def api_bulk_capture_session_image(session_id, index):
    """
    Serves a specific scanned page image from the capture session.
    """
    with _BULK_CAPTURE_LOCK:
        sdata = _BULK_CAPTURE_SESSIONS.get(session_id)
        if not sdata:
            return jsonify(error="Session not found"), 404

        images = sdata.get("images", [])
        if index < 0 or index >= len(images):
            return jsonify(error="Image index out of bounds"), 404

        img = images[index]
        img_bytes = img.get("bytes")
        mimetype = img.get("mimetype", "image/jpeg")
        filename = img.get("filename", f"page_{index + 1}.jpg")

    return send_file(
        io.BytesIO(img_bytes),
        mimetype=mimetype,
        as_attachment=False,
        download_name=filename,
    )


@app.route("/api/bulk_capture/session/cancel/<session_id>", methods=["POST"])
@login_required
def api_bulk_capture_session_cancel(session_id):
    """
    Cancels and removes a capture session immediately when user closes modal on desktop.
    """
    with _BULK_CAPTURE_LOCK:
        _BULK_CAPTURE_SESSIONS.pop(session_id, None)
    return jsonify(success=True)


# --- Simulation / Testing Endpoint for Developers ---

@app.route("/api/bulk_capture/simulate_upload/<session_id>", methods=["POST"])
@login_required
def api_bulk_capture_simulate_upload(session_id):
    """
    Developer helper endpoint to simulate mobile upload of 2 test ledger page images.
    Allows instant testing of web pairing flow right from the browser.
    """
    with _BULK_CAPTURE_LOCK:
        session_obj = _BULK_CAPTURE_SESSIONS.get(session_id)
        if not session_obj:
            return jsonify(error="Session not found"), 404

    from PIL import Image, ImageDraw # type: ignore

    def create_mock_ledger_page(page_no):
        img = Image.new("RGB", (600, 800), color="#ffffff")
        draw = ImageDraw.Draw(img)
        draw.rectangle([(20, 20), (580, 780)], outline="#2563eb", width=3)
        draw.text((40, 40), f"SD FINANCE LEDGER - PAGE {page_no}", fill="#1a1a2e")
        draw.text((40, 80), f"Captured via Standalone Mobile Web Scanner", fill="#6b7280")
        y = 130
        for r in range(1, 12):
            draw.line([(40, y), (560, y)], fill="#e5e7eb", width=1)
            draw.text((50, y + 8), f"Entry {((page_no - 1) * 20) + r}: Customer {100 + r}", fill="#1a1a2e")
            draw.text((420, y + 8), f"Rs. {r * 150}", fill="#16a34a")
            y += 45
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    p1 = create_mock_ledger_page(1)
    p2 = create_mock_ledger_page(2)

    with _BULK_CAPTURE_LOCK:
        session_obj["status"] = "completed"
        session_obj["device_info"] = {
            "name": "Simulated Mobile Phone",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        session_obj["images"] = [
            {"filename": "scanned_page_1.jpg", "mimetype": "image/jpeg", "bytes": p1},
            {"filename": "scanned_page_2.jpg", "mimetype": "image/jpeg", "bytes": p2},
        ]

    return jsonify(
        success=True,
        message="Simulated 2 scanned pages uploaded successfully!",
        session_id=session_id,
        image_count=2,
    )



@app.route("/submit_post_payment", methods=["POST"])
@login_required
def submit_post_payment():
    vid = session.get("vid")
    eid = session.get("eid")

    if not vid:
        return jsonify(error="Context not set"), 400

    rows = request.get_json()
    if not rows:
        return jsonify(error="No data received"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    submitted = 0
    skipped = []
    seen_in_batch = set()

    try:
        for row in rows:
            ano = normalize_account_number(row.get("ano"))
            if ano is None:
                skipped.append({**row, "reason": "Invalid or missing account number"})
                continue

            try:
                amt = Decimal(str(row.get("amt", 0)))
            except Exception:
                amt = Decimal(0)
            if amt <= 0:
                skipped.append({**row, "reason": f"Account #{ano}: Payment amount must be greater than 0"})
                continue

            payment_date = parse_date_input(row.get("pdt"))
            if not payment_date:
                skipped.append({**row, "reason": f"Account #{ano}: Invalid payment date '{row.get('pdt')}'"})
                continue

            # 🔹 Fetch customer
            cur.execute("""
                SELECT cid, total_amount, paid_amount, start_date
                FROM customer
                WHERE vid = %s AND ano = %s
            """, (vid, ano))

            cust = cur.fetchone()
            if not cust:
                skipped.append({**row, "reason": f"Account #{ano} not found in database for this village"})
                continue

            cid, total_amt, paid_amt, cust_start_date = cust

            # Validate payment_date >= start_date
            if cust_start_date and payment_date < cust_start_date:
                skipped.append({
                    **row,
                    "reason": f"Account #{ano}: Payment date ({format_date_display(str(payment_date))}) cannot be earlier than start date ({format_date_display(str(cust_start_date))})"
                })
                continue

            # 🔹 Intra-batch duplicate check
            batch_key = (ano, str(payment_date))
            if batch_key in seen_in_batch:
                skipped.append({
                    **row,
                    "reason": f"Account #{ano}: Multiple payments for date {format_date_display(str(payment_date))} in the same submission"
                })
                continue
            seen_in_batch.add(batch_key)

            # 🔹 Database duplicate check (prevent duplicate payment for same customer on same date)
            cur.execute("""
                SELECT pid, amt FROM payment
                WHERE vid = %s AND ano = %s AND payment_date = %s
                LIMIT 1
            """, (vid, ano, payment_date))
            existing = cur.fetchone()
            if existing:
                skipped.append({
                    **row,
                    "reason": f"Account #{ano}: Payment already recorded on {format_date_display(str(payment_date))} (Amount: ₹{existing[1]})"
                })
                continue

            total_amt = Decimal(total_amt)
            paid_amt = Decimal(paid_amt or 0)

            payment_type = str(row.get("payment_type") or "cash").lower()
            if payment_type not in ("cash", "upi", "partial", "mixed"):
                payment_type = "cash"
            cash_amount = Decimal(str(row.get("cash_amount", amt if payment_type == "cash" else 0)))
            upi_amount = Decimal(str(row.get("upi_amount", amt if payment_type == "upi" else 0)))

            # 🔹 Insert payment (pid auto-generated)
            cur.execute("""
                INSERT INTO payment (cid, vid, eid, ano, amt, payment_date, payment_type, cash_amount, upi_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (cid, vid, eid, ano, amt, payment_date, payment_type, cash_amount, upi_amount))

            # 🔹 Recalculate balances (centralized logic)
            recalc_customer_balance(cur, cid)

            submitted += 1

        # Invalidate cache for this village
        min_pdt = None
        for r in rows:
            try:
                pdt = parse_date_input(r["pdt"])
                if not min_pdt or pdt < min_pdt:# type: ignore
                    min_pdt = pdt
            except Exception:
                pass
        invalidate_village_health_cache(cur, vid, min_pdt)

        global_ttl_cache.clear()
        conn.commit()

        audit_log(
            action="submit_post_payment",
            entity_type="payment",
            entity_id=vid,
            details={
                "eid": eid,
                "vid": vid,
                "submitted_count": submitted,
                "skipped_count": len(skipped),
                "skipped_reasons": [s.get("reason") for s in skipped] if skipped else []
            }
        )

        return jsonify( 
            success=True,
            message=f"{submitted} payment(s) posted" + (f", {len(skipped)} skipped" if skipped else ""),
            submitted_count=submitted,
            skipped_count=len(skipped),
            skipped_rows=skipped
        )

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(error=str(e)), 500

    finally:
        cur.close()
        conn.close()



@app.route("/api/customer/save_payments", methods=["POST"])
@login_required
def api_customer_save_payments():
    vid = session.get("vid")
    eid = session.get("eid")
    if not vid:
        return jsonify(success=False, error="Village context missing"), 400

    data = request.get_json()
    cid = data.get("cid")
    ano = data.get("ano")
    payments = data.get("payments")

    if not cid or not ano or payments is None:
        return jsonify(success=False, error="Missing required parameters"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Determine if active or closed
        cur.execute("SELECT 1 FROM customer WHERE cid = %s", (cid,))
        is_active = cur.fetchone() is not None

        table_payment = "payment" if is_active else "closed_cust_payment"
        table_customer = "customer" if is_active else "closed_cust_account"

        # Get old balance and start_date
        cur.execute(f"SELECT balance_amount, start_date FROM {table_customer} WHERE cid = %s", (cid,))
        row = cur.fetchone()
        old_balance = row[0] if row else Decimal("0")
        cust_start_date = row[1] if row else None

        # Validate duplicate dates and amounts in incoming payments
        seen_dates = set()
        for p in payments:
            pdt_str = p.get("payment_date")
            pdt = parse_date_input(pdt_str)
            if not pdt:
                return jsonify(success=False, error=f"Invalid payment date: '{pdt_str}'"), 400

            iso_d = str(pdt)
            if iso_d in seen_dates:
                return jsonify(
                    success=False,
                    error=f"Multiple payments for date {format_date_display(pdt)} are not permitted. Only one payment per date is allowed."
                ), 400
            seen_dates.add(iso_d)

            try:
                amt_val = Decimal(str(p.get("amt", 0)))
            except Exception:
                amt_val = Decimal(0)
            if amt_val <= 0:
                return jsonify(success=False, error="Payment amount must be greater than 0"), 400

            if cust_start_date and pdt < cust_start_date:
                return jsonify(
                    success=False,
                    error=f"Payment date ({format_date_display(pdt)}) cannot be earlier than customer start date ({format_date_display(cust_start_date)})"
                ), 400

        # Get existing pids for this customer (ignoring NULLs)
        cur.execute(f"SELECT pid FROM {table_payment} WHERE cid = %s AND pid IS NOT NULL", (cid,))
        existing_pids = {row[0] for row in cur.fetchall()}

        # Remove any legacy un-indexed NULL-pid rows for this customer to prevent duplicate accumulation
        cur.execute(f"DELETE FROM {table_payment} WHERE cid = %s AND pid IS NULL", (cid,))

        incoming_pids = set()
        for p in payments:
            pid = p.get("pid")
            amt = Decimal(str(p.get("amt", 0)))
            pdt_str = p.get("payment_date")
            pdt = parse_date_input(pdt_str)

            if pid and pid in existing_pids:
                # UPDATE
                if table_payment == "payment":
                    cur.execute(f"""
                        UPDATE {table_payment}
                        SET amt = %s, payment_date = %s, updated_at = NOW()
                        WHERE pid = %s AND cid = %s
                    """, (amt, pdt, pid, cid))
                else:
                    cur.execute(f"""
                        UPDATE {table_payment}
                        SET amt = %s, payment_date = %s
                        WHERE pid = %s AND cid = %s
                    """, (amt, pdt, pid, cid))
                incoming_pids.add(pid)
            else:
                # INSERT
                cur.execute(f"""
                    INSERT INTO {table_payment} (cid, vid, eid, ano, amt, payment_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING pid
                """, (cid, vid, eid, ano, amt, pdt))
                res_pid = cur.fetchone()
                if res_pid and res_pid[0]:
                    incoming_pids.add(res_pid[0])

        # DELETE missing pids safely
        pids_to_delete = list(existing_pids - incoming_pids)
        if pids_to_delete:
            cur.execute(f"""
                DELETE FROM {table_payment}
                WHERE cid = %s AND pid = ANY(%s)
            """, (cid, pids_to_delete))

        # Recalculate totals
        cur.execute(f"SELECT total_amount, COALESCE(interest_discount, 0) FROM {table_customer} WHERE cid = %s", (cid,))
        row = cur.fetchone()
        if row:
            total_amt, interest_discount = row
            cur.execute(f"SELECT COALESCE(SUM(amt), 0) FROM {table_payment} WHERE cid = %s", (cid,))
            paid_amt = cur.fetchone()[0]
            balance_amt = total_amt - paid_amt - interest_discount

            cur.execute(f"""
                UPDATE {table_customer}
                SET paid_amount = %s,
                    balance_amount = %s
                WHERE cid = %s
            """, (paid_amt, balance_amt, cid))

            force_recalc = (balance_amt > 0) or (old_balance is not None and old_balance > 0 and balance_amt <= 0)
            recalc_customer_repayment_score(cur, cid, force_recalc=force_recalc)

        global_ttl_cache.clear()
        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/customer_detail_with_payments/<account_no>", methods=["GET"])
@login_required
def api_customer_detail_with_payments(account_no):
    vid = session.get("vid")
    
    logger.info(f"API call started: account_no={repr(account_no)}, session_vid={repr(vid)}")
        
    if not vid:
        logger.info(f"Error: session_vid missing")
        return jsonify(success=False, error="Village context missing"), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        account_no = str(account_no).strip()
        int_val = int(account_no) if account_no.isdigit() else None

        row = None
        # 1. First priority: Direct CID match in current village
        if int_val is not None:
            cur.execute("""
                SELECT 
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, 
                    balance_amount, installment_amount, type, period, pano, created_at, 
                    aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                    base_amount, cutting_amount, interest_amount, interest_discount, 
                    record_tier AS source_table, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND cid = %s
                LIMIT 1
            """, (vid, int_val))
            row = cur.fetchone()

        # 2. Second priority: ANO match in current village (active first, then closed, then historic)
        if not row and int_val is not None:
            cur.execute("""
                SELECT 
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, 
                    balance_amount, installment_amount, type, period, pano, created_at, 
                    aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                    base_amount, cutting_amount, interest_amount, interest_discount, 
                    record_tier AS source_table, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND ano = %s
                ORDER BY CASE 
                    WHEN record_tier = 'active' THEN 0 
                    WHEN record_tier = 'closed' THEN 1 
                    ELSE 2 
                END
                LIMIT 1
            """, (vid, int_val))
            row = cur.fetchone()

        # 3. Third priority: Text ANO match in current village
        if not row:
            cur.execute("""
                SELECT 
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, 
                    balance_amount, installment_amount, type, period, pano, created_at, 
                    aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                    base_amount, cutting_amount, interest_amount, interest_discount, 
                    record_tier AS source_table, ucid, cycle_number
                FROM v_all_customers
                WHERE vid = %s AND CAST(ano AS TEXT) = %s
                ORDER BY CASE 
                    WHEN record_tier = 'active' THEN 0 
                    WHEN record_tier = 'closed' THEN 1 
                    ELSE 2 
                END
                LIMIT 1
            """, (vid, account_no))
            row = cur.fetchone()

        # 4. Fourth priority: Global CID match across all villages (handles session context desync)
        if not row and int_val is not None:
            cur.execute("""
                SELECT 
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, 
                    balance_amount, installment_amount, type, period, pano, created_at, 
                    aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                    base_amount, cutting_amount, interest_amount, interest_discount, 
                    record_tier AS source_table, ucid, cycle_number
                FROM v_all_customers
                WHERE cid = %s
                LIMIT 1
            """, (int_val,))
            row = cur.fetchone()

        if not row:
            logger.info(f"404 Error: Not found in DB. search_term={repr(account_no)}, session_vid={repr(vid)}")
            return jsonify(success=False, error="Customer not found"), 404

        loanee_headers = [
            "cid", "ano", "name", "vid", "start_date", "end_date", "total_amount", "paid_amount", 
            "balance_amount", "installment_amount", "type", "period", "pano", "created_at", 
            "aadhaar_number", "notes", "latitude", "longitude", "eid", "phone_number", "status",
            "customer_rating", "final_frozen_rating", "final_risk_level", "freeze_date",
            "base_amount", "cutting_amount", "interest_amount", "interest_discount", "source_table",
            "ucid", "cycle_number"
        ]

        cust = dict(zip(loanee_headers, row))

        # Format decimal values and dates
        for key in ["total_amount", "paid_amount", "balance_amount", "installment_amount", "customer_rating", "final_frozen_rating", "base_amount", "cutting_amount", "interest_amount", "interest_discount"]:
            if cust.get(key) is not None:
                cust[key] = float(cust[key])
            else:
                cust[key] = 0.0 if key != "final_frozen_rating" else None
        for key in ["start_date", "end_date", "created_at", "freeze_date"]:
            if cust.get(key):
                cust[key] = cust[key].isoformat()

        # Fetch payments strictly from unified view
        cur.execute("""
            SELECT ano, TO_CHAR(payment_date, 'YYYY-MM-DD') as payment_date, amt, pid, cash_amount, upi_amount, payment_type
            FROM v_all_payments
            WHERE cid = %s
            ORDER BY payment_date, pid
        """, (cust["cid"],))

        prows = cur.fetchall()
        payments = []
        for prow in prows:
            payments.append({
                "ano": prow[0],
                "payment_date": prow[1],
                "amt": float(prow[2] or 0),
                "pid": prow[3],
                "cash_amount": float(prow[4] or 0) if prow[4] is not None else None,
                "upi_amount": float(prow[5] or 0) if prow[5] is not None else None,
                "payment_type": prow[6] or "CASH"
            })

        # Fetch borrower summary if ucid exists
        borrower_summary = None
        if cust.get("ucid"):
            cur.execute("""
                SELECT total_loan_cycles, lifetime_borrowed, lifetime_repaid, current_active_balance, customer_risk_tier,
                       lifetime_credit_score, lifetime_on_time_ratio, total_cycles_completed
                FROM customer_master
                WHERE ucid = %s
            """, (cust["ucid"],))
            bm_row = cur.fetchone()
            if bm_row:
                borrower_summary = {
                    "total_cycles": bm_row[0],
                    "lifetime_borrowed": float(bm_row[1] or 0),
                    "lifetime_repaid": float(bm_row[2] or 0),
                    "current_active_balance": float(bm_row[3] or 0),
                    "customer_risk_tier": bm_row[4] or "standard",
                    "lifetime_credit_score": float(bm_row[5]) if bm_row[5] is not None else 100.0,
                    "lifetime_on_time_ratio": float(bm_row[6]) if bm_row[6] is not None else 100.0,
                    "total_cycles_completed": int(bm_row[7] or 0)
                }
        cust["borrower_summary"] = borrower_summary

        # Calculate week details log dynamically (strictly read-only!)
        score, risk_level, overdue_penalty, week_details = calculate_customer_rating_details(
            cust["start_date"], cust["end_date"], cust["installment_amount"], cust["period"], payments, cust["balance_amount"], loan_type=cust.get("type", "W")
        )
        
        cust["customer_rating"] = score

        behavioral_analytics = calculate_behavioral_analytics(
            cust["start_date"], cust["end_date"], cust["installment_amount"], cust["period"], payments, cust["balance_amount"], week_details, loan_type=cust.get("type", "W")
        )

        # Fetch village rates
        target_vid = cust.get("vid") or vid
        cur.execute("SELECT interest_rate, cutting_rate FROM village WHERE vid = %s", (target_vid,))
        rates_row = cur.fetchone()
        interest_rate = float(rates_row[0]) if rates_row and rates_row[0] is not None else 0.0
        cutting_rate = float(rates_row[1]) if rates_row and rates_row[1] is not None else 0.0

        logger.info(f"Success: Found customer cid={cust['cid']}, name={cust['name']}, vid={cust['vid']}, status={cust['status']}")

        return jsonify(
            success=True,
            customer=cust,
            payments=payments,
            week_details=week_details,
            behavioral_analytics=behavioral_analytics,
            interest_rate=interest_rate,
            cutting_rate=cutting_rate
        )

    except Exception as e:
        logger.info(f"Server Exception: {str(e)}")
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/recalculate_customer_rating/<account_no>", methods=["POST"])
@login_required
def api_recalculate_customer_rating(account_no):
    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="Village context missing"), 400
        
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        account_no = str(account_no).strip()
        cid_val = None
        if account_no.isdigit():
            try:
                cid_val = int(account_no)
            except ValueError:
                pass
                
        row = None
        if cid_val is not None:
            cur.execute("""
                SELECT cid FROM v_all_customers
                WHERE vid = %s AND cid = %s 
                LIMIT 1
            """, (vid, cid_val))
            row = cur.fetchone()
        if not row:
            cur.execute("""
                SELECT cid FROM v_all_customers
                WHERE vid = %s AND CAST(ano AS TEXT) = %s 
                LIMIT 1
            """, (vid, account_no))
            row = cur.fetchone()
            
        if not row:
            return jsonify(success=False, error="Customer not found"), 404
            
        cid = row[0]
        res = recalc_customer_repayment_score(cur, cid, force_recalc=True)
        conn.commit()
        return jsonify(success=True, rating=res)
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/customer_family_full/<account_no>")
@app.route("/api/customer_linked_accounts/<account_no>")
@login_required
def api_customer_family_full(account_no):
    vid = session.get("vid")

    if not vid:
        return jsonify({
            "success": False,
            "error": "Village context missing",
            "customers": []
        }), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        normalized = normalize_account_number(account_no)
        if normalized is None:
            return jsonify(success=False)

        account_no = str(normalized)

        ano_int = int(account_no) if account_no.isdigit() else None
        
        # 1. Fetch target customer's ucid and pano
        if ano_int is not None:
            cur.execute("""
                SELECT ucid, pano, cid FROM v_all_customers
                WHERE vid = %s AND (ano = %s OR cid = %s)
                ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
                LIMIT 1
            """, (vid, ano_int, ano_int))
        else:
            cur.execute("""
                SELECT ucid, pano, cid FROM v_all_customers
                WHERE vid = %s AND CAST(ano AS TEXT) = %s
                ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
                LIMIT 1
            """, (vid, account_no))
        t_row = cur.fetchone()

        rows = []
        if t_row and t_row[0] is not None:
            # Verified borrower with UCID: fetch all cycles in 0.13ms
            ucid = t_row[0]
            cur.execute("""
                SELECT
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, pano, created_at, aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                    base_amount, cutting_amount, interest_amount, interest_discount,
                    ucid, cycle_number, record_tier
                FROM v_all_customers
                WHERE ucid = %s
                ORDER BY cycle_number ASC, start_date ASC
            """, (ucid,))
            rows = cur.fetchall()
        else:
            # Fallback if no UCID linked yet: match on pano adjacency within village
            pano_val = str(t_row[1]).strip() if t_row and t_row[1] else ""
            if pano_val.endswith(".0"):
                pano_val = pano_val[:-2]

            cur.execute("""
                SELECT
                    cid, ano, name, vid, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, pano, created_at, aadhaar_number, notes, latitude, longitude, eid, phone_number, status,
                    customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                    base_amount, cutting_amount, interest_amount, interest_discount,
                    ucid, cycle_number, record_tier
                FROM v_all_customers
                WHERE vid = %s AND (
                    CAST(ano AS TEXT) = %s 
                    OR (%s != '' AND CAST(ano AS TEXT) = %s)
                    OR (%s != '' AND pano = %s)
                    OR pano = %s
                )
                ORDER BY start_date ASC
            """, (vid, account_no, pano_val, pano_val, account_no, account_no, account_no))
            rows = cur.fetchall()

        customers = []
        for row in rows:
            customer = {
                "cid": row[0],
                "ano": str(row[1]).strip() if row[1] is not None else "",
                "name": row[2],
                "vid": row[3],
                "start_date": row[4].isoformat() if row[4] else None,
                "end_date": row[5].isoformat() if row[5] else None,
                "total_amount": float(row[6] or 0),
                "paid_amount": float(row[7] or 0),
                "balance_amount": float(row[8] or 0),
                "installment_amount": float(row[9] or 0),
                "type": row[10],
                "period": row[11],
                "pano": str(row[12]).strip() if row[12] is not None else "",
                "created_at": row[13].isoformat() if row[13] else None,
                "aadhaar_number": row[14],
                "notes": row[15],
                "latitude": row[16],
                "longitude": row[17],
                "eid": row[18],
                "phone_number": row[19],
                "status": row[20],
                "customer_rating": float(row[21]) if row[21] is not None else None,
                "final_frozen_rating": float(row[22]) if row[22] is not None else None,
                "final_risk_level": row[23],
                "freeze_date": row[24].isoformat() if row[24] else None,
                "base_amount": float(row[25] or 0.0),
                "cutting_amount": float(row[26] or 0.0),
                "interest_amount": float(row[27] or 0.0),
                "interest_discount": float(row[28] or 0.0),
                "ucid": row[29] if len(row) > 29 else None,
                "cycle_number": row[30] if len(row) > 30 else 1,
                "record_tier": row[31] if len(row) > 31 else "active"
            }
            customers.append(customer)

        customers = format_customer_ratings_with_trends(cur, customers)

        customers = sorted(
            customers,
            key=lambda x: (
                x.get("cycle_number") or 1,
                int(str(x["ano"]).strip()) if str(x["ano"]).strip().isdigit() else 999999
            )
        )

        return jsonify({
            "success": True,
            "customers": customers
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e),
            "customers": []
        }), 500

    finally:
        cur.close()
        conn.close()


@app.route("/api/customer/<identifier>/borrower_360", methods=["GET"])
@login_required
def api_customer_borrower_360(identifier):
    vid = session.get("vid")
    user_level = session.get("level")
    
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        raw_id = str(identifier).strip()
        ucid = None
        if raw_id.upper().startswith("UCID-"):
            try:
                ucid = int(raw_id.upper().replace("UCID-", ""))
            except ValueError:
                pass
        elif raw_id.isdigit():
            id_val = int(raw_id)
            # 1. If village context is present, check if identifier matches CID or ANO in this village
            if vid:
                cur.execute("""
                    SELECT ucid FROM v_all_customers
                    WHERE (cid = %s OR (vid = %s AND ano = %s)) AND ucid IS NOT NULL
                    ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
                    LIMIT 1
                """, (id_val, vid, id_val))
                u_row = cur.fetchone()
                if u_row:
                    ucid = u_row[0]

            # 2. If not found in village context, check if direct UCID in customer_master
            if not ucid:
                cur.execute("SELECT ucid FROM customer_master WHERE ucid = %s", (id_val,))
                m_row = cur.fetchone()
                if m_row:
                    ucid = m_row[0]
                else:
                    cur.execute("""
                        SELECT ucid FROM v_all_customers
                        WHERE (cid = %s OR ano = %s) AND ucid IS NOT NULL
                        ORDER BY CASE WHEN record_tier = 'active' THEN 0 WHEN record_tier = 'closed' THEN 1 ELSE 2 END
                        LIMIT 1
                    """, (id_val, id_val))
                    u_row = cur.fetchone()
                    if u_row:
                        ucid = u_row[0]

        if not ucid:
            return jsonify(success=False, error="Borrower profile (UCID) not found for identifier"), 404

        # 1. Fetch Borrower Master info
        cur.execute("""
            SELECT 
                cm.ucid, cm.primary_name, cm.primary_vid, v.village_name, cm.phone_number, cm.aadhaar_number,
                cm.total_loan_cycles, cm.first_loan_date, cm.latest_loan_date,
                cm.lifetime_borrowed, cm.lifetime_repaid, cm.current_active_balance,
                cm.customer_risk_tier, cm.created_at,
                cm.lifetime_credit_score, cm.lifetime_on_time_ratio, cm.total_cycles_completed
            FROM customer_master cm
            LEFT JOIN village v ON cm.primary_vid = v.vid
            WHERE cm.ucid = %s
        """, (ucid,))
        master_row = cur.fetchone()
        if not master_row:
            return jsonify(success=False, error="Borrower record missing in master"), 404

        borrower_info = {
            "ucid": master_row[0],
            "ucid_display": f"UCID-{master_row[0]:05d}",
            "primary_name": master_row[1],
            "primary_vid": master_row[2],
            "village_name": master_row[3] or "",
            "phone_number": master_row[4] or "",
            "aadhaar_number": master_row[5] or "",
            "total_cycles": master_row[6] or 1,
            "first_loan_date": master_row[7].isoformat() if master_row[7] else None,
            "latest_loan_date": master_row[8].isoformat() if master_row[8] else None,
            "lifetime_borrowed": float(master_row[9] or 0.0),
            "lifetime_repaid": float(master_row[10] or 0.0),
            "current_active_balance": float(master_row[11] or 0.0),
            "customer_risk_tier": master_row[12] or "standard",
            "lifetime_credit_score": float(master_row[14]) if master_row[14] is not None else 100.0,
            "lifetime_on_time_ratio": float(master_row[15]) if master_row[15] is not None else 100.0,
            "total_cycles_completed": int(master_row[16] or 0)
        }

        # 2. Fetch All Cycles for this borrower from v_all_customers
        cur.execute("""
            SELECT 
                vac.cid, vac.ano, vac.name, vac.vid, v.village_name, vac.cycle_number, vac.record_tier,
                vac.start_date, vac.end_date, vac.total_amount, vac.paid_amount, vac.balance_amount,
                vac.installment_amount, vac.type, vac.period, vac.status, vac.customer_rating,
                vac.final_frozen_rating, vac.final_risk_level, vac.base_amount, vac.cutting_amount, vac.interest_amount
            FROM v_all_customers vac
            LEFT JOIN village v ON vac.vid = v.vid
            WHERE vac.ucid = %s
            ORDER BY vac.cycle_number ASC, vac.start_date ASC
        """, (ucid,))
        cycle_rows = cur.fetchall()
        cycles = []
        cids = []
        for r in cycle_rows:
            cids.append(r[0])
            cycles.append({
                "cid": r[0],
                "ano": r[1],
                "name": r[2],
                "vid": r[3],
                "village_name": r[4] or "",
                "cycle_number": r[5] or 1,
                "record_tier": r[6],
                "start_date": r[7].isoformat() if r[7] else None,
                "end_date": r[8].isoformat() if r[8] else None,
                "total_amount": float(r[9] or 0.0),
                "paid_amount": float(r[10] or 0.0),
                "balance_amount": float(r[11] or 0.0),
                "installment_amount": float(r[12] or 0.0),
                "type": r[13] or "W",
                "period": r[14] or 0,
                "status": r[15] or "closed",
                "customer_rating": float(r[16]) if r[16] is not None else 100.0,
                "final_risk_level": r[18] or "LOW",
                "base_amount": float(r[19] or 0.0),
                "cutting_amount": float(r[20] or 0.0),
                "interest_amount": float(r[21] or 0.0)
            })

        # 3. Fetch Payments across all cycles
        payments = []
        if cids:
            cur.execute("""
                SELECT pid, cid, ano, TO_CHAR(payment_date, 'YYYY-MM-DD') as p_date, amt,
                       cash_amount, upi_amount, payment_type, record_tier
                FROM v_all_payments
                WHERE cid = ANY(%s)
                ORDER BY payment_date DESC, pid DESC
                LIMIT 100
            """, (cids,))
            for pr in cur.fetchall():
                payments.append({
                    "pid": pr[0],
                    "cid": pr[1],
                    "ano": pr[2],
                    "payment_date": pr[3],
                    "amt": float(pr[4] or 0.0),
                    "cash_amount": float(pr[5] or 0.0) if pr[5] is not None else None,
                    "upi_amount": float(pr[6] or 0.0) if pr[6] is not None else None,
                    "payment_type": pr[7] or "CASH",
                    "record_tier": pr[8]
                })

        return jsonify(
            success=True,
            borrower=borrower_info,
            cycles=cycles,
            recent_payments=payments
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()


@app.route("/print_customer/<ano>")
@login_required
def print_customer(ano):
    vid = session.get("vid")

    if not vid:
        flash("Please select Village first", "warning")
        return redirect(url_for("dashboard"))

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Fetch customer from active + closed tables
        cur.execute("""
            SELECT
                cid,
                ano,
                name,
                pano,
                start_date,
                end_date,
                total_amount,
                paid_amount,
                balance_amount,
                installment_amount,
                type,
                period,
                phone_number,
                status
            FROM (
                SELECT
                    cid,
                    ano,
                    name,
                    pano,
                    start_date,
                    end_date,
                    total_amount,
                    paid_amount,
                    balance_amount,
                    installment_amount,
                    type,
                    period,
                    phone_number,
                    'active' AS status
                FROM customer
                WHERE vid = %s

                UNION ALL

                SELECT
                    cid,
                    ano,
                    name,
                    pano,
                    start_date,
                    end_date,
                    total_amount,
                    paid_amount,
                    balance_amount,
                    installment_amount,
                    type,
                    period,
                    phone_number,
                    status
                FROM closed_cust_account
                WHERE vid = %s
            ) customer_data
            WHERE CAST(ano AS TEXT) = %s OR CAST(cid AS TEXT) = %s
            LIMIT 1
        """, (vid, vid, str(ano), str(ano)))

        customer = cur.fetchone()

        if not customer:
            return "Customer not found.", 404

        cur.execute("""
            SELECT
                ano,
                TO_CHAR(payment_date, 'DD-MM-YYYY') AS pdt,
                amt,
                pid
            FROM (
                SELECT ano, payment_date, amt, pid, cid
                FROM payment

                UNION ALL

                SELECT ano, payment_date, amt, pid, cid
                FROM closed_cust_payment
            ) payment_data
            WHERE cid = %s
            ORDER BY payment_date, pid
        """, (customer[0],))

        payments = cur.fetchall()

        customer_data = {
            "cid": customer[0],
            "ano": customer[1],
            "name": customer[2],
            "pano": customer[3],
            "start_date": format_date_display(customer[4]),
            "end_date": format_date_display(customer[5]),
            "total_amount": float(customer[6] or 0),
            "paid_amount": float(customer[7] or 0),
            "balance_amount": float(customer[8] or 0),
            "installment_amount": float(customer[9] or 0),
            "type": customer[10],
            "period": customer[11],
            "status": customer[12],
            "phone_number": customer[13]
        }

        payments_data = [
            {
                "ano": row[0],
                "pdt": row[1],
                "amt": float(row[2] or 0),
                "pid": row[3]
            }
            for row in payments
        ]

        return render_template(
            "customer_print.html",
            customer=customer_data,
            payments=payments_data
        )

    except Exception as e:
        traceback.print_exc()
        return f"Something went wrong: {e}", 500

    finally:
        cur.close()
        conn.close()


@app.route("/api/customer/close_account_pg", methods=["POST"])
@login_required
def close_customer_account_pg():
    conn = None
    cur = None
    try:
        data = request.get_json()
        cid = data.get("cid")
        action = data.get("action")  # 'defaulted' or 'written_off' or 'discount_interest' or None
        discount_amount = data.get("discount_amount")

        if not cid:
            return jsonify({"success": False, "error": "Missing customer id"})

        conn = get_pg_connection()
        cur = conn.cursor()

        # Lock row (prevents race conditions)
        cur.execute("""
            SELECT total_amount, paid_amount, balance_amount, status, vid, interest_amount, COALESCE(interest_discount, 0.00)
            FROM customer
            WHERE cid = %s
            FOR UPDATE
        """, (cid,))

        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "Customer not found"})

        total_amount, paid_amount, balance_amount, current_status, vid, interest_amount, interest_discount = row

        # -------------------------------
        # STATUS DECISION LOGIC
        # -------------------------------
        if balance_amount == 0:
            final_status = "closed"

        elif balance_amount > 0:
            if action == "discount_interest":
                if discount_amount is None:
                    conn.rollback()
                    return jsonify({"success": False, "error": "Missing discount amount"})
                try:
                    discount_val = Decimal(str(discount_amount))
                except Exception:
                    conn.rollback()
                    return jsonify({"success": False, "error": "Invalid discount amount"})

                if discount_val <= 0:
                    conn.rollback()
                    return jsonify({"success": False, "error": "Discount amount must be greater than 0"})

                if balance_amount > interest_amount:
                    conn.rollback()
                    return jsonify({"success": False, "error": "Balance is greater than interest amount. Cannot apply discount."})

                new_discount = Decimal(str(interest_discount)) + discount_val
                new_balance = balance_amount - discount_val

                cur.execute("""
                    UPDATE customer
                    SET interest_discount = %s,
                        balance_amount = %s
                    WHERE cid = %s
                """, (new_discount, new_balance, cid))

                balance_amount = new_balance
                final_status = "closed"
            elif action == "defaulted":
                final_status = "defaulted"
            else:
                conn.rollback()
                return jsonify({
                    "success": False,
                    "error": "Balance > 0. Must mark as defaulted or discount interest."
                })

        else:  # balance_amount < 0
            if action != "written_off":
                conn.rollback()
                return jsonify({
                    "success": False,
                    "error": "Balance < 0. Must mark as written_off."
                })
            final_status = "written_off"

        # -------------------------------
        # MOVE DATA (NOT COPY)
        # -------------------------------

        # Recalculate and freeze rating in customer table before moving
        recalc_customer_repayment_score(cur, cid, force_recalc=True)

        # Move customer (explicit columns to avoid mismatch)
        cur.execute("""
            INSERT INTO closed_cust_account (
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, status, phone_number,
                closed_by, closed_at,
                customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                base_amount, cutting_amount, interest_amount, interest_discount
            )
            SELECT
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, %s, phone_number,
                %s, NOW() AT TIME ZONE 'Asia/Kolkata',
                customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                base_amount, cutting_amount, interest_amount, interest_discount
            FROM customer
            WHERE cid = %s
        """, (final_status, session.get("employee_id") or session.get("eid"), cid))

        # 2ï¸âƒ£ Move payments (explicit columns)
        cur.execute("""
            INSERT INTO closed_cust_payment (
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            )
            SELECT
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            FROM payment
            WHERE cid = %s
        """, (cid,))

        # 4ï¸âƒ£ Delete from active tables (this makes it MOVE)
        cur.execute("DELETE FROM payment WHERE cid = %s", (cid,))
        cur.execute("DELETE FROM customer WHERE cid = %s", (cid,))

        audit_log(
            action="close_customer_account",
            entity_type="customer",
            entity_id=cid,
            details={
                "status": final_status,
                "paid_amount": str(paid_amount),
                "balance_amount": str(balance_amount)
            }
        )
        # Invalidate cache for this village
        KOLKATA = pytz.timezone('Asia/Kolkata')
        today = datetime.now(KOLKATA).date()
        invalidate_village_health_cache(cur, vid, today)
        conn.commit()

        return jsonify({
            "success": True,
            "status": final_status
        })

    except Exception as e:
        conn.rollback() # type: ignore
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})
    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()

# ------------------ NEW: Retrieve closed/defaulted/written_off account ------------------
@app.route("/api/customer/retrieve_account_pg", methods=["POST"])
@login_required
def retrieve_customer_account_pg():
    conn = None
    cur = None
    try:
        data = request.get_json()
        cid = data.get("cid")

        if not cid:
            return jsonify({"success": False, "error": "Missing customer id"})

        conn = get_pg_connection()
        cur = conn.cursor()        # Move customer BACK to customer table
        cur.execute("""
            INSERT INTO customer (
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, phone_number,
                base_amount, cutting_amount, interest_amount, interest_discount
            ) OVERRIDING SYSTEM VALUE
            SELECT
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, phone_number,
                base_amount, cutting_amount, interest_amount, interest_discount
            FROM closed_cust_account
            WHERE cid = %s
        """, (cid,))

        # 2ï¸âƒ£ Move payments BACK
        cur.execute("""
            INSERT INTO payment (
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            ) OVERRIDING SYSTEM VALUE
            SELECT
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            FROM closed_cust_payment
            WHERE cid = %s
        """, (cid,))

        # 3ï¸âƒ£ Delete from closed tables
        cur.execute("DELETE FROM closed_cust_payment WHERE cid = %s", (cid,))
        cur.execute("DELETE FROM closed_cust_account WHERE cid = %s", (cid,))

        # 4ï¸âƒ£ Unfreeze rating columns in customer table
        cur.execute("""
            UPDATE customer
            SET final_frozen_rating = NULL,
                final_risk_level = NULL,
                freeze_date = NULL
            WHERE cid = %s
        """, (cid,))

        # 5ï¸âƒ£ Recalculate rating for reactivated loan
        recalc_customer_repayment_score(cur, cid, force_recalc=True)

        # Invalidate cache for this village
        cur.execute("SELECT vid, start_date FROM customer WHERE cid = %s", (cid,))
        vid_row = cur.fetchone()
        if vid_row:
            c_vid, start_date = vid_row
            start_dt = start_date.date() if isinstance(start_date, datetime) else start_date
            invalidate_village_health_cache(cur, c_vid, start_dt)

        audit_log(
            action="retrieve_customer_account",
            entity_type="customer",
            entity_id=cid
        )
        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        conn.rollback() # type: ignore
        return jsonify({"success": False, "error": str(e)})

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()

@app.route("/api/update_village", methods=["POST"])
@login_required
def update_village():
    data = request.get_json()

    vid = data.get("vid")
    if not vid:
        return jsonify(success=False, error="Missing vid")

    conn = get_pg_connection()
    cur = conn.cursor()

    village_code = (data.get("village_code") or "").strip().upper()
    village_name = (data.get("village_name") or "").strip().upper()

        # ðŸ”’ Prevent duplicate village code / village name
    cur.execute("""
            SELECT vid, village_code, village_name
            FROM village
            WHERE vid != %s
              AND (
                    LOWER(village_code) = LOWER(%s)
                    OR LOWER(village_name) = LOWER(%s)
                  )
            LIMIT 1
        """, (
            vid,
            village_code,
            village_name
        ))

    existing = cur.fetchone()

    if existing:
        existing_vid, existing_code, existing_name = existing

            # Same code + same name
        if (
            existing_code
            and existing_name
            and existing_code.strip().lower() == village_code.lower()
            and existing_name.strip().lower() == village_name.lower()
        ):
            return jsonify(
                success=False,
                error="Another village already exists with same code and village name"
            )

            # Same village code
        if (
            existing_code
            and existing_code.strip().lower() == village_code.lower()
        ):
            return jsonify(
                success=False,
                error=f"Village code '{village_code}' already exists"
            )

            # Same village name
        if (
            existing_name
            and existing_name.strip().lower() == village_name.lower()
        ):
            return jsonify(
                success=False,
                error=f"Village name '{village_name}' already exists"
            )

    try:
        district = (data.get("district") or "").strip().upper()
        pincode = (data.get("pincode") or "").strip().upper()
        state = (data.get("state") or "").strip().upper()

        cur.execute("""
            UPDATE village
            SET
              village_code = %s,
              village_name = %s,
              district = %s,
              pincode = %s,
              state = %s,
              emp1 = %s,
              emp2 = %s,
              interest_rate = %s,
              cutting_rate = %s
            WHERE vid = %s
        """, (
            village_code,
            village_name,
            district,
            pincode,
            state,
            data.get("emp1"),
            data.get("emp2"),
            float(data.get("interest_rate") or 0.0),
            float(data.get("cutting_rate") or 0.0),
            vid
        ))

        conn.commit()
        audit_log(
            action="update_village",
            entity_type="village",
            entity_id=vid,
            details={
                "village_code": village_code,
                "village_name": village_name,
                "district": district,
                "pincode": pincode,
                "state": state,
                "emp1": data.get("emp1"),
                "emp2": data.get("emp2")
            }
        )
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e))

    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------
@app.route("/api/customers/recalculate_split", methods=["POST"])
@login_required
def api_recalculate_split():
    """Recalculate customer base_amount, interest_amount, cutting_amount split from total_amount using village rates."""
    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="No village selected"), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Fetch rates from village table
        cur.execute("SELECT interest_rate, cutting_rate FROM village WHERE vid = %s", (vid,))
        row = cur.fetchone()
        if not row:
            return jsonify(success=False, error="Village not found"), 404

        interest_rate = float(row[0]) if row[0] is not None else 0.0
        cutting_rate = float(row[1]) if row[1] is not None else 0.0

        # Update customer table (active customers)
        cur.execute("""
            SELECT cid, total_amount FROM customer WHERE vid = %s
        """, (vid,))
        customers = cur.fetchall()
        for cid, total_amount in customers:
            total = float(total_amount or 0)
            interest = float(round(total * (interest_rate / 100.0)))
            cutting = float(round(total * (cutting_rate / 100.0)))
            base = float(total - interest - cutting)
            cur.execute("""
                UPDATE customer
                SET interest_amount = %s, cutting_amount = %s, base_amount = %s
                WHERE cid = %s
            """, (interest, cutting, base, cid))

        # Update closed_cust_account table (all closed customers)
        cur.execute("""
            SELECT cid, total_amount FROM closed_cust_account WHERE vid = %s
        """, (vid,))
        closed_customers = cur.fetchall()
        for cid, total_amount in closed_customers:
            total = float(total_amount or 0)
            interest = float(round(total * (interest_rate / 100.0)))
            cutting = float(round(total * (cutting_rate / 100.0)))
            base = float(total - interest - cutting)
            cur.execute("""
                UPDATE closed_cust_account
                SET interest_amount = %s, cutting_amount = %s, base_amount = %s
                WHERE cid = %s
            """, (interest, cutting, base, cid))
                                            
        # Update historic_customer_data table (historic customers)
        cur.execute("""
            SELECT cid, total_amount FROM historic_customer_data WHERE vid = %s
        """, (vid,))
        historic_customers = cur.fetchall()
        for cid, total_amount in historic_customers:
            total = float(total_amount or 0)
            interest = float(round(total * (interest_rate / 100.0)))
            cutting = float(round(total * (cutting_rate / 100.0)))
            base = float(total - interest - cutting)
            cur.execute("""
                UPDATE historic_customer_data
                SET interest_amount = %s, cutting_amount = %s, base_amount = %s
                WHERE cid = %s
            """, (interest, cutting, base, cid))

        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        logger.error(f"Error recalculating split amounts: {e}")
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/feed")
@login_required
def feed():
    logger.debug("Accessing feed page")
    vid = session.get("vid")
    if not vid:
        return redirect("/dashboard")
    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Fetch village mapping
        village_map = {}
        try:
            cur.execute("SELECT vid, village_name FROM village")
            village_map = {row[0]: row[1] for row in cur.fetchall()}
        except Exception as ve:
            logger.warning(f"Failed to fetch village_map: {ve}")

        # CUSTOMER FEED
        cur.execute("""
            SELECT
                cf.feed_id,
                cf.payload,
                cf.status,
                cf.vid,
                COALESCE(
                    (cf.payload->'payload'->>'ano')::INT,
                    (cf.payload->>'ano')::INT
                ) AS ano,
                COALESCE(
                    cf.payload->'payload'->>'name',
                    cf.payload->>'name'
                ) AS name,
                COALESCE(
                    cf.payload->'payload'->>'type',
                    cf.payload->>'type'
                ) AS type,
                COALESCE(feed_docs.aadhaar_front_pic, docs.aadhaar_front_pic) AS aadhaar_front_pic,
                COALESCE(feed_docs.aadhaar_back_pic, docs.aadhaar_back_pic) AS aadhaar_back_pic,
                COALESCE(feed_docs.house_photo, docs.house_photo) AS house_photo,
                v.village_name
            FROM customer_feed cf
            LEFT JOIN village v ON v.vid = cf.vid
            LEFT JOIN LATERAL (
                SELECT
                    cdf.aadhaar_front_pic,
                    cdf.aadhaar_back_pic,
                    cdf.house_photo
                FROM customer_docs_feed cdf
                WHERE cdf.vid = cf.vid
                  AND cdf.status = 'pending'
                  AND cdf.ano = COALESCE(
                      (cf.payload->'payload'->>'ano')::INT,
                      (cf.payload->>'ano')::INT
                  )
                ORDER BY cdf.created_at DESC NULLS LAST, cdf.docs_feed_id DESC
                LIMIT 1
            ) AS feed_docs ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    cd.aadhaar_front_pic,
                    cd.aadhaar_back_pic,
                    cd.house_photo
                FROM customer_docs cd
                WHERE cd.vid = cf.vid
                  AND cd.ano = COALESCE(
                      (cf.payload->'payload'->>'ano')::INT,
                      (cf.payload->>'ano')::INT
                  )
                ORDER BY cd.uploaded_at DESC NULLS LAST, cd.doc_id DESC
                LIMIT 1
            ) AS docs ON TRUE
            WHERE cf.vid = %s AND cf.status='pending'
            ORDER BY cf.feed_id DESC
        """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore

        customers = []
        for r in rows:
            row_dict = dict(zip(columns, r))

            payload = row_dict.get("payload")

            # âœ… Normalize payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            elif payload is None:
                payload = {}

            customer_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
            # ✅ Flatten payload into row_dict (VERY IMPORTANT)
            row_dict.update({
                "ano": customer_payload.get("ano"), # type: ignore
                "name": customer_payload.get("name"), # type: ignore
                "pano": customer_payload.get("pano"), # type: ignore
                "phone_number": customer_payload.get("phone_number"), # type: ignore
                "type": customer_payload.get("type"), # type: ignore
                "period": customer_payload.get("period"), # type: ignore
                "start_date": customer_payload.get("start_date"), # type: ignore
                "end_date": customer_payload.get("end_date"), # type: ignore
                "total_amount": customer_payload.get("total_amount"), # type: ignore
                "installment_amount": customer_payload.get("installment_amount"), # type: ignore
                "aadhaar_number": customer_payload.get("aadhaar_number"), # type: ignore
                "notes": customer_payload.get("notes"), # type: ignore
                "latitude": customer_payload.get("latitude"), # type: ignore
                "longitude": customer_payload.get("longitude"), # type: ignore
                "eid": customer_payload.get("eid"), # type: ignore
                "vid": customer_payload.get("vid"), # type: ignore
            })

            # Resolved village_name
            row_dict["village_name"] = (
                row_dict.get("village_name")
                or customer_payload.get("village_name")
                or village_map.get(row_dict.get("vid"))
                or session.get("village_name")
                or (f"Village {row_dict.get('vid')}" if row_dict.get('vid') else "Village")
            )

            # keep payload also (optional)
            row_dict["payload"] = customer_payload
            row_dict["raw_payload"] = payload

            # format dates for HTML5 date inputs (must be yyyy-mm-dd)
            if row_dict.get("start_date"):
                row_dict["start_date"] = format_date_iso(row_dict["start_date"])
            if row_dict.get("end_date"):
                row_dict["end_date"] = format_date_iso(row_dict["end_date"])

            customers.append(row_dict)
        # PAYMENT FEED (Left join customer by vid and ano to detect mapped/unmapped status)
        cur.execute("""
        SELECT
            pfi.feed_payment_id,
            pfi.local_uuid,
            pfi.payload->>'ano' AS ano,
            pfi.payload->>'amt' AS amt,
            COALESCE(pfi.payload->>'payment_date', pfi.payload->>'pdate') AS pdt,
            COALESCE(pfi.payload->>'payment_type', 'cash') AS payment_type,
            pfi.payload->>'cash_amount' AS cash_amount,
            pfi.payload->>'upi_amount' AS upi_amount,
            pfi.payload->>'vid' AS vid,
            pfi.status,
            c.cid,
            c.name AS customer_name,
            c.start_date AS customer_start_date
        FROM payment_feed_items pfi
        LEFT JOIN LATERAL (
            SELECT cid, name, start_date
            FROM customer c
            WHERE c.vid = (pfi.payload->>'vid')::INT
              AND c.ano = (pfi.payload->>'ano')::INT
            ORDER BY c.cid DESC
            LIMIT 1
        ) c ON TRUE
        WHERE pfi.status='pending'
          AND (pfi.payload->>'vid')::INT = %s
        ORDER BY pfi.feed_payment_id DESC
    """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore

        payments = [dict(zip(columns, r)) for r in rows]
        for p in payments:
            raw_pdt = p.get("pdt")
            p["display_date"] = format_date_display(raw_pdt)
            p["iso_date"] = format_date_iso(raw_pdt)
            p["pdt"] = p["display_date"]

        cur.execute("""
            SELECT
                cdf.docs_feed_id,
                cdf.local_uuid,
                cdf.vid,
                cdf.ano,
                cdf.eid,
                cdf.cid,
                cdf.aadhaar_front_pic,
                cdf.aadhaar_back_pic,
                cdf.house_photo,
                cdf.status,
                cdf.created_at,
                COALESCE(
                    c.name,
                    cf.payload->>'name',
                    'Customer ' || cdf.ano::text
                ) AS name
            FROM customer_docs_feed cdf
            LEFT JOIN LATERAL (
                SELECT cid, name
                FROM customer c
                WHERE c.vid = cdf.vid
                  AND c.ano = cdf.ano
                ORDER BY c.cid DESC
                LIMIT 1
            ) c ON TRUE
            LEFT JOIN LATERAL (
                SELECT payload
                FROM customer_feed cf_inner
                WHERE cf_inner.vid = cdf.vid
                  AND cf_inner.status = 'pending'
                  AND (cf_inner.payload->>'ano')::bigint = cdf.ano
                ORDER BY cf_inner.feed_id DESC
                LIMIT 1
            ) cf ON TRUE
            WHERE cdf.vid = %s
              AND cdf.status = 'pending'
              AND c.cid IS NOT NULL
            ORDER BY cdf.docs_feed_id DESC
        """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore
        existing_customer_docs = [dict(zip(columns, r)) for r in rows]

        # Fetch customer edits submitted from mobile (customer_feed_edits)
        customer_edit_map = {}
        try:
            cur.execute("""
                SELECT local_uuid, edited_payload
                FROM customer_feed_edits
                WHERE edit_status = 'pending'
            """)
            for edit_row in cur.fetchall():
                ep = edit_row[1]
                if isinstance(ep, str):
                    try:
                        ep = json.loads(ep)
                    except Exception:
                        ep = {}
                customer_edit_map[edit_row[0]] = ep
        except Exception:
            conn.rollback()  # Table may not exist yet on first run; rollback aborted transaction

        # Attach edits to customers (match by local_uuid stored in customer_feed)
        for c in customers:
            local_uuid = None
            raw = c.get("raw_payload") or {}
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    raw = {}
            local_uuid = raw.get("local_uuid") or c.get("local_uuid")
            edit = customer_edit_map.get(local_uuid) if local_uuid else None
            if edit:
                if edit.get("start_date"):
                    edit["start_date"] = format_date_iso(edit["start_date"])
                if edit.get("end_date"):
                    edit["end_date"] = format_date_iso(edit["end_date"])
            c["edit"] = edit

        # Pre-screen duplicate Aadhaar cards across pending customer registrations
        feed_aadhaars = set()
        for c in customers:
            raw_a = str((c.get("edit") and c.get("edit", {}).get("aadhaar_number")) or c.get("aadhaar_number") or "").replace(" ", "").replace("-", "").strip()
            clean_a = "".join(ch for ch in raw_a if ch.isdigit())
            if len(clean_a) == 12:
                feed_aadhaars.add(clean_a)

        aadhaar_dupe_map = {}
        if feed_aadhaars:
            try:
                cur.execute("""
                    SELECT 
                        c.cid,
                        c.vid,
                        COALESCE(v.village_name, 'Village ' || c.vid::text) AS village_name,
                        c.ano,
                        c.name,
                        c.phone_number,
                        c.start_date,
                        c.end_date,
                        c.total_amount,
                        c.balance_amount,
                        COALESCE(c.status, 'open') AS status,
                        REPLACE(REPLACE(COALESCE(c.aadhaar_number, ''), ' ', ''), '-', '') AS clean_aadhaar
                    FROM customer c
                    LEFT JOIN village v ON v.vid = c.vid
                    WHERE REPLACE(REPLACE(COALESCE(c.aadhaar_number, ''), ' ', ''), '-', '') = ANY(%s)
                    UNION ALL
                    SELECT 
                        ca.cid,
                        ca.vid,
                        COALESCE(v.village_name, 'Village ' || ca.vid::text) AS village_name,
                        ca.ano,
                        ca.name,
                        ca.phone_number,
                        ca.start_date,
                        ca.end_date,
                        ca.total_amount,
                        ca.balance_amount,
                        'closed' AS status,
                        REPLACE(REPLACE(COALESCE(ca.aadhaar_number, ''), ' ', ''), '-', '') AS clean_aadhaar
                    FROM closed_cust_account ca
                    LEFT JOIN village v ON v.vid = ca.vid
                    WHERE REPLACE(REPLACE(COALESCE(ca.aadhaar_number, ''), ' ', ''), '-', '') = ANY(%s)
                    ORDER BY cid DESC
                """, (list(feed_aadhaars), list(feed_aadhaars)))
                dupe_rows = cur.fetchall()
                for dr in dupe_rows:
                    a_key = dr[11]
                    if a_key not in aadhaar_dupe_map:
                        aadhaar_dupe_map[a_key] = []
                    aadhaar_dupe_map[a_key].append({
                        "cid": dr[0],
                        "vid": dr[1],
                        "village_name": dr[2] or f"Village {dr[1]}",
                        "ano": dr[3],
                        "name": dr[4] or "Unnamed",
                        "phone_number": dr[5] or "",
                        "start_date": format_date_display(str(dr[6])) if dr[6] else "",
                        "end_date": format_date_display(str(dr[7])) if dr[7] else "",
                        "total_amount": float(dr[8] or 0),
                        "balance_amount": float(dr[9] or 0),
                        "status": dr[10] or "open"
                    })
            except Exception as e:
                logger.error(f"Error pre-screening duplicate aadhaars for feed: {e}")

        for c in customers:
            raw_a = str((c.get("edit") and c.get("edit", {}).get("aadhaar_number")) or c.get("aadhaar_number") or "").replace(" ", "").replace("-", "").strip()
            clean_a = "".join(ch for ch in raw_a if ch.isdigit())
            dupes = aadhaar_dupe_map.get(clean_a, [])
            c["duplicate_accounts"] = dupes
            c["duplicate_count"] = len(dupes)

        # Fetch payment edits submitted from mobile (payment_feed_edits)
        payment_edit_map = {}
        try:
            cur.execute("""
                SELECT local_uuid, edited_payload
                FROM payment_feed_edits
                WHERE edit_status = 'pending'
            """)
            for edit_row in cur.fetchall():
                ep = edit_row[1]
                if isinstance(ep, str):
                    try:
                        ep = json.loads(ep)
                    except Exception:
                        ep = {}
                payment_edit_map[edit_row[0]] = ep
        except Exception:
            conn.rollback()  # Table may not exist yet on first run; rollback aborted transaction

        # Attach edits to payments and re-verify cid if ano was edited
        for p in payments:
            local_uuid = p.get("local_uuid")
            edit = payment_edit_map.get(local_uuid) if local_uuid else None
            p["edit"] = edit
            if edit and edit.get("ano"):
                try:
                    edited_ano = int(edit["ano"])
                    cur.execute(
                        "SELECT cid, name, start_date FROM customer WHERE vid = %s AND ano = %s",
                        (vid, edited_ano)
                    )
                    cust_match = cur.fetchone()
                    if cust_match:
                        p["cid"] = cust_match[0]
                        p["customer_name"] = cust_match[1]
                        p["customer_start_date"] = cust_match[2]
                    else:
                        p["cid"] = None
                        p["customer_name"] = None
                except Exception:
                    pass

        # ACCOUNT CLOSURE FEED
        cur.execute("""
            SELECT
                acf.feed_id,
                acf.local_uuid,
                acf.device_id,
                acf.eid,
                acf.vid,
                acf.ano,
                acf.status,
                acf.created_at,
                COALESCE(c.name, ca.name, 'Customer Not Found') AS name,
                COALESCE(c.cid, ca.cid) AS cid,
                COALESCE(c.total_amount, ca.total_amount, 0) AS total_amount,
                COALESCE(c.paid_amount, ca.paid_amount, 0) AS paid_amount,
                COALESCE(c.balance_amount, ca.balance_amount, 0) AS balance_amount,
                COALESCE(c.interest_amount, ca.interest_amount, 0) AS interest_amount,
                COALESCE(c.type, ca.type, 'weekly') AS type,
                COALESCE(c.period, ca.period, 0) AS period,
                COALESCE(c.installment_amount, ca.installment_amount, 0) AS installment_amount,
                COALESCE(c.start_date, ca.start_date) AS start_date,
                COALESCE(c.end_date, ca.end_date) AS end_date,
                COALESCE(c.phone_number, ca.phone_number, '') AS phone_number,
                COALESCE(c.aadhaar_number, ca.aadhaar_number, '') AS aadhaar_number,
                COALESCE(c.notes, ca.notes, '') AS notes,
                COALESCE(c.latitude, ca.latitude) AS latitude,
                COALESCE(c.longitude, ca.longitude) AS longitude,
                COALESCE(c.status, ca.status, 'open') AS account_status,
                COALESCE(v.village_name, 'Village ' || acf.vid::text) AS village_name,
                docs.aadhaar_front_pic,
                docs.aadhaar_back_pic,
                docs.house_photo
            FROM account_closure_feed acf
            LEFT JOIN LATERAL (
                SELECT cid, name, total_amount, paid_amount, balance_amount, interest_amount, type, period, installment_amount, start_date, end_date, phone_number, aadhaar_number, notes, latitude, longitude, status
                FROM customer c
                WHERE c.vid = acf.vid
                  AND c.ano = acf.ano
                ORDER BY c.cid DESC
                LIMIT 1
            ) c ON TRUE
            LEFT JOIN LATERAL (
                SELECT cid, name, total_amount, paid_amount, balance_amount, interest_amount, type, period, installment_amount, start_date, end_date, phone_number, aadhaar_number, notes, latitude, longitude, status
                FROM closed_cust_account ca
                WHERE ca.vid = acf.vid
                  AND ca.ano = acf.ano
                ORDER BY ca.cid DESC
                LIMIT 1
            ) ca ON TRUE
            LEFT JOIN village v
              ON v.vid = acf.vid
            LEFT JOIN LATERAL (
                SELECT cd.aadhaar_front_pic, cd.aadhaar_back_pic, cd.house_photo
                FROM customer_docs cd
                WHERE cd.vid = acf.vid AND cd.ano = acf.ano
                ORDER BY cd.uploaded_at DESC NULLS LAST, cd.doc_id DESC
                LIMIT 1
            ) docs ON TRUE
            WHERE acf.vid = %s AND acf.status = 'pending'
            ORDER BY acf.feed_id DESC
        """, (vid,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore
        closure_requests = [dict(zip(columns, r)) for r in rows]

        for req in closure_requests:
            for pic_key in ("aadhaar_front_pic", "aadhaar_back_pic", "house_photo"):
                pic_val = req.get(pic_key)
                if isinstance(pic_val, memoryview):
                    req[pic_key] = base64.b64encode(pic_val.tobytes()).decode("ascii")
                elif isinstance(pic_val, (bytes, bytearray)):
                    req[pic_key] = base64.b64encode(pic_val).decode("ascii")

            if req.get("created_at"):
                try:
                    dt = req["created_at"]
                    if hasattr(dt, "strftime"):
                        req["created_at_display"] = dt.strftime("%d %b %Y, %I:%M %p")
                    else:
                        req["created_at_display"] = str(dt)
                except Exception:
                    req["created_at_display"] = str(req.get("created_at"))
            else:
                req["created_at_display"] = "Recently"

            if req.get("start_date"):
                try:
                    s_dt = req["start_date"]
                    req["start_date_display"] = s_dt.strftime("%d %b %Y") if hasattr(s_dt, "strftime") else str(s_dt)
                except Exception:
                    req["start_date_display"] = str(req.get("start_date"))
            else:
                req["start_date_display"] = "—"

            if req.get("end_date"):
                try:
                    e_dt = req["end_date"]
                    req["end_date_display"] = e_dt.strftime("%d %b %Y") if hasattr(e_dt, "strftime") else str(e_dt)
                except Exception:
                    req["end_date_display"] = str(req.get("end_date"))
            else:
                req["end_date_display"] = "—"

            t_raw = str(req.get("type") or "W").upper()
            if t_raw in ("W", "WEEKLY"):
                req["type_display"] = "Weekly"
                req["installment_freq"] = "/ week"
            elif t_raw in ("D", "DAILY"):
                req["type_display"] = "Daily"
                req["installment_freq"] = "/ day"
            elif t_raw in ("M", "MONTHLY"):
                req["type_display"] = "Monthly"
                req["installment_freq"] = "/ month"
            else:
                req["type_display"] = req.get("type", "Standard")
                req["installment_freq"] = ""

        # Highest account number recorded in DB for this village
        cur.execute("SELECT COALESCE(MAX(ano), 0) FROM customer WHERE vid = %s", (vid,))
        max_ano_res = cur.fetchone()
        max_ano = max_ano_res[0] if max_ano_res and max_ano_res[0] else 0

        # Highest payment date recorded in DB for this village
        cur.execute("SELECT MAX(payment_date) FROM payment WHERE vid = %s", (vid,))
        max_pdt_res = cur.fetchone()
        max_payment_date = max_pdt_res[0] if max_pdt_res and max_pdt_res[0] else None
        max_payment_date_display = format_date_display(str(max_payment_date)) if max_payment_date else "No payments yet"

        # Calculate pending summary totals for All Queues Dashboard
        def _parse_dec(val):
            try:
                return Decimal(str(val)) if val is not None else Decimal(0)
            except Exception:
                return Decimal(0)

        pending_payments_total = sum(
            _parse_dec(p.get("edit", {}).get("amt") if p.get("edit") and p.get("edit", {}).get("amt") else p.get("amt"))
            for p in payments
        )
        pending_customers_total = sum(
            _parse_dec(c.get("edit", {}).get("total_amount") if c.get("edit") and c.get("edit", {}).get("total_amount") else c.get("total_amount"))
            for c in customers
        )
        pending_closures_total = sum(_parse_dec(cl.get("balance_amount")) for cl in closure_requests)

        return render_template(
            "feed.html",
            customers=customers,
            payments=payments,
            existing_customer_docs=existing_customer_docs,
            closure_requests=closure_requests,
            village_map=village_map,
            max_ano=max_ano,
            max_payment_date_display=max_payment_date_display,
            pending_payments_total=pending_payments_total,
            pending_customers_total=pending_customers_total,
            pending_closures_total=pending_closures_total
        )

    finally:
        cur.close()
        conn.close()


@app.post("/feed/closure/accept/<feed_id>")
@login_required
def accept_closure_request(feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        action = data.get("action")  # 'defaulted' or 'written_off' or 'discount_interest' or None
        discount_amount = data.get("discount_amount")

        conn = get_pg_connection()
        cur = conn.cursor()

        # Get the feed item
        cur.execute("""
            SELECT ano, vid, status
            FROM account_closure_feed
            WHERE feed_id = %s
        """, (feed_id,))
        feed_row = cur.fetchone()
        if not feed_row:
            return jsonify({"success": False, "error": "Closure request not found"}), 404

        ano, vid, status = feed_row
        if status != 'pending':
            return jsonify({"success": False, "error": "Closure request already processed"}), 400

        # Find the customer
        cur.execute("""
            SELECT cid, total_amount, paid_amount, balance_amount, interest_amount, COALESCE(interest_discount, 0.00)
            FROM customer
            WHERE ano = %s AND vid = %s
            FOR UPDATE
        """, (ano, vid))
        cust_row = cur.fetchone()
        if not cust_row:
            cur.execute("SELECT cid FROM closed_cust_account WHERE ano = %s AND vid = %s", (ano, vid))
            closed_row = cur.fetchone()
            if closed_row:
                cur.execute("UPDATE account_closure_feed SET status = 'accepted' WHERE feed_id = %s", (feed_id,))
                conn.commit()
                return jsonify({"success": True, "message": "Customer account was already closed; closure feed request marked as accepted."})
            return jsonify({"success": False, "error": f"Customer with Account Number {ano} not found in this village"}), 404

        cid, total_amount, paid_amount, balance_amount, interest_amount, interest_discount = cust_row

        # status decision logic (identical to close_customer_account_pg)
        if balance_amount == 0:
            final_status = "closed"
        elif balance_amount > 0:
            if action == "discount_interest":
                if discount_amount is None:
                    return jsonify({"success": False, "error": "Missing discount amount"}), 400
                try:
                    discount_val = Decimal(str(discount_amount))
                except Exception:
                    return jsonify({"success": False, "error": "Invalid discount amount"}), 400

                if discount_val <= 0:
                    return jsonify({"success": False, "error": "Discount amount must be greater than 0"}), 400

                if balance_amount > interest_amount:
                    return jsonify({"success": False, "error": "Balance is greater than interest amount. Cannot apply discount."}), 400

                new_discount = Decimal(str(interest_discount)) + discount_val
                new_balance = balance_amount - discount_val

                cur.execute("""
                    UPDATE customer
                    SET interest_discount = %s,
                        balance_amount = %s
                    WHERE cid = %s
                """, (new_discount, new_balance, cid))

                balance_amount = new_balance
                final_status = "closed"
            elif action == "defaulted":
                final_status = "defaulted"
            else:
                return jsonify({
                    "success": False,
                    "error": "Balance > 0. Must mark as defaulted or discount interest."
                }), 400
        else: # balance_amount < 0
            if action != "written_off":
                return jsonify({
                    "success": False,
                    "error": "Balance < 0. Must mark as written_off."
                }), 400
            final_status = "written_off"

        # Recalculate and freeze rating in customer table before moving
        recalc_customer_repayment_score(cur, cid, force_recalc=True)

        # Move customer
        cur.execute("""
            INSERT INTO closed_cust_account (
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, status, phone_number,
                closed_by, closed_at,
                customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                base_amount, cutting_amount, interest_amount, interest_discount
            )
            SELECT
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, %s, phone_number,
                %s, NOW() AT TIME ZONE 'Asia/Kolkata',
                customer_rating, final_frozen_rating, final_risk_level, freeze_date,
                base_amount, cutting_amount, interest_amount, interest_discount
            FROM customer
            WHERE cid = %s
        """, (final_status, session.get("employee_id") or session.get("eid"), cid))

        # Move payments
        cur.execute("""
            INSERT INTO closed_cust_payment (
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            )
            SELECT
                pid, ano, payment_date, amt,
                created_at, eid, cid, vid
            FROM payment
            WHERE cid = %s
        """, (cid,))

        # Delete from active tables
        cur.execute("DELETE FROM payment WHERE cid = %s", (cid,))
        cur.execute("DELETE FROM customer WHERE cid = %s", (cid,))

        # Mark all pending closure requests for this customer in this village as accepted
        cur.execute("""
            UPDATE account_closure_feed
            SET status = 'accepted'
            WHERE ano = %s AND vid = %s AND status = 'pending'
            RETURNING local_uuid
        """, (ano, vid))
        closed_uuids = [r[0] for r in cur.fetchall() if r[0]]

        # Invalidate village health cache (matching customer dashboard pipeline)
        KOLKATA = pytz.timezone('Asia/Kolkata')
        today = datetime.now(KOLKATA).date()
        invalidate_village_health_cache(cur, vid, today)

        audit_log(
            action="close_customer_account_via_feed",
            entity_type="account_closure_feed",
            entity_id=feed_id,
            details={
                "ano": ano,
                "vid": vid,
                "cid": cid,
                "final_status": final_status,
                "action": action,
                "discount_amount": str(discount_amount) if discount_amount else None
            },
            status="success"
        )

        conn.commit()

        for lu in closed_uuids:
            broadcast_submission_event(vid, {
                "type": "status_update",
                "feed_type": "closure",
                "local_uuid": lu,
                "ano": ano,
                "vid": vid,
                "status": "accepted"
            })

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error accepting closure request: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/closure/edit/<feed_id>")
@login_required
def edit_closure_request(feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        ano = data.get("ano")
        vid = data.get("vid")

        if ano is None or vid is None:
            return jsonify({"success": False, "error": "Account number and village ID are required"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE account_closure_feed
            SET ano = %s, vid = %s
            WHERE feed_id = %s AND status = 'pending'
            RETURNING feed_id, local_uuid
        """, (ano, vid, feed_id))

        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Pending closure request not found"}), 404

        conn.commit()

        c_lu = row[1]
        if c_lu:
            broadcast_submission_event(vid, {
                "type": "status_update",
                "feed_type": "closure",
                "local_uuid": c_lu,
                "ano": ano,
                "vid": vid,
                "status": "rejected_edit"
            })

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing closure request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/customer/edit/<feed_id>")
@login_required
def edit_customer_feed(feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT local_uuid, payload
            FROM customer_feed
            WHERE feed_id = %s
        """, (feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Customer feed item not found"}), 404

        local_uuid, payload_raw = row
        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if not isinstance(payload, dict):
            payload = {}

        # Fields that can be edited
        editable_keys = [
            "name", "ano", "total_amount", "installment_amount", "aadhaar_number",
            "phone_number", "type", "period", "start_date", "end_date", "notes", "vid", "pano"
        ]

        edited_payload = {}
        for k in editable_keys:
            if k in data and data[k] is not None:
                val = str(data[k]).strip()
                if k in ("ano", "total_amount", "installment_amount", "period", "vid", "pano"):
                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                payload[k] = val
                edited_payload[k] = val

        cur.execute("""
            UPDATE customer_feed
            SET payload = %s
            WHERE feed_id = %s
        """, (json.dumps(payload), feed_id))

        if local_uuid:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_feed_edits (
                    edit_id SERIAL PRIMARY KEY,
                    local_uuid TEXT NOT NULL,
                    edited_payload JSONB NOT NULL,
                    eid INTEGER,
                    vid INTEGER,
                    edit_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                SELECT edit_id FROM customer_feed_edits WHERE local_uuid = %s LIMIT 1
            """, (local_uuid,))
            existing_edit = cur.fetchone()

            if existing_edit:
                cur.execute("""
                    UPDATE customer_feed_edits
                    SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                    WHERE local_uuid = %s
                """, (json.dumps(edited_payload), local_uuid))
            else:
                cur.execute("""
                    INSERT INTO customer_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', NOW())
                """, (local_uuid, json.dumps(edited_payload), payload.get("eid"), payload.get("vid")))

        conn.commit()

        if local_uuid:
            c_vid = payload.get("vid")
            c_ano = payload.get("ano")
            broadcast_submission_event(c_vid, {
                "type": "status_update",
                "feed_type": "customer",
                "local_uuid": local_uuid,
                "ano": c_ano,
                "vid": c_vid,
                "status": "rejected_edit",
                "edited_payload": edited_payload
            })

        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing customer feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/closure/delete/<feed_id>")
@login_required
def delete_closure_request(feed_id):
    conn = None
    cur = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("SELECT local_uuid, ano, vid, eid FROM account_closure_feed WHERE feed_id = %s", (feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Closure request not found"}), 404

        local_uuid, c_ano, c_vid, c_eid = row
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        if local_uuid:
            ensure_feed_tables_exist(cur)
            cur.execute("""
                INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                VALUES ('closure', %s, %s, %s, %s, 'rejected_deleted', %s)
            """, (local_uuid, c_ano, c_vid, c_eid, logged_user))

        cur.execute("DELETE FROM account_closure_feed WHERE feed_id = %s", (feed_id,))
        conn.commit()

        if local_uuid:
            broadcast_submission_event(c_vid, {
                "type": "status_update",
                "feed_type": "closure",
                "local_uuid": local_uuid,
                "ano": c_ano,
                "vid": c_vid,
                "status": "rejected_deleted"
            })

        audit_log(
            action="delete_closure_feed",
            entity_type="account_closure_feed",
            entity_id=feed_id,
            details={"deleted_by": logged_user}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting closure request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/customer/delete/<feed_id>")
@login_required
def delete_customer_feed(feed_id):
    conn = None
    cur = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("SELECT local_uuid, payload, status FROM customer_feed WHERE feed_id = %s FOR UPDATE", (feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Customer feed item not found"}), 404

        local_uuid, payload_raw, feed_status = row
        if feed_status != "pending":
            return jsonify({"success": False, "error": f"Cannot delete feed that has already been {feed_status}"}), 400

        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        c_ano = payload.get("ano")
        c_vid = payload.get("vid")
        c_eid = payload.get("eid")
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        if local_uuid:
            ensure_feed_tables_exist(cur)
            cur.execute("""
                INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                VALUES ('customer', %s, %s, %s, %s, 'rejected_deleted', %s)
            """, (local_uuid, c_ano, c_vid, c_eid, logged_user))

        cur.execute("DELETE FROM customer_feed WHERE feed_id = %s", (feed_id,))
        if local_uuid:
            try:
                cur.execute("DELETE FROM customer_feed_edits WHERE local_uuid = %s", (local_uuid,))
            except Exception:
                pass

        conn.commit()

        if local_uuid:
            broadcast_submission_event(c_vid, {
                "type": "status_update",
                "feed_type": "customer",
                "local_uuid": local_uuid,
                "ano": c_ano,
                "vid": c_vid,
                "status": "rejected_deleted"
            })

        audit_log(
            action="delete_customer_feed",
            entity_type="customer_feed",
            entity_id=feed_id,
            details={"deleted_by": logged_user}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting customer feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()




@app.post("/feed/customer/accept/<feed_id>")
@login_required
def accept_customer(feed_id):

    conn = get_pg_connection()
    cur = conn.cursor()

    # Safety check: ensure logged-in employee
    # employee_id is always set at login.
    # eid may only exist after village/context selection.
    logged_user = session.get("employee_id") or session.get("eid")

    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT local_uuid, payload, status
        FROM customer_feed
        WHERE feed_id = %s
        FOR UPDATE
    """, (feed_id,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Feed not found"}, 404
    
    local_uuid = row[0]
    data = row[1]     # type: ignore # JSON payload
    feed_status = row[2]

    if feed_status != "pending":
        cur.close()
        conn.close()
        return {"success": False, "error": f"Customer feed item has already been {feed_status}"}, 400

    # Ensure payload is dict
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid payload format"}, 400

    # Ensure feed edit tracking tables exist safely
    ensure_feed_tables_exist(cur)

    # Merge pending edit if any
    if local_uuid:
        cur.execute("""
            SELECT edited_payload
            FROM customer_feed_edits
            WHERE local_uuid = %s AND edit_status = 'pending'
            LIMIT 1
        """, (local_uuid,))
        edit_row = cur.fetchone()
        if edit_row:
            ep = edit_row[0]
            if isinstance(ep, str):
                try:
                    ep = json.loads(ep)
                except Exception:
                    ep = {}
            data = merge_edit_payload(data, ep)

        # Mark edit as accepted
        cur.execute("""
            UPDATE customer_feed_edits
            SET edit_status = 'accepted'
            WHERE local_uuid = %s AND edit_status = 'pending'
        """, (local_uuid,))

    try:
        data = normalize_mobile_customer_payload(data)
    except ValueError as exc:
        cur.close()
        conn.close()
        return {"success": False, "error": str(exc)}, 400

    # Check if (ano, vid) already exists in customer, exactly as in manual web entry (/add_customer)
    c_ano = data.get("ano")
    c_vid = data.get("vid")
    if c_ano is not None and c_vid is not None:
        cur.execute("""
            SELECT 1
            FROM customer
            WHERE ano = %s AND vid = %s
            LIMIT 1
        """, (c_ano, c_vid))
        if cur.fetchone():
            cur.close()
            conn.close()
            return {"success": False, "error": f"Account number {c_ano} already exists in this village"}, 400

    loan_type = data.get("type") # type: ignore
    if loan_type == "weekly":
        loan_type = "W"
    elif loan_type == "monthly":
        loan_type = "M"

    # Robust date parsing to ensure PostgreSQL DATE format (YYYY-MM-DD)
    start_date_obj = parse_date_input(data.get("start_date")) # type: ignore
    end_date_obj = parse_date_input(data.get("end_date")) # type: ignore
    start_date_val = start_date_obj.strftime("%Y-%m-%d") if start_date_obj else data.get("start_date") # type: ignore
    end_date_val = end_date_obj.strftime("%Y-%m-%d") if end_date_obj else data.get("end_date") # type: ignore

    cur.execute("""
        INSERT INTO customer
        (
            ano,
            name,
            vid,
            start_date,
            end_date,
            total_amount,
            base_amount,
            cutting_amount,
            interest_amount,
            paid_amount,
            balance_amount,
            installment_amount,
            type,
            period,
            pano,
            aadhaar_number,
            notes,
            latitude,
            longitude,
            eid,
            phone_number,
            status
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open')
        RETURNING cid
    """,
    (
        data.get("ano"), # type: ignore
        data.get("name"), # type: ignore
        data.get("vid"), # type: ignore
        start_date_val,
        end_date_val,
        data.get("total_amount"), # type: ignore
        data.get("base_amount", 0), # type: ignore
        data.get("cutting_amount", 0), # type: ignore
        data.get("interest_amount", 0), # type: ignore
        data.get("paid_amount"), # type: ignore
        data.get("balance_amount"), # type: ignore
        data.get("installment_amount"), # type: ignore
        loan_type,
        data.get("period"), # type: ignore
        data.get("pano"), # type: ignore
        data.get("aadhaar_number"), # type: ignore
        data.get("notes"), # type: ignore
        data.get("latitude"), # type: ignore
        data.get("longitude"), # type: ignore
        data.get("eid"), # type: ignore
        data.get("phone_number") # type: ignore
        
    ))
    cid = cur.fetchone()[0]
    recalc_customer_repayment_score(cur, cid, force_recalc=True)

    # Auto-approve and link all pending customer documents for this new customer
    try:
        vid_int = int(data.get("vid")) if data.get("vid") is not None else None
        ano_int = int(data.get("ano")) if data.get("ano") is not None else None
    except (TypeError, ValueError):
        vid_int = None
        ano_int = None

    if vid_int is not None and ano_int is not None:
        cur.execute("""
            SELECT docs_feed_id, aadhaar_front_pic, aadhaar_back_pic, house_photo
            FROM customer_docs_feed
            WHERE vid = %s AND ano = %s AND status = 'pending'
            ORDER BY docs_feed_id ASC
        """, (vid_int, ano_int))
        pending_docs_list = cur.fetchall()

        if pending_docs_list:
            cur.execute("""
                SELECT aadhaar_front_pic, aadhaar_back_pic, house_photo
                FROM customer_docs
                WHERE vid = %s AND ano = %s
                LIMIT 1
            """, (vid_int, ano_int))
            existing_docs = cur.fetchone()

            final_aadhaar_front = existing_docs[0] if existing_docs else None
            final_aadhaar_back = existing_docs[1] if existing_docs else None
            final_house = existing_docs[2] if existing_docs else None

            doc_feed_ids = []
            for d_row in pending_docs_list:
                doc_feed_ids.append(d_row[0])
                if d_row[1] is not None:
                    final_aadhaar_front = d_row[1]
                if d_row[2] is not None:
                    final_aadhaar_back = d_row[2]
                if d_row[3] is not None:
                    final_house = d_row[3]

            if final_aadhaar_front is not None or final_aadhaar_back is not None or final_house is not None:
                cur.execute("""
                    INSERT INTO customer_docs (
                        vid,
                        ano,
                        aadhaar_front_pic,
                        aadhaar_back_pic,
                        house_photo,
                        uploaded_at
                    )
                    VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
                    ON CONFLICT (vid, ano)
                    DO UPDATE SET
                        aadhaar_front_pic = COALESCE(EXCLUDED.aadhaar_front_pic, customer_docs.aadhaar_front_pic),
                        aadhaar_back_pic = COALESCE(EXCLUDED.aadhaar_back_pic, customer_docs.aadhaar_back_pic),
                        house_photo = COALESCE(EXCLUDED.house_photo, customer_docs.house_photo),
                        uploaded_at = CURRENT_TIMESTAMP
                """, (
                    vid_int,
                    ano_int,
                    final_aadhaar_front,
                    final_aadhaar_back,
                    final_house
                ))

            cur.execute("""
                UPDATE customer_docs_feed
                SET status = 'accepted',
                    cid = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
                WHERE docs_feed_id = ANY(%s::bigint[])
            """, (cid, logged_user, doc_feed_ids))

    cur.execute("""
        UPDATE customer_feed
        SET status = 'accepted',
            reviewed_by = %s,
            reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE feed_id = %s
    """, (logged_user, feed_id))

    cur.execute("SET TIME ZONE 'UTC'")

    # Invalidate cache for this village
    if data.get("vid"):
        invalidate_village_health_cache(cur, data.get("vid"), start_date_val)

    conn.commit()
    if local_uuid:
        broadcast_submission_event(data.get("vid"), {
            "type": "status_update",
            "feed_type": "customer",
            "local_uuid": local_uuid,
            "ano": data.get("ano"),
            "vid": data.get("vid"),
            "status": "accepted"
        })
    audit_log(
        action="accept_customer_feed",
        entity_type="customer_feed",
        entity_id=feed_id,
        details={
            "ano": data.get("ano"), # type: ignore
            "vid": data.get("vid"), # type: ignore
            "eid": data.get("eid"), # type: ignore
            "reviewed_by": logged_user
        }
    )
    cur.close()
    conn.close()

    return {"success":True}


@app.post("/feed/docs/accept/<feed_id>")
@login_required
def accept_customer_feed_docs(feed_id):
    conn = get_pg_connection()
    cur = conn.cursor()

    logged_user = session.get("employee_id") or session.get("eid")
    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT vid, payload
        FROM customer_feed
        WHERE feed_id = %s
    """, (feed_id,))

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Feed not found"}

    vid, payload = row
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid payload format"}

    customer_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    ano = normalize_account_number(customer_payload.get("ano"))
    vid = payload.get("vid") or customer_payload.get("vid") or vid
    if ano is None or vid is None:
        cur.close()
        conn.close()
        return {"success": False, "error": "Missing ano or vid in customer feed"}

    cur.execute("""
        SELECT aadhaar_front_pic, aadhaar_back_pic, house_photo
        FROM customer_docs
        WHERE vid = %s AND ano = %s
        LIMIT 1
    """, (vid, ano))
    docs = cur.fetchone()

    if not docs or (not docs[0] and not docs[1] and not docs[2]):
        cur.close()
        conn.close()
        return {"success": False, "error": "No customer documents found for this feed item"}

    audit_log(
        action="accept_customer_feed_docs",
        entity_type="customer_feed",
        entity_id=feed_id,
        details={
            "ano": ano,
            "vid": vid,
            "reviewed_by": logged_user
        }
    )

    cur.close()
    conn.close()
    return {"success": True}


@app.post("/feed/existing-docs/accept/<docs_feed_id>")
@login_required
def accept_existing_customer_docs(docs_feed_id):
    conn = get_pg_connection()
    cur = conn.cursor()

    logged_user = session.get("employee_id") or session.get("eid")
    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT vid, ano, aadhaar_front_pic, aadhaar_back_pic, house_photo, status
        FROM customer_docs_feed
        WHERE docs_feed_id = %s
        FOR UPDATE
    """, (docs_feed_id,))

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Docs feed item not found"}

    vid, ano, aadhaar_front_pic, aadhaar_back_pic, house_photo, status = row
    if status != "pending":
        cur.close()
        conn.close()
        return {"success": False, "error": "Docs feed item is not pending"}

    if not aadhaar_front_pic and not aadhaar_back_pic and not house_photo:
        cur.close()
        conn.close()
        return {"success": False, "error": "No documents attached"}

    cur.execute("""
        SELECT aadhaar_front_pic, aadhaar_back_pic, house_photo
        FROM customer_docs
        WHERE vid = %s AND ano = %s
        LIMIT 1
    """, (vid, ano))
    existing_docs = cur.fetchone()

    existing_aadhaar_front = existing_docs[0] if existing_docs else None
    existing_aadhaar_back = existing_docs[1] if existing_docs else None
    existing_house = existing_docs[2] if existing_docs else None

    final_aadhaar_front = aadhaar_front_pic if aadhaar_front_pic is not None else existing_aadhaar_front
    final_aadhaar_back = aadhaar_back_pic if aadhaar_back_pic is not None else existing_aadhaar_back
    final_house = house_photo if house_photo is not None else existing_house

    cur.execute("""
        INSERT INTO customer_docs (
            vid,
            ano,
            aadhaar_front_pic,
            aadhaar_back_pic,
            house_photo,
            uploaded_at
        )
        VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
        ON CONFLICT (vid, ano)
        DO UPDATE SET
            aadhaar_front_pic = EXCLUDED.aadhaar_front_pic,
            aadhaar_back_pic = EXCLUDED.aadhaar_back_pic,
            house_photo = EXCLUDED.house_photo,
            uploaded_at = CURRENT_TIMESTAMP
    """, (
        vid,
        ano,
        final_aadhaar_front,
        final_aadhaar_back,
        final_house
    ))

    cur.execute("""
        UPDATE customer_docs_feed
        SET status = 'accepted',
            reviewed_by = %s,
            reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE docs_feed_id = %s
    """, (logged_user, docs_feed_id))

    conn.commit()
    audit_log(
        action="accept_existing_customer_docs",
        entity_type="customer_docs_feed",
        entity_id=docs_feed_id,
        details={
            "ano": ano,
            "vid": vid,
            "reviewed_by": logged_user
        }
    )

    cur.close()
    conn.close()
    return {"success": True}


@app.post("/feed/existing-docs/edit/<docs_feed_id>")
@login_required
def edit_existing_customer_docs(docs_feed_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        ano = data.get("ano")
        vid = data.get("vid")

        if ano is None or vid is None:
            return jsonify({"success": False, "error": "Account number and village ID are required"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE customer_docs_feed
            SET ano = %s, vid = %s
            WHERE docs_feed_id = %s AND status = 'pending'
            RETURNING docs_feed_id
        """, (ano, vid, docs_feed_id))

        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Pending docs feed item not found"}), 404

        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing docs feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/payment/edit/<feed_payment_id>")
@login_required
def edit_payment_feed(feed_payment_id):
    conn = None
    cur = None
    try:
        data = request.get_json() or {}
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT local_uuid, payload
            FROM payment_feed_items
            WHERE feed_payment_id = %s
        """, (feed_payment_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Payment feed item not found"}), 404

        local_uuid, payload_raw = row
        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if not isinstance(payload, dict):
            payload = {}

        # Update payload fields
        if "ano" in data and data["ano"] is not None:
            try:
                payload["ano"] = int(data["ano"])
            except ValueError:
                payload["ano"] = str(data["ano"]).strip()
        if "amt" in data and data["amt"] is not None:
            try:
                payload["amt"] = float(data["amt"])
            except ValueError:
                pass
        if "payment_date" in data and data["payment_date"]:
            payload["payment_date"] = str(data["payment_date"]).strip()
            payload["pdt"] = str(data["payment_date"]).strip()
        if "pdt" in data and data["pdt"]:
            payload["pdt"] = str(data["pdt"]).strip()
            payload["payment_date"] = str(data["pdt"]).strip()
        if "payment_type" in data and data["payment_type"]:
            payload["payment_type"] = str(data["payment_type"]).strip()

        cur.execute("""
            UPDATE payment_feed_items
            SET payload = %s
            WHERE feed_payment_id = %s
        """, (json.dumps(payload), feed_payment_id))

        if local_uuid:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payment_feed_edits (
                    edit_id SERIAL PRIMARY KEY,
                    local_uuid TEXT NOT NULL,
                    edited_payload JSONB NOT NULL,
                    eid INTEGER,
                    vid INTEGER,
                    edit_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                SELECT edit_id FROM payment_feed_edits WHERE local_uuid = %s LIMIT 1
            """, (local_uuid,))
            existing_edit = cur.fetchone()

            if existing_edit:
                cur.execute("""
                    UPDATE payment_feed_edits
                    SET edited_payload = %s, edit_status = 'pending', created_at = NOW()
                    WHERE local_uuid = %s
                """, (json.dumps(payload), local_uuid))
            else:
                cur.execute("""
                    INSERT INTO payment_feed_edits (local_uuid, edited_payload, eid, vid, edit_status, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', NOW())
                """, (local_uuid, json.dumps(payload), payload.get("eid"), payload.get("vid")))

        # Check customer mapping with updated ano and vid
        customer_mapped = False
        cid = None
        customer_name = None
        chk_vid = payload.get("vid") or session.get("vid")
        chk_ano = payload.get("ano")
        if chk_vid and chk_ano is not None:
            try:
                cur.execute("""
                    SELECT cid, name
                    FROM customer
                    WHERE vid = %s AND ano = %s
                    LIMIT 1
                """, (chk_vid, int(chk_ano)))
                cust_row = cur.fetchone()
                if cust_row:
                    customer_mapped = True
                    cid = cust_row[0]
                    customer_name = cust_row[1]
            except Exception:
                pass

        conn.commit()

        if local_uuid:
            p_vid = payload.get("vid") or session.get("vid")
            p_ano = payload.get("ano")
            broadcast_submission_event(p_vid, {
                "type": "status_update",
                "feed_type": "payment",
                "local_uuid": local_uuid,
                "ano": p_ano,
                "vid": p_vid,
                "status": "rejected_edit",
                "edited_payload": payload
            })

        return jsonify({
            "success": True,
            "mapped": customer_mapped,
            "cid": cid,
            "customer_name": customer_name
        })

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error editing payment feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/existing-docs/delete/<docs_feed_id>")
@login_required
def delete_existing_customer_docs(docs_feed_id):
    conn = None
    cur = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM customer_docs_feed WHERE docs_feed_id = %s RETURNING docs_feed_id", (docs_feed_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Pending docs feed item not found"}), 404

        conn.commit()
        audit_log(
            action="delete_existing_customer_docs",
            entity_type="customer_docs_feed",
            entity_id=docs_feed_id,
            details={"deleted_by": session.get("employee_id") or session.get("eid")}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting docs feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/payment/delete/<feed_payment_id>")
@login_required
def delete_payment_feed(feed_payment_id):
    conn = None
    cur = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute("SELECT local_uuid, payload, status FROM payment_feed_items WHERE feed_payment_id = %s FOR UPDATE", (feed_payment_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Payment feed item not found"}), 404

        local_uuid, payload_raw, feed_status = row
        if feed_status != "pending":
            return jsonify({"success": False, "error": f"Cannot delete payment feed item that has already been {feed_status}"}), 400

        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        p_ano = payload.get("ano")
        p_vid = payload.get("vid") or session.get("vid")
        p_eid = payload.get("eid")
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        if local_uuid:
            ensure_feed_tables_exist(cur)
            cur.execute("""
                INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                VALUES ('payment', %s, %s, %s, %s, 'rejected_deleted', %s)
            """, (local_uuid, p_ano, p_vid, p_eid, logged_user))

        cur.execute("DELETE FROM payment_feed_items WHERE feed_payment_id = %s", (feed_payment_id,))
        if local_uuid:
            try:
                cur.execute("DELETE FROM payment_feed_edits WHERE local_uuid = %s", (local_uuid,))
            except Exception:
                pass

        conn.commit()

        if local_uuid:
            broadcast_submission_event(p_vid, {
                "type": "status_update",
                "feed_type": "payment",
                "local_uuid": local_uuid,
                "ano": p_ano,
                "vid": p_vid,
                "status": "rejected_deleted"
            })

        audit_log(
            action="delete_payment_feed",
            entity_type="payment_feed",
            entity_id=feed_payment_id,
            details={"deleted_by": logged_user}
        )
        return jsonify({"success": True})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting payment feed item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/feed/payment/delete_batch")
@login_required
def delete_payment_batch():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    try:
        ids = [int(i) for i in ids]
    except Exception:
        return jsonify({"success": False, "error": "Invalid IDs format"}), 400

    if not ids:
        return jsonify({"success": False, "error": "No payments selected"}), 400

    conn = None
    cur = None
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        # Find items and local_uuids
        cur.execute("SELECT feed_payment_id, local_uuid, payload FROM payment_feed_items WHERE feed_payment_id = ANY(%s::bigint[])", (ids,))
        rows = cur.fetchall()
        logged_user = str(session.get("employee_id") or session.get("eid") or "")

        batch_events = []
        if rows:
            ensure_feed_tables_exist(cur)
        for f_id, lu, pl_raw in rows:
            pl = pl_raw
            if isinstance(pl, str):
                try:
                    pl = json.loads(pl)
                except Exception:
                    pl = {}
            if not isinstance(pl, dict):
                pl = {}
            b_ano = pl.get("ano")
            b_vid = pl.get("vid") or session.get("vid")
            b_eid = pl.get("eid")
            if lu:
                cur.execute("""
                    INSERT INTO feed_rejections (feed_type, local_uuid, ano, vid, eid, action_type, deleted_by)
                    VALUES ('payment', %s, %s, %s, %s, 'rejected_deleted', %s)
                """, (lu, b_ano, b_vid, b_eid, logged_user))
                batch_events.append((b_vid, {
                    "type": "status_update",
                    "feed_type": "payment",
                    "local_uuid": lu,
                    "ano": b_ano,
                    "vid": b_vid,
                    "status": "rejected_deleted"
                }))

        local_uuids = [r[1] for r in rows if r[1]]
        cur.execute("DELETE FROM payment_feed_items WHERE feed_payment_id = ANY(%s::bigint[])", (ids,))
        if local_uuids:
            try:
                cur.execute("DELETE FROM payment_feed_edits WHERE local_uuid = ANY(%s)", (local_uuids,))
            except Exception:
                pass

        conn.commit()

        for b_vid, evt in batch_events:
            broadcast_submission_event(b_vid, evt)

        audit_log(
            action="delete_payment_batch",
            entity_type="payment_feed",
            entity_id=None,
            details={
                "deleted_by": logged_user,
                "count": len(ids),
                "ids": ids
            }
        )
        return jsonify({"success": True, "count": len(ids)})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error batch deleting payment feed items: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()




@app.post("/feed/payment/accept/<feed_payment_id>")
@login_required
def accept_payment(feed_payment_id):
    conn = get_pg_connection()
    cur = conn.cursor()

    logged_user = session.get("employee_id")
    if not logged_user:
        cur.close()
        conn.close()
        return {"success": False, "error": "User not logged properly"}

    cur.execute("""
        SELECT local_uuid, payload, status
        FROM payment_feed_items
        WHERE feed_payment_id = %s
        FOR UPDATE
    """, (feed_payment_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return {"success": False, "error": "Feed payment not found"}

    local_uuid = row[0]
    data = row[1]
    feed_status = row[2]

    if feed_status != "pending":
        cur.close()
        conn.close()
        return {"success": False, "error": f"Payment feed item has already been {feed_status}"}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid payload format"}

    ensure_feed_tables_exist(cur)

    # Merge pending edit if any
    if local_uuid:
        cur.execute("""
            SELECT edited_payload
            FROM payment_feed_edits
            WHERE local_uuid = %s AND edit_status = 'pending'
            LIMIT 1
        """, (local_uuid,))
        edit_row = cur.fetchone()
        if edit_row:
            ep = edit_row[0]
            if isinstance(ep, str):
                try:
                    ep = json.loads(ep)
                except Exception:
                    ep = {}
            data = merge_edit_payload(data, ep)

    try:
        data = normalize_mobile_payment_payload(data)
    except ValueError as exc:
        cur.close()
        conn.close()
        return {"success": False, "error": str(exc)}

    ano = data.get("ano")
    vid = data.get("vid")
    eid = data.get("eid")
    if ano is None or vid is None or eid is None:
        cur.close()
        conn.close()
        return {"success": False, "error": "Missing account number, village ID, or employee ID in payment payload"}

    amt = Decimal(str(data.get("amt", 0)))
    if amt <= 0:
        cur.close()
        conn.close()
        return {"success": False, "error": "Payment amount must be greater than 0"}

    try:
        raw_pdt = str(data.get("payment_date") or data.get("pdate"))[:10]
        payment_date = datetime.fromisoformat(raw_pdt).date()
    except Exception:
        cur.close()
        conn.close()
        return {"success": False, "error": "Invalid payment date format"}

    payment_type = data.get("payment_type", "cash")
    cash_amount = Decimal(str(data.get("cash_amount", 0)))
    upi_amount = Decimal(str(data.get("upi_amount", 0)))

    # Fetch customer from DB for this village
    cur.execute("""
        SELECT cid, total_amount, start_date
        FROM customer
        WHERE ano = %s AND vid = %s
    """, (ano, vid))
    cust = cur.fetchone()

    if not cust:
        cur.close()
        conn.close()
        return {
            "success": False,
            "error": f"Customer Account #{ano} not found in database for this village! Please approve the new customer registration first."
        }

    cid, total_amt, start_date = cust

    # Validate payment_date >= start_date
    if start_date and payment_date < start_date:
        cur.close()
        conn.close()
        return {
            "success": False,
            "error": f"Customer Account #{ano} start date is {format_date_display(str(start_date))}. Payment date ({format_date_display(str(payment_date))}) cannot be earlier than start date."
        }

    # Duplicate check in payment table
    cur.execute("""
        SELECT COUNT(*) FROM payment
        WHERE ano = %s AND vid = %s AND payment_date = %s
    """, (ano, vid, payment_date))
    if cur.fetchone()[0] > 0:
        cur.close()
        conn.close()
        return {
            "success": False,
            "error": f"Duplicate payment already recorded in database for Account #{ano} on {format_date_display(str(payment_date))}."
        }

    # Insert payment
    cur.execute("""
        INSERT INTO payment
        (cid, vid, eid, ano, amt, payment_date, payment_type, cash_amount, upi_amount)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        cid,
        vid,
        eid,
        ano,
        amt,
        payment_date,
        payment_type,
        cash_amount,
        upi_amount
    ))

    # Recalculate balance
    recalc_customer_balance(cur, cid)

    # Mark edit as accepted
    if local_uuid:
        cur.execute("""
            UPDATE payment_feed_edits
            SET edit_status = 'accepted'
            WHERE local_uuid = %s AND edit_status = 'pending'
        """, (local_uuid,))

    # Mark feed item as accepted
    cur.execute("""
        UPDATE payment_feed_items
        SET status='accepted',
            review_by = %s,
            review_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE feed_payment_id = %s
    """, (logged_user, feed_payment_id))

    # Invalidate cache for this village
    invalidate_village_health_cache(cur, vid, payment_date)

    conn.commit()
    if local_uuid:
        broadcast_submission_event(vid, {
            "type": "status_update",
            "feed_type": "payment",
            "local_uuid": local_uuid,
            "ano": ano,
            "vid": vid,
            "status": "accepted"
        })
    audit_log(
        action="accept_payment_feed",
        entity_type="payment_feed",
        entity_id=feed_payment_id,
        details={
            "ano": ano,
            "vid": vid,
            "eid": eid,
            "amt": str(amt),
            "reviewed_by": logged_user
        }
    )
    cur.close()
    conn.close()

    return {"success": True}


# ----------- Batch accept payments -----------
@app.post("/feed/payment/accept_batch")
@login_required
def accept_payment_batch():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    try:
        ids = [int(i) for i in ids]
    except Exception:
        return {"success": False, "error": "Invalid IDs format"}

    if not ids:
        return {"success": False, "error": "No payments selected"}

    conn = get_pg_connection()
    cur = conn.cursor()

    logged_user = session.get("employee_id")
    if not logged_user:
        cur.close()
        conn.close()
        return {"success": False, "error": "User not logged properly"}

    try:
        ensure_feed_tables_exist(cur)

        # 1. Fetch selected items with their specific feed_payment_id
        cur.execute("""
            SELECT feed_payment_id, local_uuid, payload, status
            FROM payment_feed_items
            WHERE feed_payment_id = ANY(%s::bigint[])
            FOR UPDATE
        """, (ids,))
        all_rows = cur.fetchall()
        rows = [r for r in all_rows if r[3] == 'pending']

        if not rows:
            cur.close()
            conn.close()
            return {"success": False, "error": "No pending payments found in queue"}

        # Fetch pending edits if any for these local_uuids
        local_uuids = [r[1] for r in rows if r[1]]
        payment_edit_map = {}
        if local_uuids:
            cur.execute("""
                SELECT local_uuid, edited_payload
                FROM payment_feed_edits
                WHERE local_uuid = ANY(%s) AND edit_status = 'pending'
            """, (local_uuids,))
            for edit_row in cur.fetchall():
                ep = edit_row[1]
                if isinstance(ep, str):
                    try:
                        ep = json.loads(ep)
                    except Exception:
                        ep = {}
                payment_edit_map[edit_row[0]] = ep

        # 2. Prefetch customers for all unique ANOs in this village
        batch_vid = session.get("vid")
        anos = []
        for r in rows:
            l_uuid = r[1]
            p_data = r[2]
            if isinstance(p_data, str):
                try:
                    p_data = json.loads(p_data)
                except Exception:
                    p_data = {}
            if l_uuid and l_uuid in payment_edit_map:
                p_data = merge_edit_payload(p_data, payment_edit_map[l_uuid])
            if not batch_vid and p_data.get("vid"):
                batch_vid = p_data.get("vid")
            a_val = p_data.get("ano")
            if a_val is not None:
                try:
                    anos.append(int(a_val))
                except Exception:
                    pass

        anos = list(set(anos))
        customer_map = {}
        if anos and batch_vid:
            cur.execute("""
                SELECT cid, ano, total_amount, paid_amount, balance_amount, start_date
                FROM customer
                WHERE ano = ANY(%s)
                  AND vid = %s
            """, (anos, batch_vid))
            for crow in cur.fetchall():
                customer_map[int(crow[1])] = {
                    "cid": crow[0],
                    "total_amount": crow[2],
                    "paid_amount": crow[3],
                    "balance_amount": crow[4],
                    "start_date": crow[5]
                }

        insert_values = []
        successful_feed_ids = []
        successful_local_uuids = []
        affected_cids = set()
        failed_items = []
        seen_in_batch = set()

        for r in rows:
            f_id = r[0]
            l_uuid = r[1]
            p = r[2]
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except Exception:
                    failed_items.append({
                        "feed_payment_id": f_id,
                        "ano": "?",
                        "reason": "Invalid payload format"
                    })
                    continue

            if l_uuid and l_uuid in payment_edit_map:
                p = merge_edit_payload(p, payment_edit_map[l_uuid])

            try:
                p = normalize_mobile_payment_payload(p)
            except Exception as exc:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": str(p.get("ano", "?")),
                    "reason": f"Payload error: {str(exc)}"
                })
                continue

            ano_raw = p.get("ano")
            vid_val = p.get("vid") or batch_vid
            eid_val = p.get("eid")
            if ano_raw is None or vid_val is None or eid_val is None:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": str(ano_raw or "?"),
                    "reason": "Missing account number, village ID, or employee ID"
                })
                continue

            try:
                ano_int = int(ano_raw)
            except Exception:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": str(ano_raw),
                    "reason": "Account number must be numeric"
                })
                continue

            try:
                amt = Decimal(str(p.get("amt", 0)))
            except Exception:
                amt = Decimal(0)

            if amt <= 0:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Payment amount must be greater than 0"
                })
                continue

            try:
                raw_pdt = str(p.get("payment_date") or p.get("pdate"))[:10]
                payment_date = datetime.fromisoformat(raw_pdt).date()
            except Exception:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Invalid payment date"
                })
                continue

            # Check 1: Customer existence in database for this village
            customer = customer_map.get(ano_int)
            if not customer:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Customer not found in database for this village. Please approve new customer registration first."
                })
                continue

            cid = customer["cid"]
            cust_start = customer.get("start_date")

            # Check 2: Payment date >= Customer start date
            if cust_start and payment_date < cust_start:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Payment date ({format_date_display(str(payment_date))}) cannot be earlier than customer start date ({format_date_display(str(cust_start))})."
                })
                continue

            # Check 3: Intra-batch duplicate check
            batch_pair = (ano_int, str(payment_date))
            if batch_pair in seen_in_batch:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Multiple payments for date {format_date_display(str(payment_date))} in the same selection."
                })
                continue
            seen_in_batch.add(batch_pair)

            # Check 4: Database duplicate check
            cur.execute("""
                SELECT COUNT(*) FROM payment
                WHERE ano = %s AND vid = %s AND payment_date = %s
            """, (ano_int, vid_val, payment_date))
            if cur.fetchone()[0] > 0:
                failed_items.append({
                    "feed_payment_id": f_id,
                    "ano": ano_int,
                    "reason": f"Account #{ano_int}: Duplicate payment already recorded in database on {format_date_display(str(payment_date))}."
                })
                continue

            payment_type = p.get("payment_type", "cash")
            cash_amount = Decimal(str(p.get("cash_amount", 0)))
            upi_amount = Decimal(str(p.get("upi_amount", 0)))

            insert_values.append((
                cid,
                vid_val,
                eid_val,
                ano_int,
                amt,
                payment_date,
                payment_type,
                cash_amount,
                upi_amount
            ))
            successful_feed_ids.append(f_id)
            if l_uuid:
                successful_local_uuids.append(l_uuid)
            affected_cids.add(cid)

        # 3. If there are valid payments to insert
        if insert_values:
            execute_values(
                cur,
                """
                    INSERT INTO payment (
                        cid,
                        vid,
                        eid,
                        ano,
                        amt,
                        payment_date,
                        payment_type,
                        cash_amount,
                        upi_amount
                    )
                    VALUES %s
                """,
                insert_values,
                template="(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )

            # Recalculate customer balances for affected customers
            for c_id in affected_cids:
                recalc_customer_balance(cur, c_id)

            # ONLY update status for successful payments!
            cur.execute("""
                UPDATE payment_feed_items
                SET status = 'accepted',
                    review_by = %s,
                    review_at = NOW() AT TIME ZONE 'Asia/Kolkata'
                WHERE feed_payment_id = ANY(%s::bigint[])
            """, (logged_user, successful_feed_ids))

            if successful_local_uuids:
                cur.execute("""
                    UPDATE payment_feed_edits
                    SET edit_status = 'accepted'
                    WHERE local_uuid = ANY(%s) AND edit_status = 'pending'
                """, (successful_local_uuids,))

            # Invalidate cache
            min_pdt = min(val[5] for val in insert_values)
            invalidate_village_health_cache(cur, batch_vid, min_pdt)

            conn.commit()

            if successful_local_uuids:
                for lu in successful_local_uuids:
                    broadcast_submission_event(batch_vid, {
                        "type": "status_update",
                        "feed_type": "payment",
                        "local_uuid": lu,
                        "vid": batch_vid,
                        "status": "accepted"
                    })

            audit_log(
                action="accept_payment_batch",
                entity_type="payment_feed",
                entity_id=batch_vid,
                details={
                    "reviewed_by": logged_user,
                    "selected_count": len(ids),
                    "accepted_count": len(successful_feed_ids),
                    "failed_count": len(failed_items)
                }
            )

        cur.close()
        conn.close()

        if successful_feed_ids:
            accepted_sum = float(sum(val[4] for val in insert_values)) if insert_values else 0.0
            return {
                "success": True,
                "accepted_count": len(successful_feed_ids),
                "accepted_sum": accepted_sum,
                "failed_count": len(failed_items),
                "failed_items": failed_items,
                "accepted_ids": successful_feed_ids,
                "message": f"{len(successful_feed_ids)} payments posted successfully." if not failed_items else f"{len(successful_feed_ids)} payments posted. {len(failed_items)} could not be posted."
            }
        else:
            return {
                "success": False,
                "accepted_count": 0,
                "failed_count": len(failed_items),
                "failed_items": failed_items,
                "error": "None of the selected payments could be posted.",
                "message": "None of the selected payments could be posted."
            }

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"success": False, "error": str(e)}



# ----------- NEW: Postgres-based customer update route -----------
@app.route("/api/customer/update_pg", methods=["POST"])
@login_required
def update_customer_pg():
    payload = request.get_json()

    data = payload.get("data") if isinstance(payload, dict) else None

    if not data:
        return jsonify(success=False, error="Missing data"), 400

    cid = data.get("cid")
    vid = session.get("vid")

    if not cid:
        return jsonify(success=False, error="Missing cid"), 400

    if not vid:
        return jsonify(success=False, error="Missing vid in session"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:

        # ðŸ”¹ Detect table based on status
        # 🔹 Detect target table and fetch existing data by cid
        cur.execute("""
            SELECT paid_amount, COALESCE(interest_discount, 0.00), vid, 'customer' AS target_table
            FROM customer
            WHERE cid = %s
            UNION ALL
            SELECT paid_amount, COALESCE(interest_discount, 0.00), vid, 'closed_cust_account' AS target_table
            FROM closed_cust_account
            WHERE cid = %s
            LIMIT 1;
        """, (cid, cid))

        existing = cur.fetchone()

        if not existing:
            return jsonify(success=False, error="Customer not found"), 404

        paid_amount = float(existing[0] or 0)
        actual_vid = existing[2]
        table_name = existing[3]
        target_vid = actual_vid if actual_vid else vid
        try:
            interest_discount = float(data.get("interest_discount") if data.get("interest_discount") is not None else existing[1] or 0.0)
        except Exception:
            interest_discount = float(existing[1] or 0.0)

        # 🔸 Read editable fields
        name = (data.get("name") or "").strip()
        start_date_raw = (data.get("start_date") or "").strip()
        loan_type = (data.get("type") or "").strip().upper()
        pano = (data.get("pano") or "").strip() or None

        try:
            base_amount = float(data.get("base_amount") or 0.0)
        except Exception:
            base_amount = 0.0
        try:
            cutting_amount = float(data.get("cutting_amount") or 0.0)
        except Exception:
            cutting_amount = 0.0
        try:
            interest_amount = float(data.get("interest_amount") or 0.0)
        except Exception:
            interest_amount = 0.0

        notes = (data.get("notes") or "").strip() or None
        phone_number = (data.get("phone_number") or "").strip()
        if phone_number.lower() == "none":
             phone_number = ""
        phone_number = phone_number or None

        try:
            total_amount = float(data.get("total_amount") or 0)
        except Exception:
            return jsonify(success=False, error="Invalid total amount"), 400

        try:
            period = int(data.get("period") or 0)
        except Exception:
            return jsonify(success=False, error="Invalid period"), 400 

        # ðŸ”¹ Validation
        if not name:
            return jsonify(success=False, error="Name is required"), 400

        if loan_type not in ["W", "M", "D"]:
            return jsonify(success=False, error="Loan type must be W, M or D"), 400

        if period <= 0:
            return jsonify(success=False, error="Period must be greater than 0"), 400

        if total_amount <= 0:
            return jsonify(success=False, error="Total amount must be greater than 0"), 400

        if phone_number:
            if not phone_number.isdigit() or len(phone_number) != 10:
                return jsonify(success=False, error="Phone number must be 10 digits"), 400

        # ðŸ”¹ Parse frontend date safely
        try:
            start_date = parse_date_input(start_date_raw)
            if not start_date:
                raise ValueError("bad date")
        except Exception:
            return jsonify(success=False, error="Invalid start date format"), 400

        # ðŸ”¹ Recalculate derived fields
        if loan_type == "M":
            end_date = start_date + relativedelta(months=period)
        elif loan_type == "D":
            end_date = start_date + timedelta(days=period)
        else:
            end_date = start_date + timedelta(weeks=period)

        installment_amount = round_curr(total_amount / period)
        balance_amount = round_curr(total_amount - paid_amount - interest_discount)

        # 🔸 Update customer
        if table_name == "customer":
            cur.execute("""
                UPDATE customer
                SET
                    name = %s,
                    start_date = %s,
                    end_date = %s,
                    total_amount = %s,
                    balance_amount = %s,
                    installment_amount = %s,
                    type = %s,
                    period = %s,
                    pano = %s,
                    notes = %s,
                    phone_number = %s,
                    base_amount = %s,
                    cutting_amount = %s,
                    interest_amount = %s,
                    interest_discount = %s,
                    updated_at = NOW() AT TIME ZONE 'Asia/Kolkata'
                WHERE cid = %s
            """, (
                name, start_date, end_date, total_amount, balance_amount, installment_amount,
                loan_type, period, pano, notes, phone_number,
                base_amount, cutting_amount, interest_amount, interest_discount,
                cid
            ))
        else:
            cur.execute(f"""
                UPDATE {table_name}
                SET
                    name = %s,
                    start_date = %s,
                    end_date = %s,
                    total_amount = %s,
                    balance_amount = %s,
                    installment_amount = %s,
                    type = %s,
                    period = %s,
                    pano = %s,
                    notes = %s,
                    phone_number = %s,
                    base_amount = %s,
                    cutting_amount = %s,
                    interest_amount = %s,
                    interest_discount = %s
                WHERE cid = %s
            """, (
                name, start_date, end_date, total_amount, balance_amount, installment_amount,
                loan_type, period, pano, notes, phone_number,
                base_amount, cutting_amount, interest_amount, interest_discount,
                cid
            ))


        # Force recalculation of repayment score and streaks
        recalc_customer_repayment_score(cur, cid, force_recalc=True)

        # Invalidate cache for this village
        invalidate_village_health_cache(cur, target_vid, start_date)

        conn.commit()

        return jsonify(
            success=True,
            recalculated={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "installment_amount": installment_amount,
                "balance_amount": balance_amount
            }
        )

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

# ----------- NEW: Postgres-based payment record update route (flexible by pid) -----------
@app.route("/api/payment/update_record_pg", methods=["POST"])
@login_required
def update_payment_record_pg():
    payload = request.get_json()
    if not payload:
        return jsonify(success=False, error="Missing payload"), 400

    data = payload.get("data")
    if not data:
        return jsonify(success=False, error="Missing data"), 400

    vid = session.get("vid")
    if not vid:
        return jsonify(success=False, error="Context not set"), 400

    pid = data.get("pid")
    ano = data.get("ano")
    amt = Decimal(str(data.get("amt")))
    
    # Parse payment date
    pdt_str = data.get("payment_date")
    try:
        pdt = parse_date_input(pdt_str)
        if not pdt:
            raise ValueError("bad date")
    except (ValueError, TypeError):
        return jsonify(success=False, error="Invalid date format. Use DD-MM-YYYY or YYYY-MM-DD."), 400

    if not pid or not ano or amt is None:
        return jsonify(success=False, error="Missing required fields"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # 1. Fetch current payment details
        cur.execute("SELECT cid, ano, vid, payment_date FROM payment WHERE pid = %s", (pid,))
        payment_row = cur.fetchone()
        is_active = True
        is_historic = False
        if not payment_row:
            cur.execute("SELECT cid, ano, vid, payment_date FROM closed_cust_payment WHERE pid = %s", (pid,))
            payment_row = cur.fetchone()
            is_active = False
        if not payment_row:
            cur.execute("SELECT cid, ano, vid, payment_date FROM historic_payment_data WHERE pid = %s", (pid,))
            payment_row = cur.fetchone()
            is_historic = True

        if not payment_row:
            return jsonify(success=False, error="Payment record not found"), 404

        old_cid, old_ano, p_vid, old_pdt = payment_row
        if p_vid != vid:
            return jsonify(success=False, error="Access denied: Different village context"), 403

        if is_historic:
            table_payment = "historic_payment_data"
            table_customer = "historic_customer_data"
            amount_col = "amount"
        else:
            table_payment = "payment" if is_active else "closed_cust_payment"
            table_customer = "customer" if is_active else "closed_cust_account"
            amount_col = "amt"

        # 2. If ano is changing, we must fetch the new customer's cid
        new_cid = old_cid
        if int(ano) != int(old_ano):
            cur.execute(f"SELECT cid FROM {table_customer} WHERE vid = %s AND ano = %s", (vid, ano))
            cust_row = cur.fetchone()
            if not cust_row:
                return jsonify(success=False, error=f"Customer with Account Number {ano} not found in this village"), 404
            new_cid = cust_row[0]

        # Check for duplicate payment date for this customer (another payment on same date)
        cur.execute(f"""
            SELECT pid, {amount_col} FROM {table_payment}
            WHERE vid = %s AND ano = %s AND payment_date = %s AND pid != %s
            LIMIT 1
        """, (vid, ano, pdt, pid))
        dup = cur.fetchone()
        if dup:
            return jsonify(
                success=False,
                error=f"A payment for Account #{ano} already exists on {format_date_display(str(pdt))} (Amount: ₹{dup[1]}). Only one payment per date is allowed."
            ), 400

        # 3. Update the payment record
        if is_historic:
            cur.execute("""
                UPDATE historic_payment_data
                SET ano = %s,
                    cid = %s,
                    payment_date = %s,
                    amount = %s
                WHERE pid = %s
            """, (ano, new_cid, pdt, amt, pid))
        else:
            cur.execute(f"""
                UPDATE {table_payment}
                SET ano = %s,
                    cid = %s,
                    payment_date = %s,
                    amt = %s,
                    updated_at = NOW()
                WHERE pid = %s
            """, (ano, new_cid, pdt, amt, pid))

        # 4. Recalculate balances for old and new customers
        recalc_customer_balance(cur, old_cid)
        if new_cid != old_cid:
            recalc_customer_balance(cur, new_cid)

        # Invalidate cache for this village
        min_date = min(pdt, old_pdt.date() if isinstance(old_pdt, datetime) else old_pdt)
        invalidate_village_health_cache(cur, vid, min_date)

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@app.route("/delete_payment", methods=["POST"])
@login_required
def delete_payment():
    data = request.get_json()

    ano = data.get("ano")
    pdt_raw = data.get("pdt")
    vid = session.get("vid")

    if not ano or not pdt_raw or not vid:
        return jsonify(success=False, error="Missing required fields"), 400

    # ACCEPT ISO DATE (YYYY-MM-DD)
    try:
        pdt = datetime.fromisoformat(pdt_raw).date()
    except ValueError:
        return jsonify(success=False, error="Invalid date format"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Delete payment
        cur.execute("""
            DELETE FROM payment
            WHERE vid = %s
              AND ano = %s
              AND payment_date = %s
        """, (vid, ano, pdt))

        if cur.rowcount == 0:
            conn.rollback()
            return jsonify(success=False, error="Payment not found"), 404

        # Recalculate balances
        cur.execute("""
            SELECT cid, total_amount
            FROM customer
            WHERE vid = %s AND ano = %s
        """, (vid, ano))

        row = cur.fetchone()
        if row:
            cid, total_amt = row

            recalc_customer_balance(cur, cid)

        audit_log(
            action="delete_payment",
            entity_type="payment",
            entity_id=ano,
            details={
                "vid": vid,
                "payment_date": str(pdt)
            }
        )

        # Invalidate cache for this village
        invalidate_village_health_cache(cur, vid, pdt)

        global_ttl_cache.clear()
        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

def format_waiting_duration(seconds):
    if seconds <= 0:
        return ""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

@app.route("/village")
@login_required
def village_page():
    conn = get_pg_connection()
    cur = conn.cursor()
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])

    # Fetch total active employees
    cur.execute("SELECT COUNT(*) FROM employee WHERE is_active = TRUE")
    total_employees = cur.fetchone()[0]

    sql_fields = """
        v.vid,
        v.village_code,
        v.village_name,
        v.district,
        v.pincode,
        v.state,
        v.emp1,
        e1.name AS emp1_name,
        v.emp2,
        e2.name AS emp2_name,
        v.interest_rate,
        v.cutting_rate,
        v.created_at,
        v.status,
        v.latitude,
        v.longitude,
        (SELECT COUNT(*) FROM customer WHERE vid = v.vid AND status = 'open') AS customer_count,
        COALESCE(
            (SELECT COUNT(*) FROM customer_feed WHERE vid = v.vid AND status = 'pending'), 0
        ) + COALESCE(
            (SELECT COUNT(*) FROM payment_feed_items WHERE (payload->>'vid')::INT = v.vid AND status = 'pending'), 0
        ) + COALESCE(
            (
                SELECT COUNT(*) 
                FROM customer_docs_feed cdf
                INNER JOIN customer c ON c.vid = cdf.vid AND c.ano = cdf.ano
                WHERE cdf.vid = v.vid AND cdf.status = 'pending'
            ), 0
        ) + COALESCE(
            (
                SELECT COUNT(*) 
                FROM account_closure_feed acf
                INNER JOIN customer c ON c.vid = acf.vid AND c.ano = acf.ano
                WHERE acf.vid = v.vid AND acf.status = 'pending'
            ), 0
        ) AS pending_feed_count,
        (
            SELECT MIN(t)
            FROM (
                SELECT MIN(submitted_at) AS t FROM customer_feed WHERE vid = v.vid AND status = 'pending'
                UNION ALL
                SELECT MIN(created_at) AS t FROM payment_feed_items WHERE (payload->>'vid')::INT = v.vid AND status = 'pending'
                UNION ALL
                SELECT MIN(cdf.created_at) AS t 
                FROM customer_docs_feed cdf
                INNER JOIN customer c ON c.vid = cdf.vid AND c.ano = cdf.ano
                WHERE cdf.vid = v.vid AND cdf.status = 'pending'
                UNION ALL
                SELECT MIN(acf.created_at) AS t 
                FROM account_closure_feed acf
                INNER JOIN customer c ON c.vid = acf.vid AND c.ano = acf.ano
                WHERE acf.vid = v.vid AND acf.status = 'pending'
            ) q
        ) AS oldest_pending_time
    """

    if user_level in ["admin", "mgmt"]:
        cur.execute(f"""
        SELECT {sql_fields}
        FROM village v
        LEFT JOIN employee e1 ON e1.eid = v.emp1
        LEFT JOIN employee e2 ON e2.eid = v.emp2
        ORDER BY v.village_code
        """)
    else:
        if not allowed_villages:
            cur.close()
            conn.close()
            return render_template(
                "village.html",
                headers=[],
                data=[],
                total_villages=0,
                total_employees=total_employees,
                selected_vid=session.get("vid")
            )

        cur.execute(f"""
        SELECT {sql_fields}
        FROM village v
        LEFT JOIN employee e1 ON e1.eid = v.emp1
        LEFT JOIN employee e2 ON e2.eid = v.emp2
        WHERE v.vid = ANY(%s)
        ORDER BY v.village_code
        """, (allowed_villages,))

    rows = cur.fetchall()

    headers = [desc[0] for desc in cur.description] # type: ignore
    data = []
    
    # Process calculations per row
    now_utc = datetime.now(timezone.utc)
    for r in rows:
        row_dict = dict(zip(headers, r))
        oldest_time = row_dict.get("oldest_pending_time")
        
        # Calculate duration
        waiting_seconds = 0
        waiting_duration_str = ""
        if oldest_time:
            # Handle timezone safety
            if oldest_time.tzinfo is None:
                oldest_time = oldest_time.replace(tzinfo=timezone.utc)
            delta = now_utc - oldest_time
            waiting_seconds = max(0, int(delta.total_seconds()))
            waiting_duration_str = format_waiting_duration(waiting_seconds)
            
        row_dict["waiting_seconds"] = waiting_seconds
        row_dict["waiting_duration_str"] = waiting_duration_str
        
        # Formatted fields for display
        if row_dict.get("oldest_pending_time"):
            row_dict["oldest_pending_time"] = row_dict["oldest_pending_time"].isoformat()
            
        data.append(row_dict)

    cur.close()
    conn.close()

    # Filter out columns that we want in JSON data but don't want displayed as raw table columns
    hidden_cols = {"oldest_pending_time", "waiting_seconds"}
    headers.append("waiting_duration_str")
    display_headers = [h for h in headers if h not in hidden_cols]

    return render_template(
        "village.html",
        headers=display_headers,
        data=data,
        total_villages=len(data),
        total_employees=total_employees,
        selected_vid=session.get("vid")
    )

def calculate_village_health_history(vid, cur, view, sub_view, dates, time_range="weekly"):
    is_monthly = is_village_monthly(vid, cur)

    # 1. Parse and clean input dates to datetime.date objects
    parsed_dates = []
    for d in dates:
        pd = parse_date_input(d)
        if pd:
            parsed_dates.append(pd)
    
    # Sort and remove duplicates to find unique dates needed
    unique_dates = sorted(list(set(parsed_dates)))

    # 2. Query cache table for existing snapshots
    cur.execute("""
        SELECT date_key, health_score, metrics
        FROM village_health_cache
        WHERE vid = %s AND view = %s AND sub_view = %s AND time_range = %s AND date_key = ANY(%s)
    """, (vid, view, sub_view, time_range, unique_dates))
    cache_rows = cur.fetchall()
    
    cache_by_date = {}
    for d_key, h_score, cached_metrics in cache_rows:
        if isinstance(d_key, datetime):
            d_key = d_key.date()
        
        parsed_metrics = cached_metrics
        if isinstance(parsed_metrics, str):
            try:
                parsed_metrics = json.loads(parsed_metrics)
            except Exception:
                pass
                
        cache_by_date[d_key] = {
            "health_score": float(h_score),
            "metrics": parsed_metrics
        }

    # Identify missing/uncached dates
    uncached_dates = [d for d in unique_dates if d not in cache_by_date]

    # If all dates are cached, build history_payload directly and return
    if not uncached_dates:
        history_payload = []
        for d in parsed_dates:
            cached = cache_by_date[d]
            history_payload.append({
                "date_label": d.strftime("%d-%m"),
                "full_date": d.isoformat(),
                "health_score": cached["health_score"],
                "base_score": cached["metrics"].get("base_score", cached["health_score"]),
                "metrics": cached["metrics"].get("metrics_breakdown", cached["metrics"])
            })
        return history_payload

    # 3. Cache Miss: We need to calculate ratings for the uncached dates
    # Fetch all customers of the village via unified view
    cur.execute("""
        SELECT cid, name, ano, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, type, period, phone_number, status,
               CASE WHEN record_tier = 'active' THEN 'customer' ELSE record_tier END AS origin
        FROM v_all_customers
        WHERE vid = %s
    """, (vid,))
    all_cust_rows = cur.fetchall()
    if not all_cust_rows:
        return []

    cids = [r[0] for r in all_cust_rows]
    
    # Fetch all payments for these customers via unified view
    cur.execute("""
        SELECT cid, amt, payment_date
        FROM v_all_payments
        WHERE cid = ANY(%s)
        ORDER BY payment_date
    """, (cids,))
    pmt_rows = cur.fetchall()
    
    # Pre-parse payment dates and convert amounts to Decimal to avoid conversion overhead in loops
    # Pre-parse payment dates and build cumulative payment structure
    payments_by_cid = {cid: [] for cid in cids}
    cumulative_payments_by_cid = {cid: [] for cid in cids}

    running_totals = {cid: Decimal("0") for cid in cids}

    for cid, amt, p_date in pmt_rows:
        p_dt = p_date.date() if isinstance(p_date, datetime) else p_date
        amt_dec = Decimal(str(amt))

        payments_by_cid[cid].append({
            "amt": amt_dec,
            "payment_date": p_dt
        })

        running_totals[cid] += amt_dec

        cumulative_payments_by_cid[cid].append({
            "payment_date": p_dt,
            "cumulative_paid": running_totals[cid]
        })

    # Helper function to check overdue threshold (42 days for weekly, 180 days for monthly)
    def check_is_overdue_threshold(wk_details, ref_date, end_dt, balance, inst_amt, period):
        oldest_unpaid_due = None
        for wk in wk_details:
            due_dt = datetime.fromisoformat(wk["due_date"]).date()
            if due_dt <= ref_date:
                if wk["week"] <= int(period):
                    if wk["allocated"] < inst_amt:
                        oldest_unpaid_due = due_dt
                        break
        if not oldest_unpaid_due and ref_date > end_dt and balance > 0:
            oldest_unpaid_due = end_dt
        if oldest_unpaid_due:
            threshold_days = 180 if is_monthly else 42
            return (ref_date - oldest_unpaid_due).days > threshold_days
        return False

    # Collect all evaluation dates needed (the missing dates + their preceding cycle for stability check)
    days_step = 30 if is_monthly else 7
    calc_dates_needed = set()
    for d in uncached_dates:
        calc_dates_needed.add(d)
        calc_dates_needed.add(d - timedelta(days=days_step))
    calc_dates_needed = sorted(list(calc_dates_needed))
    
    # Store ratings and statuses by date, then customer cid
    ratings_by_date = {d: {} for d in calc_dates_needed}
    statuses_by_date = {d: {} for d in calc_dates_needed}
    overdue_6_w_by_date = {d: {} for d in calc_dates_needed}
    balance_by_date = {d: {} for d in calc_dates_needed}
    
    # Precompute customer-specific parameters with pre-parsed start_dt/end_dt/installment/period
    cust_list = []
    for cid, name, ano, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, c_type, period, phone_number, status, origin in all_cust_rows:
        if not start_date or not end_date:
            continue
        start_dt = start_date.date() if isinstance(start_date, datetime) else start_date
        end_dt = end_date.date() if isinstance(end_date, datetime) else end_date
        cust_list.append({
            "cid": cid,
            "name": name,
            "ano": ano,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "total_amount": float(total_amount or 0.0),
            "balance_amount": float(balance_amount or 0.0),
            "installment_amount": float(installment_amount or 0.0),
            "period": period,
            "type": c_type,
            "origin": origin,
            "payments": payments_by_cid.get(cid, []),
            "payment_dates": [p["payment_date"]
                for p in payments_by_cid.get(cid, [])
            ],
            "cumulative_payments": cumulative_payments_by_cid.get(cid, []),
            "status_orig": status
        })
        
    def get_total_paid_until(cumulative_list, eval_date):
        if not cumulative_list:
            return 0.0
        idx = bisect_right(
            [x["payment_date"] for x in cumulative_list],
            eval_date
        ) - 1
        if idx < 0:
            return 0.0
        return float(cumulative_list[idx]["cumulative_paid"])
    
    def get_payments_until(customer, eval_date):
        idx = bisect_right(
            customer["payment_dates"],
            eval_date
        )

        return customer["payments"][:idx]

    # Precompute bal_at_d for all customers across calc_dates_needed
    for d in calc_dates_needed:
        for c in cust_list:
            if c["start_dt"] > d:
                continue
            total_paid_at_d = get_total_paid_until(c["cumulative_payments"], d)
            balance_by_date[d][c["cid"]] = max(0.0, c["total_amount"] - total_paid_at_d)

    # For each date in calc_dates_needed, calculate ratings only for active/defaulted customers in pool
    for d in calc_dates_needed:
        for c in cust_list:
            if c["start_dt"] > d:
                continue
            
            bal_at_d = balance_by_date[d][c["cid"]]
            
            # Optimization: Skip closed/historic accounts that have 0 balance on date d if evaluating active view
            if view == "active":
                if sub_view == "active_only" and c["origin"] != "customer":
                    ratings_by_date[d][c["cid"]] = 100.0
                    statuses_by_date[d][c["cid"]] = "Closed"
                    overdue_6_w_by_date[d][c["cid"]] = False
                    continue
                elif sub_view == "active_defaulted" and c["origin"] != "customer" and bal_at_d <= 0:
                    ratings_by_date[d][c["cid"]] = 100.0
                    statuses_by_date[d][c["cid"]] = "Closed"
                    overdue_6_w_by_date[d][c["cid"]] = False
                    continue
            elif bal_at_d <= 0 and c["origin"] != "customer":
                # For complete view: if loan is already closed with 0 balance, rating is fixed/closed
                ratings_by_date[d][c["cid"]] = 100.0
                statuses_by_date[d][c["cid"]] = "Closed"
                overdue_6_w_by_date[d][c["cid"]] = False
                continue

            # Filter payments before or equal to d
            sub_payments = get_payments_until(c, d)
            # Run rating details
            score_h, risk_h, pen_h, wk_details_h = calculate_customer_rating_details(
                c["start_dt"], c["end_dt"], c["installment_amount"], c["period"], sub_payments, bal_at_d, loan_type=c["type"], today=d
            )
            beh_h = calculate_behavioral_analytics(
                c["start_dt"], c["end_dt"], c["installment_amount"], c["period"], sub_payments, bal_at_d, wk_details_h, loan_type=c["type"], today=d
            )
            
            ratings_by_date[d][c["cid"]] = score_h
            statuses_by_date[d][c["cid"]] = beh_h["status"]
            overdue_6_w_by_date[d][c["cid"]] = check_is_overdue_threshold(wk_details_h, d, c["end_dt"], bal_at_d, c["installment_amount"], c["period"])
            

    # Now calculate and cache the metrics for the uncached dates
    insert_cache_rows = []
    for d in uncached_dates:
        d_prev = d - timedelta(days=days_step)
        
        # Filter customers in the evaluated pool as of d
        pool = []
        for c in cust_list:
            if c["start_dt"] > d:
                continue
            
            total_paid_at_d = get_total_paid_until(c["cumulative_payments"],d)
            bal_at_d = max(0.0, c["total_amount"] - total_paid_at_d)
            
            # View-specific inclusion
            if view == "active":
                if sub_view == "active_only":
                    if c["origin"] == "customer":
                        pool.append((c, bal_at_d))
                else: # active_defaulted
                    if c["origin"] == "customer" or bal_at_d > 0:
                        pool.append((c, bal_at_d))
            else: # complete view
                pool.append((c, bal_at_d))
        
        if not pool:
            metrics_payload = {
                "base_score": 100.0,
                "metrics_breakdown": {
                    "avg_rating": {"value": 100.0, "contribution": 65.0},
                    "stability": {"value": 100.0, "contribution": 15.0},
                    "default_rate": {"value": 0.0, "contribution": 20.0},
                    "overdue_penalty": {"value": 0.0, "contribution": 0.0},
                    "severe_risk_penalty": {"value": 0.0, "contribution": 0.0},
                    "collection_drop": {"expected": 0.0, "actual": 0.0, "drop_pct": 0.0, "contribution": 0.0},
                    "customer_count_scale": {"count": 0, "contribution": 0.0},
                    "portfolio_size_factor": {"loan_sum": 0.0, "contribution": 0.0}
                }
            }
            cache_by_date[d] = {
                "health_score": 100.0,
                "metrics": metrics_payload
            }
            insert_cache_rows.append((vid, view, sub_view, time_range, d, 100.0, json.dumps(metrics_payload)))
            continue
            
        ratings = [ratings_by_date[d][c["cid"]] for c, bal in pool]
        
        # 2. Avg Repayment Rating
        avg_rating = sum(ratings) / len(ratings) if ratings else 100.0
        
        # 3. Stability
        stable_count = 0
        for c, bal in pool:
            rating_now = ratings_by_date[d][c["cid"]]
            rating_prev = ratings_by_date[d_prev].get(c["cid"], rating_now)
            if rating_now >= rating_prev:
                stable_count += 1
        stability_pct = (stable_count / len(pool) * 100.0) if pool else 100.0
        
        # 4. All-time Default Rate as of d
        all_time_customers = [c for c in cust_list if c["start_dt"] <= d]
        defaulted_customers_count = 0
        all_time_count = len(all_time_customers)
        for c in all_time_customers:
            if c["origin"] != "customer":
                bal_at_d = balance_by_date[d][c["cid"]]
                if bal_at_d > 0:
                    defaulted_customers_count += 1
        default_rate = (defaulted_customers_count / all_time_count) if all_time_count > 0 else 0.0
        default_score = (1.0 - default_rate) * 20.0
        
        # 5. Overdue concentration (> 6 weeks overdue)
        overdue_count = sum(1 for c, bal in pool if statuses_by_date[d][c["cid"]] in ["Overdue", "To Be Defaulted"] and overdue_6_w_by_date[d][c["cid"]])
        overdue_pct = (overdue_count / len(pool) * 100.0) if pool else 0.0
        
        # 6. Severe Credit Risk
        high_risk_count = sum(1 for r in ratings if r < 40)
        high_risk_pct = (high_risk_count / len(ratings) * 100.0) if ratings else 0.0
        
        # 7. Collection Drop
        expected_collection = 0.0
        active_count = 0
        active_loan_sum = 0.0
        for c, bal in pool:
            if c["origin"] == "customer" and c["start_dt"] <= d <= c["end_dt"]:
                expected_collection += c["installment_amount"]
                active_count += 1
                active_loan_sum += c["total_amount"]
                
        lookback_days = 30 if is_monthly else 7
        actual_collected = 0.0
        for c, bal in pool:
            for p in c["payments"]:
                if d - timedelta(days=lookback_days) < p["payment_date"] <= d:
                    actual_collected += float(p["amt"])
                    
        collection_drop_penalty = 0.0
        drop_pct = 0.0
        if expected_collection > 0.0:
            drop_pct = (expected_collection - actual_collected) / expected_collection
            if drop_pct > 0.24:
                collection_drop_penalty = 10.0
                
        # 8. Customer Count Scaling (Threshold 150)
        if active_count < 150:
            customer_count_adjustment = -min(5.0, (150 - active_count) * 0.05)
        else:
            customer_count_adjustment = min(5.0, (active_count - 150) * 0.05)
            
        # 9. Portfolio size reward/risk
        portfolio_size_factor = min(5.0, (active_loan_sum / 3000000.0) * 5.0)
        
        # Base Score
        base_score = (avg_rating * 0.65) + (stability_pct * 0.15) + default_score \
                     - (overdue_pct * 0.3) - (high_risk_pct * 0.3) \
                     - collection_drop_penalty + customer_count_adjustment
                     
        if base_score >= 75.0:
            portfolio_adjustment = portfolio_size_factor
        else:
            portfolio_adjustment = -portfolio_size_factor
            
        final_health_score = max(0.0, min(100.0, base_score + portfolio_adjustment))

        metrics_payload = {
            "base_score": round(base_score, 1),
            "metrics_breakdown": {
                "avg_rating": {
                    "value": round(avg_rating, 1),
                    "contribution": round_curr(avg_rating * 0.65)
                },
                "stability": {
                    "value": round(stability_pct, 1),
                    "contribution": round_curr(stability_pct * 0.15)
                },
                "default_rate": {
                    "value": round(default_rate * 100.0, 1),
                    "contribution": round_curr(default_score)
                },
                "overdue_penalty": {
                    "value": round(overdue_pct, 1),
                    "contribution": round_curr(-overdue_pct * 0.3)
                },
                "severe_risk_penalty": {
                    "value": round(high_risk_pct, 1),
                    "contribution": round_curr(-high_risk_pct * 0.3)
                },
                "collection_drop": {
                    "expected": round_curr(expected_collection),
                    "actual": round_curr(actual_collected),
                    "drop_pct": round(drop_pct * 100.0, 1),
                    "contribution": round_curr(-collection_drop_penalty)
                },
                "customer_count_scale": {
                    "count": active_count,
                    "contribution": round_curr(customer_count_adjustment)
                },
                "portfolio_size_factor": {
                    "loan_sum": round_curr(active_loan_sum),
                    "contribution": round_curr(portfolio_adjustment)
                }
            }
        }
        
        cache_by_date[d] = {
            "health_score": round(final_health_score, 1),
            "metrics": metrics_payload
        }
        insert_cache_rows.append((
            vid, view, sub_view, time_range, d,
            round(final_health_score, 1), json.dumps(metrics_payload)
        ))

    # Write newly computed snapshots to db cache in a single transaction
    if insert_cache_rows:
        execute_values(cur, """
            INSERT INTO village_health_cache (vid, view, sub_view, time_range, date_key, health_score, metrics)
            VALUES %s
            ON CONFLICT (vid, view, sub_view, time_range, date_key)
            DO UPDATE SET health_score = EXCLUDED.health_score, metrics = EXCLUDED.metrics, updated_at = CURRENT_TIMESTAMP
        """, insert_cache_rows)

    # 4. Construct chronological history_payload to return
    history_payload = []
    for d in parsed_dates:
        cached = cache_by_date[d]
        history_payload.append({
            "date_label": d.strftime("%d-%m"),
            "full_date": d.isoformat(),
            "health_score": cached["health_score"],
            "base_score": cached["metrics"].get("base_score", cached["health_score"]),
            "metrics": cached["metrics"].get("metrics_breakdown", cached["metrics"])
        })

    return history_payload


@app.route("/api/village/health_history/<int:vid>")
@login_required
def api_village_health_history(vid):
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])
    if user_level not in ["admin", "mgmt"] and vid not in allowed_villages:
        return jsonify(success=False, error="Unauthorized village access"), 403

    KOLKATA = pytz.timezone('Asia/Kolkata')
    today = datetime.now(KOLKATA).date()
    
    view = request.args.get("view", "active")
    sub_view = request.args.get("sub_view", "active_only")
    time_range = request.args.get("range", "weekly")
    force_recalc = request.args.get("force_recalc", "false").lower() == "true"
    event_days = request.args.get("event_days", default=30, type=int)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        is_monthly = is_village_monthly(vid, cur)
        if is_monthly and time_range == "weekly":
            time_range = "monthly"

        if force_recalc:
            cur.execute("DELETE FROM village_health_cache WHERE vid = %s", (vid,))

        # Shifting reference date to mitigate posting lag
        cur.execute("SELECT MAX(payment_date) FROM v_all_payments WHERE vid = %s", (vid,))
        latest_payment_row = cur.fetchone()
        latest_payment_in_village = latest_payment_row[0] if latest_payment_row else None
        
        eval_today = today
        if latest_payment_in_village:
            if isinstance(latest_payment_in_village, datetime):
                latest_payment_in_village = latest_payment_in_village.date()
            lag_days = (today - latest_payment_in_village).days
            lag_threshold = 35 if is_monthly else 7
            max_shift = 60 if is_monthly else 14
            if lag_days > lag_threshold:
                shift_days = min(lag_days, max_shift)
                eval_today = today - timedelta(days=shift_days)

        # Generate evaluation dates based on range
        if time_range == "weekly":
            dates = [eval_today - timedelta(days=7 * i) for i in range(5, -1, -1)]
        elif time_range == "monthly":
            dates = [eval_today - timedelta(days=30 * i) for i in range(5, -1, -1)]
        elif time_range == "yearly":
            dates = [eval_today - timedelta(days=30 * i) for i in range(11, -1, -1)]
        else: # complete view
            cur.execute("SELECT MIN(start_date) FROM v_all_customers WHERE vid = %s", (vid,))
            min_s_row = cur.fetchone()
            min_start = min_s_row[0] if min_s_row and min_s_row[0] else None
            if min_start:
                if isinstance(min_start, datetime):
                    min_start = min_start.date()
                total_days = (eval_today - min_start).days
                if total_days <= 0:
                    dates = [eval_today]
                else:
                    if total_days <= 90:
                        step = 7
                    elif total_days <= 365:
                        step = 14
                    else:
                        step = 30
                    
                    dates = []
                    curr = eval_today
                    while curr >= min_start:
                        dates.append(curr)
                        curr -= timedelta(days=step)
                    dates.reverse()
                    if len(dates) > 24:
                        indices = [int(i * (len(dates) - 1) / 23) for i in range(24)]
                        dates = [dates[idx] for idx in indices]
            else:
                dates = [eval_today - timedelta(days=30 * i) for i in range(5, -1, -1)]

        t0 = pytime.perf_counter()

        history_points = calculate_village_health_history(vid, cur, view, sub_view, dates, time_range=time_range)

        print(
           f"Health history took "
           f"{pytime.perf_counter() - t0:.2f}s"
        )

        if event_days > 0:
            event_start = today - timedelta(days=event_days)
            event_end = today
        else:
            event_start = dates[0]
            event_end = dates[-1]
        
        cur.execute("""
            SELECT action, username, details, created_at, entity_type, entity_id
            FROM audit_log 
            WHERE 
              (entity_id::text = %s::text OR 
               (details->>'vid')::int = %s OR
               (entity_type = 'customer' AND (entity_id::text IN (SELECT cid::text FROM customer WHERE vid = %s) OR entity_id::text IN (SELECT cid::text FROM closed_cust_account WHERE vid = %s))))
              AND created_at >= %s AND created_at <= %s
            ORDER BY created_at DESC
        """, (vid, vid, vid, vid, event_start, event_end + timedelta(days=1)))
        event_rows = cur.fetchall()
        
        events = []
        for r in event_rows:
            evt_created = r[3]
            events.append({
                "action": r[0],
                "username": r[1],
                "details": r[2],
                "created_at": evt_created.strftime("%d-%m-%Y %I:%M %p") if evt_created else "-",
                "date_key": evt_created.strftime("%d-%m") if evt_created else "",
                "entity_type": r[4],
                "entity_id": r[5]
            })

        conn.commit()
        return jsonify(success=True, is_monthly=is_monthly, history=history_points, events=events)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()


def compute_and_cache_behavioral_analytics(vid, cur, view, sub_view, today, force_recalc=False):
    # Get village details
    cur.execute("SELECT village_name, village_code FROM village WHERE vid = %s", (vid,))
    v_row = cur.fetchone()
    if not v_row:
        raise ValueError("Village not found")
    v_name, v_code = v_row
    is_monthly = is_village_monthly(vid, cur)

    # Shifting reference date to mitigate posting lag
    cur.execute("SELECT MAX(payment_date) FROM v_all_payments WHERE vid = %s", (vid,))
    latest_payment_row = cur.fetchone()
    latest_payment_in_village = latest_payment_row[0] if latest_payment_row else None
    
    eval_today = today
    if latest_payment_in_village:
        if isinstance(latest_payment_in_village, datetime):
            latest_payment_in_village = latest_payment_in_village.date()
        lag_days = (today - latest_payment_in_village).days
        lag_threshold = 35 if is_monthly else 7
        max_shift = 60 if is_monthly else 14
        if lag_days > lag_threshold:
            shift_days = min(lag_days, max_shift)
            eval_today = today - timedelta(days=shift_days)

    if force_recalc:
        cur.execute("DELETE FROM village_health_cache WHERE vid = %s AND view = %s AND sub_view = %s AND time_range = 'dashboard'", (vid, view, sub_view))
    else:
        cur.execute("""
            SELECT metrics FROM village_health_cache
            WHERE vid = %s AND view = %s AND sub_view = %s AND time_range = 'dashboard' AND date_key = %s
        """, (vid, view, sub_view, eval_today))
        cached_row = cur.fetchone()
        if cached_row:
            cached_metrics = cached_row[0]
            if isinstance(cached_metrics, str):
                try:
                    cached_metrics = json.loads(cached_metrics)
                except Exception:
                    pass
            # Safety: the dashboard cache stores the entire payload as metrics.
            # Only return it if it actually has village_name (full payload) — not a metrics_breakdown blob.
            if isinstance(cached_metrics, dict) and "village_name" in cached_metrics:
                return cached_metrics
            # Otherwise fall through and recompute (stale/wrong format)

    # Get evaluated customers for the village via unified view
    if view == "active":
        if sub_view == "active_only":
            cur.execute("""
                SELECT cid, name, ano, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, type, period, phone_number, 'active' AS status, customer_rating
                FROM v_all_customers
                WHERE vid = %s AND record_tier = 'active'
            """, (vid,))
        else: # active_defaulted
            cur.execute("""
                SELECT cid, name, ano, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, type, period, phone_number, 
                       CASE WHEN record_tier = 'active' THEN 'active' ELSE status END AS status, customer_rating
                FROM v_all_customers
                WHERE vid = %s AND (record_tier = 'active' OR balance_amount > 0)
            """, (vid,))
    else: # complete view
        cur.execute("""
            SELECT cid, name, ano, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, type, period, phone_number, 
                   CASE WHEN record_tier = 'active' THEN 'active' ELSE status END AS status, customer_rating
            FROM v_all_customers
            WHERE vid = %s
        """, (vid,))

    cust_rows = cur.fetchall()
    if not cust_rows:
        return {
            "village_name": v_name,
            "village_code": v_code,
            "empty": True
        }

    cids = [r[0] for r in cust_rows]
    
    # Get all payments for these customers via unified view
    cur.execute("""
        SELECT cid, amt, payment_date
        FROM v_all_payments
        WHERE cid = ANY(%s)
        ORDER BY payment_date
    """, (cids,))
    pmt_rows = cur.fetchall()
    
    payments_by_cid = {cid: [] for cid in cids}
    for cid, amt, p_date in pmt_rows:
        p_dt = p_date.date() if isinstance(p_date, datetime) else p_date
        payments_by_cid[cid].append({"amt": Decimal(str(amt)), "payment_date": p_dt})

    cycle_days = 30 if is_monthly else 7
    dates = [eval_today - timedelta(days=cycle_days * i) for i in range(5, -1, -1)]
    
    historical_ratings = {i: {} for i in range(6)}
    historical_status = {i: {} for i in range(6)}
    historical_missed = {i: {} for i in range(6)}
    
    cust_details = {}
    
    dt4 = dates[4]
    dt3 = dates[3]
    
    for cid, name, ano, start_date, end_date, total_amount, paid_amount, balance_amount, installment_amount, c_type, period, phone_number, status, db_rating in cust_rows:
        if not start_date or not end_date:
            continue
        start_dt = start_date.date() if isinstance(start_date, datetime) else start_date
        end_dt = end_date.date() if isinstance(end_date, datetime) else end_date
        cust_payments = payments_by_cid.get(cid, [])
        
        # Filter payments before or equal to eval_today
        eval_payments = [p for p in cust_payments if p["payment_date"] <= eval_today]
        
        score_t, risk_t, pen_t, wk_details_t = calculate_customer_rating_details(
            start_dt, end_dt, installment_amount, period, eval_payments, balance_amount, loan_type=c_type, today=eval_today
        )
        beh_t = calculate_behavioral_analytics(
            start_dt, end_dt, installment_amount, period, eval_payments, balance_amount, wk_details_t, loan_type=c_type, today=eval_today
        )
        
        last_pay_date = None
        for p in eval_payments:
            p_dt = p["payment_date"]
            if not last_pay_date or p_dt > last_pay_date:
                last_pay_date = p_dt
        last_payment_date_str = format_date_display(last_pay_date) if last_pay_date else "-"
        
        consec_missed_count = 0
        for wk in reversed(wk_details_t):
            if wk["due_date"] <= eval_today.isoformat():
                if wk["status"] in ["MISSED", "OVERDUE"] and wk["allocated"] == 0:
                    consec_missed_count += 1
                else:
                    break
        
        cust_details[cid] = {
            "cid": cid,
            "name": name,
            "ano": ano,
            "total_amount": float(total_amount or 0),
            "paid_amount": float(paid_amount or 0),
            "balance_amount": float(balance_amount or 0),
            "rating": int(round(float(db_rating))) if db_rating is not None else (int(round(float(score_t))) if score_t is not None else 100),
            "status": beh_t["status"],
            "last_payment_date": last_payment_date_str,
            "missed_cycles": consec_missed_count,
            "predicted_next_risk": beh_t["predicted_next_risk"],
            "stability_score": beh_t["stability"]["score"],
            "stability_label": beh_t["stability"]["label"]
        }
        
        # 1. Store index 5 (today)
        historical_ratings[5][cid] = score_t
        historical_status[5][cid] = beh_t["status"]
        historical_missed[5][cid] = beh_t["discipline"]["missed"]
        
        # 2. Store index 4 (last week)
        if start_dt > dt4:
            historical_ratings[4][cid] = 100.0
            historical_status[4][cid] = "OnTrack"
            historical_missed[4][cid] = 0
        else:
            sub_payments = [p for p in eval_payments if p["payment_date"] <= dt4]
            score_h, risk_h, pen_h, wk_details_h = calculate_customer_rating_details(
                start_dt, end_dt, installment_amount, period, sub_payments, balance_amount, loan_type=c_type, today=dt4
            )
            beh_h = calculate_behavioral_analytics(
                start_dt, end_dt, installment_amount, period, sub_payments, balance_amount, wk_details_h, loan_type=c_type, today=dt4
            )
            historical_ratings[4][cid] = score_h
            historical_status[4][cid] = beh_h["status"]
            historical_missed[4][cid] = beh_h["discipline"]["missed"]
            
        # 3. Store index 3 (2 weeks ago)
        if start_dt > dt3:
            historical_ratings[3][cid] = 100.0
            historical_status[3][cid] = "OnTrack"
            historical_missed[3][cid] = 0
        else:
            sub_payments = [p for p in eval_payments if p["payment_date"] <= dt3]
            score_h, risk_h, pen_h, wk_details_h = calculate_customer_rating_details(
                start_dt, end_dt, installment_amount, period, sub_payments, balance_amount, loan_type=c_type, today=dt3
            )
            historical_ratings[3][cid] = score_h
            historical_status[3][cid] = "OnTrack"
            historical_missed[3][cid] = 0

        # 4. Fill defaults for 0, 1, 2 (never read)
        for idx in [0, 1, 2]:
            historical_ratings[idx][cid] = 100.0
            historical_status[idx][cid] = "OnTrack"
            historical_missed[idx][cid] = 0

    t0 = pytime.perf_counter()
    # Run 6-cycle shared health history calculator
    history_points = calculate_village_health_history(vid, cur, view, sub_view, dates, time_range=("monthly" if is_monthly else "weekly"))
    print(
           f"Health history took "
           f"{pytime.perf_counter() - t0:.2f}s"
        )
    
    health_trend = []
    for pt in history_points:
        health_trend.append({
            "date": pt["date_label"],
            "health_score": pt["health_score"],
            "avg_rating": pt["metrics"]["avg_rating"]["value"],
            "overdue_pct": pt["metrics"]["overdue_penalty"]["value"]
        })
        
    current_health_details = history_points[-1]
    current_health = current_health_details["health_score"]
    last_week_health = history_points[-2]["health_score"] if len(history_points) > 1 else current_health
    trend_val = current_health - last_week_health
    
    if trend_val > 0:
        trend_text = f"↑ {trend_val:.1f} points"
    elif trend_val < 0:
        trend_text = f"↓ {abs(trend_val):.1f} points"
    else:
        trend_text = "→ Stable"
        
    health_status = "Stable"
    if current_health >= 80:
        health_status = "Excellent"
    elif current_health >= 70:
        health_status = "Stable"
    elif current_health >= 55:
        health_status = "Warning"
    else:
        health_status = "Critical"
        
    predicted_risk = "Low"
    if current_health >= 85:
        predicted_risk = "Low"
    elif current_health >= 70:
        predicted_risk = "Medium"
    elif current_health >= 55:
        predicted_risk = "High"
    else:
        predicted_risk = "Critical"

    risk_dist = {"Excellent": [], "Good": [], "LowRisk": [], "HighRisk": []}
    risk_dist_last_week = {"Excellent": 0, "Good": 0, "LowRisk": 0, "HighRisk": 0}
    
    transitions = {
        "Excellent_Good": [],
        "Good_LowRisk": [],
        "LowRisk_HighRisk": [],
        "Newly_Overdue": [],
        "Recovered": []
    }
    
    for cid, details in cust_details.items():
        score_now = historical_ratings[5][cid]
        score_prev = historical_ratings[4].get(cid, score_now)
        
        status_now = historical_status[5][cid]
        status_prev = historical_status[4].get(cid, status_now)
        
        cat_now = "Excellent" if score_now > 80 else ("Good" if score_now >= 60 else ("LowRisk" if score_now >= 40 else "HighRisk"))
        cat_prev = "Excellent" if score_prev > 80 else ("Good" if score_prev >= 60 else ("LowRisk" if score_prev >= 40 else "HighRisk"))
        
        cust_payload = {
            "ano": details["ano"],
            "name": details["name"],
            "total_amount": details["total_amount"],
            "paid_amount": details["paid_amount"],
            "balance_amount": details["balance_amount"],
            "rating": details["rating"],
            "last_payment_date": details["last_payment_date"],
            "missed_cycles": details["missed_cycles"],
            "status": details["status"]
        }
        
        risk_dist[cat_now].append(cust_payload)
        risk_dist_last_week[cat_prev] += 1
        
        if cat_prev == "Excellent" and cat_now == "Good":
            transitions["Excellent_Good"].append(cust_payload)
        elif cat_prev == "Good" and cat_now == "LowRisk":
            transitions["Good_LowRisk"].append(cust_payload)
        elif cat_prev == "LowRisk" and cat_now == "HighRisk":
            transitions["LowRisk_HighRisk"].append(cust_payload)
            
        was_overdue = status_prev in ["Overdue", "To Be Defaulted"]
        is_overdue = status_now in ["Overdue", "To Be Defaulted"]
        
        if not was_overdue and is_overdue:
            transitions["Newly_Overdue"].append(cust_payload)
        elif was_overdue and not is_overdue:
            transitions["Recovered"].append(cust_payload)
            
    total_cust = len(cust_details)
    risk_dist_payload = []
    for cat in ["Excellent", "Good", "LowRisk", "HighRisk"]:
        lst = risk_dist[cat]
        cnt = len(lst)
        prev_cnt = risk_dist_last_week[cat]
        diff = cnt - prev_cnt
        pct = (cnt / total_cust * 100.0) if total_cust else 0.0
        
        risk_dist_payload.append({
            "category": cat,
            "label": "Low Risk" if cat == "LowRisk" else ("High Risk" if cat == "HighRisk" else cat),
            "count": cnt,
            "percentage": round(pct, 1),
            "change": f"+{diff}" if diff > 0 else (str(diff) if diff < 0 else "0"),
            "list": lst
        })

    stress_alerts = []
    cycle_name = "month" if is_monthly else "week"
    cycle_Name = "Month" if is_monthly else "Week"
    cycle_step = 30 if is_monthly else 7

    period_payments = {1: Decimal(0), 2: Decimal(0), 3: Decimal(0)}
    for p_list in payments_by_cid.values():
        for p in p_list:
            p_dt = p["payment_date"].date() if isinstance(p["payment_date"], datetime) else p["payment_date"]
            if eval_today - timedelta(days=cycle_step) < p_dt <= eval_today:
                period_payments[1] += Decimal(str(p["amt"]))
            elif eval_today - timedelta(days=cycle_step * 2) < p_dt <= eval_today - timedelta(days=cycle_step):
                period_payments[2] += Decimal(str(p["amt"]))
            elif eval_today - timedelta(days=cycle_step * 3) < p_dt <= eval_today - timedelta(days=cycle_step * 2):
                period_payments[3] += Decimal(str(p["amt"]))
                
    if period_payments[1] < period_payments[2] < period_payments[3]:
        stress_alerts.append({
            "type": "Collection Slowdown",
            "message": f"Collections slowing: {cycle_Name}ly payment volume decreased continuously for the last 3 {cycle_name}s ({period_payments[3]:,.0f} → {period_payments[2]:,.0f} → {period_payments[1]:,.0f}).",
            "severity": "High"
        })
        
    partial_today = sum(1 for cid in cust_details.keys() if historical_status[5][cid] == "PARTIAL")
    partial_last_cycle = sum(1 for cid in cust_details.keys() if historical_status[4].get(cid, "OnTrack") == "PARTIAL")
    if partial_today > partial_last_cycle:
        pct_inc = ((partial_today - partial_last_cycle) / partial_last_cycle * 100.0) if partial_last_cycle > 0 else 100.0
        if pct_inc >= 15.0:
            stress_alerts.append({
                "type": "Quality Decline",
                "message": f"Partial repayments increased by {pct_inc:.0f}% compared to last {cycle_name} ({partial_last_cycle} → {partial_today}).",
                "severity": "Medium"
            })
            
    overdue_today = sum(1 for cid in cust_details.keys() if historical_status[5][cid] in ["Overdue", "To Be Defaulted"])
    overdue_last_cycle = sum(1 for cid in cust_details.keys() if historical_status[4].get(cid) in ["Overdue", "To Be Defaulted"])
    if overdue_today > overdue_last_cycle:
        stress_alerts.append({
            "type": "Increasing Delay",
            "message": f"Active overdue/delayed cases increased from {overdue_last_cycle} to {overdue_today} this {cycle_name}.",
            "severity": "High"
        })
        
    avg_rating_today = health_trend[-1]["avg_rating"]
    avg_rating_3_cycles_ago = health_trend[-4]["avg_rating"] if len(health_trend) >= 4 else avg_rating_today
    if avg_rating_today < avg_rating_3_cycles_ago - 5.0:
        stress_alerts.append({
            "type": "Portfolio Stress",
            "message": f"Deteriorating portfolio: Village average rating dropped from {avg_rating_3_cycles_ago:.1f} to {avg_rating_today:.1f} over the last 3 {cycle_name}s.",
            "severity": "Critical"
        })

    critical_attention = {
        "Missed4Plus": [],
        "RapidCollapse": [],
        "SevereOverdue": [],
        "RatingBelow40": []
    }
    
    for cid, details in cust_details.items():
        score_now = historical_ratings[5][cid]
        score_2_w_ago = historical_ratings[3].get(cid, score_now)
        
        cust_payload = {
            "ano": details["ano"],
            "name": details["name"],
            "rating": details["rating"],
            "balance_amount": details["balance_amount"],
            "missed_cycles": details["missed_cycles"],
            "status": details["status"]
        }
        
        if details["missed_cycles"] >= 4:
            critical_attention["Missed4Plus"].append(cust_payload)
        if score_now < score_2_w_ago - 15.0:
            critical_attention["RapidCollapse"].append(cust_payload)
        if details["status"] == "To Be Defaulted" or (details["status"] == "Overdue" and details["rating"] < 50):
            critical_attention["SevereOverdue"].append(cust_payload)
        if details["rating"] < 40:
            critical_attention["RatingBelow40"].append(cust_payload)

    payload = {
        "village_name": v_name,
        "village_code": v_code,
        "empty": False,
        "is_monthly": is_monthly,
        "health": {
            "score": round(current_health, 1),
            "status": health_status,
            "predicted_risk": predicted_risk,
            "trend_text": trend_text,
            "trend_val": round(trend_val, 1)
        },
        "metrics": current_health_details["metrics"],
        "health_trend": health_trend,
        "risk_distribution": risk_dist_payload,
        "transitions": {k: v for k, v in transitions.items()},
        "stress_alerts": stress_alerts,
        "critical_attention": {
            "Missed4Plus": {
                "label": "4+ Consecutive Missed Cycles",
                "urgency": "Critical",
                "count": len(critical_attention["Missed4Plus"]),
                "list": critical_attention["Missed4Plus"]
            },
            "RapidCollapse": {
                "label": "Rapidly Collapsing Ratings (-15 pts)",
                "urgency": "High",
                "count": len(critical_attention["RapidCollapse"]),
                "list": critical_attention["RapidCollapse"]
            },
            "SevereOverdue": {
                "label": "Severe Overdue Behavior",
                "urgency": "Critical",
                "count": len(critical_attention["SevereOverdue"]),
                "list": critical_attention["SevereOverdue"]
            },
            "RatingBelow40": {
                "label": "Customer Ratings Below 40",
                "urgency": "Critical",
                "count": len(critical_attention["RatingBelow40"]),
                "list": critical_attention["RatingBelow40"]
            }
        }
    }
    
    # Save to dashboard cache
    cur.execute("""
        INSERT INTO village_health_cache (vid, view, sub_view, time_range, date_key, health_score, metrics)
        VALUES (%s, %s, %s, 'dashboard', %s, %s, %s)
        ON CONFLICT (vid, view, sub_view, time_range, date_key)
        DO UPDATE SET health_score = EXCLUDED.health_score, metrics = EXCLUDED.metrics, updated_at = CURRENT_TIMESTAMP
    """, (vid, view, sub_view, eval_today, round(current_health, 1), json.dumps(payload)))

    return payload


@app.route("/api/village/behavioral_analytics/<int:vid>", methods=["GET", "QUERY"])
@login_required
@ttl_cache(ttl_seconds=300)
def api_village_behavioral_analytics(vid):
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])
    if user_level not in ["admin", "mgmt"] and vid not in allowed_villages:
        return jsonify(success=False, error="Unauthorized village access"), 403

    KOLKATA = pytz.timezone('Asia/Kolkata')
    today = datetime.now(KOLKATA).date()
    view = request.args.get("view", "active")
    sub_view = request.args.get("sub_view", "active_only")
    force_recalc = request.args.get("force_recalc", "false").lower() == "true"

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        t0 = pytime.perf_counter()
        payload = compute_and_cache_behavioral_analytics(vid, cur, view, sub_view, today, force_recalc)
        conn.commit()
        print(
            f"Health history took "
            f"{pytime.perf_counter() - t0:.2f}s"
        )
        return jsonify(success=True, data=payload)
    except ValueError as e:
        return jsonify(success=False, error=str(e)), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/dashboard/analytics/<int:vid>", methods=["GET", "QUERY"])
@login_required
@ttl_cache(ttl_seconds=300)
def api_dashboard_analytics(vid):
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])
    if user_level not in ["admin", "mgmt"] and vid not in allowed_villages:
        return jsonify(success=False, error="Unauthorized village access"), 403

    KOLKATA = pytz.timezone('Asia/Kolkata')
    today = datetime.now(KOLKATA).date()
    
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        view = request.args.get("view", "active")

        # Fetch village rates
        cur.execute("SELECT interest_rate, cutting_rate FROM village WHERE vid = %s", (vid,))
        rates_row = cur.fetchone()
        interest_rate = float(rates_row[0]) if rates_row and rates_row[0] is not None else 0.0
        cutting_rate = float(rates_row[1]) if rates_row and rates_row[1] is not None else 0.0

        # Fetch customers across all tiers via unified view
        if view == "active":
            cur.execute("""
                SELECT cid, start_date, closed_at, total_amount, balance_amount, paid_amount, base_amount, cutting_amount, interest_amount, record_tier
                FROM v_all_customers
                WHERE vid = %s AND (record_tier = 'active' OR balance_amount > 0)
            """, (vid,))
        else:
            cur.execute("""
                SELECT cid, start_date, closed_at, total_amount, balance_amount, paid_amount, base_amount, cutting_amount, interest_amount, record_tier
                FROM v_all_customers
                WHERE vid = %s
            """, (vid,))
        all_cust_rows = cur.fetchall()
        
        # Partition into active (8 fields without closed_at) and closed/historic (9 fields with closed_at)
        active_rows = [(r[0], r[1], r[3], r[4], r[5], r[6], r[7], r[8]) for r in all_cust_rows if r[9] == 'active']
        closed_rows = [r[:9] for r in all_cust_rows if r[9] == 'closed']
        historic_rows = [r[:9] for r in all_cust_rows if r[9] == 'historic']

        # Gather all customer IDs to fetch their payments
        cids = [r[0] for r in all_cust_rows]

        payments_by_cid = {}
        if cids:
            # 3. Fetch all payments via unified view
            cur.execute("""
                SELECT cid, amt, payment_date
                FROM v_all_payments
                WHERE cid = ANY(%s)
                ORDER BY payment_date
            """, (cids,))
            pmt_rows = cur.fetchall()
            for cid, amt, p_date in pmt_rows:
                if cid not in payments_by_cid:
                    payments_by_cid[cid] = []
                payments_by_cid[cid].append({
                    "amt": float(amt),
                    "date": p_date.date() if isinstance(p_date, datetime) else p_date
                })

        # Helper to compute history
        def compute_history_for_dates(dates_list, label_format):
            h_list = []
            for dt in dates_list:
                active_count = 0
                defaulted_count = 0
                closed_count = 0

                active_loan = 0.0
                defaulted_loan = 0.0
                closed_loan = 0.0

                active_bal = 0.0
                defaulted_bal = 0.0

                active_loan_p = 0.0
                active_loan_i = 0.0
                active_loan_r = 0.0

                active_bal_p = 0.0
                active_bal_i = 0.0
                active_bal_r = 0.0

                defaulted_loan_p = 0.0
                defaulted_loan_i = 0.0
                defaulted_loan_r = 0.0

                defaulted_bal_p = 0.0
                defaulted_bal_i = 0.0
                defaulted_bal_r = 0.0

                closed_loan_p = 0.0
                closed_loan_i = 0.0
                closed_loan_r = 0.0

                # Process currently active customers
                for cid, start_date, total_amount, balance_amount, paid_amount, base_amount, cutting_amount, interest_amount in active_rows:
                    if not start_date:
                        continue
                    start_dt = start_date.date() if isinstance(start_date, datetime) else start_date
                    if start_dt > dt:
                        continue

                    pmts = payments_by_cid.get(cid, [])
                    paid_at_T = sum(p["amt"] for p in pmts if p["date"] <= dt)
                    bal_at_T = max(0.0, float(total_amount) - paid_at_T)

                    active_count += 1
                    active_loan += float(total_amount)
                    active_bal += bal_at_T

                    # calculate splits
                    i_orig = float(interest_amount if interest_amount is not None and interest_amount > 0 else (float(total_amount) * (interest_rate / 100.0)))
                    r_orig = float(cutting_amount if cutting_amount is not None and cutting_amount > 0 else (float(total_amount) * (cutting_rate / 100.0)))
                    p_orig = float(base_amount if base_amount is not None and base_amount > 0 else (float(total_amount) - i_orig - r_orig))

                    p_rem = max(0.0, bal_at_T - i_orig - r_orig)
                    i_rem = max(0.0, min(i_orig, bal_at_T - r_orig))
                    r_rem = max(0.0, min(r_orig, bal_at_T))

                    active_loan_p += p_orig
                    active_loan_i += i_orig
                    active_loan_r += r_orig
                    active_bal_p += p_rem
                    active_bal_i += i_rem
                    active_bal_r += r_rem

                # Process currently closed and historic customers
                for cid, start_date, closed_at, total_amount, balance_amount, paid_amount, base_amount, cutting_amount, interest_amount in closed_rows + historic_rows:
                    if not start_date:
                        continue
                    start_dt = start_date.date() if isinstance(start_date, datetime) else start_date
                    if start_dt > dt:
                        continue

                    closed_dt = closed_at.date() if isinstance(closed_at, datetime) else closed_at
                    is_active_at_T = (closed_dt is None or dt < closed_dt)

                    pmts = payments_by_cid.get(cid, [])
                    paid_at_T = sum(p["amt"] for p in pmts if p["date"] <= dt)
                    bal_at_T = max(0.0, float(total_amount) - paid_at_T)

                    # calculate splits
                    i_orig = float(interest_amount if interest_amount is not None and interest_amount > 0 else (float(total_amount) * (interest_rate / 100.0)))
                    r_orig = float(cutting_amount if cutting_amount is not None and cutting_amount > 0 else (float(total_amount) * (cutting_rate / 100.0)))
                    p_orig = float(base_amount if base_amount is not None and base_amount > 0 else (float(total_amount) - i_orig - r_orig))

                    p_rem = max(0.0, bal_at_T - i_orig - r_orig)
                    i_rem = max(0.0, min(i_orig, bal_at_T - r_orig))
                    r_rem = max(0.0, min(r_orig, bal_at_T))

                    if is_active_at_T:
                        active_count += 1
                        active_loan += float(total_amount)
                        active_bal += bal_at_T

                        active_loan_p += p_orig
                        active_loan_i += i_orig
                        active_loan_r += r_orig
                        active_bal_p += p_rem
                        active_bal_i += i_rem
                        active_bal_r += r_rem
                    else:
                        if bal_at_T > 0:
                            defaulted_count += 1
                            defaulted_loan += float(total_amount)
                            defaulted_bal += bal_at_T

                            defaulted_loan_p += p_orig
                            defaulted_loan_i += i_orig
                            defaulted_loan_r += r_orig
                            defaulted_bal_p += p_rem
                            defaulted_bal_i += i_rem
                            defaulted_bal_r += r_rem
                        else:
                            closed_count += 1
                            closed_loan += float(total_amount)

                            closed_loan_p += p_orig
                            closed_loan_i += i_orig
                            closed_loan_r += r_orig

                h_list.append({
                    "date": dt.strftime(label_format),
                    "customers": {
                        "active": active_count,
                        "defaulted": defaulted_count,
                        "closed": closed_count,
                        "total": active_count + defaulted_count + closed_count
                    },
                    "loan_amount": {
                        "active": active_loan,
                        "defaulted": defaulted_loan,
                        "closed": closed_loan,
                        "total": active_loan + defaulted_loan + closed_loan,
                        "split": {
                            "active": {"p": active_loan_p, "i": active_loan_i, "r": active_loan_r},
                            "defaulted": {"p": defaulted_loan_p, "i": defaulted_loan_i, "r": defaulted_loan_r},
                            "closed": {"p": closed_loan_p, "i": closed_loan_i, "r": closed_loan_r},
                            "total": {
                                "p": active_loan_p + defaulted_loan_p + closed_loan_p,
                                "i": active_loan_i + defaulted_loan_i + closed_loan_i,
                                "r": active_loan_r + defaulted_loan_r + closed_loan_r
                            }
                        }
                    },
                    "balance": {
                        "active": active_bal,
                        "defaulted": defaulted_bal,
                        "total": active_bal + defaulted_bal,
                        "split": {
                            "active": {"p": active_bal_p, "i": active_bal_i, "r": active_bal_r},
                            "defaulted": {"p": defaulted_bal_p, "i": defaulted_bal_i, "r": defaulted_bal_r},
                            "total": {
                                "p": active_bal_p + defaulted_bal_p,
                                "i": active_bal_i + defaulted_bal_i,
                                "r": active_bal_r + defaulted_bal_r
                            }
                        }
                    }
                })
            return h_list

        # A. Weekly Snapshots (Last 12 weeks)
        dates_weekly = [today - timedelta(days=7 * (11 - i)) for i in range(12)]
        history_weekly = compute_history_for_dates(dates_weekly, "%d-%m")

        # B. Monthly Snapshots (Last 12 calendar months)
        dates_monthly = []
        for i in range(11, -1, -1):
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1
            last_day = calendar.monthrange(y, m)[1]
            d = min(today.day, last_day)
            dates_monthly.append(date(y, m, d))
        history_monthly = compute_history_for_dates(dates_monthly, "%b %y")

        # C. Yearly Snapshots (Last 5 calendar years)
        dates_yearly = []
        for i in range(4, -1, -1):
            y = today.year - i
            last_day = calendar.monthrange(y, today.month)[1]
            d = min(today.day, last_day)
            dates_yearly.append(date(y, today.month, d))
        history_yearly = compute_history_for_dates(dates_yearly, "%Y")

        current = history_weekly[-1]
        previous = history_weekly[-2] if len(history_weekly) > 1 else current

        def get_trend(cur_val, prev_val):
            if cur_val > prev_val:
                return "up"
            elif cur_val < prev_val:
                return "down"
            return "stable"

        trends = {
            "customers": {
                "active": get_trend(current["customers"]["active"], previous["customers"]["active"]),
                "defaulted": get_trend(current["customers"]["defaulted"], previous["customers"]["defaulted"]),
                "closed": get_trend(current["customers"]["closed"], previous["customers"]["closed"]),
                "total": get_trend(current["customers"]["total"], previous["customers"]["total"])
            },
            "loan_amount": {
                "active": get_trend(current["loan_amount"]["active"], previous["loan_amount"]["active"]),
                "defaulted": get_trend(current["loan_amount"]["defaulted"], previous["loan_amount"]["defaulted"]),
                "closed": get_trend(current["loan_amount"]["closed"], previous["loan_amount"]["closed"]),
                "total": get_trend(current["loan_amount"]["total"], previous["loan_amount"]["total"])
            },
            "balance": {
                "active": get_trend(current["balance"]["active"], previous["balance"]["active"]),
                "defaulted": get_trend(current["balance"]["defaulted"], previous["balance"]["defaulted"]),
                "total": get_trend(current["balance"]["total"], previous["balance"]["total"])
            }
        }

        return jsonify(
            success=True,
            data={
                "current": current,
                "trends": trends,
                "history": {
                    "weekly": history_weekly,
                    "monthly": history_monthly,
                    "yearly": history_yearly
                }
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/dashboard/posting_analytics/<int:vid>", methods=["GET", "QUERY"])
@login_required
@ttl_cache(ttl_seconds=300)
def api_dashboard_posting_analytics(vid):
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])
    if user_level not in ["admin", "mgmt"] and vid not in allowed_villages:
        return jsonify(success=False, error="Unauthorized village access"), 403

    KOLKATA = pytz.timezone('Asia/Kolkata')
    today = datetime.now(KOLKATA).date()

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # 1. Fetch active customers
        cur.execute("""
            SELECT cid, start_date, installment_amount, eid, name, total_amount, paid_amount, balance_amount, customer_rating, status, ano
            FROM customer
            WHERE vid = %s;
        """, (vid,))
        active_customers = cur.fetchall()

        # 2. Fetch closed customers
        cur.execute("""
            SELECT cid, start_date, closed_at, installment_amount, eid, name, total_amount, paid_amount, balance_amount, final_frozen_rating, status, ano
            FROM closed_cust_account
            WHERE vid = %s;
        """, (vid,))
        closed_customers = cur.fetchall()

        # 3. Fetch all payments (active and closed)
        cur.execute("""
            SELECT cid, amt, payment_date, created_at, eid
            FROM v_all_payments
            WHERE vid = %s;
        """, (vid,))
        raw_payments = cur.fetchall()

        # Do not globally filter payments by year so the history chart remains intact
        payments = raw_payments

        # Group payments by payment_date
        payments_by_date = {}
        for p_cid, p_amt, p_date, p_created_at, p_eid in (p[:5] for p in payments):
            if not p_date:
                continue
            dt = p_date.date() if isinstance(p_date, datetime) else p_date
            if dt not in payments_by_date:
                payments_by_date[dt] = []
            payments_by_date[dt].append({
                "cid": p_cid,
                "amt": float(p_amt) if p_amt is not None else 0.0,
                "created_at": p_created_at,
                "eid": p_eid
            })

        # Sorted unique posting dates desc
        unique_dates = sorted(list(payments_by_date.keys()), reverse=True)

        if not unique_dates:
            return jsonify(success=True, data={
                "empty": True,
                "recent_posting": {
                    "last_date": None,
                    "elapsed_days": None,
                    "status": "neutral",
                    "avg_entry_lag_days": 0.0
                },
                "recent_week_stats": {},
                "comparisons": {},
                "risk_alerts": {
                    "consecutive_skippers_count": 0,
                    "consecutive_skippers_pct": 0.0,
                    "first_time_skippers_count": 0,
                    "first_time_skippers_pct": 0.0,
                    "consecutive_skippers_list": [],
                    "first_time_skippers_list": [],
                    "avg_entry_lag_days": 0.0
                },
                "employee_breakdown": [],
                "historical_trend": []
            })

        # Helper to compute stats for a date
        def get_stats_for_date(dt):
            active_at_dt = []
            for cid, start_date, inst_amt, c_eid, c_name, tot_amt, paid_amt, bal_amt, rating, status, ano in active_customers:
                if start_date is None:
                    continue
                s_dt = start_date.date() if isinstance(start_date, datetime) else start_date
                if s_dt <= dt:
                    active_at_dt.append({
                        "cid": cid,
                        "ano": ano,
                        "name": c_name,
                        "installment_amount": float(inst_amt) if inst_amt is not None else 0.0,
                        "eid": c_eid,
                        "total_amount": float(tot_amt) if tot_amt is not None else 0.0,
                        "paid_amount": float(paid_amt) if paid_amt is not None else 0.0,
                        "balance_amount": float(bal_amt) if bal_amt is not None else 0.0,
                        "rating": float(rating) if rating is not None else 0.0,
                        "status": "OnTrack" if status == "open" else (status or "OnTrack")
                    })
            for cid, start_date, closed_at, inst_amt, c_eid, c_name, tot_amt, paid_amt, bal_amt, rating, status, ano in closed_customers:
                if start_date is None:
                    continue
                s_dt = start_date.date() if isinstance(start_date, datetime) else start_date
                cl_dt = closed_at.date() if isinstance(closed_at, datetime) else closed_at if closed_at else None
                if s_dt <= dt and (cl_dt is None or dt < cl_dt):
                    active_at_dt.append({
                        "cid": cid,
                        "ano": ano,
                        "name": c_name,
                        "installment_amount": float(inst_amt) if inst_amt is not None else 0.0,
                        "eid": c_eid,
                        "total_amount": float(tot_amt) if tot_amt is not None else 0.0,
                        "paid_amount": float(paid_amt) if paid_amt is not None else 0.0,
                        "balance_amount": float(bal_amt) if bal_amt is not None else 0.0,
                        "rating": float(rating) if rating is not None else 0.0,
                        "status": "OnTrack" if status == "open" else (status or "OnTrack")
                    })

            expected_amt = sum(item["installment_amount"] for item in active_at_dt)
            pmts = payments_by_date.get(dt, [])
            actual_amt = sum(p["amt"] for p in pmts)
            paying_cids = {p["cid"] for p in pmts}

            active_count = len(active_at_dt)
            paying_count = len(paying_cids)
            skipped_count = active_count - paying_count

            coverage_pct = (paying_count / active_count * 100) if active_count > 0 else 0
            skipping_pct = (skipped_count / active_count * 100) if active_count > 0 else 0
            unpaid_amt = max(0.0, expected_amt - actual_amt)
            unpaid_pct = (unpaid_amt / expected_amt * 100) if expected_amt > 0 else 0

            return {
                "date": dt,
                "active_count": active_count,
                "paying_count": paying_count,
                "skipped_count": skipped_count,
                "coverage_pct": coverage_pct,
                "skipping_pct": skipping_pct,
                "expected_amt": expected_amt,
                "actual_amt": actual_amt,
                "unpaid_amt": unpaid_amt,
                "unpaid_pct": unpaid_pct,
                "paying_cids": paying_cids,
                "active_list": active_at_dt
            }

        # Analyze T0 (Latest)
        t0 = unique_dates[0]
        t0_stats = get_stats_for_date(t0)

        is_monthly = is_village_monthly(vid, cur)

        # Elapsed days since latest posting
        elapsed_days = (today - t0).days
        if is_monthly:
            if elapsed_days <= 32:
                lag_status = "active"
            elif elapsed_days <= 45:
                lag_status = "delayed"
            else:
                lag_status = "critical"
        else:
            if elapsed_days <= 7:
                lag_status = "active"
            elif elapsed_days <= 14:
                lag_status = "delayed"
            else:
                lag_status = "critical"

        # T1 (Previous Week)
        t1 = unique_dates[1] if len(unique_dates) > 1 else None
        t1_stats = get_stats_for_date(t1) if t1 else None

        # T2 (Two weeks ago)
        t2 = unique_dates[2] if len(unique_dates) > 2 else None
        t2_stats = get_stats_for_date(t2) if t2 else None

        # Compare T0 vs T1
        comp_prev = {
            "amount_change_pct": 0.0,
            "skipping_change_pct": 0.0,
            "coverage_change_pct": 0.0
        }
        if t1_stats:
            if t1_stats["actual_amt"] > 0:
                comp_prev["amount_change_pct"] = ((t0_stats["actual_amt"] / t1_stats["actual_amt"]) - 1.0) * 100
            comp_prev["skipping_change_pct"] = t0_stats["skipping_pct"] - t1_stats["skipping_pct"]
            comp_prev["coverage_change_pct"] = t0_stats["coverage_pct"] - t1_stats["coverage_pct"]

        # Compare T0 vs Historical averages
        all_stats = [get_stats_for_date(d) for d in unique_dates]
        hist_avg_amt = sum(s["actual_amt"] for s in all_stats) / len(all_stats)
        hist_avg_skipping = sum(s["skipping_pct"] for s in all_stats) / len(all_stats)
        hist_avg_coverage = sum(s["coverage_pct"] for s in all_stats) / len(all_stats)

        comp_hist = {
            "amount_vs_avg_pct": ((t0_stats["actual_amt"] / hist_avg_amt) - 1.0) * 100 if hist_avg_amt > 0 else 0.0,
            "skipping_vs_avg_pct": t0_stats["skipping_pct"] - hist_avg_skipping,
            "coverage_vs_avg_pct": t0_stats["coverage_pct"] - hist_avg_coverage,
            "weekly_avg_collected": hist_avg_amt
        }

        # Consecutive Skippers (skipped T0 AND T1)
        consecutive_skippers = []
        if t1_stats:
            for item in t0_stats["active_list"]:
                cid = item["cid"]
                if cid not in t0_stats["paying_cids"] and cid not in t1_stats["paying_cids"]:
                    consecutive_skippers.append(item)

        # First-Time Skippers (skipped T0 but paid T1 AND T2)
        first_time_skippers = []
        if t1_stats and t2_stats:
            for item in t0_stats["active_list"]:
                cid = item["cid"]
                if cid not in t0_stats["paying_cids"] and cid in t1_stats["paying_cids"] and cid in t2_stats["paying_cids"]:
                    first_time_skippers.append(item)

        # Employee Breakdown (Lag and Collections)
        employee_map = {}
        for p_cid, p_amt, p_date, p_created_at, p_eid in (p[:5] for p in payments):
            if not p_eid:
                continue
            if p_eid not in employee_map:
                employee_map[p_eid] = {"eid": p_eid, "name": "Unknown", "payment_count": 0, "total_collected": 0.0, "total_lag_days": 0.0}
            
            p_dt = p_date.date() if isinstance(p_date, datetime) else p_date
            c_dt = p_created_at.date() if (p_created_at and isinstance(p_created_at, datetime)) else p_created_at
            employee_map[p_eid]["payment_count"] += 1
            employee_map[p_eid]["total_collected"] += float(p_amt) if p_amt is not None else 0.0
            if p_dt and c_dt:
                lag = max(0, (c_dt - p_dt).days)
                employee_map[p_eid]["total_lag_days"] += lag

        # Fetch employee names
        if employee_map:
            eids = list(employee_map.keys())
            cur.execute("SELECT eid, name FROM employee WHERE eid = ANY(%s);", (eids,))
            for r_eid, r_name in cur.fetchall():
                employee_map[r_eid]["name"] = r_name

        employee_breakdown = []
        overall_total_lag = 0.0
        overall_payment_count = 0
        for emp in employee_map.values():
            avg_lag = (emp["total_lag_days"] / emp["payment_count"]) if emp["payment_count"] > 0 else 0.0
            overall_total_lag += emp["total_lag_days"]
            overall_payment_count += emp["payment_count"]
            employee_breakdown.append({
                "eid": emp["eid"],
                "name": emp["name"],
                "payment_count": emp["payment_count"],
                "total_collected": emp["total_collected"],
                "avg_lag_days": avg_lag
            })
        employee_breakdown.sort(key=lambda x: x["total_collected"], reverse=True)

        # Calculate avg_entry_lag_days as the average of the weekly averages
        weekly_lags = {}
        for p_cid, p_amt, p_date, p_created_at, p_eid in (p[:5] for p in payments):
            p_dt = p_date.date() if isinstance(p_date, datetime) else p_date
            c_dt = p_created_at.date() if (p_created_at and isinstance(p_created_at, datetime)) else p_created_at
            if p_dt and c_dt and p_dt.year >= 2025:
                lag = max(0, (c_dt - p_dt).days)
                if p_dt not in weekly_lags:
                    weekly_lags[p_dt] = []
                weekly_lags[p_dt].append(lag)

        weekly_avg_lags = []
        for p_dt, lags in weekly_lags.items():
            if lags:
                weekly_avg_lags.append(sum(lags) / len(lags))
        
        avg_entry_lag_days = sum(weekly_avg_lags) / len(weekly_avg_lags) if weekly_avg_lags else 0.0

        # Historical weekly trend for chart (last 10 posting dates in chronological order)
        historical_trend = []
        for s in reversed(all_stats[:10]):
            historical_trend.append({
                "date": s["date"].strftime("%d-%m"),
                "collected_amount": s["actual_amt"],
                "expected_amount": s["expected_amt"],
                "coverage_pct": s["coverage_pct"],
                "skipping_pct": s["skipping_pct"],
                "unpaid_pct": s["unpaid_pct"]
            })

        return jsonify(success=True, data={
            "empty": False,
            "is_monthly": is_monthly,
            "recent_posting": {
                "last_date": format_date_display(t0),
                "elapsed_days": elapsed_days,
                "status": lag_status,
                "avg_entry_lag_days": avg_entry_lag_days
            },
            "recent_week_stats": {
                "collected_amount": t0_stats["actual_amt"],
                "expected_amount": t0_stats["expected_amt"],
                "unpaid_amount": t0_stats["unpaid_amt"],
                "unpaid_pct": t0_stats["unpaid_pct"],
                "paying_count": t0_stats["paying_count"],
                "active_count": t0_stats["active_count"],
                "skipped_count": t0_stats["skipped_count"],
                "coverage_pct": t0_stats["coverage_pct"],
                "skipping_pct": t0_stats["skipping_pct"]
            },
            "comparisons": {
                "previous_week": comp_prev,
                "historical": comp_hist
            },
            "risk_alerts": {
                "consecutive_skippers_count": len(consecutive_skippers),
                "consecutive_skippers_pct": (len(consecutive_skippers) / t0_stats["active_count"] * 100) if t0_stats["active_count"] > 0 else 0.0,
                "first_time_skippers_count": len(first_time_skippers),
                "first_time_skippers_pct": (len(first_time_skippers) / t0_stats["active_count"] * 100) if t0_stats["active_count"] > 0 else 0.0,
                "consecutive_skippers_list": consecutive_skippers,
                "first_time_skippers_list": first_time_skippers,
                "avg_entry_lag_days": avg_entry_lag_days
            },
            "employee_breakdown": employee_breakdown,
            "historical_trend": historical_trend
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/ledger", methods=["GET"])
@login_required
def api_ledger():
    emp1 = request.args.get("emp1", type=int)
    emp2 = request.args.get("emp2", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not emp1 or not start_date_str or not end_date_str:
        return jsonify(success=False, error="Missing required parameters"), 400

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify(success=False, error="Invalid date format"), 400

    if emp2:
        pair_filter = "emp1 = %s AND emp2 = %s"
        pair_params_single = (emp1, emp2)
    else:
        pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
        pair_params_single = (emp1,)

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # 1. Fetch active villages for this employee group
        if emp2:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND emp2 = %s AND status = 'active'
            """, (emp1, emp2))
        else:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
            """, (emp1,))
        
        village_rows = cur.fetchall()
        vids = [r[0] for r in village_rows]

        if not vids:
            return jsonify(success=True, opening_balance=0.0, dates={}, dates_list=[])

        # -----------------------------------------------------------------
        # CALCULATE OPENING BALANCE (all transactions before start_date)
        # -----------------------------------------------------------------
        # Manual transactions before start_date
        cur.execute(f"""
            SELECT txn, txn_sub, amount
            FROM cashbag_transactions
            WHERE ({pair_filter} OR vid = ANY(%s)) AND created_at::date < %s
        """, pair_params_single + (vids, start_date))
        hist_manual = cur.fetchall()

        office_cash_h = 0.0
        expenses_h = 0.0
        adj_add_h = 0.0
        adj_minus_h = 0.0

        for txn, txn_sub, amount in hist_manual:
            amt = float(amount or 0)
            if txn == 'OFFICE_CASH':
                office_cash_h += amt
            elif txn == 'EXPENSE':
                expenses_h += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    adj_add_h += amt
                elif txn_sub == 'MINUS':
                    adj_minus_h += amt
            elif txn == 'PROFIT_LOSS':
                if txn_sub == 'PROFIT':
                    adj_add_h += amt
                elif txn_sub == 'LOSS':
                    adj_minus_h += amt

        # Payments before start_date (including archived/closed payments)
        cur.execute("""
            SELECT COALESCE(SUM(p.amt), 0)
            FROM (
                SELECT pid, cid, amt, payment_date, vid FROM payment
                UNION ALL
                SELECT pid, cid, amt, payment_date, vid FROM closed_cust_payment
            ) p
            WHERE p.vid = ANY(%s) AND p.payment_date < %s
        """, (vids, start_date))
        installments_h = float(cur.fetchone()[0] or 0)

        # Loans & commissions before start_date (including archived/closed accounts)
        cur.execute("""
            SELECT c.base_amount, c.cutting_amount, c.total_amount,
                   v.interest_rate, v.cutting_rate
            FROM (
                SELECT base_amount, cutting_amount, total_amount, start_date, status, vid FROM customer
                UNION ALL
                SELECT base_amount, cutting_amount, total_amount, start_date, status, vid FROM closed_cust_account
            ) c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted' AND c.start_date < %s
        """, (vids, start_date))
        hist_loans = cur.fetchall()

        loans_total_h = 0.0
        loans_commission_h = 0.0
        loans_interest_h = 0.0

        for base_amt_db, cutting_amt_db, total_amt_db, ir_db, cr_db in hist_loans:
            base_amt = float(base_amt_db or 0)
            cutting_amt = float(cutting_amt_db or 0)
            total_amt = float(total_amt_db or 0)
            ir = float(ir_db or 0)
            cr = float(cr_db or 0)
            interest = round_curr(total_amt * (ir / 100.0))

            if base_amt <= 0.0:
                cutting_amt = round_curr(total_amt * (cr / 100.0))
                base_amt = round_curr(total_amt - interest - cutting_amt)

            loans_total_h += total_amt
            loans_commission_h += cutting_amt
            loans_interest_h += interest

        opening_balance = (
            office_cash_h
            + installments_h
            + loans_commission_h
            + loans_interest_h
            + adj_add_h
            - loans_total_h
            - expenses_h
            - adj_minus_h
        )

        # -----------------------------------------------------------------
        # QUERY DAILY DETAILS (within [start_date, end_date])
        # -----------------------------------------------------------------
        # A. Loans & Commissions within range (including archived/closed accounts)
        cur.execute("""
            SELECT c.cid, c.ano, c.name, c.base_amount, c.cutting_amount, c.total_amount, c.start_date,
                   v.village_code, v.interest_rate, v.cutting_rate, c.payment_type
            FROM (
                SELECT cid, ano, name, base_amount, cutting_amount, total_amount, start_date, status, vid, payment_type FROM customer
                UNION ALL
                SELECT cid, ano, name, base_amount, cutting_amount, total_amount, start_date, status, vid, payment_type FROM closed_cust_account
            ) c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted'
              AND c.start_date >= %s AND c.start_date <= %s
            ORDER BY c.start_date ASC, c.cid ASC
        """, (vids, start_date, end_date))
        loans_rows = cur.fetchall()

        # B. Payments (Collections) within range (including archived/closed payments)
        cur.execute("""
            SELECT p.pid, c.ano, c.name, p.amt, p.payment_date, v.village_code, p.payment_type, p.cash_amount, p.upi_amount, v.village_name
            FROM (
                SELECT pid, cid, ano, amt, payment_date, vid, payment_type, cash_amount, upi_amount FROM payment
                UNION ALL
                SELECT pid, cid, ano, amt, payment_date, vid, 'cash' AS payment_type, amt AS cash_amount, 0.0 AS upi_amount FROM closed_cust_payment
            ) p
            JOIN (
                SELECT cid, ano, name, vid FROM customer
                UNION ALL
                SELECT cid, ano, name, vid FROM closed_cust_account
            ) c ON p.cid = c.cid
            JOIN village v ON p.vid = v.vid
            WHERE p.vid = ANY(%s)
              AND p.payment_date >= %s AND p.payment_date <= %s
            ORDER BY p.payment_date ASC, p.pid ASC
        """, (vids, start_date, end_date))
        payments_rows = cur.fetchall()

        # C. Manual entries within range
        cur.execute(f"""
            SELECT id, txn, txn_sub, txn_type, amount, notes, created_at
            FROM cashbag_transactions
            WHERE ({pair_filter} OR vid = ANY(%s))
              AND created_at::date >= %s AND created_at::date <= %s
            ORDER BY created_at ASC, id ASC
        """, pair_params_single + (vids, start_date, end_date))
        manual_rows = cur.fetchall()

        # -----------------------------------------------------------------
        # GROUP BY DATE (chronological ASC)
        # -----------------------------------------------------------------
        dates_in_range = []
        curr = start_date
        while curr <= end_date:
            dates_in_range.append(curr)
            curr += timedelta(days=1)

        dates_data = {}
        for d in dates_in_range:
            d_str = d.strftime("%Y-%m-%d")
            dates_data[d_str] = {
                "date_label": d.strftime("%d-%m-%Y"),
                "villages": [],
                "loans": [],
                "loans_total": {"commission": 0.0, "amount": 0.0, "interest": 0.0, "base_amount": 0.0},
                "loans_cash_total": 0.0,
                "loans_upi_total": 0.0,
                "loans_base_cash_total": 0.0,
                "loans_base_upi_total": 0.0,
                "commissions_cash_total": 0.0,
                "commissions_upi_total": 0.0,
                "interest_cash_total": 0.0,
                "interest_upi_total": 0.0,
                "payments": [],
                "payments_total": 0.0,
                "payments_cash_total": 0.0,
                "payments_upi_total": 0.0,
                "expenses": [],
                "expenses_total": 0.0,
                "expenses_cash_total": 0.0,
                "expenses_upi_total": 0.0,
                "office_cash": [],
                "office_cash_total": 0.0,
                "office_cash_cash_total": 0.0,
                "office_cash_upi_total": 0.0,
                "adjustments_add": [],
                "adjustments_total_add": 0.0,
                "adjustments_add_cash_total": 0.0,
                "adjustments_add_upi_total": 0.0,
                "adjustments_minus": [],
                "adjustments_total_minus": 0.0,
                "adjustments_minus_cash_total": 0.0,
                "adjustments_minus_upi_total": 0.0
            }

        # Populate Loans
        for cid, ano, name, base_amt_db, cutting_amt_db, total_amt_db, start_dt, v_code, ir_db, cr_db, pay_type in loans_rows:
            d_str = start_dt.strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            base_amt = float(base_amt_db or 0)
            cutting_amt = float(cutting_amt_db or 0)
            total_amt = float(total_amt_db or 0)

            ir = float(ir_db or 0)
            cr = float(cr_db or 0)
            interest = round_curr(total_amt * (ir / 100.0))
            if base_amt <= 0.0:
                cutting_amt = round_curr(total_amt * (cr / 100.0))
                base_amt = round_curr(total_amt - interest - cutting_amt)

            # In the loans dispensed section, Amount is the Total Loan Amount (e.g. 12,500)
            dates_data[d_str]["loans"].append({
                "ano": ano,
                "name": name,
                "amount": total_amt,
                "base_amount": base_amt,
                "total_amount": total_amt,
                "interest": interest,
                "commission": cutting_amt,
                "village_code": v_code,
                "payment_type": pay_type
            })
            dates_data[d_str]["loans_total"]["amount"] += total_amt
            dates_data[d_str]["loans_total"]["base_amount"] = dates_data[d_str]["loans_total"].get("base_amount", 0.0) + base_amt
            dates_data[d_str]["loans_total"]["interest"] += interest
            dates_data[d_str]["loans_total"]["commission"] += cutting_amt

            # Loans dispensed breakdown: loans_cash_total / loans_upi_total tracks total loan amount
            # Rusum (cutting_amt) and Commission (interest) are also tracked by cash/upi
            is_upi = (pay_type or '').strip().lower() == 'upi'
            if is_upi:
                dates_data[d_str]["loans_upi_total"] += total_amt
                dates_data[d_str]["loans_base_upi_total"] += base_amt
                dates_data[d_str]["commissions_upi_total"] += cutting_amt
                dates_data[d_str]["interest_upi_total"] += interest
            else:
                dates_data[d_str]["loans_cash_total"] += total_amt
                dates_data[d_str]["loans_base_cash_total"] += base_amt
                dates_data[d_str]["commissions_cash_total"] += cutting_amt
                dates_data[d_str]["interest_cash_total"] += interest

            if v_code not in dates_data[d_str]["villages"]:
                dates_data[d_str]["villages"].append(v_code)

        # Populate Payments
        for pid, ano, name, amt, payment_date, v_code, pay_type, cash_amt, upi_amt, v_name in payments_rows:
            d_str = payment_date.strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            dates_data[d_str]["payments"].append({
                "ano": ano,
                "name": name,
                "amount": float(amt or 0),
                "village_code": v_code,
                "village_name": v_name,
                "payment_type": pay_type,
                "cash_amount": float(cash_amt or 0),
                "upi_amount": float(upi_amt or 0)
            })
            p_amt = float(amt or 0)
            dates_data[d_str]["payments_total"] += p_amt

            # Populate cash/upi payments totals
            p_type = (pay_type or "cash").lower()
            c_amt = float(cash_amt or 0)
            u_amt = float(upi_amt or 0)
            if p_type == "cash":
                dates_data[d_str]["payments_cash_total"] += p_amt
            elif p_type == "upi":
                dates_data[d_str]["payments_upi_total"] += p_amt
            elif p_type == "partial":
                dates_data[d_str]["payments_cash_total"] += c_amt
                dates_data[d_str]["payments_upi_total"] += u_amt
            else:
                dates_data[d_str]["payments_cash_total"] += p_amt

            if v_code not in dates_data[d_str]["villages"]:
                dates_data[d_str]["villages"].append(v_code)

        # Populate Manual transactions
        for tid, txn, txn_sub, txn_type, amount_db, notes, created_at in manual_rows:
            d_str = created_at.date().strftime("%Y-%m-%d")
            if d_str not in dates_data:
                continue

            amt = float(amount_db or 0)
            t_type = (txn_type or "CASH").upper()
            if txn == 'OFFICE_CASH':
                dates_data[d_str]["office_cash"].append({
                    "notes": notes or "Office Cash",
                    "amount": amt,
                    "txn_type": txn_type
                })
                dates_data[d_str]["office_cash_total"] += amt
                if t_type == 'UPI':
                    dates_data[d_str]["office_cash_upi_total"] += amt
                else:
                    dates_data[d_str]["office_cash_cash_total"] += amt
            elif txn == 'EXPENSE':
                dates_data[d_str]["expenses"].append({
                    "notes": notes or "Expense",
                    "amount": amt,
                    "txn_type": txn_type
                })
                dates_data[d_str]["expenses_total"] += amt
                if t_type == 'UPI':
                    dates_data[d_str]["expenses_upi_total"] += amt
                else:
                    dates_data[d_str]["expenses_cash_total"] += amt
            elif txn == 'ADJUSTMENT':
                if txn_sub == 'ADD':
                    dates_data[d_str]["adjustments_add"].append({
                        "notes": notes or "Adjustment Add",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_add"] += amt
                    if t_type == 'UPI':
                        dates_data[d_str]["adjustments_add_upi_total"] += amt
                    else:
                        dates_data[d_str]["adjustments_add_cash_total"] += amt
                elif txn_sub == 'MINUS':
                    dates_data[d_str]["adjustments_minus"].append({
                        "notes": notes or "Adjustment Minus",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_minus"] += amt
                    if t_type == 'UPI':
                        dates_data[d_str]["adjustments_minus_upi_total"] += amt
                    else:
                        dates_data[d_str]["adjustments_minus_cash_total"] += amt
            elif txn == 'PROFIT_LOSS':
                if txn_sub == 'PROFIT':
                    dates_data[d_str]["adjustments_add"].append({
                        "notes": notes or "Profit",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_add"] += amt
                    if t_type == 'UPI':
                        dates_data[d_str]["adjustments_add_upi_total"] += amt
                    else:
                        dates_data[d_str]["adjustments_add_cash_total"] += amt
                elif txn_sub == 'LOSS':
                    dates_data[d_str]["adjustments_minus"].append({
                        "notes": notes or "Loss",
                        "amount": amt,
                        "txn_type": txn_type
                    })
                    dates_data[d_str]["adjustments_total_minus"] += amt
                    if t_type == 'UPI':
                        dates_data[d_str]["adjustments_minus_upi_total"] += amt
                    else:
                        dates_data[d_str]["adjustments_minus_cash_total"] += amt

        dates_list = [d.strftime("%Y-%m-%d") for d in dates_in_range]
        assigned_villages = [
            {"vid": r[0], "name": r[1], "code": r[2]}
            for r in village_rows
        ]

        return jsonify(
            success=True,
            opening_balance=opening_balance,
            dates=dates_data,
            dates_list=dates_list,
            assigned_villages=assigned_villages
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/cashbag/breakdown", methods=["GET"])
@login_required
def api_cashbag_breakdown():
    emp1 = request.args.get("emp1", type=int)
    emp2 = request.args.get("emp2", type=int)
    breakdown_type = request.args.get("type", type=str)
    end_day = request.args.get("end_day", default=3, type=int)
    if end_day is None or end_day < 0 or end_day > 6:
        end_day = 3

    if not emp1 or not breakdown_type:
        return jsonify(success=False, error="Missing required parameters"), 400

    if emp2:
        pair_filter = "emp1 = %s AND emp2 = %s"
        pair_params_single = (emp1, emp2)
    else:
        pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
        pair_params_single = (emp1,)

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        def get_breakdown_timeline(dt_val, end_day_val):
            d = dt_val.date() if isinstance(dt_val, datetime) else dt_val
            our_day = (d.weekday() + 1) % 7  # 0=Sunday, 1=Monday, ..., 6=Saturday
            days_to_end = (end_day_val - our_day) % 7
            week_end = d + timedelta(days=days_to_end)
            week_start = week_end - timedelta(days=6)

            month_name = week_end.strftime("%B")
            month_key = f"{month_name} {week_end.year}"
            month_sort = (week_end.year, week_end.month)

            start_str = week_start.strftime("%d %b")
            end_str = week_end.strftime("%d %b %Y")
            week_label = f"{start_str} – {end_str}"
            week_key = f"{week_start.strftime('%Y-%m-%d')}_{week_end.strftime('%Y-%m-%d')}"
            week_sort = week_start

            day_str = d.strftime("%d/%m/%Y")
            day_key = d.strftime("%Y-%m-%d")
            day_sort = d

            return month_key, month_sort, week_key, week_label, week_sort, day_key, day_str, day_sort

        # 1. Fetch active villages for this employee group
        if emp2:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND emp2 = %s AND status = 'active'
            """, (emp1, emp2))
        else:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
            """, (emp1,))
        
        village_rows = cur.fetchall()
        vids = [r[0] for r in village_rows]

        # Handle manual txn types: office_cash, expenses, adjustments, profit_loss
        if breakdown_type in ('office_cash', 'expenses', 'adjustments', 'profit_loss'):
            txn_filter = ""
            if breakdown_type == 'office_cash':
                txn_filter = "txn = 'OFFICE_CASH'"
            elif breakdown_type == 'expenses':
                txn_filter = "txn = 'EXPENSE'"
            elif breakdown_type == 'adjustments':
                txn_filter = "txn = 'ADJUSTMENT'"
            elif breakdown_type == 'profit_loss':
                txn_filter = "txn = 'PROFIT_LOSS'"

            if vids:
                manual_filter = f"({pair_filter} OR vid = ANY(%s))"
                manual_params = pair_params_single + (vids,)
            else:
                manual_filter = pair_filter
                manual_params = pair_params_single

            cur.execute(f"""
                SELECT id, txn, txn_sub, txn_type, amount, notes, created_by, created_at
                FROM cashbag_transactions
                WHERE {manual_filter} AND {txn_filter}
                ORDER BY created_at DESC, id DESC
            """, manual_params)
            rows = cur.fetchall()

            grouped = {}
            for tid, txn, txn_sub, txn_type, amount_db, notes, created_by, created_at in rows:
                amt = float(amount_db or 0)
                if not created_at:
                    continue

                month_key, month_sort, week_key, week_label, week_sort, day_key, day_str, day_sort = get_breakdown_timeline(created_at, end_day)

                signed_amt = amt
                if txn == 'ADJUSTMENT' and txn_sub == 'MINUS':
                    signed_amt = -amt
                elif txn == 'PROFIT_LOSS' and txn_sub == 'LOSS':
                    signed_amt = -amt

                if month_key not in grouped:
                    grouped[month_key] = {"month_name": month_key, "month_sort": month_sort, "total_amount": 0.0, "weeks": {}}
                grouped[month_key]["total_amount"] += signed_amt

                weeks = grouped[month_key]["weeks"]
                if week_key not in weeks:
                    weeks[week_key] = {"week_date": week_label, "week_label": week_label, "week_key": week_key, "week_sort": week_sort, "total_amount": 0.0, "days": {}}
                weeks[week_key]["total_amount"] += signed_amt

                days = weeks[week_key]["days"]
                if day_key not in days:
                    days[day_key] = {"day_date": day_str, "day_key": day_key, "day_sort": day_sort, "total_amount": 0.0, "transactions": []}
                days[day_key]["total_amount"] += signed_amt

                txn_dict = {
                    "id": tid,
                    "txn_type": txn_type,
                    "amount": amt,
                    "notes": notes,
                    "created_by": created_by
                }
                if txn in ('ADJUSTMENT', 'PROFIT_LOSS'):
                    txn_dict["txn_sub"] = txn_sub
                    txn_dict["signed_amount"] = signed_amt

                days[day_key]["transactions"].append(txn_dict)

            tree_list = []
            sorted_months = sorted(grouped.values(), key=lambda m: m["month_sort"], reverse=True)
            for m_data in sorted_months:
                sorted_weeks = sorted(m_data["weeks"].values(), key=lambda w: w["week_sort"], reverse=True)
                weeks_list = []
                for w_data in sorted_weeks:
                    sorted_days = sorted(w_data["days"].values(), key=lambda d: d["day_sort"], reverse=True)
                    days_list = []
                    for d_data in sorted_days:
                        days_list.append({
                            "day_date": d_data["day_date"],
                            "total_amount": d_data["total_amount"],
                            "transactions": d_data["transactions"]
                        })
                    weeks_list.append({
                        "week_date": w_data["week_date"],
                        "week_label": w_data.get("week_label", w_data["week_date"]),
                        "total_amount": w_data["total_amount"],
                        "days": days_list
                    })
                tree_list.append({
                    "month_name": m_data["month_name"],
                    "total_amount": m_data["total_amount"],
                    "weeks": weeks_list
                })
            return jsonify(success=True, tree=tree_list)

        elif breakdown_type in ('loans', 'commissions', 'interest'):
            if not vids:
                return jsonify(success=True, tree=[])

            cur.execute("""
                SELECT c.cid, c.ano, c.name, c.base_amount, c.cutting_amount, c.total_amount, c.start_date,
                       v.interest_rate, v.cutting_rate, c.interest_amount
                FROM (
                    SELECT cid, ano, name, base_amount, cutting_amount, total_amount, start_date, interest_amount, status, vid FROM customer
                    UNION ALL
                    SELECT cid, ano, name, base_amount, cutting_amount, total_amount, start_date, interest_amount, status, vid FROM closed_cust_account
                ) c
                JOIN village v ON c.vid = v.vid
                WHERE c.vid = ANY(%s) AND c.status != 'deleted'
                ORDER BY c.start_date DESC, c.cid DESC
            """, (vids,))
            loan_rows = cur.fetchall()

            grouped = {}
            for cid, ano, name, base_amt_db, cutting_amt_db, total_amt_db, start_date, ir_db, cr_db, interest_amt_db in loan_rows:
                base_amt = float(base_amt_db or 0)
                cutting_amt = float(cutting_amt_db or 0)
                total_amt = float(total_amt_db or 0)
                interest_amt = float(interest_amt_db or 0)

                ir = float(ir_db or 0)
                cr = float(cr_db or 0)
                interest = interest_amt if interest_amt > 0 else round_curr(total_amt * (ir / 100.0))
                if base_amt <= 0.0:
                    cutting_amt = round_curr(total_amt * (cr / 100.0))
                    base_amt = round_curr(total_amt - interest - cutting_amt)

                if breakdown_type == 'loans':
                    amt = base_amt
                elif breakdown_type == 'commissions':
                    amt = cutting_amt
                else:
                    amt = interest
                if amt <= 0.0:
                    continue

                if not start_date:
                    continue

                month_key, month_sort, week_key, week_label, week_sort, day_key, day_str, day_sort = get_breakdown_timeline(start_date, end_day)

                if month_key not in grouped:
                    grouped[month_key] = {"month_name": month_key, "month_sort": month_sort, "total_amount": 0.0, "weeks": {}}
                grouped[month_key]["total_amount"] += amt

                weeks = grouped[month_key]["weeks"]
                if week_key not in weeks:
                    weeks[week_key] = {"week_date": week_label, "week_label": week_label, "week_key": week_key, "week_sort": week_sort, "total_amount": 0.0, "days": {}}
                weeks[week_key]["total_amount"] += amt

                days = weeks[week_key]["days"]
                if day_key not in days:
                    days[day_key] = {"day_date": day_str, "day_key": day_key, "day_sort": day_sort, "total_amount": 0.0, "customers": []}
                days[day_key]["total_amount"] += amt

                days[day_key]["customers"].append({
                    "cid": cid,
                    "ano": ano,
                    "name": name,
                    "amount": amt,
                    "base_amount": base_amt,
                    "total_amount": total_amt
                })

            tree_list = []
            sorted_months = sorted(grouped.values(), key=lambda m: m["month_sort"], reverse=True)
            for m_data in sorted_months:
                sorted_weeks = sorted(m_data["weeks"].values(), key=lambda w: w["week_sort"], reverse=True)
                weeks_list = []
                for w_data in sorted_weeks:
                    sorted_days = sorted(w_data["days"].values(), key=lambda d: d["day_sort"], reverse=True)
                    days_list = []
                    for d_data in sorted_days:
                        days_list.append({
                            "day_date": d_data["day_date"],
                            "total_amount": d_data["total_amount"],
                            "customers": d_data["customers"]
                        })
                    weeks_list.append({
                        "week_date": w_data["week_date"],
                        "week_label": w_data.get("week_label", w_data["week_date"]),
                        "total_amount": w_data["total_amount"],
                        "days": days_list
                    })
                tree_list.append({
                    "month_name": m_data["month_name"],
                    "total_amount": m_data["total_amount"],
                    "weeks": weeks_list
                })
            return jsonify(success=True, tree=tree_list)

        elif breakdown_type == 'installments':
            if not vids:
                return jsonify(success=True, tree=[])

            cur.execute("""
                SELECT p.pid, c.ano, c.name, p.amt, p.payment_date, v.village_code, v.village_name
                FROM v_all_payments p
                JOIN v_all_customers c ON p.cid = c.cid
                JOIN village v ON p.vid = v.vid
                WHERE p.vid = ANY(%s)
                ORDER BY p.payment_date DESC, p.pid DESC
            """, (vids,))
            pay_rows = cur.fetchall()

            grouped = {}
            for pid, ano, name, amt, payment_date, v_code, v_name in pay_rows:
                if not payment_date:
                    continue

                val = float(amt or 0)
                if val <= 0.0:
                    continue

                month_key, month_sort, week_key, week_label, week_sort, day_key, day_str, day_sort = get_breakdown_timeline(payment_date, end_day)

                if month_key not in grouped:
                    grouped[month_key] = {"month_name": month_key, "month_sort": month_sort, "total_amount": 0.0, "weeks": {}}
                grouped[month_key]["total_amount"] += val

                weeks = grouped[month_key]["weeks"]
                if week_key not in weeks:
                    weeks[week_key] = {"week_date": week_label, "week_label": week_label, "week_key": week_key, "week_sort": week_sort, "total_amount": 0.0, "days": {}}
                weeks[week_key]["total_amount"] += val

                days = weeks[week_key]["days"]
                if day_key not in days:
                    days[day_key] = {"day_date": day_str, "day_key": day_key, "day_sort": day_sort, "total_amount": 0.0, "villages": [], "customers": []}
                days[day_key]["total_amount"] += val

                v_label = v_code if not v_name else f"{v_code} ({v_name})"
                if v_label not in days[day_key]["villages"]:
                    days[day_key]["villages"].append(v_label)

                days[day_key]["customers"].append({
                    "pid": pid,
                    "ano": ano,
                    "name": name,
                    "village_code": v_code,
                    "amount": val
                })

            tree_list = []
            sorted_months = sorted(grouped.values(), key=lambda m: m["month_sort"], reverse=True)
            for m_data in sorted_months:
                sorted_weeks = sorted(m_data["weeks"].values(), key=lambda w: w["week_sort"], reverse=True)
                weeks_list = []
                for w_data in sorted_weeks:
                    sorted_days = sorted(w_data["days"].values(), key=lambda d: d["day_sort"], reverse=True)
                    days_list = []
                    for d_data in sorted_days:
                        days_list.append({
                            "day_date": d_data["day_date"],
                            "total_amount": d_data["total_amount"],
                            "villages": d_data.get("villages", []),
                            "customers": d_data["customers"]
                        })
                    weeks_list.append({
                        "week_date": w_data["week_date"],
                        "week_label": w_data.get("week_label", w_data["week_date"]),
                        "total_amount": w_data["total_amount"],
                        "days": days_list
                    })
                tree_list.append({
                    "month_name": m_data["month_name"],
                    "total_amount": m_data["total_amount"],
                    "weeks": weeks_list
                })
            return jsonify(success=True, tree=tree_list)

        return jsonify(success=False, error="Unknown breakdown type"), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/village/toggle_status", methods=["POST"])
@login_required
def toggle_village_status():
    if session.get("level") not in ["admin", "mgmt"]:
        return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    vid = data.get("vid")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Toggle active ↔ inactive
        cur.execute("""
            UPDATE village
            SET status = CASE
                WHEN status = 'active' THEN 'inactive'
                ELSE 'active'
            END
            WHERE vid = %s
            RETURNING status
        """, (vid,))

        result = cur.fetchone()

        conn.commit()

        return jsonify(success=True, status=result[0] if result else None)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e))

    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------
# GEOCODE VILLAGE API
# ----------------------------------------------------
@app.route("/api/village/geocode", methods=["POST"])
@login_required
def api_village_geocode():
    """Geocode a single village using Nominatim (same logic as geocode_villages.py)."""

    data = request.get_json()
    vid = data.get("vid")
    if not vid:
        return jsonify(success=False, error="Missing vid"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT village_name, district, state, pincode
            FROM village WHERE vid = %s
        """, (vid,))
        row = cur.fetchone()
        if not row:
            return jsonify(success=False, error="Village not found"), 404

        village_name, district, state, pincode = row

        # Clean village name: remove all digits (e.g. HUBBILLI2 -> HUBBILLI) and trim dashes/spaces
        clean_name = ""
        if village_name:
            clean_name = re.sub(r'\d+', '', village_name)
            clean_name = re.sub(r'[-\s]+$', '', clean_name)
            clean_name = re.sub(r'^[-\s]+', '', clean_name).strip()

        geocode_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        def _geocode_query(q):
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
            try:
                resp = requests.get(url, headers=geocode_headers, timeout=10)
                if resp.status_code == 200:
                    results = resp.json()
                    if results:
                        return float(results[0]["lat"]), float(results[0]["lon"])
            except Exception:
                pass
            return None

        coords = None

        # Step 1: name + pincode + district + state
        if clean_name and pincode and district and state:
            q = f"{clean_name}, {pincode}, {district}, {state}, India"
            coords = _geocode_query(q)

        # Step 2: name + pincode
        if not coords and clean_name and pincode:
            q = f"{clean_name}, {pincode}, India"
            coords = _geocode_query(q)

        # Step 3: name + district + state
        if not coords and clean_name and district and state:
            q = f"{clean_name}, {district}, {state}, India"
            coords = _geocode_query(q)

        # Step 4: name + state
        if not coords and clean_name and state:
            q = f"{clean_name}, {state}, India"
            coords = _geocode_query(q)

        # Step 5: pincode
        if not coords and pincode:
            q = f"{pincode}, India"
            coords = _geocode_query(q)

        if not coords:
            return jsonify(success=False, error="Could not geocode this village. Try updating the village name, district, or pincode and retry.")

        res_lat, res_lon = coords

        cur.execute("""
            UPDATE village
            SET latitude = %s, longitude = %s
            WHERE vid = %s
        """, (res_lat, res_lon, vid))
        conn.commit()

        return jsonify(success=True, latitude=res_lat, longitude=res_lon)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------
@app.route("/api/geocode_coordinates", methods=["POST"])
@login_required
def api_geocode_coordinates():
    """Geocode arbitrary address for Create Village form coordinates."""

    data = request.get_json()
    if not data:
        return jsonify(success=False, error="Invalid request"), 400

    village_name = data.get("village_name", "").strip()
    district = data.get("district", "").strip()
    state = data.get("state", "").strip()
    pincode = data.get("pincode", "").strip()

    if not village_name or not state:
        return jsonify(success=False, error="Village name and State are required for geocoding"), 400

    # Clean village name: remove all digits and trim dashes/spaces
    clean_name = ""
    if village_name:
        clean_name = re.sub(r'\d+', '', village_name)
        clean_name = re.sub(r'[-\s]+$', '', clean_name)
        clean_name = re.sub(r'^[-\s]+', '', clean_name).strip()

    geocode_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def _geocode_query(q):
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
        try:
            resp = requests.get(url, headers=geocode_headers, timeout=10)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception:
            pass
        return None

    coords = None

    # Step 1: name + pincode + district + state
    if clean_name and pincode and district and state:
        q = f"{clean_name}, {pincode}, {district}, {state}, India"
        coords = _geocode_query(q)

    # Step 2: name + pincode
    if not coords and clean_name and pincode:
        q = f"{clean_name}, {pincode}, India"
        coords = _geocode_query(q)

    # Step 3: name + district + state
    if not coords and clean_name and district and state:
        q = f"{clean_name}, {district}, {state}, India"
        coords = _geocode_query(q)

    # Step 4: name + state
    if not coords and clean_name and state:
        q = f"{clean_name}, {state}, India"
        coords = _geocode_query(q)

    # Step 5: pincode
    if not coords and pincode:
        q = f"{pincode}, India"
        coords = _geocode_query(q)

    if not coords:
        return jsonify(success=False, error="Could not geocode this location. Try entering coordinates manually.")

    res_lat, res_lon = coords
    return jsonify(success=True, latitude=res_lat, longitude=res_lon)

# ----------------------------------------------------
# EMPLOYEE DB HELPERS (Postgres)
# ----------------------------------------------------
def get_employee_photo_url(eid):
    """Return URL of employee photo if it exists on disk, else None (0 DB changes)."""
    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'employees')
    if not os.path.exists(upload_dir):
        return None
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        path = os.path.join(upload_dir, f"{eid}{ext}")
        if os.path.exists(path):
            mtime = int(os.path.getmtime(path))
            return f"/static/uploads/employees/{eid}{ext}?v={mtime}"
    return None

def get_all_employees():
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            eid,
            name,
            phone_number,
            city,
            joining_date,
            level,
            state,
            is_active
        FROM employee
        ORDER BY eid
    """)

    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description] if cur.description else []

    cur.close()
    conn.close()

    result = []
    for r in rows:
        d = dict(zip(headers, r))
        d['photo_url'] = get_employee_photo_url(d['eid'])
        result.append(d)
    return result


def update_employee_in_db(data):
    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        eid = data.get("eid")

        name = (data.get("name") or "").strip()
        phone_number = (data.get("phone_number") or "").strip()

        # ðŸ”’ Required validation
        if not name:
            return {
                "success": False,
                "error": "Employee name is required"
            }

        # ðŸ”’ Prevent duplicate employee name / phone while editing
        cur.execute(
            """
            SELECT eid, name, phone_number
            FROM employee
            WHERE eid != %s
              AND (
                    LOWER(name) = LOWER(%s)
                    OR phone_number = %s
                  )
            LIMIT 1
            """,
            (eid, name, phone_number)
        )

        existing_employee = cur.fetchone()

        if existing_employee:
            existing_eid, existing_name, existing_phone = existing_employee

            # Same name + same phone
            if (
                existing_name
                and existing_phone
                and existing_name.strip().lower() == name.lower()
                and str(existing_phone).strip() == phone_number
            ):
                return {
                    "success": False,
                    "error": "Another employee already exists with same name and mobile number"
                }

            # Same employee name
            if (
                existing_name
                and existing_name.strip().lower() == name.lower()
            ):
                return {
                    "success": False,
                    "error": f"Employee name '{name}' already exists"
                }

            # Same phone number
            if (
                existing_phone
                and str(existing_phone).strip() == phone_number
            ):
                return {
                    "success": False,
                    "error": f"Mobile number '{phone_number}' is already assigned to another employee"
                }

        # âœ… Update employee
        cur.execute("""
            UPDATE employee
            SET
                name = %s,
                phone_number = %s,
                city = %s,
                joining_date = %s,
                level = %s,
                state = %s
            WHERE eid = %s
        """, (
            name,
            phone_number,
            data.get("city"),
            data.get("joining_date"),
            data.get("level").strip().lower() if data.get("level") else None,
            data.get("state"),
            eid,
        ))

        conn.commit()
        audit_log(
            action="update_employee",
            entity_type="employee",
            entity_id=eid,
            details={
                "name": name,
                "phone_number": phone_number,
                "city": data.get("city"),
                "joining_date": data.get("joining_date"),
                "level": data.get("level").strip().lower() if data.get("level") else None,
                "state": data.get("state")
            }
        )

        return {
            "success": True
        }

    except Exception as e:
        conn.rollback()

        return {
            "success": False,
            "error": str(e)
        }

    finally:
        cur.close()
        conn.close()


def delete_employee_from_db(eid):
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM employee WHERE eid = %s", (eid,))

    conn.commit()
    cur.close()
    conn.close()

@app.route("/employee")
@login_required
@admin_required
def employee_page():
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM village")
    total_villages = cur.fetchone()[0]
    cur.close()
    conn.close()

    rows = get_all_employees()  # your repo function
    headers = rows[0].keys() if rows else []
    return render_template(
        "employee.html",
        data=rows,
        headers=headers,
        total_employees=len(rows),
        total_villages=total_villages
    )

@app.route("/api/update_employee", methods=["POST"])
@login_required
@admin_required
def update_employee():
    data = request.json
    try:
        result = update_employee_in_db(data)  # implement in repo
        if result["success"]:
            return jsonify(success=True)
        else:
            return jsonify(success=False, error=result["error"])
    except Exception as e:
        return jsonify(success=False, error=str(e))
    
@app.route("/api/delete_employee", methods=["POST"])
@admin_required
def delete_employee():
    data = request.json
    if not data:
        return jsonify(success=False, error="Invalid request body"), 400
    try:
        delete_employee_from_db(data["eid"])
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route("/employee/<int:eid>")
@login_required
@admin_required
def employee_detail_page(eid):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # 1. Fetch employee details
        cur.execute("""
            SELECT eid, name, phone_number, city, state, joining_date, level, is_active, created_at
            FROM employee
            WHERE eid = %s
        """, (eid,))
        emp_row = cur.fetchone()
        if not emp_row:
            flash("Employee not found", "danger")
            return redirect(url_for("employee_page"))
        
        emp_headers = [desc[0] for desc in cur.description]
        emp = dict(zip(emp_headers, emp_row))
        emp['photo_url'] = get_employee_photo_url(eid)

        # 2. Fetch linked user account
        cur.execute("""
            SELECT id, username, is_active, created_at
            FROM users
            WHERE employee_id = %s
            LIMIT 1
        """, (eid,))
        user_row = cur.fetchone()
        user = None
        user_id = None
        if user_row:
            user = {
                "id": user_row[0],
                "username": user_row[1],
                "is_active": user_row[2],
                "created_at": user_row[3]
            }
            user_id = user["id"]

        # 3. Fetch registered devices (if user exists)
        devices = []
        if user_id:
            ensure_user_devices_table(cur)
            cur.execute("""
                SELECT id, device_id, device_model, last_active, is_active
                FROM user_devices
                WHERE user_id = %s
                ORDER BY last_active DESC NULLS LAST, id DESC
            """, (user_id,))
            for r in cur.fetchall():
                is_pending = (r[1] == 'PENDING')
                formatted_last_active = "Never" if (is_pending or not r[3]) else r[3].strftime("%d-%m-%Y %I:%M %p")
                devices.append({
                    "id": r[0],
                    "device_id": "Pending Bind" if is_pending else r[1],
                    "raw_device_id": r[1],
                    "device_model": r[2] or "Mobile Device",
                    "last_active": formatted_last_active,
                    "is_active": r[4]
                })

        # 4. Fetch assigned villages
        assigned_vids = set()
        if user_id:
            cur.execute("SELECT village_id FROM user_village_access WHERE user_id = %s", (user_id,))
            assigned_vids.update(r[0] for r in cur.fetchall())

        cur.execute("SELECT vid FROM village WHERE emp1 = %s OR emp2 = %s", (eid, eid))
        assigned_vids.update(r[0] for r in cur.fetchall())

        # 5. Fetch all villages
        cur.execute("SELECT vid, village_name, district FROM village ORDER BY village_name")
        all_villages = [
            {
                "vid": r[0],
                "village_name": r[1],
                "district": r[2] or "",
                "is_assigned": r[0] in assigned_vids
            }
            for r in cur.fetchall()
        ]

        assigned_villages = [v for v in all_villages if v["is_assigned"]]

        user_level = session.get("level")
        is_admin = (user_level in ["admin", "superadmin"])

        return render_template(
            "employee_detail.html",
            emp=emp,
            user=user,
            devices=devices,
            assigned_villages=assigned_villages,
            all_villages=all_villages,
            user_level=user_level,
            is_admin=is_admin
        )
    finally:
        cur.close()
        conn.close()

@app.route("/api/employee/upload_photo", methods=["POST"])
@login_required
@admin_required
def upload_employee_photo():
    eid = request.form.get("eid")
    if not eid:
        return jsonify(success=False, error="Employee ID is required"), 400
    
    if "photo" not in request.files:
        return jsonify(success=False, error="No photo file provided"), 400
    
    file = request.files["photo"]
    if not file or not file.filename:
        return jsonify(success=False, error="No file selected"), 400
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        return jsonify(success=False, error="Invalid image type. Supported: JPG, PNG, WEBP"), 400
    
    upload_dir = os.path.join(app.root_path, "static", "uploads", "employees")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Remove older formats
    for old_ext in [".jpg", ".jpeg", ".png", ".webp"]:
        old_file = os.path.join(upload_dir, f"{eid}{old_ext}")
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
            except Exception:
                pass
                
    save_path = os.path.join(upload_dir, f"{eid}{ext}")
    file.save(save_path)
    
    mtime = int(os.path.getmtime(save_path))
    new_url = f"/static/uploads/employees/{eid}{ext}?v={mtime}"
    
    return jsonify(success=True, photo_url=new_url)

@app.route("/api/employee/<int:eid>/update_villages", methods=["POST"])
@login_required
@admin_required
def update_employee_villages(eid):
    data = request.get_json() or {}
    village_ids = data.get("village_ids", [])
    
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Check if user exists for this employee
        cur.execute("SELECT id FROM users WHERE employee_id = %s", (eid,))
        user_row = cur.fetchone()
        if user_row:
            user_id = user_row[0]
            cur.execute("DELETE FROM user_village_access WHERE user_id = %s", (user_id,))
            for vid in village_ids:
                cur.execute("INSERT INTO user_village_access (user_id, village_id) VALUES (%s, %s)", (user_id, vid))
        
        conn.commit()
        return jsonify(ok=True, success=True)
    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, success=False, error=str(e)), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/employee/<int:eid>/create_user", methods=["POST"])
@login_required
@admin_required
def create_employee_user(eid):
    if session.get("level") not in ["admin", "superadmin"]:
        return jsonify(ok=False, msg="Admin privilege required"), 403

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify(ok=False, msg="Username and password are required")

    hashed = generate_password_hash(password, method="pbkdf2:sha256")

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        if cur.fetchone():
            return jsonify(ok=False, msg=f"Username '{username}' already exists")

        cur.execute("""
            INSERT INTO users (username, password_hash, employee_id, is_active)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id
        """, (username, hashed, eid))
        new_uid = cur.fetchone()[0]

        # Auto-assign villages from village table where emp1 or emp2 is eid
        cur.execute("SELECT vid FROM village WHERE emp1 = %s OR emp2 = %s", (eid, eid))
        vids = cur.fetchall()
        for v in vids:
            cur.execute("""
                INSERT INTO user_village_access (user_id, village_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (new_uid, v[0]))

        conn.commit()
        return jsonify(ok=True, success=True, user_id=new_uid, username=username)
    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))
    finally:
        cur.close()
        conn.close()
# ----------------------------------------------------
# ROUTES
# ----------------------------------------------------
@app.route("/")
@login_required
def home():
    return redirect("/village")

@app.route("/landing")
@login_required
def landing():
    # Clear active village context so the header shows nothing
    # and the user must pick a village on this page.
    session.pop("vid", None)
    session.pop("eid", None)
    session.pop("village_name", None)
    session.pop("village_code", None)
    session.pop("employee_name", None)
    return render_template("landing.html")

# ----------------------------------------------------
# Login / Logout
# ----------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")
    device_id = request.form.get("device_id")
    session.permanent = True

    if not username or not password:
        flash("Username and password required")
        return redirect("/login")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # ---------------------------
        # 1ï¸âƒ£ Fetch user
        # ---------------------------
        cur.execute("""
            SELECT u.id,
                   u.password_hash,
                   u.employee_id,
                   u.is_active,
                   e.level
            FROM users u
            JOIN employee e ON e.eid = u.employee_id
            WHERE u.username = %s
        """, (username,))
        user = cur.fetchone()
        if not user:
            flash("Incorrect username. Please contact admin to reset credentials")
            return redirect("/login")

        user_id, password_hash, employee_id, is_active, level = user


        if not is_active:
            return render_template(
        "login.html",
        error="User account disabled by admin. Contact admin for activation."
        )

        # ---------------------------
        # 2️⃣ Check password
        # ---------------------------
        if not check_password_hash(password_hash, password):
            flash("Incorrect password. Please contact admin to reset credentials")
            return redirect("/login")

        # ---------------------------
        # 3️⃣ Device registration initialization (Web only)
        # ---------------------------
        # Web logins do not require device lock. We only initialize/reset the user_devices record
        # to 'PENDING' and is_active = TRUE when they log in to download the app. This ensures
        # deactivated or old physical bindings are reset correctly.
        if level and level.strip().lower() in ("j", "m", "s"):
            ensure_user_devices_table(cur)
            cur.execute("SELECT id FROM user_devices WHERE user_id = %s AND device_id = 'PENDING'", (user_id,))
            pending_row = cur.fetchone()
            if not pending_row:
                cur.execute("""
                    INSERT INTO user_devices (user_id, device_id, is_active, last_active)
                    VALUES (%s, 'PENDING', TRUE, NULL)
                    ON CONFLICT (user_id, device_id)
                    DO UPDATE SET is_active = TRUE, last_active = NULL
                """, (user_id,))
            else:
                cur.execute("""
                    UPDATE user_devices
                    SET is_active = TRUE, last_active = NULL
                    WHERE id = %s
                """, (pending_row[0],))
            conn.commit()

        # ---------------------------
        # 4ï¸ âƒ£ Load village access
        # ---------------------------
        cur.execute("""
            SELECT vid
            FROM village
            WHERE emp1 = %s OR emp2 = %s
        """, (employee_id, employee_id))

        villages = [row[0] for row in cur.fetchall()]

        # Preserve download token keys before clearing session if any
        prev_download_eid = session.get("download_token_eid")
        prev_download_exp = session.get("download_token_expiry")
        prev_download_str = session.get("download_token_str")

        # ---------------------------
        # 5ï¸ âƒ£ Save session
        # ---------------------------
        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        session["employee_id"] = employee_id
        session["level"] = level.strip().lower() if level else None
        session["villages"] = villages
        session.permanent = True

        audit_log(
            action="login",
            entity_type="user",
            entity_id=user_id,
            details={
                "employee_id": employee_id,
                "username": username,
                "level": level,
                "device_id": device_id
            }
        )

        user_level = level.strip().lower() if level else ""
        if user_level in ("j", "m", "s"):
            # Check if this user has a valid active temporary download token session
            allowed = False
            token = request.form.get("token") or request.args.get("token") or prev_download_str
            token_eid = None
            token_exp = None

            if token:
                try:
                    payload = serializer.loads(token)
                    token_eid = payload.get("eid")
                    token_exp = payload.get("exp")
                except Exception as e:
                    logger.warning("login token signature load failed: %s", e)

            if not token_eid or not token_exp:
                token_eid = prev_download_eid
                token_exp = prev_download_exp

            if token_eid and token_exp:
                try:
                    exp_dt = datetime.fromisoformat(token_exp)
                    if datetime.now(timezone.utc) < exp_dt and int(token_eid) == int(employee_id):
                        allowed = True
                except Exception:
                    pass

            if allowed:
                session["download_authorized"] = True
                session["download_token_eid"] = int(token_eid)
                session["download_token_expiry"] = token_exp
                if token:
                    session["download_token_str"] = token
                    return redirect(url_for("app_portal", token=token))
                return redirect("/app/portal")
            else:
                session.clear()
                flash("Web access denied. If you need to install the mobile app, request a temporary installation link from your administrator.")
                return redirect("/login")

        return redirect("/village")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Login error for user %s: %s", username, e)
        flash("An error occurred during login. Please try again or contact your administrator.", "danger")
        return redirect("/login")

    finally:
        cur.close()
        conn.close()

@app.route("/logout")
@login_required
def logout():
    user_id = session.get("user_id")
    eid = session.get("eid")

    audit_log(
        action="logout",
        entity_type="user",
        entity_id=user_id,
        details={
            "eid": eid
        }
    )

    session.clear()

    response = redirect(url_for("login"))

    response.delete_cookie(app.config.get("SESSION_COOKIE_NAME", "sivadurga_session"))
    # Active cleanup of legacy/stale 'session' cookies
    response.delete_cookie("session")
    response.delete_cookie("session", domain=".sivadurga.in")

    flash("Logged out", "info")

    return response


@app.route("/users")
@login_required
def users_page():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("level") != "admin":
        flash("Access denied")
        return redirect("/dashboard")

    return redirect("/employee")

@app.route("/api/users/list")
@login_required
@admin_required
def list_users():
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        u.id,
        u.username,
        u.employee_id,
        u.is_active,
        e.name,
        e.level
    FROM users u
    LEFT JOIN employee e ON e.eid = u.employee_id
    ORDER BY u.id
""")

    users = []
    rows = cur.fetchall()

    user_ids = [r[0] for r in rows]

    devices_by_user = {}
    villages_by_user = {}

    if user_ids:

        ensure_user_devices_table(cur)

        # Batch fetch devices ordered by last_active
        cur.execute("""
            SELECT user_id, device_id, device_model, last_active, is_active
            FROM user_devices
            WHERE user_id = ANY(%s)
            ORDER BY last_active DESC NULLS LAST, id DESC
        """, (user_ids,))

        for uid, device_id, device_model, last_active, is_active in cur.fetchall():
            is_pending = (device_id == 'PENDING')
            formatted_last_active = "Never" if (is_pending or not last_active) else last_active.strftime("%d/%m/%Y %I:%M %p")
            dev_obj = {
                "device_id": "Pending Bind" if is_pending else device_id,
                "device_model": device_model or "Mobile Device",
                "last_active": formatted_last_active,
                "is_active": is_active
            }
            devices_by_user.setdefault(uid, []).append(dev_obj)

        # Batch fetch village access
        cur.execute("""
            SELECT
                uva.user_id,
                v.vid,
                v.village_name,
                v.district
            FROM user_village_access uva
            JOIN village v ON v.vid = uva.village_id
            WHERE uva.user_id = ANY(%s)
            ORDER BY v.village_name
        """, (user_ids,))

        for uid, vid, village_name, district in cur.fetchall():
            villages_by_user.setdefault(uid, []).append({
                "vid": vid,
                "name": village_name,
                "district": district
            })

    for row in rows:
        user_id, username, employee_id, is_active, emp_name, level = row
        user_devs = devices_by_user.get(user_id, [])
        primary_dev = user_devs[0] if user_devs else {"device_id": "-", "device_model": "-", "last_active": "Never"}

        users.append({
            "id": user_id,
            "username": username,
            "employee_id": employee_id,
            "employee_name": emp_name,
            "role": level,
            "device_id": primary_dev["device_id"],
            "device_model": primary_dev["device_model"],
            "last_active": primary_dev["last_active"],
            "device_count": len(user_devs),
            "devices": user_devs,
            "is_active": is_active,
            "villages": villages_by_user.get(user_id, [])
        })

    cur.close()
    conn.close()

    return jsonify(users)

@app.route("/api/users/add", methods=["POST"])
@login_required
@admin_required
def add_user():

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")
    employee_id = data.get("employee_id")

    if not username or not password or not employee_id:
        return jsonify(ok=False, msg="Missing required fields")

    hashed = generate_password_hash(password, method="pbkdf2:sha256")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (username, password_hash, employee_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (username, hashed, employee_id))

        result = cur.fetchone()
        if not result:
            conn.rollback()
            return jsonify(ok=False, msg="Failed to create user")
        
        new_user_id = result[0]

        # ðŸ”¹ Assign villages to user in user_village_access
        cur.execute("""
            SELECT vid
            FROM village
            WHERE emp1 = %s OR emp2 = %s
        """, (employee_id, employee_id))

        village_rows = cur.fetchall()

        for v in village_rows:
            cur.execute("""
                INSERT INTO user_village_access (user_id, village_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (new_user_id, v[0]))

        conn.commit()
        return jsonify(ok=True)

    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))

    finally:
        cur.close()
        conn.close()

@app.route("/api/users/update", methods=["POST"])
@login_required
@admin_required
def update_user():
    data = request.get_json()
    uid = data.get("id")
    username = data.get("username")
    employee_id = data.get("employee_id")

    if not uid or not username or not employee_id:
        return jsonify(ok=False, msg="Missing required fields")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Prevent duplicate username
        cur.execute("""
            SELECT id FROM users WHERE LOWER(username) = LOWER(%s) AND id != %s
        """, (username, uid))
        if cur.fetchone():
            return jsonify(ok=False, msg=f"Username '{username}' already exists")

        cur.execute("""
            UPDATE users
            SET username = %s, employee_id = %s
            WHERE id = %s
        """, (username, employee_id, uid))

        # Re-sync village access
        cur.execute("DELETE FROM user_village_access WHERE user_id = %s", (uid,))
        cur.execute("""
            SELECT vid
            FROM village
            WHERE emp1 = %s OR emp2 = %s
        """, (employee_id, employee_id))
        village_rows = cur.fetchall()
        for v in village_rows:
            cur.execute("""
                INSERT INTO user_village_access (user_id, village_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (uid, v[0]))

        conn.commit()
        audit_log(
            action="update_user",
            entity_type="user",
            entity_id=uid,
            details={
                "username": username,
                "employee_id": employee_id
            }
        )
        return jsonify(ok=True)
    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))
    finally:
        cur.close()
        conn.close()

@app.route("/api/users/delete", methods=["POST"])
@login_required
@admin_required
def delete_user():
    data = request.get_json()
    user_id = data.get("id") if data else None

    if not user_id:
        return jsonify(ok=False, msg="Missing user id")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Delete device records first (FK safety)
        cur.execute("DELETE FROM user_devices WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))

        conn.commit()
        return jsonify(ok=True)

    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))

    finally:
        cur.close()
        conn.close()

@app.route("/api/users/reset_device", methods=["POST"])
@login_required
@admin_required
def reset_user_device():
    if session.get("level") not in ("admin", "superadmin"):
        return jsonify(ok=False, msg="Access denied: Admin role required"), 403

    data = request.get_json()
    user_id = data.get("id") if data else None

    if not user_id:
        return jsonify(ok=False, msg="Missing user id")

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        ensure_user_devices_table(cur)
        # Deactivate existing physical devices so they cannot be reused without re-binding
        cur.execute("UPDATE user_devices SET is_active = FALSE WHERE user_id = %s AND device_id != 'PENDING'", (user_id,))
        # Ensure a PENDING device record exists and is active
        cur.execute("""
            INSERT INTO user_devices (user_id, device_id, is_active, last_active)
            VALUES (%s, 'PENDING', TRUE, NULL)
            ON CONFLICT (user_id, device_id)
            DO UPDATE SET is_active = TRUE, last_active = NULL
        """, (user_id,))

        conn.commit()
        return jsonify(ok=True)

    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))

    finally:
        cur.close()
        conn.close()

@app.route("/api/users/reset_password", methods=["POST"])
@login_required
@admin_required
def reset_user_password():
    if session.get("level") != "admin":
        return jsonify(ok=False, msg="Access denied: Admin role required"), 403

    data = request.get_json()
    user_id = data.get("id") if data else None
    password = data.get("password") if data else None

    if not user_id or not password:
        return jsonify(ok=False, msg="Missing required fields")

    hashed = generate_password_hash(password, method="pbkdf2:sha256")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
        """, (hashed, user_id))

        conn.commit()

        audit_log(
            action="reset_password",
            entity_type="user",
            entity_id=user_id,
            details={
                "admin_user_id": session.get("user_id")
            }
        )
        return jsonify(ok=True)

    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))

    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------
# Toggle user status
# ----------------------------------------------------
@app.route("/api/users/toggle_status", methods=["POST"])
@admin_required
def toggle_user_status():
    if session.get("level") not in ("admin", "superadmin"):
        return jsonify(ok=False, msg="Access denied: Admin role required"), 403

    data = request.get_json()
    user_id = data.get("id")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Flip boolean
        cur.execute("""
            UPDATE users
            SET is_active = NOT is_active
            WHERE id = %s
            RETURNING is_active
        """, (user_id,))

        conn.commit()
        return jsonify(ok=True)

    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))

    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------
# Update user's village access
# ----------------------------------------------------
@app.route("/api/users/update_villages", methods=["POST"])
@login_required
@admin_required
def update_user_villages():
    data = request.get_json()
    user_id = data.get("user_id")
    village_ids = data.get("village_ids", [])

    if not user_id:
        return jsonify(ok=False, msg="Missing user_id")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # ðŸ”¹ Remove existing mappings
        cur.execute("""
            DELETE FROM user_village_access
            WHERE user_id = %s
        """, (user_id,))

        # ðŸ”¹ Insert new mappings
        for vid in village_ids:
            cur.execute("""
                INSERT INTO user_village_access (user_id, village_id)
                VALUES (%s, %s)
            """, (user_id, vid))

        conn.commit()
        return jsonify(ok=True)

    except Exception as e:
        conn.rollback()
        return jsonify(ok=False, msg=str(e))

    finally:
        cur.close()
        conn.close()
# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    vid = session.get("vid")
    # ✅ NO CONTEXT → SHOW ZERO DASHBOARD
    if not vid:
        if request.args.get("partial"):
            return render_template(
                "dashboard.html",
                total_customers=0,
                sum_amt=0,
                sum_pamt=0,
                sum_bamt=0,
            )
        return render_template(
            "dashboard.html",
            total_customers=0,
            sum_amt=0,
            sum_pamt=0,
            sum_bamt=0,
        )
    totals = {
        "total_customers": 0,
        "sum_amt": 0,
        "sum_pamt": 0,
        "sum_bamt": 0,
    }
    if vid:
        user_level = session.get("level")
        allowed_villages = session.get("villages", [])

        if user_level not in ["admin", "mgmt"]:
            if vid not in allowed_villages:
                return redirect("/dashboard")

        totals = get_dashboard_totals(vid)

    return render_template(
         "dashboard.html",
         total_customers=totals["total_customers"],
         sum_amt=totals["sum_amt"],
         sum_pamt=totals["sum_pamt"],
         sum_bamt=totals["sum_bamt"],
    )

@app.route("/reselect", methods=["POST"])
def reselect():
    session.pop("active_db", None)
    session.pop("active_path", None)
    session.pop("village_name", None)
    return redirect("/dashboard")


@app.route("/update_payment_date_bulk", methods=["POST"])
@login_required
def update_payment_date_bulk():
    data = request.get_json()
    old_date = data.get("find_date")
    new_date = data.get("replace_date")
    vid = session.get("vid")

    if not old_date or not new_date or not vid:
        return jsonify(success=False, error="Missing data"), 400

    # Convert any date format â†’ date object
    try:
        old_iso = parse_date_input(old_date)
        new_iso = parse_date_input(new_date)
        if not old_iso or not new_iso:
            raise ValueError("bad date")
    except (ValueError, TypeError):
        return jsonify(success=False, error="Invalid date format"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Check if updating would create duplicate payments on new_iso for any customer
        cur.execute("""
            SELECT ano FROM payment
            WHERE vid = %s AND payment_date = %s AND ano IN (
                SELECT ano FROM payment WHERE vid = %s AND payment_date = %s
            )
            LIMIT 5
        """, (vid, old_iso, vid, new_iso))
        conflicts = [r[0] for r in cur.fetchall()]
        if conflicts:
            return jsonify(
                success=False,
                error=f"Cannot bulk update date: Accounts ({', '.join(map(str, conflicts))}) already have payments on {format_date_display(str(new_iso))}."
            ), 400

        cur.execute("""
            UPDATE payment
            SET payment_date = %s
            WHERE vid = %s AND payment_date = %s
        """, (new_iso, vid, old_iso))

        # Also update closed customer payments
        cur.execute("""
            UPDATE closed_cust_payment
            SET payment_date = %s
            WHERE vid = %s AND payment_date = %s
        """, (new_iso, vid, old_iso))

        # Also update historic payment data if matching
        cur.execute("""
            UPDATE historic_payment_data
            SET payment_date = %s
            WHERE vid = %s AND payment_date = %s
        """, (new_iso, vid, old_iso))

        # Invalidate cache for this village
        min_pdt = min(old_iso, new_iso)
        invalidate_village_health_cache(cur, vid, min_pdt)

        global_ttl_cache.clear()
        conn.commit()
        return jsonify(success=True, message="Payment dates updated")

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------
# CASHBAG ROUTES
# ----------------------------------------------------

@app.route("/cashbag")
@login_required
def cashbag():

    # ── Scope: employee pair from query params ──
    emp1 = request.args.get("emp1", type=int)
    emp2 = request.args.get("emp2", type=int)  # may be None if solo employee

    if not emp1:
        flash("Please open Cash Bag from a village group tile.", "warning")
        return redirect(url_for("village_page"))

    conn = get_pg_connection()
    cur = conn.cursor()

    try:

        # ------------------------------------------------
        # BUILD emp pair WHERE clause helper
        # ------------------------------------------------
        if emp2:
            pair_filter = "emp1 = %s AND emp2 = %s"
            pair_params_single = (emp1, emp2)
        else:
            pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
            pair_params_single = (emp1,)

        # ------------------------------------------------
        # EMPLOYEE NAMES for page header
        # ------------------------------------------------
        cur.execute("SELECT name FROM employee WHERE eid = %s", (emp1,))
        row_e1 = cur.fetchone()
        emp1_name = row_e1[0] if row_e1 else f"Employee {emp1}"

        emp2_name = None
        if emp2:
            cur.execute("SELECT name FROM employee WHERE eid = %s", (emp2,))
            row_e2 = cur.fetchone()
            emp2_name = row_e2[0] if row_e2 else f"Employee {emp2}"

        # ------------------------------------------------
        # VILLAGES in this group (for context display)
        # ------------------------------------------------
        if emp2:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND emp2 = %s AND status = 'active'
                ORDER BY village_code
            """, (emp1, emp2))
        else:
            cur.execute("""
                SELECT vid, village_name, village_code
                FROM village
                WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
                ORDER BY village_code
            """, (emp1,))
        rows_v = cur.fetchall()
        group_villages = [{"id": r[0], "name": r[1], "code": r[2]} for r in rows_v]
        vids = [r[0] for r in rows_v]

        # ------------------------------------------------
        # SUMMARY TOTALS  (scoped to emp pair / vids)
        # ------------------------------------------------

        # 1. Manual transactions sum
        cur.execute(f"""
            SELECT 
                COALESCE(SUM(CASE WHEN txn = 'OFFICE_CASH' THEN amount ELSE 0 END), 0) AS office_cash,
                COALESCE(SUM(CASE WHEN txn = 'OFFICE_CASH' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS office_cash_cash,
                COALESCE(SUM(CASE WHEN txn = 'OFFICE_CASH' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS office_cash_upi,
                
                COALESCE(SUM(CASE WHEN txn = 'EXPENSE' THEN amount ELSE 0 END), 0) AS expenses,
                COALESCE(SUM(CASE WHEN txn = 'EXPENSE' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS expenses_cash,
                COALESCE(SUM(CASE WHEN txn = 'EXPENSE' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS expenses_upi,
                
                COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' THEN amount ELSE 0 END), 0) AS adj_add,
                COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS adj_add_cash,
                COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS adj_add_upi,
                
                COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' THEN amount ELSE 0 END), 0) AS adj_minus,
                COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS adj_minus_cash,
                COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS adj_minus_upi,

                COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' THEN amount ELSE 0 END), 0) AS profit_val,
                COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS profit_cash,
                COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS profit_upi,
                
                COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'LOSS' THEN amount ELSE 0 END), 0) AS loss_val,
                COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'LOSS' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS loss_cash,
                COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'LOSS' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS loss_upi
            FROM cashbag_transactions
            WHERE {pair_filter}
        """, pair_params_single)
        row_manual = cur.fetchone()
        office_cash = float(row_manual[0] or 0)
        office_cash_cash = float(row_manual[1] or 0)
        office_cash_upi = float(row_manual[2] or 0)
        expenses = float(row_manual[3] or 0)
        expenses_cash = float(row_manual[4] or 0)
        expenses_upi = float(row_manual[5] or 0)
        adjustments_add = float(row_manual[6] or 0)
        adjustments_add_cash = float(row_manual[7] or 0)
        adjustments_add_upi = float(row_manual[8] or 0)
        adjustments_minus = float(row_manual[9] or 0)
        adjustments_minus_cash = float(row_manual[10] or 0)
        adjustments_minus_upi = float(row_manual[11] or 0)
        profit_val = float(row_manual[12] or 0)
        profit_cash = float(row_manual[13] or 0)
        profit_upi = float(row_manual[14] or 0)
        loss_val = float(row_manual[15] or 0)
        loss_cash = float(row_manual[16] or 0)
        loss_upi = float(row_manual[17] or 0)
        profit_loss_net = profit_val - loss_val

        # 2. Installments sum
        installments = 0.0
        installments_cash = 0.0
        installments_upi = 0.0
        if vids:
            cur.execute("""
                SELECT 
                    COALESCE(SUM(p.amt), 0) AS total,
                    COALESCE(SUM(CASE 
                        WHEN LOWER(p.payment_type) = 'cash' THEN p.amt 
                        WHEN LOWER(p.payment_type) = 'upi' THEN 0 
                        WHEN LOWER(p.payment_type) = 'partial' THEN COALESCE(p.cash_amount, 0)
                        ELSE p.amt 
                    END), 0) AS cash,
                    COALESCE(SUM(CASE 
                        WHEN LOWER(p.payment_type) = 'upi' THEN p.amt 
                        WHEN LOWER(p.payment_type) = 'partial' THEN COALESCE(p.upi_amount, 0)
                        ELSE 0 
                    END), 0) AS upi
                FROM v_all_payments p
                WHERE p.vid = ANY(%s)
            """, (vids,))
            row_inst = cur.fetchone()
            installments = float(row_inst[0] or 0)
            installments_cash = float(row_inst[1] or 0)
            installments_upi = float(row_inst[2] or 0)

        # 3. Loans & commissions sum
        loans_disbursed = 0.0
        loans_disbursed_cash = 0.0
        loans_disbursed_upi = 0.0
        loan_commission = 0.0
        loan_commission_cash = 0.0
        loan_commission_upi = 0.0
        interest_total = 0.0
        if vids:
            cur.execute("""
                SELECT 
                    COALESCE(SUM(CASE 
                        WHEN c.base_amount > 0 THEN c.base_amount 
                        ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) 
                    END), 0) AS loans_disbursed,
                    COALESCE(SUM(CASE 
                        WHEN LOWER(c.payment_type) = 'upi' THEN 0
                        ELSE (CASE WHEN c.base_amount > 0 THEN c.base_amount ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) END)
                    END), 0) AS loans_disbursed_cash,
                    COALESCE(SUM(CASE 
                        WHEN LOWER(c.payment_type) = 'upi' THEN (CASE WHEN c.base_amount > 0 THEN c.base_amount ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) END)
                        ELSE 0
                    END), 0) AS loans_disbursed_upi,
                    
                    COALESCE(SUM(CASE 
                        WHEN c.cutting_amount > 0 THEN c.cutting_amount 
                        ELSE ROUND(c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0), 2) 
                    END), 0) AS loan_commission,
                    COALESCE(SUM(CASE 
                        WHEN LOWER(c.payment_type) = 'upi' THEN 0
                        ELSE (CASE WHEN c.cutting_amount > 0 THEN c.cutting_amount ELSE ROUND(c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0), 2) END)
                    END), 0) AS loan_commission_cash,
                    COALESCE(SUM(CASE 
                        WHEN LOWER(c.payment_type) = 'upi' THEN (CASE WHEN c.cutting_amount > 0 THEN c.cutting_amount ELSE ROUND(c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0), 2) END)
                        ELSE 0
                    END), 0) AS loan_commission_upi,
                    
                    COALESCE(SUM(CASE 
                        WHEN c.interest_amount > 0 THEN c.interest_amount 
                        ELSE ROUND(c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0), 2) 
                    END), 0) AS interest_total
                FROM v_all_customers c
                JOIN village v ON c.vid = v.vid
                WHERE c.vid = ANY(%s) AND c.status != 'deleted'
            """, (vids,))
            row_loans = cur.fetchone()
            loans_disbursed = float(row_loans[0] or 0)
            loans_disbursed_cash = float(row_loans[1] or 0)
            loans_disbursed_upi = float(row_loans[2] or 0)
            loan_commission = float(row_loans[3] or 0)
            loan_commission_cash = float(row_loans[4] or 0)
            loan_commission_upi = float(row_loans[5] or 0)
            interest_total = float(row_loans[6] or 0)

        # ------------------------------------------------
        # FINAL CASHBAG TOTALS
        # ------------------------------------------------
        cashbag_total_cash = (
            office_cash_cash
            + installments_cash
            + loan_commission_cash
            + adjustments_add_cash
            + profit_cash
            - loans_disbursed_cash
            - expenses_cash
            - adjustments_minus_cash
            - loss_cash
        )
        cashbag_total_upi = (
            office_cash_upi
            + installments_upi
            + loan_commission_upi
            + adjustments_add_upi
            + profit_upi
            - loans_disbursed_upi
            - expenses_upi
            - adjustments_minus_upi
            - loss_upi
        )
        cashbag_total = cashbag_total_cash + cashbag_total_upi

        # ------------------------------------------------
        # TRANSACTION HISTORY (Unified Ledger)
        # ------------------------------------------------
        if vids:
            query = f"""
                SELECT 
                    id,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by,
                    TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH12:MI AM') AS created_at
                FROM (
                    -- Manual entries (Office Cash, Expense, Adjustment)
                    SELECT 
                        id::text AS id,
                        txn,
                        txn_sub,
                        txn_type,
                        amount,
                        notes,
                        created_by,
                        created_at
                    FROM cashbag_transactions
                    WHERE {pair_filter}
                      AND txn IN ('OFFICE_CASH', 'EXPENSE', 'ADJUSTMENT', 'PROFIT_LOSS')

                    UNION ALL

                    -- Customer Loans (Auto)
                    SELECT 
                        'loan_' || c.cid::text AS id,
                        'LOAN' AS txn,
                        NULL AS txn_sub,
                        'CASH' AS txn_type,
                        CASE 
                            WHEN c.base_amount > 0 THEN c.base_amount
                            ELSE ROUND(c.total_amount - (c.total_amount * (v.interest_rate / 100.0)) - (c.total_amount * (v.cutting_rate / 100.0)), 2)
                        END AS amount,
                        'Loan issued to ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                        'System' AS created_by,
                        c.start_date::timestamp WITH time zone AS created_at
                    FROM (
                        SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid FROM customer
                        UNION ALL
                        SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid FROM closed_cust_account
                    ) c
                    JOIN village v ON c.vid = v.vid
                    WHERE c.vid = ANY(%s) AND c.status != 'deleted'

                    UNION ALL

                    -- Customer Loan Commission (Auto)
                    SELECT 
                        'comm_' || c.cid::text AS id,
                        'LOAN_COMMISION' AS txn,
                        NULL AS txn_sub,
                        'CASH' AS txn_type,
                        CASE 
                            WHEN c.cutting_amount > 0 THEN c.cutting_amount
                            ELSE ROUND(c.total_amount * (v.cutting_rate / 100.0), 2)
                        END AS amount,
                        'Rusum - ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                        'System' AS created_by,
                        c.start_date::timestamp WITH time zone AS created_at
                    FROM (
                        SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid FROM customer
                        UNION ALL
                        SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid FROM closed_cust_account
                    ) c
                    JOIN village v ON c.vid = v.vid
                    WHERE c.vid = ANY(%s) AND c.status != 'deleted'

                    UNION ALL

                    -- Customer Payments (Auto)
                    SELECT 
                        'pay_' || p.pid::text AS id,
                        'INSTALLMENT_AMOUNT' AS txn,
                        NULL AS txn_sub,
                        p.payment_type AS txn_type,
                        p.amt AS amount,
                        'Collection from ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                        'System' AS created_by,
                        p.created_at AS created_at
                    FROM v_all_payments p
                    JOIN v_all_customers c ON p.cid = c.cid
                    WHERE p.vid = ANY(%s)
                ) AS combined
                ORDER BY combined.created_at DESC, id DESC
                LIMIT 250
            """
            if emp2:
                params = (emp1, emp2, vids, vids, vids)
            else:
                params = (emp1, vids, vids, vids)
            cur.execute(query, params)
        else:
            query = f"""
                SELECT 
                    id::text AS id,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by,
                    TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH12:MI AM') AS created_at
                FROM cashbag_transactions
                WHERE {pair_filter}
                  AND txn IN ('OFFICE_CASH', 'EXPENSE', 'ADJUSTMENT', 'PROFIT_LOSS')
                ORDER BY created_at DESC, id DESC
                LIMIT 250
            """
            cur.execute(query, pair_params_single)

        rows = cur.fetchall()
        transactions = []

        for row in rows:
            transactions.append({
                "id":         row[0],
                "txn":        row[1],
                "txn_sub":    row[2],
                "txn_type":   row[3],
                "amount":     float(row[4] or 0),
                "notes":      row[5],
                "created_by": row[6],
                "created_at": row[7]
            })

        return render_template(
            "cashbag.html",

            emp1=emp1,
            emp2=emp2,
            emp1_name=emp1_name,
            emp2_name=emp2_name,
            group_villages=group_villages,

            cashbag_total=cashbag_total,
            cashbag_total_cash=cashbag_total_cash,
            cashbag_total_upi=cashbag_total_upi,
            office_cash=office_cash,
            installments=installments,
            loans_disbursed=loans_disbursed,
            loan_commission=loan_commission,
            interest_total=interest_total,
            expenses=expenses,
            adjustments_add=adjustments_add,
            adjustments_minus=adjustments_minus,
            profit_loss_net=profit_loss_net,

            transactions=transactions
        )

    except Exception as e:

        traceback.print_exc()
        flash(f"Cashbag loading failed: {str(e)}", "danger")
        return redirect(url_for("village_page"))

    finally:

        cur.close()
        conn.close()


# ----------------------------------------------------
# ADD CASHBAG TRANSACTION
# ----------------------------------------------------

@app.route("/cashbag/add", methods=["POST"])
@login_required
def add_cashbag_transaction():

    # emp1/emp2 come as hidden fields from the cashbag form
    emp1 = request.form.get("emp1", type=int)
    emp2 = request.form.get("emp2", type=int)

    if not emp1:
        flash("Employee group context missing", "warning")
        return redirect(url_for("village_page"))

    # ── New schema fields ──
    txn      = request.form.get("txn", "").strip().upper()       # main category
    txn_sub  = request.form.get("txn_sub", "").strip().upper()   # sub-type (optional)
    txn_type = request.form.get("txn_type", "CASH").strip().upper()  # payment method

    amount = request.form.get("amount")
    notes  = request.form.get("notes", "").strip()
    username = session.get("username") or "Unknown"

    # Valid transaction categories
    allowed_txn = [
        "OFFICE_CASH",
        "EXPENSE",
        "ADJUSTMENT",
        "PROFIT_LOSS"
    ]

    # Valid expense sub-types
    allowed_txn_sub = [
        "PETROL", "SADAR", "SALARY", "ARA",
        "ROOM_RENT", "ROOM_RENT_ADVANCE", "BIKE", "OTHER_EXPENSES"
    ]

    # Valid adjustment directions
    allowed_adj_sub = ["ADD", "MINUS"]

    # Valid profit/loss sub-types
    allowed_pl_sub = ["PROFIT", "LOSS"]

    # Valid payment methods
    allowed_txn_type = ["CASH", "UPI"]

    # Build redirect URL back to cashbag page with pair params
    redirect_args = {"emp1": emp1}
    if emp2:
        redirect_args["emp2"] = emp2

    # Validate
    if txn not in allowed_txn:
        flash("Invalid transaction category", "danger")
        return redirect(url_for("cashbag", **redirect_args))  # type: ignore

    if txn == "EXPENSE" and txn_sub not in allowed_txn_sub:
        flash("Invalid expense sub-type", "danger")
        return redirect(url_for("cashbag", **redirect_args))  # type: ignore

    if txn == "ADJUSTMENT" and txn_sub not in allowed_adj_sub:
        flash("Invalid adjustment direction (must select Add or Minus)", "danger")
        return redirect(url_for("cashbag", **redirect_args))  # type: ignore

    if txn == "PROFIT_LOSS" and txn_sub not in allowed_pl_sub:
        flash("Invalid profit/loss type (must select Profit or Loss)", "danger")
        return redirect(url_for("cashbag", **redirect_args))  # type: ignore

    if txn == "OFFICE_CASH":
        txn_sub = ""  # No subtype needed for office cash

    if txn_type not in allowed_txn_type:
        txn_type = "CASH"

    try:
        amount = float(amount or 0)
        if amount <= 0:
            flash("Amount must be greater than zero", "warning")
            return redirect(url_for("cashbag", **redirect_args))  # type: ignore
    except Exception:
        flash("Invalid amount", "danger")
        return redirect(url_for("cashbag", **redirect_args))  # type: ignore

    txn_date_str = request.form.get("txn_date")
    created_at_val = None
    if txn_date_str:
        try:
            now = datetime.now()
            parsed_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
            created_at_val = parsed_date.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)
        except Exception:
            pass

    conn = get_pg_connection()
    cur = conn.cursor()

    try:

        if created_at_val:
            cur.execute("""
                INSERT INTO cashbag_transactions (
                    emp1,
                    emp2,
                    eid,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                emp1,
                emp2,
                session.get("eid"),
                txn,
                txn_sub or None,
                txn_type,
                amount,
                notes or None,
                username,
                created_at_val
            ))
        else:
            cur.execute("""
                INSERT INTO cashbag_transactions (
                    emp1,
                    emp2,
                    eid,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                emp1,
                emp2,
                session.get("eid"),
                txn,
                txn_sub or None,
                txn_type,
                amount,
                notes or None,
                username
            ))

        conn.commit()

        audit_log(
            action="cashbag_transaction_added",
            entity_type="cashbag_transaction",
            entity_id=emp1,
            details={
                "emp1":     emp1,
                "emp2":     emp2,
                "txn":      txn,
                "txn_sub":  txn_sub,
                "txn_type": txn_type,
                "amount":   amount,
                "notes":    notes
            }
        )

        flash("Cashbag entry added successfully", "success")

    except Exception as e:

        conn.rollback()
        traceback.print_exc()
        flash(f"Failed to add transaction: {str(e)}", "danger")

    finally:

        cur.close()
        conn.close()

    return redirect(url_for("cashbag", **redirect_args))  # type: ignore



@app.route("/api/village/update_employee_pair", methods=["POST"])
@login_required
@admin_required
def update_employee_pair():

    data = request.get_json()

    old_emp1 = data.get("old_emp1")
    old_emp2 = data.get("old_emp2")

    new_emp1 = data.get("new_emp1")
    new_emp2 = data.get("new_emp2")

    if old_emp1 == new_emp1 and old_emp2 == new_emp2:
        return jsonify(success=True)

    # Prevent duplicate employee assignment
    if (
        new_emp1
        and new_emp2
        and str(new_emp1) == str(new_emp2)
    ):
        return jsonify(
            success=False,
            error="Same employee cannot occupy both slots"
        )

    conn = get_pg_connection()
    cur = conn.cursor()

    try:

        # Check if target pair already exists
        cur.execute("""
            SELECT COUNT(*)
            FROM village
            WHERE
                COALESCE(emp1,-1) = COALESCE(%s,-1)
            AND COALESCE(emp2,-1) = COALESCE(%s,-1)
        """, (
            new_emp1,
            new_emp2
        ))

        existing_count = cur.fetchone()[0]

        if (existing_count > 0 and not (str(old_emp1) == str(new_emp1) and str(old_emp2) == str(new_emp2))):
            return jsonify(
                success=False,
                error="Employee pair already exists"
            )

        # Bulk update entire cluster
        cur.execute("""
            UPDATE village
            SET
                emp1 = %s,
                emp2 = %s
            WHERE
                COALESCE(emp1,-1) = COALESCE(%s,-1)
            AND COALESCE(emp2,-1) = COALESCE(%s,-1)
        """, (
            new_emp1,
            new_emp2,
            old_emp1,
            old_emp2
        ))

        updated_rows = cur.rowcount

        conn.commit()

        audit_log(
            action="update_employee_pair",
            entity_type="village_cluster",
            entity_id=f"{old_emp1}_{old_emp2}",
            details={
                "old_emp1": old_emp1,
                "old_emp2": old_emp2,
                "new_emp1": new_emp1,
                "new_emp2": new_emp2,
                "villages_updated": updated_rows
            }
        )

        return jsonify(
            success=True,
            villages_updated=updated_rows
        )

    except Exception as e:
        conn.rollback()

        return jsonify(
            success=False,
            error=str(e)
        )

    finally:
        cur.close()
        conn.close()

@app.template_filter('b64encode')
def b64encode_filter(data):
    if not data:
        return ""
    return base64.b64encode(data).decode('utf-8')

@app.template_filter('format_date_iso')
def format_date_iso_filter(value):
    return format_date_iso(value)


# ====================================================
# SELF-HOSTED APK DISTRIBUTION
# ====================================================
# APK files live in  <WorkingDirectory>/apk_releases/
# version.json  is the single source of truth.
# All download routes require a valid X-Mobile-Token —
# never exposed directly by Nginx.
# ====================================================

APK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apk_releases")
VERSION_JSON_PATH = os.path.join(APK_DIR, "version.json")


def _read_version_json():
    """Read version.json from disk. Returns dict or None."""
    try:
        with open(VERSION_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_version_json_atomic(data: dict):
    """Write version.json atomically (temp-file + os.replace) so gunicorn
    workers never read a half-written file."""
    os.makedirs(APK_DIR, exist_ok=True)
    tmp_path = VERSION_JSON_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, VERSION_JSON_PATH)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Mobile: check for update ─────────────────────────────────────────────────

@app.route("/api/mobile/app/version", methods=["GET"])
@limiter.limit("60 per hour")
def mobile_app_version():
    """
    GET /api/mobile/app/version
    Header: X-Mobile-Token: <token>
    Query:  current_version_code=<int>   (optional — used to compute upgrade_required)

    Returns version.json enriched with `upgrade_required` and `force_update_required`.
    Public metadata only — no APK binary.
    """
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return jsonify({"error": "missing token"}), 401

    token_data = verify_mobile_token(token)
    if not token_data:
        return jsonify({"error": "invalid or expired token"}), 401

    # Verify the employee, user, and device are still active
    device_id = request.args.get("device_id")
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        # Check employee activity
        cur.execute("SELECT is_active FROM employee WHERE eid = %s", (token_data.get("eid"),))
        emp_row = cur.fetchone()
        emp_active = emp_row[0] if emp_row else False

        # Check user account activity
        cur.execute("SELECT is_active FROM users WHERE id = %s", (token_data.get("user_id"),))
        user_row = cur.fetchone()
        user_active = user_row[0] if user_row else False

        # Check device activity and enforce hardware matching (Admins are exempt)
        device_active = True
        if token_data.get("level") and token_data.get("level").strip().lower() in ("j", "m", "s"):
            if device_id:
                cur.execute(
                    "SELECT device_id, is_active FROM user_devices WHERE user_id = %s",
                    (token_data.get("user_id"),)
                )
                dev_row = cur.fetchone()
                if not dev_row:
                    device_active = False  # Not registered
                else:
                    saved_device_id, dev_is_active = dev_row
                    if not dev_is_active:
                        device_active = False
                    elif saved_device_id == 'PENDING':
                        # First check-in, bind this device
                        cur.execute(
                            "UPDATE user_devices SET device_id = %s, last_active = NOW() WHERE user_id = %s AND device_id = 'PENDING'",
                            (device_id, token_data.get("user_id"))
                        )
                        conn.commit()
                    elif saved_device_id != device_id:
                        device_active = False  # Device mismatch!
                    else:
                        # Device matches, update last active
                        cur.execute(
                            "UPDATE user_devices SET last_active = NOW() WHERE user_id = %s AND device_id = %s",
                            (token_data.get("user_id"), device_id)
                        )
                        conn.commit()
            else:
                device_active = False  # device_id is required

        if not emp_active or not user_active or not device_active:
            # Log the trigger event
            cur.execute(
                """
                INSERT INTO device_wipe_audit (user_id, device_id, reason, ip_address)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    token_data.get("user_id"),
                    device_id or "unknown",
                    f"Revoked status: emp={emp_active}, user={user_active}, dev={device_active}",
                    request.remote_addr
                )
            )
            conn.commit()
            cur.close()
            conn.close()

            # Return 403 Forbidden with wipe action
            return jsonify({
                "status": "revoked",
                "action": "wipe_and_lock",
                "message": "Access to this device has been revoked by administration. All data has been wiped."
            }), 403

        cur.close()
        conn.close()
    except Exception as e:
        logger.error("version check: security validation failed: %s", e)
        # non-fatal on transient DB issues, but log it

    version_data = _read_version_json()
    if not version_data:
        return jsonify({"error": "no release published yet"}), 404

    # Determine if client needs to upgrade
    try:
        current_code = int(request.args.get("current_version_code", 0))
    except (ValueError, TypeError):
        current_code = 0

    latest_code = int(version_data.get("latest_version_code", 0))
    min_code    = int(version_data.get("min_supported_version_code", 0))

    upgrade_required     = latest_code > current_code
    force_update_required = (
        version_data.get("force_update", False)
        or current_code < min_code
    )

    return jsonify({
        **version_data,
        "upgrade_required": upgrade_required,
        "force_update_required": force_update_required,
    }), 200


# ── Mobile: authenticated APK download ───────────────────────────────────────

@app.route("/api/mobile/app/download/<version>", methods=["GET"])
@limiter.limit("60 per hour")
def mobile_app_download(version):
    """
    GET /api/mobile/app/download/<version>
    Header: X-Mobile-Token: <token>

    Streams the signed release APK after verifying:
      1. Valid active-employee token
      2. Requested version matches the latest published version
         (prevents re-downloading old/arbitrary versions)
    """
    token = request.headers.get("X-Mobile-Token")
    if not token:
        return jsonify({"error": "missing token"}), 401

    token_data = verify_mobile_token(token)
    if not token_data:
        return jsonify({"error": "invalid or expired token"}), 401

    # Verify employee still active
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT eid, is_active FROM employee WHERE eid = %s",
            (token_data.get("eid"),)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or not row[1]:
            return jsonify({"error": "employee account inactive"}), 403
        eid = row[0]
    except Exception as e:
        logger.error("download: employee lookup failed: %s", e)
        return jsonify({"error": "server error"}), 500

    # Validate requested version against published version.json
    version_data = _read_version_json()
    if not version_data:
        return jsonify({"error": "no release published"}), 404

    published_version = version_data.get("latest_version", "")
    if version != published_version:
        return jsonify({
            "error": "version not found",
            "latest_version": published_version
        }), 404

    # Locate the APK on disk
    apk_filename = f"sdfin-{version}.apk"
    apk_path = os.path.join(APK_DIR, apk_filename)

    if not os.path.isfile(apk_path):
        logger.error("download: APK file not found: %s", apk_path)
        return jsonify({"error": "APK file not found on server"}), 404

    # Audit log
    audit_log(
        action="apk_download",
        entity_type="apk_release",
        entity_id=version,
        details={
            "eid": eid,
            "version": version,
            "filename": apk_filename,
            "ip": request.remote_addr,
        },
        status="success"
    )

    return send_file(
        apk_path,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name=apk_filename,
    )


# ── Admin: publish a new APK release ─────────────────────────────────────────

@app.route("/api/admin/app/publish", methods=["POST"])
def admin_app_publish():
    """
    POST /api/admin/app/publish
    Requires active admin web session (session['role'] == 'admin').
    Multipart body:
      - apk_file        : the signed release APK
      - version         : e.g. "1.1.0"
      - version_code    : integer, e.g. 5
      - min_version_code: integer — oldest version still allowed to run
      - force_update    : "true" / "false"
      - release_notes   : plain text

    Workflow:
      1. Validate session and inputs
      2. Compute SHA-256 server-side
      3. Save APK as sdfin-<version>.apk in apk_releases/
      4. Atomically write version.json
      5. Audit log
    """
    # Auth: must be admin web session
    if session.get("role") not in ("admin", "superadmin"):
        return jsonify({"error": "admin access required"}), 403

    # --- Input validation ---
    version = (request.form.get("version") or "").strip()
    if not version or not all(c.isdigit() or c == "." for c in version):
        return jsonify({"error": "invalid version string"}), 400

    try:
        version_code = int(request.form.get("version_code", 0))
        if version_code <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "version_code must be a positive integer"}), 400

    try:
        min_version_code = int(request.form.get("min_version_code", version_code))
    except (ValueError, TypeError):
        min_version_code = version_code

    force_update = request.form.get("force_update", "false").lower() == "true"
    release_notes = (request.form.get("release_notes") or "").strip()

    apk_file = request.files.get("apk_file")
    if not apk_file:
        return jsonify({"error": "apk_file is required"}), 400

    original_filename = apk_file.filename or ""
    if not original_filename.lower().endswith(".apk"):
        return jsonify({"error": "file must be an APK (.apk)"}), 400

    # --- Save APK ---
    os.makedirs(APK_DIR, exist_ok=True)
    apk_filename = f"sdfin-{version}.apk"
    apk_path = os.path.join(APK_DIR, apk_filename)

    try:
        apk_file.save(apk_path)
    except Exception as e:
        logger.error("admin_app_publish: save failed: %s", e)
        return jsonify({"error": "failed to save APK"}), 500

    # --- Compute SHA-256 ---
    try:
        sha256_hex = _sha256_file(apk_path)
    except Exception as e:
        logger.error("admin_app_publish: sha256 failed: %s", e)
        return jsonify({"error": "failed to compute checksum"}), 500

    # --- Write version.json atomically ---
    download_url = f"https://sivadurga.in/api/mobile/app/download/{version}"
    version_payload = {
        "latest_version": version,
        "latest_version_code": version_code,
        "min_supported_version_code": min_version_code,
        "force_update": force_update,
        "sha256": sha256_hex,
        "url": download_url,
        "release_notes": release_notes,
        "released_at": datetime.now(timezone.utc).isoformat(),
        "published_by": session.get("username", "unknown"),
    }

    try:
        _write_version_json_atomic(version_payload)
    except Exception as e:
        logger.error("admin_app_publish: version.json write failed: %s", e)
        return jsonify({"error": "failed to update version manifest"}), 500

    # --- Audit ---
    audit_log(
        action="apk_published",
        entity_type="apk_release",
        entity_id=version,
        details={
            "version": version,
            "version_code": version_code,
            "sha256": sha256_hex,
            "force_update": force_update,
            "release_notes": release_notes,
        },
        status="success"
    )

    logger.info(
        "APK published: %s (versionCode=%s, sha256=%s, force=%s)",
        version, version_code, sha256_hex[:16] + "…", force_update
    )

    # Broadcast instant OTA notification to all connected mobile clients
    try:
        broadcast_submission_event(None, {
            "type": "app_update",
            "version": version,
            "version_code": version_code,
            "min_version_code": min_version_code,
            "force_update": force_update,
            "release_notes": release_notes,
            "url": download_url,
            "sha256": sha256_hex
        })
    except Exception as _b_err:
        logger.error("admin_app_publish: SSE broadcast failed: %s", _b_err)

    return jsonify({
        "success": True,
        "version": version,
        "version_code": version_code,
        "sha256": sha256_hex,
        "url": download_url,
        "force_update": force_update,
    }), 201


# ── Admin: list published releases ───────────────────────────────────────────

@app.route("/api/admin/app/releases", methods=["GET"])
def admin_app_releases():
    """
    GET /api/admin/app/releases
    Admin session only. Returns current version.json and list of APK files on disk.
    """
    if session.get("role") not in ("admin", "superadmin"):
        return jsonify({"error": "admin access required"}), 403

    version_data = _read_version_json()

    apk_files = []
    if os.path.isdir(APK_DIR):
        for fname in sorted(os.listdir(APK_DIR)):
            if fname.endswith(".apk"):
                fpath = os.path.join(APK_DIR, fname)
                apk_files.append({
                    "filename": fname,
                    "size_bytes": os.path.getsize(fpath),
                    "modified_at": datetime.fromtimestamp(
                        os.path.getmtime(fpath), tz=timezone.utc
                    ).isoformat(),
                })

    return jsonify({
        "current_version": version_data,
        "apk_files": apk_files,
    }), 200


# ── Admin: generate private download link ────────────────────────────────────

# ── Admin: generate private download link ────────────────────────────────────

@app.route("/admin/generate_download_link", methods=["POST"])
def generate_download_link():
    """
    POST /admin/generate_download_link
    Requires admin web session (level: admin/mgmt/superadmin).
    Expects JSON body:
      - employee_id: int
    Generates a cryptographically signed token valid for 30 minutes.
    """
    if session.get("level") not in ("admin", "superadmin"):
        return jsonify({"error": "admin access required"}), 403

    data = request.json or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        return jsonify({"error": "employee_id is required"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Verify employee exists and is active
        cur.execute("SELECT name, is_active, phone_number FROM employee WHERE eid = %s", (employee_id,))
        emp = cur.fetchone()
        if not emp:
            return jsonify({"error": "employee not found"}), 404
        if not emp[1]:
            return jsonify({"error": "employee account is disabled"}), 400

        # Generate signed token with 30-minute expiration (1800 seconds)
        expiry = (datetime.now(timezone.utc) + timedelta(seconds=1800)).isoformat()
        token_payload = {
            "eid": int(employee_id),
            "exp": expiry
        }
        signed_token = serializer.dumps(token_payload)

        # Make the full portal URL
        portal_url = url_for("app_portal", token=signed_token, _external=True)

        audit_log(
            action="app_download_link_generated",
            entity_type="employee",
            entity_id=employee_id,
            details={
                "target_employee": emp[0],
                "expiry": expiry
            },
            status="success"
        )

        return jsonify({
            "success": True,
            "url": portal_url,
            "expires_at": expiry,
            "phone": emp[2] or ""
        }), 200

    except Exception as e:
        logger.error("generate_download_link error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ── App Download Portal landing & self-registration ────────────────────────────

@app.route("/app/portal", methods=["GET"])
def app_portal():
    """
    GET /app/portal?token=<signed_token> (or session fallback)
    Secured landing page that allows employee self-registration and APK download.
    """
    token = request.args.get("token")
    token_eid = None

    if token:
        try:
            payload = serializer.loads(token)
            token_eid = int(payload.get("eid"))
            exp_str = payload.get("exp")
            
            # Check expiration
            exp_dt = datetime.fromisoformat(exp_str)
            if datetime.now(timezone.utc) > exp_dt:
                flash("This installation link has expired (links are valid for 30 minutes). Please request a new link from your administrator.", "danger")
                return redirect(url_for("login"))
                
            # Cache valid token in session
            session["download_token_eid"] = token_eid
            session["download_token_expiry"] = exp_str
            session["download_token_str"] = token
            
        except Exception as e:
            logger.warning("app_portal: invalid token signature: %s", e)
            flash("Invalid or corrupted installation link. Please contact your administrator.", "danger")
            return redirect(url_for("login"))
    else:
        token_eid = session.get("download_token_eid")
        exp_str = session.get("download_token_expiry")
        token = session.get("download_token_str")
        if token_eid and exp_str:
            try:
                exp_dt = datetime.fromisoformat(exp_str)
                if datetime.now(timezone.utc) > exp_dt:
                    session.pop("download_token_eid", None)
                    session.pop("download_token_expiry", None)
                    session.pop("download_token_str", None)
                    flash("This installation link has expired. Please request a new link.", "danger")
                    return redirect(url_for("login"))
            except Exception:
                token_eid = None

    user_id = session.get("user_id")
    user_level = session.get("level")
    session_eid = session.get("employee_id")

    if user_level in ("admin", "mgmt", "superadmin"):
        session["download_authorized"] = True

    if not token_eid and not user_id:
        flash("Web access denied. A valid installation link is required.", "danger")
        return redirect(url_for("login"))

    target_eid = token_eid or session_eid

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT eid, name, phone_number, level, is_active FROM employee WHERE eid = %s", (target_eid,))
        emp_row = cur.fetchone()
        if not emp_row or not emp_row[4]:
            flash("Employee account not found or disabled.", "danger")
            return redirect(url_for("login"))

        emp_data = {
            "eid": emp_row[0],
            "name": emp_row[1],
            "phone": emp_row[2] or "N/A",
            "level": emp_row[3] or "staff"
        }

        # Check if user account already exists for this employee
        cur.execute("SELECT id, username FROM users WHERE employee_id = %s", (target_eid,))
        user_row = cur.fetchone()

        version_data = _read_version_json() or {}
        apk_size = "Unknown"
        if version_data:
            version = version_data.get("latest_version")
            apk_path = os.path.join(APK_DIR, f"sdfin-{version}.apk")
            if os.path.isfile(apk_path):
                size_mb = os.path.getsize(apk_path) / (1024 * 1024)
                apk_size = f"{size_mb:.1f} MB"

        # If user account does not exist, render Self-Registration state
        if not user_row:
            return render_template(
                "portal.html",
                registration_mode=True,
                employee=emp_data,
                token=token or "",
                version=version_data.get("latest_version", "N/A"),
                size=apk_size,
                notes=version_data.get("release_notes", "No release notes available.")
            )

        # If user account exists, authorize download
        session["download_authorized"] = True
        return render_template(
            "portal.html",
            registration_mode=False,
            employee=emp_data,
            user_account=user_row[1],
            token=token or "",
            version=version_data.get("latest_version", "N/A"),
            size=apk_size,
            notes=version_data.get("release_notes", "No release notes available."),
            released_at=version_data.get("released_at", ""),
            force_update=version_data.get("force_update", False)
        )
    finally:
        cur.close()
        conn.close()


@app.route("/app/portal/register", methods=["POST"])
@csrf.exempt
def app_portal_register():
    """
    POST /app/portal/register
    Allows employee to create their username and password via link.
    """
    token = request.form.get("token") or session.get("download_token_str")
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not token:
        flash("Installation link token missing.", "danger")
        return redirect(url_for("login"))

    try:
        payload = serializer.loads(token)
        eid = int(payload.get("eid"))
        exp_str = payload.get("exp")
        exp_dt = datetime.fromisoformat(exp_str)
        if datetime.now(timezone.utc) > exp_dt:
            flash("This installation link has expired. Request a new link from your administrator.", "danger")
            return redirect(url_for("login"))
    except Exception as e:
        logger.warning("app_portal_register: invalid token: %s", e)
        flash("Invalid or corrupted installation link.", "danger")
        return redirect(url_for("login"))

    if not username or len(username) < 3:
        flash("Username must be at least 3 characters long.", "danger")
        return redirect(url_for("app_portal", token=token))

    if not password or len(password) < 4:
        flash("Password must be at least 4 characters long.", "danger")
        return redirect(url_for("app_portal", token=token))

    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("app_portal", token=token))

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Check if username is already taken
        cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        if cur.fetchone():
            flash(f"Username '{username}' is already taken. Please choose another username.", "danger")
            return redirect(url_for("app_portal", token=token))

        # Verify employee exists and does not already have a user
        cur.execute("SELECT eid, name, level, is_active FROM employee WHERE eid = %s", (eid,))
        emp_row = cur.fetchone()
        if not emp_row or not emp_row[3]:
            flash("Employee account not found or disabled.", "danger")
            return redirect(url_for("login"))

        cur.execute("SELECT id FROM users WHERE employee_id = %s", (eid,))
        if cur.fetchone():
            flash("An account already exists for this employee. Please log in.", "info")
            return redirect(url_for("app_portal", token=token))

        # Create user account
        hashed = generate_password_hash(password, method="pbkdf2:sha256")
        cur.execute("""
            INSERT INTO users (username, password_hash, employee_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (username, hashed, eid))
        new_user_id = cur.fetchone()[0]

        # Assign village access for assigned employee
        cur.execute("SELECT vid FROM village WHERE emp1 = %s OR emp2 = %s", (eid, eid))
        for v in cur.fetchall():
            cur.execute("""
                INSERT INTO user_village_access (user_id, village_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (new_user_id, v[0]))

        conn.commit()

        # Set session login
        session["user_id"] = new_user_id
        session["username"] = username
        session["level"] = (emp_row[2] or "staff").lower()
        session["employee_id"] = eid
        session["download_authorized"] = True

        audit_log(
            action="user_self_registered_via_link",
            entity_type="user",
            entity_id=new_user_id,
            details={
                "username": username,
                "employee_id": eid,
                "employee_name": emp_row[1]
            },
            status="success"
        )

        flash("Account created successfully! You can now download the app.", "success")
        return redirect(url_for("app_portal", token=token))

    except Exception as e:
        conn.rollback()
        logger.error("app_portal_register exception: %s", e)
        flash(f"Failed to create account: {str(e)}", "danger")
        return redirect(url_for("app_portal", token=token))
    finally:
        cur.close()
        conn.close()


# ── Secure download stream endpoint ──────────────────────────────────────────

@app.route("/app/download-action", methods=["GET"])
def app_download_action():
    """
    GET /app/download-action
    Verifies that the request has an active authorized session (admin/mgmt or download_authorized)
    OR a valid, non-expired temporary installation link token.
    """
    user_level = session.get("level")
    is_authorized = session.get("download_authorized") == True

    # Validate token if present in query parameter or session
    token = request.args.get("token") or session.get("download_token_str")
    target_eid = session.get("employee_id") or session.get("download_token_eid")

    if token and not is_authorized:
        try:
            payload = serializer.loads(token)
            token_eid = int(payload.get("eid"))
            exp_str = payload.get("exp")
            exp_dt = datetime.fromisoformat(exp_str)
            if datetime.now(timezone.utc) <= exp_dt:
                is_authorized = True
                target_eid = token_eid
                session["download_authorized"] = True
                session["download_token_eid"] = token_eid
                session["download_token_expiry"] = exp_str
                session["download_token_str"] = token
        except Exception as e:
            logger.warning("app_download_action invalid token: %s", e)

    if user_level not in ("admin", "mgmt", "superadmin") and not is_authorized:
        flash("Access denied. A valid installation link is required.", "danger")
        return redirect(url_for("login"))

    version_data = _read_version_json()
    if not version_data:
        return "No release published", 404

    version = version_data.get("latest_version")
    apk_filename = f"sdfin-{version}.apk"
    apk_path = os.path.join(APK_DIR, apk_filename)

    if not os.path.isfile(apk_path):
        return "APK file not found on server", 404

    # Log the download event
    audit_log(
        action="web_apk_download",
        entity_type="apk_release",
        entity_id=version,
        details={
            "employee_id": target_eid,
            "username": session.get("username"),
            "level": user_level,
            "ip": request.remote_addr,
        },
        status="success"
    )

    response = send_file(
        apk_path,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name=apk_filename,
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "true").strip().lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=debug_mode)

