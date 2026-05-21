import os
import traceback
import logging
import uuid
import platform
import base64
import hashlib
import json
from functools import wraps
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from flask import (
    Flask, render_template, request, redirect,
    session, jsonify, flash, url_for
)
from db import get_pg_connection, get_pool_stats
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from psycopg2.extras import execute_values
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
def log_db_pool_stats(context=""):
    try:
        stats = get_pool_stats()

        logger.info(
            "DB Pool Stats%s -> used=%s available=%s max=%s",
            f" [{context}]" if context else "",
            stats.get("used_connections"),
            stats.get("available_connections"),
            stats.get("max_connections")
        )

    except Exception as e:
        logger.warning("Unable to fetch DB pool stats: %s", e)


def generate_system_id():
    """Generate stable system fingerprint."""
    machine_id = hex(uuid.getnode())
    os_info = platform.platform()
    processor = platform.processor()
    uname = platform.uname()._asdict()

    combined = json.dumps({
        "machine_id": machine_id,
        "os_info": os_info,
        "processor": processor,
        "uname": uname
    }, sort_keys=True)

    hash_bytes = hashlib.sha256(combined.encode()).digest()
    return base64.b64encode(hash_bytes).decode()

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
# ----------------------------------------------------
# FLASK APP SETUP
# ----------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")

secret_key = os.environ.get("SECRET_KEY")

if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set")

app.secret_key = secret_key

app.config["WTF_CSRF_ENABLED"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=3)

# Secure session cookie settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Only force secure cookies in production HTTPS deployments
# Local development on http://127.0.0.1:8080 must keep this disabled,
# otherwise Flask cannot store the session cookie and CSRF fails.
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"

csrf = CSRFProtect(app)
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

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


@app.before_request
def fix_cookie_domain():
    host = request.headers.get("Host", "")
    # Allow both domains
    if "sivadurga.in" in host:
        app.config["SESSION_COOKIE_DOMAIN"] = ".sivadurga.in"
    else:
        # Allows Cloud Run direct link to work
        app.config["SESSION_COOKIE_DOMAIN"] = None

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

    return response


# ----------------------------------------------------
# Session timeout and activity tracking
# ----------------------------------------------------
@app.before_request
def session_timeout_check():

    if "user_id" not in session:
        return

    now = datetime.utcnow()
    last_activity = session.get("_last_activity")

    if last_activity:
        try:
            last_activity_dt = datetime.fromisoformat(last_activity)

            if now - last_activity_dt > app.config["PERMANENT_SESSION_LIFETIME"]:
                session.clear()
                flash("Session expired. Please login again.", "warning")
                return redirect(url_for("login"))

        except Exception:
            session.clear()
            return redirect(url_for("login"))

    session["_last_activity"] = now.isoformat()

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)
# ----------------------------------------------------
# Decorators
# ----------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        level = session.get("level")

        if not user_id:
            flash("Please login", "danger")
            return redirect(url_for("login"))

        # Only admin and mgmt allowed
        if level not in ["admin", "mgmt"]:
            flash("Access denied", "danger")
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)
    return wrapper


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
                    SELECT vid, village_name
                    FROM village
                    WHERE (emp1 = %s OR emp2 = %s)
                      AND status = 'active'
                    ORDER BY village_name
                """, (eid, eid))
            else:
                cur.execute("""
                    SELECT vid, village_name
                    FROM village WHERE status = 'active'
                    ORDER BY village_name
                """)

        # s / m / j → only assigned villages
        else:
            if not user_villages:
                return jsonify([])

            cur.execute("""
                SELECT vid, village_name
                FROM village
                WHERE vid = ANY(%s)
                  AND status = 'active'
                ORDER BY village_name
            """, (user_villages,))

        rows = cur.fetchall()

        return jsonify([
            {"vid": r[0], "name": r[1]}
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
        "vid": session.get("vid")
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
        SELECT emp1, village_name
        FROM village
        WHERE vid = %s
          AND status = 'active'
    """, (vid,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify(success=False, error="Inactive or invalid village"), 400

    eid = row[0]
    village_name = row[1]

    # fetch employee name
    cur.execute("SELECT name FROM employee WHERE eid = %s", (eid,))
    result = cur.fetchone()
    employee_name = result[0] if result else "Unknown"

    # store session
    session["vid"] = vid
    session["eid"] = eid
    session["village_name"] = village_name
    session["employee_name"] = employee_name

    cur.close()
    conn.close()
    return jsonify(success=True)

@app.route("/reset_context", methods=["POST"])
@login_required
def reset_context():
    session.pop("eid", None)
    session.pop("vid", None)
    session.pop("village_name", None)
    session.pop("employee_name", None)
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
            created_at, source_file, status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NULL,'active')
    """, (
        vid,
        data["village_code"],
        data["village_name"],
        data["district"],
        data["pincode"],
        state,
        data["emp1_eid"],
        data.get("emp2_eid")
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
        # 1️⃣ Get next EID
        cur.execute("SELECT COALESCE(MAX(eid), 0) + 1 FROM employee")
        result = cur.fetchone()
        if not result:
            return jsonify(success=False, error="Failed to generate EID"), 500
        new_eid = result[0]

        phone_number = (data.get("phone_number") or "").strip()

        # 🔒 Prevent duplicate employee name + phone combinations
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
            data.get("level"),
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


def get_customer_info_by_ano(ano, vid):
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            name,
            total_amount,
            paid_amount,
            balance_amount,
            installment_amount
        FROM customer
        WHERE ano = %s AND vid = %s
    """, (ano, vid))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "name": row[0],
        "amt": float(row[1] or 0),
        "pamt": float(row[2] or 0),
        "bamt": float(row[3] or 0),
        "da": float(row[4] or 0)
    }

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

def get_all_customers_by_context(vid):
    conn = get_pg_connection()
    cur = conn.cursor()

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
  phone_number
