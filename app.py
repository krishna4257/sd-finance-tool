"""
app.py - Complete application entry point for SD Finance (full routes + manage-files).

This file:
 - initializes Flask
 - exposes all routes required by the UI
 - uses database_manager.py and gcs_utils through that module for local/cloud DB handling
"""

from flask import (
    Flask, render_template, request, redirect, session, jsonify, flash, send_file, url_for
)
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import sqlite3
import tempfile
import traceback
import logging
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any

# Try package relative import first for when run as package; else fallback
try:
    from .config import SECRET_KEY  # type: ignore
    from . import database_manager as db  # type: ignore
    from .config import RUN_MODE  # type: ignore
except Exception:
    from config import SECRET_KEY, RUN_MODE  # type: ignore
    import database_manager as db  # type: ignore

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Derive paths for templates/static based on database_manager BASE_DIR if available
BASE_DIR = getattr(db, "BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)
app.secret_key = SECRET_KEY

ALLOWED_EXTENSIONS = {"sqlite", "db"}

# ---------- Utility helpers ----------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_float(val) -> float:
    try:
        return float(val or 0)
    except Exception:
        return 0.0

def get_village_files() -> List[str]:
    try:
        return db.list_village_databases()
    except Exception:
        logger.exception("list_village_databases failed")
        return []

def connect_db(filename: str) -> Optional[sqlite3.Connection]:
    if not filename:
        raise ValueError("Missing DB filename")
    try:
        return db.connect(filename)
    except FileNotFoundError:
        logger.warning("Database not found: %s", filename)
        return None
    except Exception:
        logger.exception("Error connecting to DB: %s", filename)
        return None

def get_village_name_from_db(filepath: str) -> str:
    conn = None
    try:
        conn = sqlite3.connect(filepath)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT ADD1 FROM LOANEE WHERE ADD1 IS NOT NULL AND ADD1 != '' LIMIT 1")
        r = cur.fetchone()
        if r:
            val = r["ADD1"].strip()
            if val and val.lower() != "unknown":
                return val
        cur.execute("SELECT value FROM META WHERE key = 'village_name'")
        m = cur.fetchone()
        if m:
            return m["value"]
    except Exception:
        logger.debug("Failed to read village name from %s", filepath, exc_info=True)
    finally:
        if conn:
            conn.close()
    return "Unknown"

# Context injected into all templates
@app.context_processor
def inject_common_vars():
    return {
        "files": get_village_files(),
        "selected_file": session.get("selected_file", ""),
        "village_name": session.get("village_name", "")
    }

# ---------- Basic navigation ----------

@app.route("/")
def home():
    return redirect("/dashboard")

# ---------- Dashboard / village selection ----------

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    try:
        files = get_village_files()
        if request.method == "POST":
            selected = request.form.get("village_db")
            if selected:
                session["selected_file"] = selected
                try:
                    path = db.get_database_path(selected)
                    session["village_name"] = f"{selected.split('.')[0]} - {get_village_name_from_db(path)}"
                except Exception:
                    session["village_name"] = selected.split('.')[0]
                return redirect("/dashboard")

        selected_file = session.get("selected_file")
        village_name = session.get("village_name", "Unknown")

        total_customers = sum_amt = sum_pamt = sum_bamt = 0
        if selected_file:
            conn = None
            try:
                conn = connect_db(selected_file)
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*), SUM(AMT), SUM(PAMT), SUM(BAMT) FROM LOANEE")
                    row = cur.fetchone()
                    if row:
                        total_customers = row[0] or 0
                        sum_amt = row[1] or 0
                        sum_pamt = row[2] or 0
                        sum_bamt = row[3] or 0
            except Exception:
                logger.exception("Dashboard totals failed")
            finally:
                if conn:
                    conn.close()

        return render_template(
            "dashboard.html",
            files=files,
            selected_file=selected_file,
            village_name=village_name,
            total_customers=total_customers,
            sum_amt=sum_amt,
            sum_pamt=sum_pamt,
            sum_bamt=sum_bamt
        )
    except Exception:
        logger.exception("Error loading dashboard")
        return "Something went wrong", 500

@app.route("/reselect_village", methods=["POST"])
def reselect_village():
    session.pop("selected_file", None)
    session.pop("village_name", None)
    return redirect("/dashboard")

# ---------- Manage files (upload, delete, download, list) ----------

