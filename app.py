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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import (
    Flask, render_template, request, redirect,
    session, jsonify, flash, url_for
)
from db import get_pg_connection, init_db
from config import POSTGRES_URI
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
load_dotenv()
# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy (does NOT replace SQLite yet)
init_db(POSTGRES_URI)

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
# ----------------------------------------------------
# FLASK APP SETUP
# ----------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
limiter = Limiter(get_remote_address, app=app)

@app.before_request
def fix_cookie_domain():
    host = request.headers.get("Host", "")
    # Allow both domains
    if "sivadurga.in" in host:
        app.config["SESSION_COOKIE_DOMAIN"] = ".sivadurga.in"
    else:
        # Allows Cloud Run direct link to work
        app.config["SESSION_COOKIE_DOMAIN"] = None


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


@app.route("/admin/monitor")
def admin_monitor():
    if session.get("username") != "jayakrishna":
        return redirect(url_for("login"))
    return render_template("monitor.html")
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


@app.route("/api/villages")
@login_required
def api_villages():
    eid = request.args.get("eid")
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
                    WHERE emp1 = %s OR emp2 = %s
                    ORDER BY village_name
                """, (eid, eid))
            else:
                cur.execute("""
                    SELECT vid, village_name
                    FROM village
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
        SELECT vid, village_name
        FROM village
        WHERE emp1 = %s OR emp2 = %s
        ORDER BY village_name
    """, (eid, eid))

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
        "eid": session.get("eid"),
        "vid": session.get("vid")
    })

def resolve_emp1_for_context(vid, selected_eid):
    """
    Always return emp1 for a village, even if emp2 was selected
    """
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT emp1, emp2
        FROM village
        WHERE vid = %s
    """, (vid,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return selected_eid  # fallback (should never happen)

    emp1, emp2 = row

    # If selected employee is emp2 → normalize to emp1
    if selected_eid == emp2:
        return emp1

    # If selected employee is emp1 → keep as is
    return emp1

@app.route("/set_context", methods=["POST"])
@login_required
def set_context():
    data = request.get_json()
    vid = int(data.get("vid"))
    selected_eid = int(data.get("eid"))
    user_level = session.get("level")
    allowed_villages = session.get("villages", [])

    if user_level not in ["admin", "mgmt"]:
        if vid not in allowed_villages:
           return jsonify(success=False, error="Unauthorized village"), 403

    # 🔑 Normalize employee
    eid = resolve_emp1_for_context(vid, selected_eid)

    session["vid"] = vid
    session["eid"] = eid
    
    # 🔽 FETCH HUMAN-READABLE NAMES FROM DB
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("SELECT village_name FROM village WHERE vid = %s", (vid,))
    result = cur.fetchone()
    village_name = result[0] if result else "Unknown"

    cur.execute("SELECT name FROM employee WHERE eid = %s", (eid,))
    result = cur.fetchone()
    employee_name = result[0] if result else "Unknown"

    # 🔽 STORE IN SESSION (THIS IS WHAT YOU ASKED)
    session["village_name"] = village_name
    session["employee_name"] = employee_name
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
    cur.execute("""
        SELECT 1
        FROM village
        WHERE village_code = %s
          AND village_name = %s
          AND emp1 = %s
    """, (
        data["village_code"],
        data["village_name"],
        data["emp1_eid"]
    ))

    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "error": "Village already exists for this employee"
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
            created_at, source_file
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NULL)
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
        # 🔒 Prevent duplicate employee names (case-insensitive)
        cur.execute(
            "SELECT 1 FROM employee WHERE LOWER(name) = LOWER(%s)",
            (name,)
        )
        if cur.fetchone():
            return jsonify(success=False, error="Employee already exists")

        cur.execute("""
            INSERT INTO employee (eid, name, phone_number, city, joining_date, level, state)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING eid
        """, (
            new_eid,
            name,
            data.get("phone_number"),
            data.get("city"),
            data.get("joining_date"),
            data.get("level"),
            data.get("state")
        ))

        result = cur.fetchone()
        if not result:
            return jsonify(success=False, error="Failed to create employee"), 500
        
        conn.commit()

        return jsonify(success=True, eid=new_eid, name=name)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500

    finally:
        cur.close()
        conn.close()

@app.route("/api/village/check")
def api_check_village():
    code = request.args.get("code")
    name = request.args.get("name")
    emp1 = request.args.get("emp1")

    conn = get_pg_connection()
    cur = conn.cursor()


    cur.execute("""
        SELECT 1
        FROM village
        WHERE village_code = %s
          AND village_name = %s
          AND emp1 = %s
        LIMIT 1
    """, (code, name, emp1))

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

def get_all_customers_by_context(eid, vid):
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
  aadhar_number,
  notes,
  latitude,
  longitude,
  eid
