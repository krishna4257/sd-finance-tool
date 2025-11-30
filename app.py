
import os
import sqlite3
import traceback
import logging
import sqlite3
from functools import wraps
from google.cloud import storage
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from flask import (
    Flask, render_template, request, redirect,
    session, jsonify, flash, send_file, url_for
)
from werkzeug.utils import secure_filename
import database_manager as dbm
# GCS Database manager
from database_manager import (
    list_gcs_files,
    get_local_db_path,
    upload_to_gcs,
    delete_from_gcs,
    download_from_gcs,
    init_auth_db,
    get_auth_db_path,
    _get_client,
)
from config import TEAM_BUCKETS, AUTH_BUCKET, GCS_DEFAULT_BUCKET
# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import uuid
import platform
import base64
import hashlib
import json



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
# ----------------------------------------------------
# FLASK APP SETUP
# ----------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config.update({
    "SESSION_COOKIE_SECURE": True,
    "SESSION_COOKIE_SAMESITE": "None",
    "SESSION_COOKIE_DOMAIN": ".sivadurga.in"
})
# ---- AUTH helpers ----
AUTH_GCS_NAME = "auth.sqlite"

LOCAL_AUTH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_auth")
AUTH_LOCAL_PATH = os.path.join(LOCAL_AUTH_DIR, "auth.sqlite")   # <–– ONE FINAL LOCATION



def ensure_local_auth_dir():
    os.makedirs(LOCAL_AUTH_DIR, exist_ok=True)