@app.route("/manage_files", methods=["GET"])
def manage_files():
    files = get_village_files()
    return render_template("manage_files.html", files=files)

@app.route("/api/files", methods=["GET"])
def api_list_files():
    try:
        files = get_village_files()
        return jsonify(success=True, files=files)
    except Exception:
        logger.exception("Failed listing files")
        return jsonify(success=False, error="Server error"), 500

@app.route("/api/upload_db", methods=["POST"])
def api_upload_db():
    """
    Accepts uploaded sqlite file via form-data 'file' or via fetch POST with file.
    Uses database_manager.upload_sqlite to put file into local folder or GCS.
    """
    if "file" not in request.files:
        return jsonify(success=False, error="No file part"), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify(success=False, error="No selected file"), 400
    raw_filename = f.filename or ""
    filename = secure_filename(raw_filename)
    if not allowed_file(filename):
        return jsonify(success=False, error="Only .sqlite or .db files allowed"), 400

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(tmp_fd)
    try:
        f.save(tmp_path)
        # call database_manager.upload_sqlite
        ok = db.upload_sqlite(tmp_path, filename)
        if not ok:
            return jsonify(success=False, error="Upload failed"), 500
        # return new list
        files = get_village_files()
        return jsonify(success=True, files=files)
    except Exception:
        logger.exception("Upload DB failed")
        return jsonify(success=False, error="Server error"), 500
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@app.route("/api/delete_db", methods=["POST"])
def api_delete_db():
    data = request.get_json() or {}
    filename = data.get("filename")
    if not filename:
        return jsonify(success=False, error="Missing filename"), 400
    try:
        ok = db.delete_sqlite(filename)
        if not ok:
            return jsonify(success=False, error="Delete failed (file missing?)"), 404
        # If deleted file was selected, remove selection
        if session.get("selected_file") == filename:
            session.pop("selected_file", None)
            session.pop("village_name", None)
        files = get_village_files()
        return jsonify(success=True, files=files)
    except Exception:
        logger.exception("Delete DB failed")
        return jsonify(success=False, error="Server error"), 500

@app.route("/download_db/<filename>", methods=["GET"])
def download_db(filename):
    # Send the sqlite file (download from GCS if necessary)
    try:
        # get a local path (database_manager.get_database_path will download in cloud mode)
        local_path = db.get_database_path(filename)
        if not os.path.exists(local_path):
            return "Not found", 404
        # Use send_file; set attachment filename
        return send_file(local_path, as_attachment=True, download_name=filename)
    except Exception:
        logger.exception("Download DB failed")
        return "Server error", 500

@app.route("/api/select_db", methods=["POST"])
def api_select_db():
    data = request.get_json() or {}
    filename = data.get("filename")
    if not filename:
        return jsonify(success=False, error="Missing filename"), 400
    try:
        path = db.get_database_path(filename)
        if not os.path.exists(path):
            return jsonify(success=False, error="DB not found"), 404
        session["selected_file"] = filename
        session["village_name"] = f"{filename.split('.')[0]} - {get_village_name_from_db(path)}"
        return jsonify(success=True)
    except Exception:
        logger.exception("Select DB failed")
        return jsonify(success=False, error="Server error"), 500

# ---------- Customers (add / view / edit) ----------