FROM customer
WHERE eid = %s AND vid = %s
ORDER BY ano;
    """, (eid, vid))

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
            "aadhar_number": r[14],
            "notes": r[15],
            "latitude": r[16],
            "longitude": r[17],
            "eid": r[18]
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
                    aadhar_number, notes,
                    latitude, longitude
                )
                VALUES (
                    %(ano)s, %(name)s, %(pano)s, %(vid)s, %(eid)s,
                    %(start_date)s, %(end_date)s,
                    %(total_amount)s, %(paid_amount)s, %(balance_amount)s, %(installment_amount)s,
                    %(type)s, %(period)s,
                    %(aadhar_number)s, %(notes)s,
                    %(latitude)s, %(longitude)s
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

# ----------------------------------------------------
# ROUTES - mobile app
# ----------------------------------------------------

@app.post("/api/mobile/login")
def mobile_login():

    data = request.json
    if not data:
        return {"error": "invalid"}, 401
    
    username = data.get("username")
    password = data.get("password")

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id,password_hash,is_active
        FROM users
        WHERE username=%s
    """,(username,))

    user = cur.fetchone()

    if not user:
        return {"error":"invalid"},401

    user_id,password_hash,is_active = user

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

    return {
        "token":token,
        "user_id":user_id,
        "username":username,
        "eid": eid
    }

@app.get("/api/mobile/villages")
def mobile_villages():

    token = request.headers.get("X-Mobile-Token")

    if not token:
        return {"error": "missing token"}, 401

    data = verify_mobile_token(token)

    if not data:
        return {"error": "invalid token"}, 401

    eid = data["eid"]

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT vid, village_name, district
        FROM village
        WHERE emp1 = %s OR emp2 = %s
        ORDER BY village_name
    """, (eid, eid))

    villages = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "villages": [
            {
                "vid": v[0],
                "village_name": v[1],
                "district": v[2]
            }
            for v in villages
        ]
    }

@app.get("/api/mobile/customers")
def mobile_customers():

    vid = request.args.get("vid")

    conn = get_pg_connection()
    cur = conn.cursor()

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

@app.get("/api/mobile/payments")
def mobile_payments():

    vid = request.args.get("vid")

    conn = get_pg_connection()
    cur = conn.cursor()

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

@app.route("/api/mobile/customer_feed", methods=["POST"])
def create_customer_feed():

    data = request.json

    local_uuid = str(uuid.uuid4())
    device_id = request.headers.get("Device-Id", "mobile")
    if not data:
        return jsonify({"error": "invalid request body"}), 400
    vid = data.get("vid")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    payload = json.dumps(data)

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO customer_feed
        (
            local_uuid,
            device_id,
            vid,
            payload,
            latitude,
            longitude,
            status,
            submitted_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,'pending',NOW())
    """, (
        local_uuid,
        device_id,
        vid,
        payload,
        latitude,
        longitude
    ))

    conn.commit()

    return jsonify({"status":"ok"})