# ----------------------------------------------------
# AUTH helpers (ensure auth DB exists and schema)
# ----------------------------------------------------
def _ensure_auth_schema(conn=None):
    close_me = False
    if conn is None:
        conn = sqlite3.connect(AUTH_LOCAL_PATH)
        close_me = True
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            system_id TEXT,
            notes TEXT,
            role TEXT DEFAULT 'user',
            team TEXT DEFAULT 'teamA'
        )
    """)

    for column, default in [
       ("system_id", None),
       ("notes", None),
       ("role", "user"),
       ("team", "teamA")   # default team
    ]:
        try:
           c.execute(f"ALTER TABLE USERS ADD COLUMN {column} TEXT DEFAULT ?", (default,))
        except:
            pass
    conn.commit()
    if close_me:
        conn.close()

def init_auth_db():
    ensure_local_auth_dir()
    try:
        download_from_gcs(AUTH_GCS_NAME, AUTH_LOCAL_PATH, bucket=AUTH_BUCKET)
        conn = sqlite3.connect(AUTH_LOCAL_PATH)
        _ensure_auth_schema(conn)
        conn.close()
    except FileNotFoundError:
        # create new
        conn = sqlite3.connect(AUTH_LOCAL_PATH)
        _ensure_auth_schema(conn)
        conn.close()
        upload_to_gcs(AUTH_LOCAL_PATH, AUTH_GCS_NAME, bucket=AUTH_BUCKET)

def _open_auth_conn():
    ensure_local_auth_dir()
    if not os.path.exists(AUTH_LOCAL_PATH):
        # if no local file, download once
        try:
            download_from_gcs(AUTH_GCS_NAME, AUTH_LOCAL_PATH, bucket=AUTH_BUCKET)
        except:
            pass
    return sqlite3.connect(AUTH_LOCAL_PATH)

def _commit_and_upload_auth(conn):
    conn.commit()
    conn.close()
    upload_to_gcs(AUTH_LOCAL_PATH, AUTH_GCS_NAME, bucket=AUTH_BUCKET)



def ensure_auth_db():
    """Download the auth DB from GCS (or create locally if missing)."""
    try:
        download_from_gcs(AUTH_GCS_NAME, AUTH_LOCAL_PATH) # type: ignore
        # ensure schema on downloaded DB (migrations)
        conn = sqlite3.connect(AUTH_LOCAL_PATH)
        _ensure_auth_schema(conn)
        conn.close()
    except Exception:
        # create new local auth DB if not present
        conn = sqlite3.connect(AUTH_LOCAL_PATH)
        _ensure_auth_schema(conn)
        conn.close()
        # upload new blank DB so GCS has it next time
        try:
            upload_to_gcs(AUTH_LOCAL_PATH, AUTH_GCS_NAME)
        except Exception:
            pass

# ----------------------------------------------------
# DB HELPERS (GCS MODE)
# ----------------------------------------------------
def connect_db_from_gcs():
    """Return sqlite3 connection using active DB loaded from GCS."""
    local_path = session.get("active_path")
    if not local_path:
        raise RuntimeError("No active village selected.")
    return sqlite3.connect(local_path)


def sync_active_db_to_gcs():
    """After every DB write, upload updated DB back to GCS."""
    filename = session.get("active_db")
    local_path = session.get("active_path")
    if filename and local_path:
        try:
            upload_to_gcs(local_path, filename)
            print(f"✔ Synced {filename} back to GCS")
        except Exception as e:
            print("⚠ Failed to sync DB:", e)


def get_village_name_from_db(local_path):
    """
    Returns village name from LOANEE.ADD1 (first non-empty value).
    META table is ignored because old DBs do not contain it.
    """
    conn = None
    try:
        conn = sqlite3.connect(local_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try LOANEE table first
        try:
            cursor.execute("SELECT ADD1 FROM LOANEE LIMIT 1")
            row = cursor.fetchone()
            if row:
                name = (row["ADD1"] or "").strip()
                if name and name.lower() != "unknown":
                    return name.upper()
        except Exception:
            pass

        return "UNKNOWN"

    except Exception as e:
        print("Village name fetch error:", e)
        return "UNKNOWN"
    finally:
        if conn:
            conn.close()


# ----------------------------------------------------
# Template context
# ----------------------------------------------------
@app.context_processor
def inject_layout_data():
    # Provide files list using user's bucket
    user_bucket = session.get("bucket") or os.environ.get("GCS_DEFAULT_BUCKET")
    files = []
    try:
        files = dbm.list_gcs_files(bucket=user_bucket)
    except Exception as ex:
        app.logger.debug("Could not list bucket files: %s", ex)
        files = []
    return {
        "active_db": session.get("active_db"),
        "village_name": session.get("village_name", ""),
        "files": files
    }


# ----------------------------------------------------
# Decorators
# ----------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username = session.get("user")
        if not username:
            flash("Please login", "danger")
            return redirect(url_for("login"))
        # check role from auth DB
        conn = _open_auth_conn()
        c = conn.cursor()
        c.execute("SELECT role FROM USERS WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        if not row or (row[0] or "").lower() != "admin":
            flash("Access denied", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper
# ----------------------------------------------------
# ROUTES
# ----------------------------------------------------

@app.route("/")
@login_required
def home():
    init_auth_db()
    return redirect("/dashboard")

def get_active_db_path():
    path = session.get("active_path")
    if not path:
        raise Exception("No active database selected.")
    return path
# ----------------------------------------------------
# ADMIN ROUTES
# ----------------------------------------------------
@app.route("/users")
@admin_required
def users_page():
    users = list_users()
    return render_template("user_management.html", users=users)

# --- APIs for table actions (AJAX) ---
@app.route("/api/users/list", methods=["GET"])
@admin_required
def api_users_list():
    return jsonify(list_users())

@app.route("/api/users/add", methods=["POST"])
@admin_required
def api_users_add():
    payload = request.json or request.form
    username = (payload.get("username","") or "").strip()
    password = (payload.get("password","") or "").strip()
    system_id = (payload.get("system_id","") or "").strip() or None
    notes = (payload.get("notes","") or "").strip() or None
    role = (payload.get("role","") or "user").strip().lower()
    team = (payload.get("team","") or "teamA").strip()
    if role not in ("user", "admin"):
        role = "user"
    if not username or not password:
        return jsonify({"ok": False, "msg": "username and password required"}), 400
    try:
        create_user(username, password, system_id, notes, role=role, team=team) # type: ignore
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/users/edit", methods=["POST"])
@admin_required
def api_users_edit():
    payload = request.json or request.form
    username = (payload.get("username","") or "").strip()
    new_username = (payload.get("new_username","") or "").strip() or None
    new_password = (payload.get("new_password","") or "").strip() or None
    system_id = (payload.get("system_id","") or "").strip() or None
    notes = (payload.get("notes","") or "").strip() or None
    role = (payload.get("role","") or "").strip().lower() or None
    team = (payload.get("team","") or "teamA").strip()
    if role and role not in ("user","admin"):
        role = None
    try:
        update_user(username, new_username=new_username, new_password=new_password, system_id=system_id, notes=notes, role=role, team=team) # type: ignore
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/users/delete", methods=["POST"])
@admin_required
def api_users_delete():
    payload = request.json or request.form
    username = payload.get("username","").strip()
    try:
        delete_user(username)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
    
@app.route("/api/users/reset_device", methods=["POST"])
@admin_required
def api_users_reset_device():
    payload = request.json or request.form
    username = payload.get("username", "").strip()
    conn = _open_auth_conn()
    c = conn.cursor()
    c.execute("UPDATE USERS SET system_id=NULL WHERE username=?", (username,))
    _commit_and_upload_auth(conn)
    return jsonify({"ok": True})
# ----------------------------------------------------
# Login / Logout
# ----------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user"):
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    device_id = request.headers.get("X-Device-ID") or request.form.get("device_id")

    conn = _open_auth_conn()
    _ensure_auth_schema(conn) 
    c = conn.cursor()
    # SELECT order: password_hash, system_id, role, team
    c.execute("SELECT password_hash, system_id, role, team FROM USERS WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        flash("Unknown username", "danger")
        return redirect(url_for("login"))

    # Correct unpacking: row[0] = password_hash, row[1] = system_id, row[2] = role, row[3] = team
    stored_hash = row[0]
    stored_system_id = row[1]
    role = row[2] if len(row) > 2 else "user"
    team = row[3] if len(row) > 3 else "teamA"

    if not check_password_hash(stored_hash, password):
        flash("Invalid password", "danger")
        return redirect(url_for("login"))

    # Admin bypasses device lock
    if role == "admin":
        session["user"] = username
        session["role"] = role
        session["team"] = team
        session["bucket"] = TEAM_BUCKETS.get(session["team"], "sd-finance-db")
        return redirect(url_for("dashboard"))

    # Generate system fingerprint if browser didn't send one
    if not device_id:
        device_id = generate_system_id()

    # First time login → attach system ID
    if stored_system_id is None:
        conn = _open_auth_conn()
        c = conn.cursor()
        c.execute("UPDATE USERS SET system_id=? WHERE username=?", (device_id, username))
        conn.commit()
        conn.close()
        _commit_and_upload_auth(sqlite3.connect(AUTH_LOCAL_PATH))  # upload change

        stored_system_id = device_id

    # Enforce device match
    if stored_system_id != device_id:
        flash("This user is restricted to another device", "danger")
        return redirect(url_for("login"))

    # success — set session and bucket
    session["user"] = username
    session["role"] = (role or "user").lower()
    session["team"] = team or "teamA"
    session["bucket"] = TEAM_BUCKETS.get(session["team"], "sd-finance-db")
    
    flash("Logged in", "success")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("role", None)
    session.pop("bucket", None)
    flash("Logged out", "info")
    session.pop('_flashes', None)
    return redirect(url_for("login"))


# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    flash("Logged in", "success")
    session.pop('_flashes', None)
    username = session.get("user")
    try:
        conn = _open_auth_conn()
        c = conn.cursor()
        c.execute("SELECT team FROM USERS WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        team = row[0] if row and row[0] else "teamA"
    except Exception as e:
        team = "teamA"

    session["bucket"] = TEAM_BUCKETS.get(team, TEAM_BUCKETS["teamA"])

    bucket = session["bucket"]

    # Implementation kept similar to your original code
    files = list_gcs_files(bucket=bucket)
    if request.method == "POST":
        selected_file = request.form.get("village_db", "").strip()
        if selected_file:
            selected_file = str(selected_file).strip()
            if isinstance(selected_file, dict):
                selected_file = selected_file.get("name", "")
            if selected_file:
                session["active_db"] = selected_file
                # DOWNLOAD using user's bucket
                try:
                    local_path = get_local_db_path(selected_file, bucket=bucket)
                    session["active_path"] = local_path
                except Exception as e:
                    app.logger.exception("Failed to load DB %s: %s", selected_file, e)
                    flash(f"Could not load selected DB: {e}", "danger")
                    return redirect("/manage_files")
                
                file_number = selected_file.split(".")[0]
                vname = get_village_name_from_db(local_path)
                session["village_name"] = f"{file_number} - {vname}"
                return redirect("/dashboard")

    active_db = session.get("active_db")
    local_path = session.get("active_path")
    village_name = session.get("village_name", "Unknown")
    total_customers = sum_amt = sum_pamt = sum_bamt = 0

    if active_db and local_path:
        try:
            conn = sqlite3.connect(local_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(AMT), SUM(PAMT), SUM(BAMT) FROM LOANEE")
            row = cursor.fetchone()
            if row:
                total_customers, sum_amt, sum_pamt, sum_bamt = row
        except Exception as e:
            app.logger.exception("Dashboard calculation error: %s", e)
        finally:
            try:
                conn.close()
            except:
                pass

    return render_template("dashboard.html",
                           files=files,
                           selected_file=session.get("active_db"),
                           village_name=session.get("village_name", "Unknown"),
                           total_customers=total_customers,
                           sum_amt=sum_amt,
                           sum_pamt=sum_pamt,
                           sum_bamt=sum_bamt)

@app.route("/reselect", methods=["POST"])
def reselect():
    session.pop("active_db", None)
    session.pop("active_path", None)
    session.pop("village_name", None)
    return redirect("/dashboard")
# ----------------------------------------------------
# Manage files - example routes updated to pass bucket
# ----------------------------------------------------
@app.route("/manage_files")
@login_required
def manage_files():
    return render_template("manage_files.html", files=dbm.list_gcs_files(bucket=session.get("bucket")))

@app.route("/upload_to_gcs", methods=["POST"])
@login_required
def upload_to_gcs_route():
    """
    Accept multiple files (input name 'files') and upload each.
    Returns JSON with uploaded file names (client-side JS expects JSON).
    """
    if "files" not in request.files:
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    uploaded = []
    user_bucket = session.get("bucket") or os.environ.get("GCS_DEFAULT_BUCKET")

    for f in files:
        filename = f.filename or ""
        if not filename.lower().endswith(".sqlite"):
            continue
        safe_name = secure_filename(filename)
        tmp_path = os.path.join("/tmp", safe_name)
        try:
            f.save(tmp_path)
            dbm.upload_to_gcs(tmp_path, safe_name, bucket=user_bucket)
            uploaded.append(safe_name)
        except Exception as ex:
            app.logger.exception("upload failed %s", ex)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass

    return jsonify({"uploaded": uploaded}), 200

@app.route("/delete_from_gcs", methods=["POST"])
@login_required
def delete_from_gcs_route():
    filename = request.form.get("filename")
    if not filename:
        flash("Missing filename", "danger")
        return redirect("/manage_files")
    bucket = session.get("bucket") or os.environ.get("GCS_DEFAULT_BUCKET")
    try:
        dbm.delete_from_gcs(filename, bucket=bucket)
        flash("Deleted", "success")
    except Exception as e:
        app.logger.exception("delete failed: %s", e)
        flash("Delete failed", "danger")
    return redirect("/manage_files")

@app.route("/download_gcs/<path:filename>")
@login_required
def download_gcs_file(filename):
    bucket = session.get("bucket") or os.environ.get("GCS_DEFAULT_BUCKET")
    try:
        local_path = dbm.download_from_gcs(filename, local_path=os.path.join("/tmp", os.path.basename(filename)), bucket=bucket)
        return send_file(local_path, as_attachment=True, download_name=filename)
    except FileNotFoundError:
        return "Not found", 404
    except Exception as ex:
        app.logger.exception("download error: %s", ex)
        return "Internal server error", 500

@app.route("/select_gcs_file", methods=["POST"])
@login_required
def select_gcs_file():
    filename = request.form.get("filename")
    if not filename:
        flash("No file chosen", "danger")
        return redirect("/manage_files")
    bucket = session.get("bucket") or os.environ.get("GCS_DEFAULT_BUCKET")
    try:
        # download to /tmp and set active
        local_path = dbm.get_local_db_path(filename, bucket=bucket)
        session["active_db"] = filename
        session["active_path"] = local_path
        # set village name immediately
        try:
            vname = get_village_name_from_db(local_path)
            file_number = filename.split(".")[0]
            session["village_name"] = f"{file_number} - {vname}"
        except Exception:
            session["village_name"] = filename
        flash("File set", "success")
    except Exception as ex:
        app.logger.exception("select_gcs_file error: %s", ex)
        flash("Could not select file: " + str(ex), "danger")
    return redirect("/dashboard")

# ----------------------------------------------------
# CREATE VILLAGE
# ----------------------------------------------------
@app.route("/create_village", methods=["POST"])
def create_village():
    try:
        data = request.get_json()
        number = data.get("number", "").strip()
        name = data.get("name", "").strip()

        if not number or not name:
            return jsonify({"success": False, "error": "Missing fields"}), 400

        filename = f"{number}.sqlite"
        local_path = f"/tmp/{filename}"

        # --- Create a new SQLite database with LOANEE table ---
        conn = sqlite3.connect(local_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE LOANEE (
                ANO TEXT PRIMARY KEY, NAME TEXT, ADD1 TEXT, ADD2 TEXT, ADD3 TEXT,
                FDT TEXT, TDT TEXT, AMT REAL, PAMT REAL, BAMT REAL,
                DA REAL, DW TEXT, DS INTEGER, PANO TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE PAMT1 (
                ANO TEXT, PDT TEXT, AMT REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE EXAMT (
                DT TEXT, AMT REAL, LAMT REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE META (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cursor.execute("INSERT INTO META (key, value) VALUES (?, ?)", ("village_name", name))

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_ano ON PAMT1(ANO)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_pdt ON PAMT1(PDT)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_amt ON PAMT1(AMT)")

        conn.commit()
        conn.close()


        # --- Upload to GCS ---
        upload_to_gcs(local_path, filename)

        return jsonify({"success": True})

    except Exception as e:
        print("Create village error:", e)
        return jsonify({"success": False, "error": str(e)}), 500
# ----------------------------------------------------
# ADD CUSTOMER
# ----------------------------------------------------
@app.route("/check_parent_link")
def check_parent_link():
    pano = request.args.get("pano", "").strip()
    if not pano:
        return jsonify({"found": False, "accounts": []})

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Find accounts where PARENT or PANO column matches; be permissive
        # First try exact numeric match
        try:
            pano_int = int(pano)
            cursor.execute("SELECT ANO FROM LOANEE WHERE PANO = ? OR ANO = ? LIMIT 20", (pano_int, pano_int))
            rows = cursor.fetchall()
        except Exception:
            cursor.execute("SELECT ANO FROM LOANEE WHERE CAST(PANO AS TEXT) = ? OR CAST(ANO AS TEXT) = ? LIMIT 20", (pano, pano))
            rows = cursor.fetchall()

        accounts = [r["ANO"] for r in rows] if rows else []
        return jsonify({"found": bool(accounts), "accounts": accounts})
    except Exception as ex:
        app.logger.exception("check_parent_link error: %s", ex)
        return jsonify({"found": False, "accounts": []})
    finally:
        if conn:
            conn.close()


@app.route("/add_customer", methods=["GET", "POST"])
@login_required
def add_customer():
    active_db = session.get("active_db")
    if not active_db:
        return redirect("/dashboard")

    if request.method == "POST":
        try:
            conn = connect_db_from_gcs()
            cursor = conn.cursor()

            data = request.form
            ano = data["ano"].strip()
            name = data["name"].strip()
            add1 = data["add1"].strip()
            add2 = data["add2"].strip()
            add3 = data["add3"].strip()
            dw = data["dw"].strip()
            fdt_str = data["fdt"].strip()
            ds = int(data["ds"]) if data["ds"] else 0
            amt = float(data["amt"]) if data["amt"] else 0
            pano = data["pano"].strip()

            cursor.execute("SELECT 1 FROM LOANEE WHERE ANO=?", (ano,))
            if cursor.fetchone():
                return jsonify(error="Customer exists"), 400

            pamt = 0
            bamt = amt
            da = round(amt / ds, 2) if ds > 0 else 0

            fdt = datetime.datetime.strptime(fdt_str, "%d/%m/%Y")
            if dw == "M":
                tdt = fdt + relativedelta(months=ds)
            else:
                tdt = fdt + timedelta(weeks=ds)

            cursor.execute("""
                INSERT INTO LOANEE
                (ANO, NAME, ADD1, ADD2, ADD3, FDT, TDT, AMT,
                 PAMT, BAMT, DA, DW, DS, PANO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ano, name, add1, add2, add3,
                fdt.strftime("%d/%m/%Y"),
                tdt.strftime("%d/%m/%Y"),
                amt, pamt, bamt, da, dw, ds, pano
            ))

            conn.commit()
            cursor.execute("SELECT MAX(ANO) FROM LOANEE")
            highest_ano = cursor.fetchone()[0]
            sync_active_db_to_gcs()

            return jsonify({"message": "Customer added","highest_ano": highest_ano})

        except Exception as e:
            traceback.print_exc()
            return jsonify(error=str(e)), 500

    # GET mode → show next ANO
    conn = connect_db_from_gcs()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(CAST(ANO AS INTEGER)) FROM LOANEE")
    highest_ano = cursor.fetchone()[0] or 0

    return render_template("add_customer.html", highest_ano=highest_ano)

