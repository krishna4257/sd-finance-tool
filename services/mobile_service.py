import logging
from decimal import Decimal
from datetime import datetime
from db import get_pg_connection

logger = logging.getLogger(__name__)


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


def get_resolved_pg_connection():
    get_conn = _resolve_func("get_pg_connection", get_pg_connection)
    return get_conn()


def to_decimal(value, default="0.00"):
    """Convert any numeric, string, or currency input to a precise Decimal."""
    if value is None or value == "":
        return Decimal(str(default))
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    clean = str(value).replace(",", "").replace("₹", "").replace("$", "").strip()
    try:
        return Decimal(clean)
    except Exception:
        return Decimal(str(default))


def normalize_account_number(value):
    """Normalize account number to integer or None."""
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
    normalized = dict(source)

    normalized["ano"] = normalize_account_number(normalized.get("ano"))
    normalized["vid"] = normalize_account_number(normalized.get("vid"))
    normalized["eid"] = normalize_account_number(normalized.get("eid"))
    normalized["pano"] = normalize_account_number(normalized.get("pano"))

    base_amount = to_decimal(normalized.get("base_amount"))
    cutting_amount = to_decimal(normalized.get("cutting_amount"))
    interest_amount = to_decimal(normalized.get("interest_amount"))
    total_amount = to_decimal(normalized.get("total_amount"))

    normalized["base_amount"] = base_amount
    normalized["cutting_amount"] = cutting_amount
    normalized["interest_amount"] = interest_amount
    normalized["total_amount"] = total_amount

    if total_amount > 0:
        component_sum = base_amount + cutting_amount + interest_amount
        if component_sum > 0 and component_sum != total_amount:
            logger.warning(
                "Customer ano=%s total_amount=%s does not equal base+cutting+interest=%s",
                normalized.get("ano"),
                total_amount,
                component_sum,
            )

    loan_type = normalized.get("type")
    if loan_type == "weekly":
        normalized["type"] = "W"
    elif loan_type == "monthly":
        normalized["type"] = "M"

    normalized["paid_amount"] = to_decimal(normalized.get("paid_amount"))
    if normalized.get("balance_amount") is None and total_amount > 0:
        normalized["balance_amount"] = total_amount - normalized["paid_amount"]
    elif normalized.get("balance_amount") is not None:
        normalized["balance_amount"] = to_decimal(normalized.get("balance_amount"))

    return normalized


def normalize_mobile_payment_payload(payload):
    """Normalize payment payload from mobile app to match DB column names."""
    if not isinstance(payload, dict):
        raise ValueError("Invalid payment payload")

    normalized = dict(payload)

    payment_type = (normalized.get("payment_type") or "cash").lower().strip()
    if payment_type not in ("cash", "upi", "partial"):
        payment_type = "cash"

    amt = to_decimal(normalized.get("amt"))

    cash_raw = normalized.get("cash_amount", normalized.get("cash_amt"))
    upi_raw = normalized.get("upi_amount", normalized.get("upi_amt"))

    if payment_type == "cash":
        cash_amount = amt
        upi_amount = Decimal("0.00")
    elif payment_type == "upi":
        cash_amount = Decimal("0.00")
        upi_amount = amt
    else:
        cash_amount = to_decimal(cash_raw)
        upi_amount = to_decimal(upi_raw)
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
    normalized["amt"] = amt
    normalized["cash_amount"] = cash_amount
    normalized["upi_amount"] = upi_amount
    normalized["payment_date"] = payment_date.isoformat()
    normalized.pop("pdate", None)
    normalized.pop("cash_amt", None)

    return normalized


def add_sse_subscriber(vid, q):
    pass


def remove_sse_subscriber(vid, q):
    pass


def broadcast_submission_event(vid, event_data):
    """Deprecated: Status updates are written to PostgreSQL and fetched via polling."""
    pass


def ensure_feed_tables_exist(cur):
    """Ensure customer_feed_edits and payment_feed_edits tables exist."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_feed_edits (
            edit_id SERIAL PRIMARY KEY,
            local_uuid TEXT NOT NULL,
            edited_payload JSONB NOT NULL,
            edited_at TIMESTAMPTZ DEFAULT NOW(),
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (local_uuid)
        );
        CREATE TABLE IF NOT EXISTS payment_feed_edits (
            edit_id SERIAL PRIMARY KEY,
            local_uuid TEXT NOT NULL,
            edited_payload JSONB NOT NULL,
            edited_at TIMESTAMPTZ DEFAULT NOW(),
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (local_uuid)
        );
    """)


def ensure_user_devices_table(cur):
    """Ensure user_devices table has device_model and real-time telemetry columns."""
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
        ALTER TABLE user_devices 
            ADD COLUMN IF NOT EXISTS device_model TEXT,
            ADD COLUMN IF NOT EXISTS latest_latitude DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS latest_longitude DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS latest_speed REAL DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS latest_heading REAL DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS latest_accuracy REAL,
            ADD COLUMN IF NOT EXISTS latest_battery_pct SMALLINT,
            ADD COLUMN IF NOT EXISTS is_charging BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS gps_status VARCHAR(20) DEFAULT 'active';
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_devices_user_device 
        ON user_devices (user_id, device_id)
    """)
    try:
        cur.execute("""
            UPDATE user_devices
            SET is_active = FALSE
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY user_id, COALESCE(device_model, 'unknown')
                               ORDER BY last_active DESC NULLS LAST, id DESC
                           ) as rn
                    FROM user_devices
                    WHERE is_active = TRUE AND device_id != 'PENDING'
                ) sub
                WHERE rn > 1
            );
        """)
    except Exception:
        pass


def ensure_location_tables(cur):
    """Ensure user_locations and user_daily_trips tables exist with proper B-Tree indexes."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_locations (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            device_id VARCHAR(64) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            accuracy REAL,
            speed REAL DEFAULT 0.0,
            heading REAL DEFAULT 0.0,
            battery_pct SMALLINT,
            is_charging BOOLEAN DEFAULT FALSE,
            activity_type VARCHAR(20) DEFAULT 'unknown',
            recorded_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_user_locations_user_recorded 
        ON user_locations (user_id, recorded_at DESC);
        CREATE INDEX IF NOT EXISTS idx_user_locations_recorded_at 
        ON user_locations (recorded_at);

        CREATE TABLE IF NOT EXISTS user_daily_trips (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            trip_date DATE NOT NULL,
            total_distance_km NUMERIC(8, 2) DEFAULT 0.00,
            travel_minutes INTEGER DEFAULT 0,
            stop_minutes INTEGER DEFAULT 0,
            stop_count INTEGER DEFAULT 0,
            first_ping_at TIMESTAMPTZ,
            last_ping_at TIMESTAMPTZ,
            battery_start_pct SMALLINT,
            battery_end_pct SMALLINT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (user_id, trip_date)
        );
        CREATE INDEX IF NOT EXISTS idx_user_daily_trips_user_date 
        ON user_daily_trips (user_id, trip_date DESC);
    """)
