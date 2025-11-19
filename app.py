
import os
import sqlite3
import traceback
import datetime
import logging
from google.cloud import storage
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from database_manager import GCS_BUCKET, _get_client, get_local_db_path
from flask import (
    Flask, render_template, request, redirect,
    session, jsonify, flash, send_file
)
from werkzeug.utils import secure_filename

# GCS Database manager
from database_manager import (
    list_gcs_files,
    get_local_db_path,
    upload_to_gcs,
    delete_from_gcs,
    download_from_gcs,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------
# FLASK APP SETUP
# ----------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")


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
    """Reads village name stored in META or LOANEE table."""
    try:
        local_path = get_active_db_path()
        conn = sqlite3.connect(local_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT ADD1 FROM LOANEE WHERE ADD1 IS NOT NULL AND ADD1 != '' LIMIT 1")
        row = cursor.fetchone()
        if row:
            name = row["ADD1"]
            if name.strip() and name.strip().lower() != "unknown":
                return name

        cursor.execute("SELECT value FROM META WHERE key='village_name'")
        row = cursor.fetchone()
        return row["value"] if row else "Unknown"

    except Exception as e:
        print("Village name error:", e)
        return "Unknown"
    finally:
        try: conn.close()
        except: pass


# ----------------------------------------------------
# CONTEXT FOR TEMPLATES
# ----------------------------------------------------
@app.context_processor
def inject_layout_data():
    return {
        "active_db": session.get("active_db"),
        "village_name": session.get("village_name", ""),
        "files": list_gcs_files(),
    }


# ----------------------------------------------------
# ROUTES
# ----------------------------------------------------

@app.route("/")
def home():
    return redirect("/dashboard")

def get_active_db_path():
    path = session.get("active_path")
    if not path:
        raise Exception("No active database selected.")
    return path
# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    files = list_gcs_files()

    if request.method == "POST":
        selected_file = request.form.get("village_db")

        # ===============================
        # FIX #2 — ensure clean filename
        # ===============================
        if selected_file:
            # In case HTML sends a dict or extra spaces
            selected_file = str(selected_file).strip()

            # Ensure only actual filename is stored
            # (Protects from accidental dict-like inputs)
            if isinstance(selected_file, dict):
                selected_file = selected_file.get("name", "")
            # ===============================

            if selected_file:
                # Save active DB name
                session["active_db"] = selected_file

                # Download from GCS → /tmp
                try:
                  local_path = get_local_db_path(selected_file)   # WILL download and return /tmp path
                except Exception as e:
                    # log & show error, do not try to query the DB
                    app.logger.exception("Failed to load DB %s: %s", selected_file, e)
                    flash(f"Could not load selected DB: {e}", "danger")
                    return redirect("/manage_files") 
                session["active_path"] = local_path

                # Get friendly village name
                file_number = selected_file.split(".")[0]
                vname = get_village_name_from_db(local_path)
                session["village_name"] = f"{file_number} - {vname}"

                return redirect("/dashboard")

    # ------------ GET MODE ------------
    active_db = session.get("active_db")
    local_path = session.get("active_path")
    village_name = session.get("village_name", "Unknown")

    total_customers = sum_amt = sum_pamt = sum_bamt = 0

    if active_db and local_path:
        try:
            local_path = get_active_db_path()
            conn = sqlite3.connect(local_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(AMT), SUM(PAMT), SUM(BAMT) FROM LOANEE")
            row = cursor.fetchone()
            if row:
                total_customers, sum_amt, sum_pamt, sum_bamt = row
        except sqlite3.OperationalError as e:
        # most common: table doesn't exist -> show friendly message & log
           app.logger.exception("Database schema problem for %s: %s", active_db, e)
           flash("Selected database does not appear to have the expected schema (missing tables).", "warning")
           total_customers = sum_amt = sum_pamt = sum_bamt = 0
        except Exception as e:
           app.logger.exception("Unexpected error reading DB %s: %s", active_db, e)
        finally:
            try:
              conn.close()
            except:
               pass

    return render_template(
        "dashboard.html",
        files=files,
        selected_file=active_db,
        village_name=village_name,
        total_customers=total_customers,
        sum_amt=sum_amt,
        sum_pamt=sum_pamt,
        sum_bamt=sum_bamt,
    )


@app.route("/reselect", methods=["POST"])
def reselect():
    session.pop("active_db", None)
    session.pop("active_path", None)
    session.pop("village_name", None)
    return redirect("/dashboard")
# ----------------------------------------------------
# MANAGE FILES (GCS)
# ----------------------------------------------------
@app.route("/manage_files")
def manage_files():
    return render_template(
        "manage_files.html",
        files=list_gcs_files(),
        gcs_bucket=os.environ.get("GCS_BUCKET")
    )


@app.route("/upload_to_gcs", methods=["POST"])
def upload_to_gcs_route():
    # Expecting multiple files named "files"
    if "files" not in request.files:
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    uploaded = []
    client = _get_client()
    # If you need bucket from env/config, your upload_to_gcs helper should use it.
    for f in files:
        # filter: only .sqlite
        filename = f.filename or ""
        if not filename.lower().endswith(".sqlite"):
            # skip non-sqlite files silently
            continue

        safe_name = secure_filename(filename)
        # create a temporary file in /tmp
        tmp_dir = "/tmp"
        tmp_path = os.path.join(tmp_dir, safe_name)

        try:
            f.save(tmp_path)
            # call your helper which uploads local file to GCS (keep its signature)
            # here I assume upload_to_gcs(local_path, target_name) is available
            upload_to_gcs(tmp_path, safe_name)
            uploaded.append(safe_name)
        except Exception as ex:
            app.logger.exception("Failed to upload %s: %s", safe_name, ex)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    return jsonify({"uploaded": uploaded}), 200


@app.route("/delete_from_gcs", methods=["POST"])
def delete_from_gcs_route():
    delete_from_gcs(request.form["filename"])
    return redirect("/manage_files")


@app.route("/download_gcs/<path:filename>")
def download_gcs_file(filename):
    try:
        # download_from_gcs should return a local filesystem path (e.g. /tmp/filename)
        local_path = download_from_gcs(filename)
        if not local_path or not os.path.exists(local_path):
            app.logger.warning("download_gcs: local file not found for %s", filename)
            return "Not found", 404

        return send_file(local_path, as_attachment=True, download_name=filename)
    except Exception as ex:
        app.logger.exception("Error downloading %s: %s", filename, ex)
        return "Internal server error", 500

@app.route("/select_gcs_file", methods=["POST"])
def select_gcs_file():
    filename = request.form["filename"]
    local_path = download_from_gcs(filename)
    session["ACTIVE_DB"] = filename
    return redirect("/dashboard")


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

            fdt = datetime.strptime(fdt_str, "%d/%m/%Y")
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
            sync_active_db_to_gcs()

            return jsonify(message="Customer added")

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
def post_payment_page():
    active_db = session.get("active_db")
    if not active_db:
        return redirect("/dashboard")

    return render_template("post_payment.html")
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
                return jsonify({"exists": True})
        except Exception:
            # not int — fall through to text match
            pass

        cursor.execute("SELECT 1 FROM LOANEE WHERE CAST(ANO AS TEXT) = ? LIMIT 1", (ano,))
        found = cursor.fetchone() is not None
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
import database_manager as db  # used for helper funcs like update_loanee_balances

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
                db.update_loanee_balances(conn, ano)
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
                    db.update_loanee_balances(conn, ano)
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
    data = request.get_json()
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
            db.update_loanee_balances(conn, ano)
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
            db.update_loanee_balances(conn, ano)
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
            'ano': customer['ANO'],
            'name': customer['NAME'],
            'village': customer['ADD1'],
            'parent_ano': customer.get('PANO', ''),
            'fdt': customer['FDT'],
            'tdt': customer['TDT'],
            'amt': customer['AMT'],
            'pamt': customer['PAMT'],
            'bamt': customer['BAMT'],
            'da': customer['DA'],
            'dw': customer['DW'],
            'ds': customer['DS']
        }
        payments_data = [{'pdt': p['PDT'], 'amt': p['AMT']} for p in payments]

        return render_template('customer_print.html', customer=customer_data, payments=payments_data)

    except Exception as e:
        traceback.print_exc()
        return "Something went wrong.", 500
    finally:
        if conn:
            conn.close()


# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))