@app.route("/post_payment", methods=["GET"])
@login_required
def post_payment_page():
    active_db = session.get("active_db")
    if not active_db:
        return redirect("/dashboard")
    customers = get_all_customers()
    return render_template("post_payment.html", customers=customers)

def get_all_customers():
    """Return all customers from LOANEE table."""
    conn = None
    try:
        local_path = session.get("active_path")
        if not local_path or not os.path.exists(local_path):
            print("❌ No active DB path in session")
            return []

        conn = sqlite3.connect(local_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM LOANEE ORDER BY CAST(ANO AS INTEGER)")
        rows = cursor.fetchall()
        print("✔ get_all_customers fetched:", len(rows))
        print("\n======= DEBUG: get_all_customers() =======")
        print("Local DB Path:", local_path)
        print("Total Rows Fetched:", len(rows))

        try:
            anos = [row["ANO"] for row in rows]
            print("ANO list:", anos)
        except:
            print("Could not list ANO values")

        print("==========================================\n")
        return [dict(row) for row in rows]
    except Exception as e:
        print("get_all_customers error:", e)
        return []
    finally:
        if conn:
            conn.close()
# ----------------------------------------------------
# POST PAYMENT
# ----------------------------------------------------
@app.route("/get_customer_info")
def get_customer_info():
    ano = request.args.get("ano", "").strip()
    if not ano:
        return jsonify({"error": "missing ano"}), 400

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try to locate the row by numeric or text ANO
        found = None
        try:
            ano_int = int(ano)
            cursor.execute("SELECT * FROM LOANEE WHERE ANO = ? LIMIT 1", (ano_int,))
            found = cursor.fetchone()
        except Exception:
            cursor.execute("SELECT * FROM LOANEE WHERE CAST(ANO AS TEXT) = ? LIMIT 1", (ano,))
            found = cursor.fetchone()

        if not found:
            return jsonify({"error": "not found"}), 404

        # Safe extraction of columns
        def _getval(row, name):
            try:
                return row[name]
            except Exception:
                return None

        name = _getval(found, "NAME") or ""
        amt = _getval(found, "AMT") or 0
        pamt = _getval(found, "PAMT") or 0
        bamt = _getval(found, "BAMT") or 0
        da = _getval(found, "DA") or 0

        # Normalize numbers to floats (or formatted strings if you prefer)
        try:
            amt = float(amt or 0)
        except Exception:
            amt = 0.0
        try:
            pamt = float(pamt or 0)
        except Exception:
            pamt = 0.0
        try:
            bamt = float(bamt or 0)
        except Exception:
            bamt = 0.0

        print("\n------- DEBUG: get_customer_info() -------")
        print("Requested ANO:", ano)
        print("Found? ->", "YES" if found else "NO")
        if found:
            print("Name:", name)
            print("AMT:", amt, "PAMT:", pamt, "BAMT:", bamt)
        print("------------------------------------------\n")

        return jsonify({
            "name": name,
            "amt": amt,
            "pamt": pamt,
            "bamt": bamt,
            "da": da
        })
    except Exception as ex:
        app.logger.exception("get_customer_info error: %s", ex)
        return jsonify({"error": "internal"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/check_ano_exists")
def check_ano_exists():
    ano = request.args.get("ano", "").strip()
    if not ano:
        return jsonify({"exists": False})

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try numeric match first, then fallback to text match
        try:
            ano_int = int(ano)
            cursor.execute("SELECT 1 FROM LOANEE WHERE ANO = ? LIMIT 1", (ano_int,))
            found = cursor.fetchone() is not None
            if found:
                print("\n------- DEBUG: check_ano_exists() -------")
                print("ANO Requested:", ano)
                print("Row Exists:", found)
                print("-----------------------------------------\n")
                return jsonify({"exists": True})
        except Exception:
            # not int — fall through to text match
            pass

        cursor.execute("SELECT 1 FROM LOANEE WHERE CAST(ANO AS TEXT) = ? LIMIT 1", (ano,))
        found = cursor.fetchone() is not None
        print("\n------- DEBUG: check_ano_exists() -------")
        print("ANO Requested:", ano)
        print("Row Exists:", found)
        print("-----------------------------------------\n")
        return jsonify({"exists": bool(found)})
    except Exception as ex:
        app.logger.exception("check_ano_exists error: %s", ex)
        return jsonify({"exists": False})
    finally:
        if conn:
            conn.close()

@app.route("/submit_post_payment", methods=["POST"])
def submit_post_payment():
    active_db = session.get("active_db")
    if not active_db:
        return jsonify(error="No DB selected"), 400

    data = request.get_json()
    if not data:
        return jsonify(error="No data received"), 400

    try:
        conn = connect_db_from_gcs()
        cursor = conn.cursor()

        submitted = 0
        skipped = []

        for row in data:
            ano = row["ano"]
            pdt = row["pdt"]
            amt = float(row["amt"])

            cursor.execute("SELECT 1 FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
            if cursor.fetchone():
                skipped.append(row)
                continue

            cursor.execute("INSERT INTO PAMT1 (ANO, PDT, AMT) VALUES (?, ?, ?)", (ano, pdt, amt))
            cursor.execute("UPDATE LOANEE SET PAMT = PAMT + ?, BAMT = BAMT - ? WHERE ANO=?", (amt, amt, ano))
            submitted += 1

        conn.commit()
        sync_active_db_to_gcs()

        return jsonify(
            message=f"{submitted} posted, {len(skipped)} skipped",
            skipped_rows=skipped
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500

import datetime

def _find_payment_table(cursor):
    # return table name that contains both ANO and PDT columns (if any)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    for t in tables:
        try:
            cursor.execute(f"PRAGMA table_info('{t}')")
            cols = [r[1].upper() for r in cursor.fetchall()]
            if 'ANO' in cols and 'PDT' in cols:
                return t
        except Exception:
            continue
    return None

@app.route("/check_payment_exists")
def check_payment_exists():
    ano = request.args.get("ano", "").strip()
    pdt = request.args.get("pdt", "").strip()  # dd/mm/yyyy expected
    if not ano or not pdt:
        return jsonify({"exists": False})

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        payment_table = _find_payment_table(cursor)
        if not payment_table:
            # can't determine payment table -> return not found to allow client to proceed
            return jsonify({"exists": False})

        # normalize date format in DB same as what is stored; we try multiple patterns
        # assume DB stores PDT like dd/mm/yyyy (common in existing app)
        # Query using text equality
        cursor.execute(f"SELECT 1 FROM {payment_table} WHERE CAST(ANO AS TEXT)=? AND PDT = ? LIMIT 1", (ano, pdt))
        found = cursor.fetchone() is not None
        return jsonify({"exists": bool(found)})
    except Exception as ex:
        app.logger.exception("check_payment_exists error: %s", ex)
        return jsonify({"exists": False})
    finally:
        if conn:
            conn.close()
# ---------- Part 2: Remaining routes (GCS-enabled) ----------
# used for helper funcs like update_loanee_balances

def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


@app.route('/get_customers_data/<filename>')
def get_customers_data(filename):
    """Return LOANEE rows for the given filename (served from active/selected)."""
    # Security: ensure requested filename matches active_db or is in GCS
    active_db = session.get("active_db")
    if filename != active_db:
        # Prevent arbitrary file access — require selection or return error
        return jsonify({"error": "File not active"}), 403

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM LOANEE")
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description]
        data = [dict(zip(columns, r)) for r in rows]
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/view_customers")
@login_required
def view_customers():
    # --- restore top bar data ---
    files = list_gcs_files()
    active_db = session.get("active_db")
    village_name = session.get("village_name", "Unknown")

    if not active_db:
        return redirect("/dashboard")

    conn = None
    try:
        # 🔥 FIX  — always load correct local DB path
        local_path = get_active_db_path()

        conn = sqlite3.connect(local_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM LOANEE")
        rows = cursor.fetchall()

        # --- Restore original header extraction ---
        headers = [col[0] for col in cursor.description]

        # --- Restore original field mapping ---
        col_map = {name: i for i, name in enumerate(headers)}
        amt_idx = col_map.get("AMT", -1)
        pamt_idx = col_map.get("PAMT", -1)
        bamt_idx = col_map.get("BAMT", -1)
        da_idx = col_map.get("DA", -1)

        processed = []
        for r in rows:
            row_list = list(r)

            # Convert numerics
            if amt_idx != -1:
                row_list[amt_idx] = float(row_list[amt_idx] or 0)
            if pamt_idx != -1:
                row_list[pamt_idx] = float(row_list[pamt_idx] or 0)
            if bamt_idx != -1:
                row_list[bamt_idx] = float(row_list[bamt_idx] or 0)
            if da_idx != -1:
                row_list[da_idx] = float(row_list[da_idx] or 0)

            processed.append(row_list)

        # --- Restore summary calculations ---
        total_customers = len(processed)
        sum_amt = sum(row[amt_idx] for row in processed) if amt_idx != -1 else 0
        sum_pamt = sum(row[pamt_idx] for row in processed) if pamt_idx != -1 else 0
        sum_bamt = sum(row[bamt_idx] for row in processed) if bamt_idx != -1 else 0

        return render_template(
            "view_customers.html",
            headers=headers,
            data=processed,
            total_customers=total_customers,
            sum_amt=sum_amt,
            sum_pamt=sum_pamt,
            sum_bamt=sum_bamt,
            files=files,
            selected_file=active_db,
            village_name=village_name
        )

    except Exception as e:
        print("Error in view_customers:", e)
        return "Something went wrong loading customers.", 500
    finally:
        if conn:
            conn.close()


@app.route("/search", methods=["GET", "POST"])
@login_required
def search_customer():
    active_db = session.get("active_db")
    if not active_db:
        return redirect("/dashboard")

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        conn = None
        try:
            conn = connect_db_from_gcs()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            search_like = f"%{query}%"
            cursor.execute("SELECT * FROM LOANEE WHERE ANO = ? OR NAME LIKE ?", (query, search_like))
            customers = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description]

            pamt1_records = {}
            for cust in customers:
                ano = cust[headers.index("ANO")]
                cursor.execute("SELECT * FROM PAMT1 WHERE ANO = ?", (ano,))
                pamt1_records[ano] = cursor.fetchall()

            return render_template("search.html", customers=customers, loanee_headers=headers, pamt1_records=pamt1_records, query=query)

        except Exception as e:
            traceback.print_exc()
            return "Search error", 500
        finally:
            if conn:
                conn.close()

    # GET
    return render_template("search.html")


# ----------- New /search_postings route -----------
@app.route("/search_postings", methods=["POST"])
@login_required
def search_postings():
    active_db = session.get("active_db")
    if not active_db:
        return jsonify(success=False, error="No DB selected")

    payload = request.get_json(force=True)
    ano = (payload.get("ano") or "").strip()
    date = (payload.get("date") or "").strip()

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = "SELECT ANO, PDT, AMT FROM PAMT1 WHERE 1=1"
        params = []

        # If user entered A.no → exact match
        if ano:
            sql += " AND CAST(ANO AS TEXT) = ?"
            params.append(ano)

        # If user entered Date dd/mm/yyyy → match exact PDT
        if date:
            sql += " AND PDT = ?"
            params.append(date)

        sql += " ORDER BY substr(PDT,7,4)||substr(PDT,4,2)||substr(PDT,1,2) ASC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "ANO": r["ANO"],
                "PDT": r["PDT"],
                "AMT": r["AMT"]
            })

        return jsonify(success=True, data=results)

    except Exception as e:
        print("search_postings error:", e)
        return jsonify(success=False, error=str(e))

    finally:
        if conn:
            conn.close()


@app.route("/update_customer_and_payments", methods=["POST"])
def update_customer_and_payments():
    active_db = session.get("active_db")
    if not active_db:
        return jsonify(success=False, error="No DB file selected")

    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data received")

    update_type = data.get("type")
    conn = None

    try:
        conn = connect_db_from_gcs()
        cursor = conn.cursor()

        if update_type == "customer":
            customer = data.get("data", {})
            if not customer or "ANO" not in customer:
                return jsonify(success=False, error="Invalid customer data")

            amt = safe_float(customer.get("AMT", 0))
            pamt = safe_float(customer.get("PAMT", 0))
            bamt = safe_float(customer.get("BAMT", 0))
            da = safe_float(customer.get("DA", 0))
            ds = int(customer.get("DS", 0) or 0)

            cursor.execute("""
                UPDATE LOANEE SET
                    NAME=?, ADD2=?, ADD3=?, FDT=?, TDT=?,
                    AMT=?, PAMT=?, BAMT=?, DA=?, DW=?, DS=?, PANO=?
                WHERE ANO=?
            """, (
                customer.get("NAME", ""), customer.get("ADD2", ""), customer.get("ADD3", ""),
                customer.get("FDT", ""), customer.get("TDT", ""), amt,
                pamt, bamt, da,
                customer.get("DW", ""), ds, customer.get("PANO", ""), customer["ANO"]
            ))

        elif update_type == "payment_posting_update":
            upd = data.get("data", {})
            ano = upd.get("ano")
            original_pdt = upd.get("original_pdt")
            new_pdt = upd.get("new_pdt")
            new_amt = safe_float(upd.get("new_amt", 0))

            if not all([ano, original_pdt, new_pdt]):
                return jsonify(success=False, error="Missing required data")

            cursor.execute("UPDATE PAMT1 SET PDT = ?, AMT = ? WHERE ANO = ? AND PDT = ?", (new_pdt, new_amt, ano, original_pdt))
            # update balances helper
            try:
                dbm.update_loanee_balances(conn, ano)
            except AttributeError:
                # Fall back: compute balances if helper missing
                pass

        elif update_type == "payments":
            updated = data.get("data", [])
            anos_to_update = set()
            for row in updated:
                cursor.execute("UPDATE PAMT1 SET AMT = ? WHERE ANO = ? AND PDT = ?", (safe_float(row.get("amt", 0)), row.get("ano", ""), row.get("pdt", "")))
                anos_to_update.add(row.get("ano", ""))
            for ano in anos_to_update:
                try:
                    dbm.update_loanee_balances(conn, ano)
                except AttributeError:
                    pass

        else:
            return jsonify(success=False, error="Unknown update type")

        conn.commit()
        sync_active_db_to_gcs()
        return jsonify(success=True)

    except Exception as e:
        if conn:
            conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()


@app.route("/add_payment", methods=["POST"])
def add_payment():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify(success=False, error="No data received")

    ano = data.get("ano")
    pdt = data.get("pdt")
    amt = safe_float(data.get("amt", 0))

    if not ano or not pdt:
        return jsonify(success=False, error="Missing ano or date")

    conn = None
    try:
        conn = connect_db_from_gcs()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
        if cursor.fetchone()[0] > 0:
            return jsonify(success=False, error="Duplicate entry exists")

        cursor.execute("INSERT INTO PAMT1 (ANO, PDT, AMT) VALUES (?, ?, ?)", (ano, pdt, amt))
        try:
            dbm.update_loanee_balances(conn, ano)
        except AttributeError:
            pass

        conn.commit()
        sync_active_db_to_gcs()
        return jsonify(success=True)

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()


@app.route("/delete_payment", methods=["POST"])
def delete_payment():
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data received")

    ano = data.get("ano")
    pdt = data.get("pdt")
    if not ano or not pdt:
        return jsonify(success=False, error="Missing ano or pdt")

    conn = None
    try:
        conn = connect_db_from_gcs()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
        try:
            dbm.update_loanee_balances(conn, ano)
        except AttributeError:
            pass

        conn.commit()
        sync_active_db_to_gcs()
        return jsonify(success=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()


@app.route("/update_posting_date_bulk", methods=["POST"]) 
@login_required
def update_posting_date_bulk():
    """Bulk replace PDT values in PAMT1.
    Expects JSON: { "find_date": "dd/mm/yyyy", "replace_date": "dd/mm/yyyy" }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify(success=False, error="No data received"), 400

    find_date = (data.get("find_date") or "").strip()
    replace_date = (data.get("replace_date") or "").strip()
    if not find_date or not replace_date:
        return jsonify(success=False, error="Missing find_date or replace_date"), 400

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # collect affected ANO values (so balances can be recalculated per-account)
        cursor.execute("SELECT ANO FROM PAMT1 WHERE PDT = ?", (find_date,))
        rows = cursor.fetchall()
        affected_anos = [r[0] for r in rows]

        # perform the update
        cursor.execute("UPDATE PAMT1 SET PDT = ? WHERE PDT = ?", (replace_date, find_date))

        # attempt to refresh LOANEE balances for affected accounts
        for ano in set(affected_anos):
            try:
                dbm.update_loanee_balances(conn, ano)
            except Exception:
                # if helper missing or fails, continue — we'll still commit the date changes
                app.logger.exception("Failed to update balances for %s", ano)

        conn.commit()
        sync_active_db_to_gcs()

        return jsonify(success=True, message=f"Updated dates for {len(rows)} rows across {len(set(affected_anos))} accounts")

    except Exception as e:
        if conn:
            conn.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()


@app.route('/get_payments_data/<filename>')
def get_payments_data(filename: str):
    active_db = session.get("active_db")
    if filename != active_db:
        return jsonify({"error": "File not active"}), 403

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PAMT1")
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        data = [dict(zip(cols, r)) for r in rows]
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()


@app.route("/post_payment_report", methods=["GET", "POST"])
@login_required
def post_payment_report():
    active_db = session.get("active_db")
    if not active_db:
        return redirect("/dashboard")
    
    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # ensure indexes exist (no harm if they already do)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_ano ON PAMT1 (ANO)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_pdt ON PAMT1 (PDT)")

        ano_filter = request.form.get("ano_filter", "").strip()
        from_date = request.form.get("from_date", "")
        to_date = request.form.get("to_date", "")

        date_transform = "substr(PDT, 7, 4) || '-' || substr(PDT, 4, 2) || '-' || substr(PDT, 1, 2)"
        query = f"SELECT ANO, PDT, AMT FROM PAMT1 WHERE 1=1"
        params = []

        if ano_filter:
            query += " AND ANO = ?"
            params.append(ano_filter)

        def to_db_date(d):
            return datetime.datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")

        if from_date and to_date:
            query += f" AND {date_transform} BETWEEN ? AND ?"
            params.extend([to_db_date(from_date), to_db_date(to_date)])
        elif from_date:
            query += f" AND {date_transform} = ?"
            params.append(to_db_date(from_date))

        query += f" ORDER BY {date_transform} DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        payments = [list(r) for r in rows]

        return render_template("post_payment_report.html", payments=payments, ano_filter=ano_filter, from_date=from_date, to_date=to_date)

    except Exception as e:
        traceback.print_exc()
        return "Something went wrong.", 500
    finally:
        if conn:
            conn.close()


@app.route('/print_customer/<ano>')
def print_customer(ano):
    active_db = session.get("active_db")
    if not active_db:
        return "No village selected.", 400

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ANO, NAME, ADD1, ADD2, FDT, TDT, AMT, PAMT, BAMT, DA, DW, DS
            FROM LOANEE
            WHERE ANO = ?
        """, (ano,))
        customer = cursor.fetchone()
        if not customer:
            return "Customer not found.", 404

        cursor.execute("""
            SELECT PDT, AMT FROM PAMT1 WHERE ANO = ? ORDER BY
            substr(PDT,7,4) || substr(PDT,4,2) || substr(PDT,1,2) ASC
        """, (ano,))
        payments = cursor.fetchall()

        customer_data = {
            'ano': customer[0],
            'name': customer[1],
            'village': customer[2],
            'parent_ano': customer[3],
            'fdt': customer[4],
            'tdt': customer[5],
            'amt': customer[6],
            'pamt': customer[7],
            'bamt': customer[8],
            'da': customer[9],
            'dw': customer[10],
            'ds': customer[11]
        }

        payments_data = [{'pdt': row[0], 'amt': row[1]} for row in payments]

        return render_template('customer_print.html', customer=customer_data, payments=payments_data)

    except Exception as e:
        traceback.print_exc()
        return "Something went wrong.", 500
    finally:
        if conn:
            conn.close()

# ----------------------------------------------------
# USER MANAGEMENT PAGE
# ----------------------------------------------------
def list_users():
    conn = _open_auth_conn()
    _ensure_auth_schema(conn)   # ensure schema present
    c = conn.cursor()
    c.execute("SELECT username, system_id, notes, role, team FROM USERS ORDER BY username")
    rows = c.fetchall()
    conn.close()
    return [{
        "username": r[0], 
        "system_id": r[1], 
        "notes": r[2], 
        "role": (r[3] or "user"),
        "team": (r[4] or "teamA")
        } for r in rows]


def create_user(username, raw_password, system_id=None, notes=None, role="user", team="teamA"):
    conn = _open_auth_conn()
    _ensure_auth_schema(conn)
    c = conn.cursor()
    pw_hash = generate_password_hash(raw_password, method="pbkdf2:sha256")
    c.execute("""
      INSERT OR REPLACE INTO USERS (username, password_hash, system_id, notes, role, team)
      VALUES (?, ?, ?, ?, ?, ?)
    """, (username, pw_hash, system_id, notes, role, team))
    _commit_and_upload_auth(conn)


def update_user(username, new_username=None, new_password=None, system_id=None, notes=None, role=None, team=None):
    conn = _open_auth_conn()
    _ensure_auth_schema(conn)
    c = conn.cursor()
    if new_username and new_username != username:
        # rename: copy password_hash then delete old row
        c.execute("SELECT password_hash FROM USERS WHERE username=?", (username,))
        row = c.fetchone()
        if not row:
            conn.close()
            raise ValueError("User not found")
        pw_hash = row[0]
        c.execute("DELETE FROM USERS WHERE username=?", (username,))
        c.execute("INSERT OR REPLACE INTO USERS (username, password_hash, system_id, notes, role, team) VALUES (?, ?, ?, ?, ?, ?)",
                  (new_username, pw_hash, system_id, notes, role or "user", team or "teamA"))
    else:
        if new_password:
            pw_hash = generate_password_hash(new_password, method="pbkdf2:sha256")
            c.execute("UPDATE USERS SET password_hash=? WHERE username=?", (pw_hash, username))
        if system_id is not None:
            c.execute("UPDATE USERS SET system_id=? WHERE username=?", (system_id, username))
        if notes is not None:
            c.execute("UPDATE USERS SET notes=? WHERE username=?", (notes, username))
        if role is not None:
            c.execute("UPDATE USERS SET role=? WHERE username=?", (role, username))
        if team is not None:
            c.execute("UPDATE USERS SET team=? WHERE username=?", (team, username))
    _commit_and_upload_auth(conn)


def delete_user(username):
    conn = _open_auth_conn()
    c = conn.cursor()
    c.execute("DELETE FROM USERS WHERE username=?", (username,))
    _commit_and_upload_auth(conn)

def check_credentials(username, raw_password, device_id=None):
    """Return (True, '') if ok, else (False, 'reason msg')"""
    conn = _open_auth_conn()
    c = conn.cursor()
    c.execute("SELECT password_hash, system_id, role, team FROM USERS WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False, "Unknown username"
    stored_hash = row[0]
    allowed_system_id = row[1]
    # role/team are available in row[2], row[3] if caller needs them
    if not check_password_hash(stored_hash, raw_password):
        return False, "Invalid password"
    # If user has a system_id set, check it must match device_id
    if allowed_system_id and device_id and allowed_system_id != device_id:
        return False, "This user is allowed only from a specific device"
    if allowed_system_id and not device_id:
        # strict: require device id header
        return False, "Device ID header required"
    return True, ""
# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    init_auth_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))