@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    selected_file = session.get("selected_file")
    village_name = session.get("village_name", "Unknown")
    if not selected_file:
        return redirect("/dashboard")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return "Could not connect to DB", 500
        cur = conn.cursor()

        if request.method == "POST":
            form = request.form
            ano = form.get("ano", "").strip()
            name = form.get("name", "").strip()
            add1_village = form.get("add1", "").strip()
            add2 = form.get("add2", "").strip()
            add3 = form.get("add3", "").strip()
            dw = form.get("dw", "").strip()
            fdt_str = form.get("fdt", "").strip()
            ds = int(form.get("ds") or 0)
            amt = safe_float(form.get("amt"))
            pano = form.get("pano", "").strip()

            cur.execute("SELECT 1 FROM LOANEE WHERE ANO = ?", (ano,))
            if cur.fetchone():
                return jsonify({"error": f"A.no {ano} already exists"}), 400

            pamt = 0.0
            bamt = amt
            da = round(amt / ds, 2) if ds > 0 else 0.0

            try:
                fdt_obj = datetime.strptime(fdt_str, "%d/%m/%Y")
            except Exception:
                return jsonify({"error": "Invalid date format (expected dd/mm/YYYY)"}), 400

            if dw == "M":
                tdt_obj = fdt_obj + relativedelta(months=ds)
            else:
                tdt_obj = fdt_obj + timedelta(weeks=ds)

            fdt = fdt_obj.strftime("%d/%m/%Y")
            tdt = tdt_obj.strftime("%d/%m/%Y")

            insert_q = """
                INSERT INTO LOANEE (ANO, NAME, ADD1, ADD2, ADD3, FDT, TDT, AMT, PAMT, BAMT, DA, DW, DS, PANO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (ano, name, add1_village, add2, add3, fdt, tdt, amt, pamt, bamt, da, dw, ds, pano)
            cur.execute(insert_q, values)
            conn.commit()
            cur.execute("SELECT MAX(CAST(ANO AS INTEGER)) FROM LOANEE")
            highest = (cur.fetchone() or [None])[0]
            return jsonify({"message": "Customer added", "highest_ano": highest})

        cur.execute("SELECT MAX(CAST(ANO AS INTEGER)) FROM LOANEE")
        highest = (cur.fetchone() or [None])[0] or "N/A"
        return render_template("add_customer.html", village_name=village_name, highest_ano=highest)
    except Exception:
        logger.exception("Error in add_customer")
        if request.method == "POST":
            return jsonify({"error": "Server error"}), 500
        return "Server error", 500
    finally:
        if conn:
            conn.close()

@app.route("/view_customers")
def view_customers():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return "Could not connect to DB", 500

        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM LOANEE")
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description] if cur.description else []
        processed = []
        mapping = {h: i for i, h in enumerate(headers)}
        for r in rows:
            rowlist = list(r)
            for key in ("AMT", "PAMT", "BAMT", "DA"):
                idx = mapping.get(key)
                if idx is not None:
                    try:
                        rowlist[idx] = float(rowlist[idx] or 0)
                    except Exception:
                        rowlist[idx] = 0.0
            processed.append(rowlist)

        total_customers = len(processed)
        sum_amt = sum((r[mapping["AMT"]] for r in processed)) if "AMT" in mapping else 0
        sum_pamt = sum((r[mapping["PAMT"]] for r in processed)) if "PAMT" in mapping else 0
        sum_bamt = sum((r[mapping["BAMT"]] for r in processed)) if "BAMT" in mapping else 0

        return render_template("view_customers.html",
                               headers=headers, data=processed,
                               total_customers=total_customers,
                               sum_amt=sum_amt, sum_pamt=sum_pamt, sum_bamt=sum_bamt)
    except Exception:
        logger.exception("Error viewing customers")
        return "Server error", 500
    finally:
        if conn:
            conn.close()

# ---------- Post payment pages and endpoints ----------

@app.route("/post_payment", methods=["GET"])
def post_payment():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")
    return render_template("post_payment.html")

@app.route("/check_payment_exists")
def check_payment_exists():
    ano = request.args.get("ano")
    pdt = request.args.get("pdt")
    selected_file = session.get("selected_file")
    if not (ano and pdt and selected_file):
        return jsonify({"exists": False})
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({"exists": False})
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM PAMT1 WHERE ANO = ? AND PDT = ?", (ano, pdt))
        return jsonify({"exists": bool(cur.fetchone())})
    except Exception:
        logger.exception("Error checking payment")
        return jsonify({"exists": False})
    finally:
        if conn:
            conn.close()

@app.route("/get_customer_info")
def get_customer_info():
    ano = request.args.get("ano")
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify({"error": "No DB selected"})
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({"error": "Could not connect"})
        cur = conn.cursor()
        cur.execute("SELECT NAME, AMT, PAMT, BAMT, DA FROM LOANEE WHERE ANO = ?", (ano,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"})
        return jsonify({
            "name": row[0],
            "amt": row[1],
            "pamt": row[2],
            "bamt": row[3],
            "da": row[4]
        })
    except Exception:
        logger.exception("Error getting customer info")
        return jsonify({"error": "Server error"})
    finally:
        if conn:
            conn.close()

@app.route("/submit_post_payment", methods=["POST"])
def submit_post_payment():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify({"error": "No DB selected"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({"error": "Could not connect"}), 500
        cur = conn.cursor()
        submitted = 0
        skipped = []
        for r in data:
            ano = r.get("ano")
            pdt = r.get("pdt")
            amt = safe_float(r.get("amt"))
            cur.execute("SELECT 1 FROM PAMT1 WHERE ANO = ? AND PDT = ?", (ano, pdt))
            if cur.fetchone():
                skipped.append(r)
                continue
            cur.execute("INSERT INTO PAMT1 (ANO, PDT, AMT) VALUES (?, ?, ?)", (ano, pdt, amt))
            try:
                db.update_loanee_balances(conn, ano)
            except Exception:
                logger.debug("update_loanee_balances error", exc_info=True)
            submitted += 1
        conn.commit()
        return jsonify({"message": "Done", "submitted": submitted, "skipped": skipped})
    except Exception:
        logger.exception("Error submitting post payments")
        if conn:
            conn.rollback()
        return jsonify({"error": "Server error"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/reset_post_payment", methods=["POST"])
def reset_post_payment():
    return jsonify({"success": True})

# ---------- Posting report & posting helpers ----------

@app.route("/post_payment_report", methods=["GET", "POST"])
def post_payment_report():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return "Could not connect", 500
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_ano ON PAMT1 (ANO)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pamt1_pdt ON PAMT1 (PDT)")
        except Exception:
            logger.debug("Index creation skipped")

        ano_filter = request.form.get("ano_filter", "").strip()
        from_date = request.form.get("from_date", "").strip()
        to_date = request.form.get("to_date", "").strip()

        def to_db(d):
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")

        date_transform = "substr(PDT, 7, 4) || '-' || substr(PDT, 4, 2) || '-' || substr(PDT, 1, 2)"
        query = "SELECT ANO, PDT, AMT FROM PAMT1 WHERE 1=1"
        params = []
        if ano_filter:
            query += " AND ANO = ?"
            params.append(ano_filter)
        if from_date and to_date:
            query += f" AND {date_transform} BETWEEN ? AND ?"
            params.extend([to_db(from_date), to_db(to_date)])
        elif from_date:
            query += f" AND {date_transform} = ?"
            params.append(to_db(from_date))

        query += f" ORDER BY {date_transform} DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        payments = [list(r) for r in rows]
        return render_template("post_payment_report.html", payments=payments, ano_filter=ano_filter, from_date=from_date, to_date=to_date)
    except Exception:
        logger.exception("Error in post_payment_report")
        return "Server error", 500
    finally:
        if conn:
            conn.close()

@app.route("/search_postings", methods=["POST"])
def search_postings():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB selected")
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data")
    ano = data.get("ano", "").strip()
    date = data.get("date", "").strip()
    if not ano and not date:
        return jsonify(success=False, error="Provide ano or date")
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect")
        cur = conn.cursor()
        query = "SELECT ANO, PDT, AMT FROM PAMT1 WHERE 1=1"
        params = []
        if ano:
            query += " AND ANO = ?"
            params.append(ano)
        if date:
            query += " AND PDT LIKE ?"
            params.append(f"{date}%")
        cur.execute(query, params)
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        return jsonify(success=True, data=results)
    except Exception:
        logger.exception("Error search_postings")
        return jsonify(success=False, error="Server error")
    finally:
        if conn:
            conn.close()

@app.route("/update_posting_date_bulk", methods=["POST"])
def update_posting_date_bulk():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB selected")
    data = request.get_json() or {}
    find_date = data.get("find_date", "").strip()
    replace_date = data.get("replace_date", "").strip()
    if not find_date or not replace_date:
        return jsonify(success=False, error="Both dates required")
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM PAMT1 WHERE PDT LIKE ?", (f"{find_date}%",))
        count = cur.fetchone()[0]
        if count == 0:
            return jsonify(success=False, message=f"No records for {find_date}")
        cur.execute("UPDATE PAMT1 SET PDT = ? WHERE PDT LIKE ?", (replace_date, f"{find_date}%"))
        cur.execute("SELECT DISTINCT ANO FROM PAMT1 WHERE PDT = ?", (replace_date,))
        anos = [r[0] for r in cur.fetchall()]
        for a in anos:
            try:
                db.update_loanee_balances(conn, a)
            except Exception:
                logger.debug("update_loanee_balances failed for %s", a, exc_info=True)
        conn.commit()
        return jsonify(success=True, message=f"{count} records updated")
    except Exception:
        logger.exception("Error update_posting_date_bulk")
        if conn:
            conn.rollback()
        return jsonify(success=False, error="Server error")
    finally:
        if conn:
            conn.close()

# ---------- Search / update / payments management ----------

@app.route("/search", methods=["GET", "POST"])
def search_customer():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        customers = []
        pamt1_records = {}
        conn = None
        try:
            conn = connect_db(selected_file)
            if conn is None:
                return "Could not connect", 500
            cur = conn.cursor()
            like = f"%{query}%"
            cur.execute("SELECT * FROM LOANEE WHERE ANO = ? OR NAME LIKE ?", (query, like))
            customers = cur.fetchall()
            headers = [d[0] for d in cur.description] if cur.description else []
            for cust in customers:
                ano = cust[headers.index("ANO")]
                cur.execute("SELECT * FROM PAMT1 WHERE ANO = ?", (ano,))
                pamt1_records[ano] = cur.fetchall()
            return render_template("search.html", customers=customers, loanee_headers=headers, pamt1_records=pamt1_records, query=query)
        except Exception:
            logger.exception("Error in search")
            return "Server error", 500
        finally:
            if conn:
                conn.close()
    return render_template("search.html")

@app.route("/update_customer_and_payments", methods=["POST"])
def update_customer_and_payments():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB selected")
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data provided")
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect")
        cur = conn.cursor()
        update_type = data.get("type")
        if update_type == "customer":
            cust = data.get("data", {})
            if not cust or "ANO" not in cust:
                return jsonify(success=False, error="Invalid customer data")
            amt = safe_float(cust.get("AMT"))
            pamt = safe_float(cust.get("PAMT"))
            bamt = safe_float(cust.get("BAMT"))
            da = safe_float(cust.get("DA"))
            ds = int(cust.get("DS") or 0)
            cur.execute("""
                UPDATE LOANEE SET
                    NAME=?, ADD2=?, ADD3=?, FDT=?, TDT=?, AMT=?, PAMT=?, BAMT=?, DA=?, DW=?, DS=?, PANO=?
                WHERE ANO=?
            """, (
                cust.get("NAME",""), cust.get("ADD2",""), cust.get("ADD3",""),
                cust.get("FDT",""), cust.get("TDT",""), amt, pamt, bamt, da,
                cust.get("DW",""), ds, cust.get("PANO",""), cust["ANO"]
            ))
        elif update_type == "payment_posting_update":
            payload = data.get("data", {})
            ano = payload.get("ano")
            original = payload.get("original_pdt")
            new_pdt = payload.get("new_pdt")
            new_amt = safe_float(payload.get("new_amt", 0))
            if not all([ano, original, new_pdt]):
                return jsonify(success=False, error="Missing data")
            cur.execute("UPDATE PAMT1 SET PDT = ?, AMT = ? WHERE ANO = ? AND PDT = ?", (new_pdt, new_amt, ano, original))
            db.update_loanee_balances(conn, ano)
        elif update_type == "payments":
            updated = data.get("data", [])
            anos_to_update = set()
            for row in updated:
                cur.execute("UPDATE PAMT1 SET AMT = ? WHERE ANO = ? AND PDT = ?", (safe_float(row.get("amt")), row.get("ano"), row.get("pdt")))
                anos_to_update.add(row.get("ano"))
            for a in anos_to_update:
                db.update_loanee_balances(conn, a)
        else:
            return jsonify(success=False, error="Unknown update type")
        conn.commit()
        return jsonify(success=True)
    except Exception:
        logger.exception("Error update_customer_and_payments")
        if conn:
            conn.rollback()
        return jsonify(success=False, error="Server error")
    finally:
        if conn:
            conn.close()

@app.route("/add_payment", methods=["POST"])
def add_payment():
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data")
    ano = data.get("ano")
    pdt = data.get("pdt")
    amt = safe_float(data.get("amt"))
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB selected")
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
        if cur.fetchone()[0] > 0:
            return jsonify(success=False, error="Duplicate entry")
        cur.execute("INSERT INTO PAMT1 (ANO, PDT, AMT) VALUES (?, ?, ?)", (ano, pdt, amt))
        db.update_loanee_balances(conn, ano)
        conn.commit()
        return jsonify(success=True)
    except Exception:
        logger.exception("Error adding payment")
        if conn:
            conn.rollback()
        return jsonify(success=False, error="Server error")
    finally:
        if conn:
            conn.close()

@app.route("/delete_payment", methods=["POST"])
def delete_payment():
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data")
    ano = data.get("ano")
    pdt = data.get("pdt")
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB selected")
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect")
        cur = conn.cursor()
        cur.execute("DELETE FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
        db.update_loanee_balances(conn, ano)
        conn.commit()
        return jsonify(success=True)
    except Exception:
        logger.exception("Error deleting payment")
        if conn:
            conn.rollback()
        return jsonify(success=False, error="Server error")
    finally:
        if conn:
            conn.close()

# ---------- Parent link / existence checks ----------

@app.route('/check_ano_exists')
def check_ano_exists():
    ano = request.args.get('ano', '').strip()
    selected_file = session.get('selected_file')
    if not ano or not selected_file:
        return jsonify({'exists': False})
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({'exists': False})
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM LOANEE WHERE ANO = ?", (ano,))
        exists = cur.fetchone() is not None
        return jsonify({'exists': exists})
    except Exception:
        logger.exception("Error check_ano_exists")
        return jsonify({'exists': False})
    finally:
        if conn:
            conn.close()

@app.route('/check_parent_link')
def check_parent_link():
    pano_to_check = request.args.get('pano', '').strip()
    selected_file = session.get('selected_file')
    if not pano_to_check or not selected_file:
        return jsonify(found=False, accounts=[])
    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(found=False, error='Could not connect')
        cur = conn.cursor()
        cur.execute("""
            SELECT ANO FROM LOANEE WHERE ANO = ? AND (PANO IS NULL OR PANO = '')
            UNION
            SELECT ANO FROM LOANEE WHERE ANO IN (SELECT PANO FROM LOANEE WHERE ANO = ?)
        """, (pano_to_check, pano_to_check))
        root_row = cur.fetchone()
        root_ano = root_row[0] if root_row else pano_to_check
        cur.execute("""
            WITH RECURSIVE family(ANO) AS (
                SELECT ANO FROM LOANEE WHERE ANO = ?
                UNION ALL
                SELECT l.ANO FROM LOANEE l JOIN family f ON l.PANO = f.ANO
            )
            SELECT ANO FROM family ORDER BY CAST(ANO AS INTEGER);
        """, (root_ano,))
        family_accounts = [r[0] for r in cur.fetchall()]
        if family_accounts:
            return jsonify(found=True, accounts=family_accounts)
        return jsonify(found=False, accounts=[])
    except Exception:
        logger.exception("Error check_parent_link")
        return jsonify(found=False, error="Server error")
    finally:
        if conn:
            conn.close()

# ---------- Print ----------

@app.route('/print_customer/<ano>')
def print_customer(ano):
    db_file = session.get('selected_file')
    if not db_file:
        return "No village selected.", 400
    conn = None
    try:
        conn = connect_db(db_file)
        if conn is None:
            return "Could not connect", 500
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT ANO, NAME, ADD1, ADD2, FDT, TDT, AMT, PAMT, BAMT, DA, DW, DS
            FROM LOANEE
            WHERE ANO = ?
        """, (ano,))
        customer = cur.fetchone()
        cur.execute("""
            SELECT PDT, AMT FROM PAMT1 WHERE ANO = ? ORDER BY substr(PDT, 7, 4) || substr(PDT, 4, 2) || substr(PDT, 1, 2) ASC
        """, (ano,))
        payments = cur.fetchall()
        if not customer:
            return "Customer not found", 404
        customer_data = {
            'ano': customer['ANO'], 'name': customer['NAME'], 'village': customer['ADD1'],
            'parent_ano': customer['ADD2'], 'fdt': customer['FDT'], 'tdt': customer['TDT'],
            'amt': customer['AMT'], 'pamt': customer['PAMT'], 'bamt': customer['BAMT'],
            'da': customer['DA'], 'dw': customer['DW'], 'ds': customer['DS']
        }
        payments_data = [{'pdt': p['PDT'], 'amt': p['AMT']} for p in payments]
        return render_template('customer_print.html', customer=customer_data, payments=payments_data)
    except Exception:
        logger.exception("Error print_customer")
        return "Server error", 500
    finally:
        if conn:
            conn.close()

# ---------- Jinja filters ----------

@app.template_filter('format_rupee')
def format_rupee(value):
    try:
        return "₹{:,.2f}".format(float(value))
    except Exception:
        return value

# ---------- Run locally ----------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))