@app.route("/api/mobile/payment_feed_batch", methods=["POST"])
def payment_feed_batch():
    try:
        data = request.json
        print("PAYMENT REQUEST:", data)

        payments = data.get("payments", [])# type: ignore
        vid = data.get("vid") # type: ignore
        eid = data.get("eid")# type: ignore
        device_id = data.get("device_id", "mobile")# type: ignore

        if not payments:
            return jsonify({"error": "no payments provided"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()

        total_records = len(payments)

        cur.execute("""
            INSERT INTO payment_feed_batch (
                eid,
                vid,
                device_id,
                total_records,
                status,
                submitted_at
            )
            VALUES (%s,%s,%s,%s,'pending',NOW())
            RETURNING batch_id
        """, (eid, vid, device_id, total_records))

        batch_id = cur.fetchone()[0] # type: ignore

        for p in payments:
            cur.execute("""
                INSERT INTO payment_feed_items (
                    batch_id,
                    ano,
                    cid,
                    amount,
                    payment_date,
                    status
                )
                VALUES (%s,%s,%s,%s,%s,'pending')
            """, (
                batch_id,
                p.get("ano"),
                p.get("cid"),
                p.get("amt"),
                p.get("pdate")
            ))

        conn.commit()

        return jsonify({
            "status": "ok",
            "batch_id": batch_id,
            "payments_received": total_records
        })

    except Exception as e:
        print("PAYMENT API ERROR:", str(e))
        return jsonify({"error": str(e)}), 500
# ----------------------------------------------------
# ROUTES - postgre
# ----------------------------------------------------

def get_dashboard_totals(vid, eid=None):
    conn = get_pg_connection()
    cur = conn.cursor()

    if eid:
        cur.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(c.total_amount), 0),
                COALESCE(SUM(c.paid_amount), 0),
                COALESCE(SUM(c.balance_amount), 0)
            FROM customer c
            JOIN village v ON v.vid = c.vid
            WHERE c.vid = %s
              AND (v.emp1 = %s OR v.emp2 = %s)
        """, (vid, eid, eid))
    else:
        cur.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(paid_amount), 0),
                COALESCE(SUM(balance_amount), 0)
            FROM customer
            WHERE vid = %s
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

@app.route("/add_customer", methods=["GET", "POST"])
@login_required
def add_customer():
    vid = session.get("vid")
    eid = session.get("eid")

    if not vid or not eid:
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
            "aadhar_number": data.get("aadhar_number") or None,
            "notes": data.get("notes") or None,
            "latitude": data.get("latitude") or None,
            "longitude": data.get("longitude") or None,
        }

        cid = insert_customer(payload)

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
    eid = session.get("eid")
    vid = session.get("vid")

    # ❗ Enforce context
    if not eid or not vid:
        flash("Please select Employee and Village from Dashboard first", "warning")
        return redirect(url_for("dashboard"))

    # 🔹 Fetch ALL customers for context
    rows = get_all_customers_by_context(eid, vid)


    headers = [
        "cid", "ano", "name", "vid",
        "start_date", "end_date",
        "total_amount", "paid_amount",
        "balance_amount", "installment_amount",
        "type", "period", "pano",
        "created_at", "aadhar_number",
        "notes", "latitude", "longitude", "eid"
    ]

    # ✅ Use same aggregation logic as dashboard
    totals = get_dashboard_totals(vid, eid)

    total_customers = totals["total_customers"]
    sum_amt = totals["sum_amt"]
    sum_pamt = totals["sum_pamt"]
    sum_bamt = totals["sum_bamt"]

    return render_template(
        "view_customers.html",
        headers=headers,
        data=rows,
        total_customers=total_customers,
        sum_amt=sum_amt,
        sum_pamt=sum_pamt,
        sum_bamt=sum_bamt
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
    eid = session.get("eid")

    if not vid or not eid:
        flash("Please select Employee and Village first", "warning")
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
            vid
        FROM payment
        WHERE vid = %s
          AND eid = %s
        ORDER BY payment_date DESC, pid DESC
    """, (vid, eid))

    rows = cur.fetchall()
    # cur.description can be None for some drivers or edge cases; guard against that
    if cur.description:
        headers = [desc[0] for desc in cur.description]
    else:
        headers = ["pid", "ano", "payment_date", "amt", "created_at", "eid", "cid", "vid"]

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
    eid = session.get("eid")

    if not vid or not eid:
        flash("Please select Employee and Village first", "warning")
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



@app.route("/submit_post_payment", methods=["POST"])
@login_required
def submit_post_payment():
    vid = session.get("vid")
    eid = session.get("eid")

    if not vid or not eid:
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
            ano = int(row["ano"])
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

            # 🔹 Update balances
            new_paid = paid_amt + amt
            new_balance = total_amt - new_paid

            cur.execute("""
                UPDATE customer
                SET paid_amount = %s,
                    balance_amount = %s
                WHERE cid = %s
            """, (new_paid, new_balance, cid))

            submitted += 1

        conn.commit()

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
    eid = session.get("eid")

    if not vid or not eid:
        flash("Please select Employee and Village first", "warning")
        return redirect("/dashboard")

    customers = []
    pamt1_records = {}
    loanee_headers = [
        "cid", "ano", "name",
        "total_amount", "paid_amount",
        "balance_amount", "installment_amount", "type", "period", "created_at"
    ]

    if request.method == "POST":
        query = request.form.get("query", "").strip()

        conn = get_pg_connection()
        cur = conn.cursor()

        # 🔍 Search by A.no OR Name (within context)
        cur.execute("""
            SELECT
                cid, ano, name,
                total_amount, paid_amount,
                balance_amount, installment_amount, type, period, created_at
            FROM customer
            WHERE vid = %s
              AND (CAST(ano AS TEXT) = %s OR LOWER(name) LIKE LOWER(%s))
            ORDER BY ano
            LIMIT 1
        """, (vid, query, f"%{query}%"))

        row = cur.fetchone()

        if row:
            cust = dict(zip(loanee_headers, row))
            customers = [cust]

            # 🔹 Fetch payments for this customer
            cur.execute("""
                SELECT ano, payment_date, amt
                FROM payment
                WHERE cid = %s
                ORDER BY payment_date
            """, (cust["cid"],))

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