FROM customer
WHERE vid = %s
ORDER BY ano;
    """, (vid, ))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    customers = []
    for r in rows:
        customers.append({
            "cid": r[0],
            "ano": r[1],
            "name": r[2],
            "vid": r[3],
            "start_date": r[4],
            "end_date": r[5],
            "total_amount": float(r[6] or 0),
            "paid_amount": float(r[7] or 0),
            "balance_amount": float(r[8] or 0),
            "installment_amount": float(r[9] or 0),
            "type": r[10],
            "period": r[11],
            "pano": r[12],
            "created_at": r[13],
            "aadhaar_number": r[14],
            "notes": r[15],
            "latitude": r[16],
            "longitude": r[17],
            "eid": r[18],
            "phone_number": r[19]
        })

    return customers


def customer_exists_by_ano(ano: int) -> bool:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM customer WHERE ano = %s LIMIT 1", (ano,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def get_highest_ano() -> int:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(CAST(ano AS INTEGER)) FROM customer;")
    result = cur.fetchone()
    highest = result[0] if result else 0
    cur.close()
    conn.close()
    return highest

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

def insert_customer(data):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO customer (
                    ano, name, pano, vid, eid,
                    start_date, end_date,
                    total_amount, paid_amount, balance_amount, installment_amount,
                    type, period,
                    aadhaar_number, notes,
                    latitude, longitude,phone_number,
                    status
                )
                VALUES (
                    %(ano)s, %(name)s, %(pano)s, %(vid)s, %(eid)s,
                    %(start_date)s, %(end_date)s,
                    %(total_amount)s, %(paid_amount)s, %(balance_amount)s, %(installment_amount)s,
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

def recalc_customer_balance(cur, cid):
    cur.execute("SELECT total_amount FROM customer WHERE cid = %s", (cid,))
    row = cur.fetchone()
    if not row:
        return

    total_amt = row[0]

    cur.execute("""
        SELECT COALESCE(SUM(amt), 0)
        FROM payment
        WHERE cid = %s
    """, (cid,))

    paid_amt = cur.fetchone()[0]
    balance_amt = total_amt - paid_amt

    cur.execute("""
        UPDATE customer
        SET paid_amount = %s,
            balance_amount = %s
        WHERE cid = %s
    """, (paid_amt, balance_amt, cid))
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
            SELECT v.vid, v.village_name, v.district
            FROM user_village_access uva
            JOIN village v ON v.vid = uva.village_id
            WHERE uva.user_id = %s
            ORDER BY v.village_name
        """, (user_id,))

        villages = cur.fetchall()

        return {
            "villages": [
                {
                    "vid": v[0],
                    "village_name": v[1],
                    "district": v[2],
                    "employee_name": employee_name
                }
                for v in villages
            ]
        }
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
        data = json.loads(payload_json) # type: ignore

        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC'")

        local_uuid = data.get("local_uuid")
        device_id = data.get("device_id", "mobile")
        eid = data.get("eid")
        vid = data.get("vid")
        status = data.get("status", "pending")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        gps_accuracy = data.get("gps_accuracy")
        
        customer_payload = data.get("payload")

        if isinstance(customer_payload, str):
           customer_payload = json.loads(customer_payload)
        ano = customer_payload.get("ano")
        payload = json.dumps(customer_payload)
        logger.debug("Customer feed received for vid=%s ano=%s", vid, ano)
        # 1️⃣ Insert into customer_feed
        cur.execute("""
            INSERT INTO customer_feed
            (local_uuid, device_id, eid, vid, status, payload, latitude, longitude, gps_accuracy)
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
        aadhaar_file = request.files.get("aadhaar_photo")
        house_file = request.files.get("house_photo")

        aadhaar_bytes = aadhaar_file.read() if aadhaar_file else None
        house_bytes = house_file.read() if house_file else None

        # 3️⃣ Insert into customer_docs
        if aadhaar_bytes or house_bytes:
            cur.execute("""
                INSERT INTO customer_docs (vid, ano, aadhaar_photo, house_photo)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (vid, ano)
                DO UPDATE SET
                    aadhaar_photo = EXCLUDED.aadhaar_photo,
                    house_photo = EXCLUDED.house_photo
            """, (
                vid,
                ano,
                aadhaar_bytes,
                house_bytes
            ))

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
                "status": status
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

        conn = get_pg_connection()
        cur = conn.cursor()

        total_records = len(payments)

        # insert each payment as JSON payload
        for p in payments:

            local_uuid = p.get("local_uuid")
            payload = json.dumps(p)

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

        # 🔐 Validate user + employee mapping and active status
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

        # 🚨 DELETE ALL DATA (SAFE ORDER USING TRUNCATE CASCADE)
        cur.execute("""
            TRUNCATE TABLE
                payment,
                closed_cust_payment,
                customer,
                closed_cust_account,
                customer_docs,
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

@app.route("/admin_control")
@login_required
@admin_required
def admin_control():
    return render_template("admin_control.html")

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

        fdt = datetime.strptime(data["start_date"], "%d/%m/%Y").date()
        period = int(data["period"])
        loan_type = data["type"]

        if loan_type == "M":
            tdt = fdt + relativedelta(months=period)
        else:
            tdt = fdt + timedelta(weeks=period)

        total_amount = float(data["total_amount"])
        installment_amount = round(total_amount / period, 2)
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
            "cid": cid
        })

    # GET
    highest_ano = get_highest_ano_by_vid(vid)

    return render_template(
        "add_customer.html",
        highest_ano=highest_ano,
        village_name=session.get("village_name"),
        employee_name=session.get("employee_name")
    )