@app.route("/api/update_village", methods=["POST"])
@login_required
def update_village():
    data = request.get_json()

    vid = data.get("vid")
    if not vid:
        return jsonify(success=False, error="Missing vid")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE village
            SET
              village_code = %s,
              village_name = %s,
              district = %s,
              pincode = %s,
              state = %s,
              emp1 = %s,
              emp2 = %s
            WHERE vid = %s
        """, (
            data.get("village_code"),
            data.get("village_name"),
            data.get("district"),
            data.get("pincode"),
            data.get("state"),
            data.get("emp1"),
            data.get("emp2"),
            vid
        ))

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e))

    finally:
        cur.close()
        conn.close()

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
        cur.execute("""
            UPDATE customer
            SET
              name = %s,
              total_amount = %s,
              paid_amount = %s,
              balance_amount = %s,
              installment_amount = %s
            WHERE cid = %s
              AND vid = %s
        """, (
            data.get("name"),
            data.get("total_amount"),
            data.get("paid_amount"),
            data.get("balance_amount"),
            data.get("installment_amount"),
            cid,
            vid
        ))

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        conn.rollback()
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
    eid = session.get("eid")

    if not vid or not eid:
        return jsonify(success=False, error="Context not set"), 400

    ano = data.get("ano")
    try:
        old_pdt = datetime.fromisoformat(data["old_pdt"]).date()
        new_pdt = datetime.fromisoformat(data["pdt"]).date()
    except Exception as ex:
        return jsonify(success=False, error=f"Invalid date format: {ex}"), 400
    amt = data.get("amt")

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

        cur.execute("""
            SELECT COALESCE(SUM(amt), 0)
            FROM payment
            WHERE cid = %s
        """, (cid,))
        result = cur.fetchone()
        paid_amt = result[0] if result else 0

        balance_amt = total_amt - paid_amt

        cur.execute("""
            UPDATE customer
            SET paid_amount = %s,
                balance_amount = %s
            WHERE cid = %s
        """, (paid_amt, balance_amt, cid))

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
    if not vid or not eid:
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

    new_paid = paid_amt + amt
    new_balance = Decimal(total_amt) - new_paid

    cur.execute("""
        UPDATE customer
        SET paid_amount=%s, balance_amount=%s
        WHERE cid=%s
    """, (new_paid, new_balance, cid))

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
              AND eid = %s
              AND ano = %s
              AND payment_date = %s
        """, (vid, session.get("eid"), ano, pdt))

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

            cur.execute("""
                SELECT COALESCE(SUM(amt), 0)
                FROM payment
                WHERE cid = %s
            """, (cid,))

            result = cur.fetchone()
            paid_amt = result[0] if result else 0
            balance_amt = total_amt - paid_amt

            cur.execute("""
                UPDATE customer
                SET paid_amount = %s,
                    balance_amount = %s
                WHERE cid = %s
            """, (paid_amt, balance_amt, cid))

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
            created_at
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
            created_at
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

@app.route("/api/delete_village", methods=["POST"])
@login_required
def delete_village():
    if session.get("level") not in ["admin", "mgmt"]:
       return jsonify(success=False, error="Unauthorized"), 403
    data = request.get_json()
    vid = data.get("vid")

    conn = get_pg_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM village WHERE vid = %s", (vid,))
        conn.commit()
        return jsonify(success=True)
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
            state
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
        data.get("name"),
        data.get("phone_number"),
        data.get("city"),
        data.get("joining_date"),
        data.get("level"),
        data.get("state"),
        data.get("eid"),
    ))

    conn.commit()
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
def update_employee():
    data = request.json
    try:
        update_employee_in_db(data)  # implement in repo
        return jsonify(success=True)
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
    print("⚠️ LOCAL mode: skipping GCS auth DB initialization")
    return redirect("/dashboard")

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
            flash("Invalid credentials")
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
            flash("Invalid credentials")
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

        return redirect("/dashboard")

    finally:
        cur.close()
        conn.close()

@app.route("/logout")
def logout():
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

    for row in rows:
        user_id, username, employee_id, is_active, emp_name, level = row

        # Fetch device
        cur.execute("""
            SELECT device_id 
            FROM user_devices 
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        device = cur.fetchone()

        users.append({
            "id": user_id,
            "username": username,
            "employee_id": employee_id,
            "employee_name": emp_name,
            "role": level,
            "device_id": device[0] if device else "",
            "is_active": is_active
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
# DASHBOARD
# ----------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    vid = session.get("vid")
    eid = session.get("eid")
    # ✅ NO CONTEXT → SHOW ZERO DASHBOARD
    if not vid and not eid:
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
    print("DEBUG DASHBOARD SESSION → vid:", session.get("vid"), "eid:", session.get("eid"))
    # Defensive log before dashboard totals
    print("DASHBOARD QUERY USING → vid:", vid, "eid:", eid)
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

        totals = get_dashboard_totals(vid, eid)

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



# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))