@app.route("/view_customers")
@login_required
def view_customers():
    vid = session.get("vid")

    # ❗ Enforce context
    if not vid:
        flash("Please select Village from Dashboard first", "warning")
        return redirect(url_for("dashboard"))

    # 🔹 NEW: mode toggle (active / closed)
    mode = request.args.get("mode", "active")  # default = active

    conn = get_pg_connection()
    cur = conn.cursor()

    if mode == "closed":
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
                status
            FROM closed_cust_account
            WHERE vid = %s
            ORDER BY ano
        """, (vid,))
    elif mode == "yearly":
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
            'active' AS status
        FROM customer
        WHERE vid = %s

        UNION ALL

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
            status
        FROM closed_cust_account
        WHERE vid = %s
        AND LOWER(TRIM(status)) != 'written_off'
        ORDER BY ano

    """, (vid, vid))
    else:
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
                'active' AS status
            FROM customer
            WHERE vid = %s
            ORDER BY ano
        """, (vid,))

    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description] # type: ignore

    cur.close()
    conn.close()

    data = [dict(zip(headers, r)) for r in rows]

    # 🔹 Recalculate totals based on mode
    total_customers = len(data)
    sum_amt = sum(float(r["total_amount"] or 0) for r in data)
    sum_pamt = sum(float(r["paid_amount"] or 0) for r in data)
    sum_bamt = sum(float(r["balance_amount"] or 0) for r in data)

    return render_template(
        "view_customers.html",
        headers=headers,
        data=data,
        total_customers=total_customers,
        sum_amt=sum_amt,
        sum_pamt=sum_pamt,
        sum_bamt=sum_bamt,
        mode=mode  # 🔹 pass to frontend for toggle button
    )

@app.route("/check_ano_exists")
@login_required
def check_ano_exists():
    ano = request.args.get("ano", "").strip()
    vid = session.get("vid")

    if not ano or not vid:
        return jsonify({"exists": False})

    exists = customer_exists_by_ano_and_vid(ano, vid)
    return jsonify({"exists": exists})

@app.route("/post_payment_report", methods=["GET"])
@login_required
def post_payment_report():
    vid = session.get("vid")

    if not vid:
        flash("Please select Village first", "warning")
        return redirect(url_for("dashboard"))

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            pid,
            ano,
            payment_date,
            amt,
            created_at,
            eid,
            cid,
            vid,
            'active' AS payment_status
        FROM payment
        WHERE vid = %s

        UNION ALL

        SELECT
            pid,
            ano,
            payment_date,
            amt,
            created_at,
            eid,
            cid,
            vid,
            'closed' AS payment_status
        FROM closed_cust_payment
        WHERE vid = %s

        ORDER BY payment_date DESC, pid DESC
    """, (vid, vid))

    rows = cur.fetchall()
    # cur.description can be None for some drivers or edge cases; guard against that
    if cur.description:
        headers = [desc[0] for desc in cur.description]
    else:
        headers = ["pid", "ano", "payment_date", "amt", "created_at", "eid", "cid", "vid", "payment_status"]

    cur.close()
    conn.close()

    payments = [dict(zip(headers, r)) for r in rows]

    return render_template(
        "post_payment_report.html",
        headers=headers,
        payments=payments
    )

@app.route("/post_payment", methods=["GET"])
@login_required
def post_payment_page():
    vid = session.get("vid")

    if not vid:
        flash("Please select Village first", "warning")
        return redirect("/dashboard")

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            cid,
            ano,
            name,
            total_amount,
            paid_amount,
            balance_amount,
            installment_amount
        FROM customer
        WHERE vid = %s
    """, (vid,))

    customers = [
        dict(
            cid=r[0],
            ano=r[1],
            name=r[2],
            total_amount=r[3],
            paid_amount=r[4],
            balance_amount=r[5],
            installment_amount=r[6],
        )
        for r in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return render_template("post_payment.html", customers=customers)

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
        payment_date = datetime.strptime(date_str, "%d/%m/%Y").date()
    except Exception:
        return jsonify({"error": "Invalid date"}), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:

        cur.execute("""

            WITH village_collection_day AS (

                SELECT DISTINCT ON (p.vid)

                    p.vid,

                    TRIM(TO_CHAR(p.payment_date, 'Day'))
                        AS collection_day,

                    COUNT(*) AS payment_count

                FROM payment p

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

                FROM customer c
                JOIN village_collection_day vcd
                    ON vcd.vid = c.vid

                WHERE c.vid = %s
                  AND c.type = 'W'

                  AND (
                        c.start_date + INTERVAL '7 days'
                      )::date <= %s

                  AND TRIM(TO_CHAR(%s::date, 'Day'))
                      = vcd.collection_day
            ),

            actual_payments AS (

                SELECT
                    COUNT(DISTINCT ano) AS paid_accounts

                FROM payment

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

    try:
        for row in rows:
            ano = normalize_account_number(row.get("ano"))
            amt = Decimal(str(row["amt"]))
            payment_date = datetime.strptime(row["pdt"], "%d/%m/%Y").date()

            # 🔹 Fetch customer
            cur.execute("""
                SELECT cid, total_amount, paid_amount
                FROM customer
                WHERE vid = %s AND ano = %s
            """, (vid, ano))

            cust = cur.fetchone()
            if not cust:
                skipped.append(row)
                continue

            cid, total_amt, paid_amt = cust

            total_amt = Decimal(total_amt)
            paid_amt = Decimal(paid_amt or 0)

            # 🔹 Insert payment (pid auto-generated)
            cur.execute("""
                INSERT INTO payment (cid, vid, eid, ano, amt, payment_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cid, vid, eid, ano, amt, payment_date))

            # 🔹 Recalculate balances (centralized logic)
            recalc_customer_balance(cur, cid)

            submitted += 1

        conn.commit()

        audit_log(
            action="submit_post_payment",
            entity_type="payment",
            entity_id=vid,
            details={
                "eid": eid,
                "vid": vid,
                "submitted_count": submitted,
                "skipped_count": len(skipped)
            }
        )

        return jsonify( 
            success=True,
            message=f"{submitted} payments posted",
            skipped_rows=skipped
        )

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify(error=str(e)), 500

    finally:
        cur.close()
        conn.close()



@app.route("/search", methods=["GET", "POST"])
@login_required
def search_customer():
    vid = session.get("vid")

    if not vid:
        flash("Please select Village first", "warning")
        return redirect("/dashboard")

    customers = []
    pamt1_records = {}
    loanee_headers = [
        "cid", "ano", "name", "vid", "start_date", "end_date",
        "total_amount", "paid_amount",
        "balance_amount", "installment_amount",
        "type", "period","pano", "created_at","aadhaar_number","notes","latitude", "longitude","eid", "status",
        "updated_at","phone_number"
    ]

    if request.method == "POST":
        query = request.form.get("query", "").strip()

        conn = get_pg_connection()
        cur = conn.cursor()

        # 🔍 Search by A.no OR Name (within context), across both active and closed accounts
        cur.execute("""
            (
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
                    'active' AS status,
                    updated_at,
                    phone_number
                FROM customer
                WHERE vid = %s
                  AND (
                        CAST(ano AS TEXT) = %s
                        OR LOWER(name) LIKE LOWER(%s)
                  )
            )
            UNION ALL
            (
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
                    status,
                    NULL AS updated_at,
                    phone_number
                FROM closed_cust_account
                WHERE vid = %s
                  AND (
                        CAST(ano AS TEXT) = %s
                        OR LOWER(name) LIKE LOWER(%s)
                  )
            )
            ORDER BY ano
            LIMIT 1
        """, (vid, query, f"%{query}%", vid, query, f"%{query}%"))

        row = cur.fetchone()

        if row:
            cust = dict(zip(loanee_headers, row))
            customers = [cust]

            # 🔹 Fetch payments for this customer (from both payment and closed_cust_payment)
            cur.execute("""
                SELECT ano, payment_date, amt, pid
                FROM payment
                WHERE cid = %s

                UNION ALL

                SELECT ano, payment_date, amt, pid
                FROM closed_cust_payment
                WHERE cid = %s

                ORDER BY payment_date, pid
            """, (cust["cid"], cust["cid"]))

            pamt1_records[cust["ano"]] = cur.fetchall()

        cur.close()
        conn.close()

    return render_template(
        "search.html",
        customers=customers,
        loanee_headers=loanee_headers,
        pamt1_records=pamt1_records,
        query=request.form.get("query") if request.method == "POST" else ""
    )


@app.route("/api/customer_family_full/<account_no>")
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
                status
            FROM (
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
                    'active' AS status
                FROM customer
                WHERE vid = %s

                UNION ALL

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
                    status
                FROM closed_cust_account
                WHERE vid = %s
            ) all_customers
        """, (vid, vid))

        rows = cur.fetchall()

        family_map = {}
        customer_map = {}

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
                "status": row[20]
            }

            ano = customer["ano"]
            pano = customer["pano"]

            if ano.endswith(".0"):
                ano = ano[:-2]
                customer["ano"] = ano

            if pano.endswith(".0"):
                pano = pano[:-2]
                customer["pano"] = pano

            if not ano:
                continue

            customer_map[ano] = customer

            if ano not in family_map:
                family_map[ano] = set()

            if pano:

                if pano not in family_map:
                    family_map[pano] = set()

                family_map[ano].add(pano)
                family_map[pano].add(ano)

        visited = set()
        queue = [account_no]

        while queue:

            current = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            for linked in family_map.get(current, set()):

                if linked not in visited:
                    queue.append(linked)

        customers = []

        for acc in visited:

            customer = customer_map.get(str(acc).strip())

            if customer:
                customers.append(customer)

        customers = sorted(
            customers,
            key=lambda x: (
                0,
                int(str(x["ano"]).strip())
            ) if str(x["ano"]).strip().isdigit() else (
                1,
                str(x["ano"]).strip()
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
            WHERE CAST(ano AS TEXT) = %s
            LIMIT 1
        """, (vid, vid, str(ano)))

        customer = cur.fetchone()

        if not customer:
            return "Customer not found.", 404

        cur.execute("""
            SELECT
                ano,
                TO_CHAR(payment_date, 'DD/MM/YYYY') AS pdt,
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
            "start_date": customer[4],
            "end_date": customer[5],
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


@app.route("/search_postings", methods=["POST"])
@login_required
def search_postings():
    vid = session.get("vid")

    if not vid:
        return jsonify(success=False, error="No village selected"), 400

    data = request.get_json()

    if not data:
        return jsonify(success=False, error="No data received"), 400

    ano = str(data.get("ano", "")).strip()
    date = str(data.get("date", "")).strip()

    if not ano and not date:
        return jsonify(success=False, error="Provide A.no or Date"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                ano AS \"ANO\",
                TO_CHAR(payment_date, 'DD/MM/YYYY') AS \"PDT\",
                amt AS \"AMT\"
            FROM payment
            WHERE vid = %s
        """

        params = [vid]

        if ano:
            query += " AND CAST(ano AS TEXT) = %s"
            params.append(ano)

        if date:
            query += " AND TO_CHAR(payment_date, 'DD/MM/YYYY') = %s"
            params.append(date)

        query += " ORDER BY payment_date, pid"

        cur.execute(query, params)

        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()

        results = [dict(zip(columns, row)) for row in rows]

        return jsonify(success=True, data=results)

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

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
        action = data.get("action")  # 'defaulted' or 'written_off' or None

        if not cid:
            return jsonify({"success": False, "error": "Missing customer id"})

        conn = get_pg_connection()
        cur = conn.cursor()

        # 🔒 Lock row (prevents race conditions)
        cur.execute("""
            SELECT total_amount, paid_amount, balance_amount, status
            FROM customer
            WHERE cid = %s
            FOR UPDATE
        """, (cid,))

        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "Customer not found"})

        total_amount, paid_amount, balance_amount, current_status = row

        # -------------------------------
        # 🧠 STATUS DECISION LOGIC
        # -------------------------------
        if balance_amount == 0:
            final_status = "closed"

        elif balance_amount > 0:
            if action != "defaulted":
                conn.rollback()
                return jsonify({
                    "success": False,
                    "error": "Balance > 0. Must mark as defaulted."
                })
            final_status = "defaulted"

        else:  # balance_amount < 0
            if action != "written_off":
                conn.rollback()
                return jsonify({
                    "success": False,
                    "error": "Balance < 0. Must mark as written_off."
                })
            final_status = "written_off"

        # -------------------------------
        # 📦 MOVE DATA (NOT COPY)
        # -------------------------------

        # 1️⃣ Move customer (explicit columns to avoid mismatch)
        cur.execute("""
            INSERT INTO closed_cust_account (
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, status, phone_number,
                closed_by, closed_at
            )
            SELECT
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, %s, phone_number,
                %s, NOW() AT TIME ZONE 'Asia/Kolkata'
            FROM customer
            WHERE cid = %s
        """, (final_status, session.get("employee_id") or session.get("eid"), cid))

        # 2️⃣ Move payments (explicit columns)
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

        # 4️⃣ Delete from active tables (this makes it MOVE)
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
        cur = conn.cursor()

        # 1️⃣ Move customer BACK to customer table
        cur.execute("""
            INSERT INTO customer (
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, phone_number
            ) OVERRIDING SYSTEM VALUE
            SELECT
                cid, ano, name, vid,
                start_date, end_date,
                total_amount, paid_amount, balance_amount, installment_amount,
                type, period, created_at,
                aadhaar_number, notes,
                latitude, longitude, eid, phone_number
            FROM closed_cust_account
            WHERE cid = %s
        """, (cid,))

        # 2️⃣ Move payments BACK
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

        # 3️⃣ Delete from closed tables
        cur.execute("DELETE FROM closed_cust_payment WHERE cid = %s", (cid,))
        cur.execute("DELETE FROM closed_cust_account WHERE cid = %s", (cid,))

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

        # 🔒 Prevent duplicate village code / village name
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
        cur.execute("""
            UPDATE village
            SET
              village_code = %s,
              village_name = %s,
              emp1 = %s,
              emp2 = %s
            WHERE vid = %s
        """, (
            village_code,
            village_name,
            data.get("emp1"),
            data.get("emp2"),
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
        # CUSTOMER FEED
        cur.execute("""
            SELECT
                cf.feed_id,
                cf.payload,
                cf.status,
                cf.vid,
                (cf.payload->>'ano')::INT AS ano,
                cf.payload->>'name' AS name,
                cf.payload->>'type' AS type,
                cd.aadhaar_photo,
                cd.house_photo
            FROM customer_feed cf
            LEFT JOIN customer_docs cd
              ON cd.vid = cf.vid
             AND cd.ano = (cf.payload->>'ano')::INT
            WHERE cf.vid = %s AND cf.status='pending'
            ORDER BY cf.feed_id DESC
        """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore

        customers = []
        for r in rows:
            row_dict = dict(zip(columns, r))

            payload = row_dict.get("payload")

            # ✅ Normalize payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            elif payload is None:
                payload = {}

            # ✅ Flatten payload into row_dict (VERY IMPORTANT)
            row_dict.update({
                "ano": payload.get("ano"),
                "name": payload.get("name"),
                "pano": payload.get("pano"),
                "phone_number": payload.get("phone_number"),
                "type": payload.get("type"),
                "period": payload.get("period"),
                "start_date": payload.get("start_date"),
                "end_date": payload.get("end_date"),
                "total_amount": payload.get("total_amount"),
                "installment_amount": payload.get("installment_amount"),
                "aadhaar_number": payload.get("aadhaar_number"),
                "notes": payload.get("notes"),
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
                "eid": payload.get("eid"),
                "vid": payload.get("vid"),
            })

            # keep payload also (optional)
            row_dict["payload"] = payload

            customers.append(row_dict)
        # PAYMENT FEED
        cur.execute("""
        SELECT
            feed_payment_id,
            payload->>'ano' AS ano,
            payload->>'amt' AS amt,
            payload->>'pdate' AS pdt,
            payload->>'vid' AS vid,
            status
        FROM payment_feed_items
        WHERE status='pending'
          AND (payload->>'vid')::INT = %s
        ORDER BY feed_payment_id DESC
    """, (vid,))

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] # type: ignore

        payments = [dict(zip(columns, r)) for r in rows]

        return render_template(
            "feed.html",
            customers=customers,
            payments=payments
        )

    finally:
        cur.close()
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
        SELECT payload
        FROM customer_feed
        WHERE feed_id = %s
    """, (feed_id,))

    row = cur.fetchone()
    print("ROW:", row)

    if not row:
        return {"success": False, "error": "Feed not found"}
    
    data = row[0]     # type: ignore # JSON payload
    # Ensure payload is dict
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return {"success": False, "error": "Invalid payload format"}
    print("PAYLOAD:", data)
    loan_type = data.get("type")
    if loan_type == "weekly":
        loan_type = "W"
    elif loan_type == "monthly":
        loan_type = "M"

    cur.execute("""
        INSERT INTO customer
        (
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
            aadhaar_number,
            notes,
            latitude,
            longitude,
            eid,
            phone_number,
            status
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open')
    """,
    (
        data.get("ano"),
        data.get("name"),
        data.get("vid"),
        data.get("start_date"),
        data.get("end_date"),
        data.get("total_amount"),
        data.get("paid_amount"),
        data.get("balance_amount"),
        data.get("installment_amount"),
        loan_type,
        data.get("period"),
        data.get("pano"),
        data.get("aadhaar_number"),
        data.get("notes"),
        data.get("latitude"),
        data.get("longitude"),
        data.get("eid"),
        data.get("phone_number")
        
    ))

    cur.execute("""
        UPDATE customer_feed
        SET status = 'accepted',
            reviewed_by = %s,
            reviewed_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE feed_id = %s
    """, (logged_user, feed_id))

    cur.execute("SET TIME ZONE 'UTC'")

    conn.commit()
    audit_log(
        action="accept_customer_feed",
        entity_type="customer_feed",
        entity_id=feed_id,
        details={
            "ano": data.get("ano"),
            "vid": data.get("vid"),
            "eid": data.get("eid"),
            "reviewed_by": logged_user
        }
    )
    cur.close()
    conn.close()

    return {"success":True}


@app.post("/feed/payment/accept/<feed_payment_id>")
@login_required
def accept_payment(feed_payment_id):

    conn = get_pg_connection()
    cur = conn.cursor()

    # Safety check: ensure logged-in employee
    logged_user = session.get("employee_id")

    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    # 1️⃣ Get payload
    cur.execute("""
        SELECT payload
        FROM payment_feed_items
        WHERE feed_payment_id = %s
    """, (feed_payment_id,))

    row = cur.fetchone()

    if not row:
        return {"success": False, "error": "Feed not found"}

    data = row[0]

    ano = data.get("ano")
    vid = data.get("vid")
    eid = data.get("eid")
    amt = Decimal(str(data.get("amt")))
    pdate = datetime.fromisoformat(data.get("pdate")).date()

    # 2️⃣ Get customer
    cur.execute("""
        SELECT cid, total_amount
        FROM customer
        WHERE ano = %s AND vid = %s
    """, (ano, vid))

    cust = cur.fetchone()

    if not cust:
        return {"success": False, "error": "Customer not found"}

    cid, total_amt = cust

    # 3️⃣ Insert payment
    cur.execute("""
        INSERT INTO payment
        (cid, vid, eid, ano, amt, payment_date)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        cid,
        vid,
        eid,
        ano,
        amt,
        pdate
    ))

    # 4️⃣ Recalculate balance
    recalc_customer_balance(cur, cid)

    # 5️⃣ Mark feed accepted
    cur.execute("""
        UPDATE payment_feed_items
        SET status='accepted',
            review_by = %s,
            review_at = NOW() AT TIME ZONE 'Asia/Kolkata'
        WHERE feed_payment_id = %s
    """, (logged_user, feed_payment_id))

    conn.commit()
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

    data = request.get_json()
    ids = data.get("ids", [])
    # ✅ Ensure IDs are integers (fix bigint = text error)
    try:
        ids = [int(i) for i in ids]
    except Exception:
        return {"success": False, "error": "Invalid IDs format"}

    if not ids:
        return {"success": False, "error": "No payments selected"}

    conn = get_pg_connection()
    cur = conn.cursor()

    # Safety check: ensure logged-in employee
    logged_user = session.get("employee_id")

    if not logged_user:
        return {"success": False, "error": "User not logged properly"}

    try:
        # 1️⃣ Fetch all selected payloads
        cur.execute("""
            SELECT payload
            FROM payment_feed_items
            WHERE feed_payment_id = ANY(%s::bigint[])
        """, (ids,))

        rows = cur.fetchall()

        if not rows:
            return {"success": False, "error": "No valid payments found"}

        # -------------------------------------------------
        # Batch prefetch customers
        # -------------------------------------------------
        anos = []

        for r in rows:
            payload = r[0]
            ano = payload.get("ano")

            if ano is not None:
                try:
                    anos.append(int(ano))
                except Exception:
                    pass

        anos = list(set(anos))

        customer_map = {}

        if anos:

            # Use vid from first payload (all selected payments belong to same village)
            first_payload = rows[0][0]
            batch_vid = first_payload.get("vid")

            cur.execute("""
                SELECT
                    cid,
                    ano,
                    total_amount,
                    paid_amount,
                    balance_amount
                FROM customer
                WHERE ano = ANY(%s)
                  AND vid = %s
            """, (anos, batch_vid))

            for row in cur.fetchall():
                customer_map[int(row[1])] = {
                    "cid": row[0],
                    "total_amount": row[2],
                    "paid_amount": row[3],
                    "balance_amount": row[4]
                }

        insert_values = []

        # 2️⃣ Prepare bulk insert
        for r in rows:
            p = r[0]

            ano = p.get("ano")
            vid = p.get("vid")
            eid = p.get("eid")
            amt = Decimal(str(p.get("amt")))
            pdate = datetime.fromisoformat(p.get("pdate")).date()

            customer = customer_map.get(int(ano))

            if not customer:
                continue

            cid = customer["cid"]

            insert_values.append((cid, vid, eid, ano, amt, pdate))

        if not insert_values:
            return {"success": False, "error": "No valid payments to insert"}

        # 3️⃣ BULK INSERT (safe + parameterized)
        execute_values(
            cur,
            """
                INSERT INTO payment (
                    cid,
                    vid,
                    eid,
                    ano,
                    amt,
                    payment_date
                )
                VALUES %s
            """,
            insert_values,
            template="(%s,%s,%s,%s,%s,%s)"
        )

        # 4️⃣ Update customers (optimized)
        for customer in customer_map.values():
            recalc_customer_balance(cur, customer["cid"])

        # 5️⃣ Mark all as accepted
        cur.execute("""
            UPDATE payment_feed_items
            SET status = 'accepted',
                review_by = %s,
                review_at = NOW() AT TIME ZONE 'Asia/Kolkata'
            WHERE feed_payment_id = ANY(%s::bigint[])
        """, (logged_user, ids))

        conn.commit()
        audit_log(
            action="accept_payment_batch",
            entity_type="payment_feed",
            entity_id=vid,
            details={
                "reviewed_by": logged_user,
                "selected_feed_ids": ids,
                "payments_inserted": len(insert_values)
            }
        )
        conn.close()

        return {
            "success": True,
            "message": f"{len(insert_values)} payments inserted"
        }

    except Exception as e:
        conn.rollback()
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

        # 🔹 Detect table based on status
        status = (data.get("status") or "active").strip().lower()

        if status == "active":
            table_name = "customer"
        else:
            table_name = "closed_cust_account"

        # 🔹 Fetch existing paid amount
        cur.execute(f"""
            SELECT paid_amount
            FROM {table_name}
            WHERE cid = %s
              AND vid = %s
        """, (cid, vid))

        existing = cur.fetchone()

        if not existing:
            return jsonify(success=False, error="Customer not found"), 404

        paid_amount = float(existing[0] or 0)

        # 🔹 Read editable fields
        name = (data.get("name") or "").strip()
        start_date_raw = (data.get("start_date") or "").strip()
        loan_type = (data.get("type") or "").strip().upper()
        pano = (data.get("pano") or "").strip() or None
        notes = (data.get("notes") or "").strip() or None
        phone_number = (data.get("phone_number") or "").strip() or None

        try:
            total_amount = float(data.get("total_amount") or 0)
        except Exception:
            return jsonify(success=False, error="Invalid total amount"), 400

        try:
            period = int(data.get("period") or 0)
        except Exception:
            return jsonify(success=False, error="Invalid period"), 400

        # 🔹 Validation
        if not name:
            return jsonify(success=False, error="Name is required"), 400

        if loan_type not in ["W", "M"]:
            return jsonify(success=False, error="Loan type must be W or M"), 400

        if period <= 0:
            return jsonify(success=False, error="Period must be greater than 0"), 400

        if total_amount <= 0:
            return jsonify(success=False, error="Total amount must be greater than 0"), 400

        if phone_number:
            if not phone_number.isdigit() or len(phone_number) != 10:
                return jsonify(success=False, error="Phone number must be 10 digits"), 400

        # 🔹 Parse frontend date safely
        try:
            if "/" in start_date_raw:
                start_date = datetime.strptime(start_date_raw, "%d/%m/%Y").date()
            else:
                start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        except Exception:
            return jsonify(success=False, error="Invalid start date format"), 400

        # 🔹 Recalculate derived fields
        if loan_type == "M":
            end_date = start_date + relativedelta(months=period)
        else:
            end_date = start_date + timedelta(weeks=period)

        installment_amount = round(total_amount / period, 2)
        balance_amount = round(total_amount - paid_amount, 2)

        # 🔹 Update customer
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
                updated_at = NOW() AT TIME ZONE 'Asia/Kolkata'
            WHERE cid = %s
              AND vid = %s
        """, (
            name,
            start_date,
            end_date,
            total_amount,
            balance_amount,
            installment_amount,
            loan_type,
            period,
            pano,
            notes,
            phone_number,
            cid,
            vid
        ))

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

# ----------- NEW: Postgres-based payment update route -----------
@app.route("/api/payment/update_pg", methods=["POST"])
@login_required
def update_payment_pg():
    payload = request.get_json()

    if not payload:
        return jsonify(success=False, error="Missing payload"), 400

    data = payload.get("data")
    if not data:
        return jsonify(success=False, error="Missing data"), 400

    vid = session.get("vid")

    if not vid:
        return jsonify(success=False, error="Context not set"), 400

    ano = data.get("ano")
    try:
        old_pdt = datetime.fromisoformat(data["old_pdt"]).date()
        new_pdt = datetime.fromisoformat(data["pdt"]).date()
    except Exception as ex:
        return jsonify(success=False, error=f"Invalid date format: {ex}"), 400
    amt = Decimal(str(data.get("amt")))

    if not all([ano, old_pdt, new_pdt, amt]):
        return jsonify(success=False, error="Missing required fields"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Update payment row
        cur.execute("""
            UPDATE payment
            SET payment_date = %s,
                amt = %s
            WHERE vid = %s
              AND ano = %s
              AND payment_date = %s
        """, (new_pdt, amt, vid, ano, old_pdt))

        # Recalculate customer balances
        cur.execute("""
            SELECT cid, total_amount
            FROM customer
            WHERE vid = %s AND ano = %s
        """, (vid, ano))
        row = cur.fetchone()
        if not row:
            raise Exception("Customer not found")

        cid, total_amt = row

        recalc_customer_balance(cur, cid)

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@app.route("/add_payment", methods=["POST"])
@login_required
def add_payment():
    
    vid = session.get("vid")
    eid = session.get("eid")
    if not vid:
       return jsonify(success=False, error="Context not set"), 400

    data = request.get_json()
    ano = int(data["ano"])
    amt = Decimal(str(data["amt"]))
    pdt = datetime.strptime(data["pdt"], "%d/%m/%Y").date()

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT cid, total_amount, paid_amount
        FROM customer
        WHERE vid=%s AND ano=%s
    """, (vid, ano))

    cust = cur.fetchone()
    if not cust:
        return jsonify(success=False, error="Customer not found")

    cid, total_amt, paid_amt = cust
    paid_amt = Decimal(paid_amt or 0)

    cur.execute("""
        INSERT INTO payment (cid, vid, eid, ano, amt, payment_date)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (cid, vid, eid, ano, amt, pdt))

    recalc_customer_balance(cur, cid)

    conn.commit()
    cur.close()
    conn.close()

    return jsonify(success=True)

@app.route("/delete_payment", methods=["POST"])
@login_required
def delete_payment():
    data = request.get_json()

    ano = data.get("ano")
    pdt_raw = data.get("pdt")
    vid = session.get("vid")

    if not ano or not pdt_raw or not vid:
        return jsonify(success=False, error="Missing required fields"), 400

    # ✅ ACCEPT ISO DATE (YYYY-MM-DD)
    try:
        pdt = datetime.fromisoformat(pdt_raw).date()
    except ValueError:
        return jsonify(success=False, error="Invalid date format"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # 🔹 Delete payment
        cur.execute("""
            DELETE FROM payment
            WHERE vid = %s
              AND ano = %s
              AND payment_date = %s
        """, (vid, ano, pdt))

        if cur.rowcount == 0:
            conn.rollback()
            return jsonify(success=False, error="Payment not found"), 404

        # 🔹 Recalculate balances
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

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@app.route("/village")
@login_required
@admin_required
def village_page():
    conn = get_pg_connection()
    cur = conn.cursor()
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])

    if user_level in ["admin", "mgmt"]:
        cur.execute("""
        SELECT
            vid,
            village_code,
            village_name,
            district,
            pincode,
            state,
            emp1,
            emp2,
            created_at,
            status
        FROM village
        ORDER BY vid
    """)
    else:
        if not allowed_villages:
            cur.close()
            conn.close()
            return render_template(
                "village.html",
                headers=[],
                data=[],
                total_villages=0
        )

        cur.execute("""
        SELECT
            vid,
            village_code,
            village_name,
            district,
            pincode,
            state,
            emp1,
            emp2,
            created_at,
            status
        FROM village
        WHERE vid = ANY(%s)
        ORDER BY vid
    """, (allowed_villages,))

    rows = cur.fetchall()

    headers = [desc[0] for desc in cur.description] # type: ignore
    data = [dict(zip(headers, r)) for r in rows]

    cur.close()
    conn.close()

    return render_template(
        "village.html",
        headers=headers,
        data=data,
        total_villages=len(data)
    )

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
# EMPLOYEE DB HELPERS (Postgres)
# ----------------------------------------------------
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

    return [dict(zip(headers, r)) for r in rows]


def update_employee_in_db(data):
    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        eid = data.get("eid")

        name = (data.get("name") or "").strip()
        phone_number = (data.get("phone_number") or "").strip()

        # 🔒 Required validation
        if not name:
            return {
                "success": False,
                "error": "Employee name is required"
            }

        # 🔒 Prevent duplicate employee name / phone while editing
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

        # ✅ Update employee
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
            data.get("level"),
            data.get("state"),
            eid,
        ))

        conn.commit()

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
    rows = get_all_employees()  # your repo function
    headers = rows[0].keys() if rows else []
    return render_template(
        "employee.html",
        data=rows,
        headers=headers,
        total_employees=len(rows)
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
# ----------------------------------------------------
# ROUTES
# ----------------------------------------------------
@app.route("/")
@login_required
def home():
    return redirect("/landing")

@app.route("/landing")
@login_required
def landing():
    # Clear active village context so the header shows nothing
    # and the user must pick a village on this page.
    session.pop("vid", None)
    session.pop("eid", None)
    session.pop("village_name", None)
    session.pop("employee_name", None)
    return render_template("landing.html")

def get_active_db_path():
    path = session.get("active_path")
    if not path:
        raise Exception("No active database selected.")
    return path




# ----------------------------------------------------
# Login / Logout
# ----------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
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
        # 1️⃣ Fetch user
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
        # 3️⃣ Device lock logic
        # ---------------------------
        # 🔓 Admin users are NOT device locked
        if level != "admin":

            cur.execute("""
                SELECT device_id, is_active
                FROM user_devices
                WHERE user_id = %s AND is_active = TRUE
            """, (user_id,))
            device = cur.fetchone()

            if not device:
                # First login or after reset → clear old devices and register new
                cur.execute("""
                    DELETE FROM user_devices
                    WHERE user_id = %s
                """, (user_id,))

                cur.execute("""
                    INSERT INTO user_devices (user_id, device_id, is_active)
                    VALUES (%s, %s, TRUE)
                """, (user_id, device_id))

                conn.commit()

            else:
                saved_device_id, device_active = device

                if not device_active:
                    flash("Device disabled. Contact admin.")
                    return redirect("/login")

                if saved_device_id != device_id:
                    flash("Login not allowed from this device.")
                    return redirect("/login")

        # ---------------------------
        # 4️⃣ Load village access
        # ---------------------------
        cur.execute("""
            SELECT vid
            FROM village
            WHERE emp1 = %s OR emp2 = %s
        """, (employee_id, employee_id))

        villages = [row[0] for row in cur.fetchall()]

        # ---------------------------
        # 5️⃣ Save session
        # ---------------------------
        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        session["employee_id"] = employee_id
        session["level"] = level
        session["villages"] = villages

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

        return redirect("/landing")

    finally:
        cur.close()
        conn.close()

@app.route("/logout")
def logout():
    audit_log(
      action="logout",
      entity_type="user",
      entity_id=session.get("user_id"),
      details={
          "eid": session.get("eid")
      }
    )
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/users")
@login_required
def users_page():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("level") != "admin":
        flash("Access denied")
        return redirect("/dashboard")

    return render_template("user_management.html")

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

        # Batch fetch active devices
        cur.execute("""
            SELECT user_id, device_id
            FROM user_devices
            WHERE user_id = ANY(%s)
              AND is_active = TRUE
        """, (user_ids,))

        for uid, device_id in cur.fetchall():
            devices_by_user[uid] = device_id

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

        users.append({
            "id": user_id,
            "username": username,
            "employee_id": employee_id,
            "employee_name": emp_name,
            "role": level,
            "device_id": devices_by_user.get(user_id, ""),
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

        # 🔹 Assign villages to user in user_village_access
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
    data = request.get_json()
    user_id = data.get("id") if data else None

    if not user_id:
        return jsonify(ok=False, msg="Missing user id")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        # Disable existing device so next login re-registers
        cur.execute("""
            UPDATE user_devices
            SET is_active = FALSE
            WHERE user_id = %s
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
# Toggle user status
# ----------------------------------------------------
@app.route("/api/users/toggle_status", methods=["POST"])
@admin_required
def toggle_user_status():
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
        # 🔹 Remove existing mappings
        cur.execute("""
            DELETE FROM user_village_access
            WHERE user_id = %s
        """, (user_id,))

        # 🔹 Insert new mappings
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
    print("DEBUG DASHBOARD SESSION → vid:", session.get("vid"))
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


def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


@app.route("/update_payment_date_bulk", methods=["POST"])
@login_required
def update_payment_date_bulk():
    data = request.get_json()
    old_date = data.get("find_date")
    new_date = data.get("replace_date")
    vid = session.get("vid")

    if not old_date or not new_date or not vid:
        return jsonify(success=False, error="Missing data"), 400

    # Convert dd/mm/yyyy → yyyy-mm-dd
    try:
        old_iso = datetime.strptime(old_date, "%d/%m/%Y").date()
        new_iso = datetime.strptime(new_date, "%d/%m/%Y").date()
    except ValueError:
        return jsonify(success=False, error="Invalid date format"), 400

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE payment
            SET payment_date = %s
            WHERE vid = %s AND payment_date = %s
        """, (new_iso, vid, old_iso))

        conn.commit()
        return jsonify(success=True, message="Payment dates updated")

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@app.template_filter('b64encode')
def b64encode_filter(data):
    if not data:
        return ""
    return base64.b64encode(data).decode('utf-8')

# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))