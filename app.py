"""
Application entry point for SD Finance (Cloud Run + GCS temporary storage).

Mode B: Cloud mode (RUN_MODE=cloud)
- Files are stored in GCS (configured in config.py)
- Files are downloaded to /tmp/ when needed and uploaded back after changes
- There is a simple file management API: list, upload, set_active, download, delete
"""

from __future__ import annotations

import os
import sqlite3
import logging
import traceback
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any

from flask import (
    Flask, render_template, request, redirect, session, jsonify, flash, send_file
)

# local imports (database_manager will use gcs_utils under the hood)
try:
    from .config import SECRET_KEY, RUN_MODE, GCS_BUCKET_NAME  # type: ignore
    from . import database_manager as db  # type: ignore
except Exception:
    # fallback when run directly
    from config import SECRET_KEY, RUN_MODE, GCS_BUCKET_NAME  # type: ignore
    import database_manager as db  # type: ignore

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app with template/static folders from package base
base_path = getattr(db, "_get_base_path", lambda: os.path.dirname(os.path.abspath(__file__)))()
template_folder = os.path.join(base_path, "templates")
static_folder = os.path.join(base_path, "static")

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.secret_key = SECRET_KEY

# -----------------------
# Utility helpers
# -----------------------

def safe_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

def connect_db(filename: str) -> Optional[sqlite3.Connection]:
    """Return sqlite3.Connection using database_manager.connect (handles download)."""
    if not filename:
        raise ValueError("Database filename missing")
    try:
        return db.connect(filename)
    except FileNotFoundError:
        logger.exception("DB file not found: %s", filename)
        return None
    except Exception:
        logger.exception("Unexpected error connecting to DB: %s", filename)
        return None

def get_village_files() -> List[str]:
    try:
        return db.list_village_databases()
    except Exception as e:
        logger.exception("Could not list village databases: %s", e)
        return []

def get_village_name_from_db(filepath: str) -> str:
    conn = None
    try:
        conn = sqlite3.connect(filepath)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT ADD1 FROM LOANEE WHERE ADD1 IS NOT NULL AND ADD1 != '' LIMIT 1")
        r = cur.fetchone()
        if r and r["ADD1"] and str(r["ADD1"]).strip().lower() != "unknown":
            return str(r["ADD1"]).strip()
        cur.execute("SELECT value FROM META WHERE key = 'village_name'")
        r2 = cur.fetchone()
        if r2 and r2[0]:
            return str(r2[0])
        return "Unknown"
    except Exception as e:
        logger.exception("Village name fetch error: %s", e)
        return "Unknown"
    finally:
        if conn:
            conn.close()

# -----------------------
# Context processor
# -----------------------
@app.context_processor
def inject_common_variables():
    return {
        "files": get_village_files(),
        "selected_file": session.get("selected_file", ""),
        "village_name": session.get("village_name", "")
    }

# -----------------------
# Routes (core + manage files)
# -----------------------

@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    try:
        files = get_village_files()
        if request.method == "POST":
            selected_file = request.form.get("village_db")
            if selected_file:
                session["selected_file"] = selected_file
                file_number = selected_file.split(".")[0]
                try:
                    db_path = db.get_database_path(selected_file)
                    village_name = get_village_name_from_db(db_path)
                    session["village_name"] = f"{file_number} - {village_name}"
                except Exception:
                    session["village_name"] = file_number
                return redirect("/dashboard")

        selected_file = session.get("selected_file")
        village_name = session.get("village_name", "Unknown")
        total_customers = sum_amt = sum_pamt = sum_bamt = 0

        if selected_file:
            try:
                with db.get_db_connection(selected_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*), SUM(AMT), SUM(PAMT), SUM(BAMT) FROM LOANEE")
                    row = cursor.fetchone()
                    if row:
                        total_customers = int(row[0] or 0)
                        sum_amt = float(row[1] or 0.0)
                        sum_pamt = float(row[2] or 0.0)
                        sum_bamt = float(row[3] or 0.0)
            except Exception as e:
                logger.exception("Error calculating totals: %s", e)

        return render_template(
            "dashboard.html",
            files=files,
            selected_file=selected_file,
            village_name=village_name,
            total_customers=total_customers,
            sum_amt=sum_amt,
            sum_pamt=sum_pamt,
            sum_bamt=sum_bamt,
        )
    except Exception as e:
        logger.exception("Error loading dashboard: %s", e)
        return "Something went wrong.", 500

# -----------------------
# Manage files endpoints (GCS-backed)
# -----------------------

@app.route("/api/list_files", methods=["GET"])
def api_list_files():
    """List files in GCS (or local folder in local mode). Returns list of dicts."""
    try:
        files = db.list_village_databases(full_meta=True)  # full_meta returns dicts
        return jsonify(success=True, files=files)
    except Exception as e:
        logger.exception("Error listing files: %s", e)
        return jsonify(success=False, error=str(e)), 500

@app.route("/api/upload_sqlite", methods=["POST"])
def api_upload_sqlite():
    """
    Accept multiple files. Save to /tmp and upload to GCS via db.upload_sqlite.
    Returns filenames uploaded.
    """
    if "files[]" not in request.files and "file" not in request.files:
        return jsonify({"success": False, "error": "No files uploaded"}), 400

    uploaded_files = request.files.getlist("files[]") or request.files.getlist("file")
    uploaded_names = []
    errors = []

    for f in uploaded_files:
        if not f or f.filename == "":
            continue
        filename = os.path.basename(f.filename or "")
        local_tmp = f"/tmp/{filename}"
        try:
            f.save(local_tmp)
            db.upload_sqlite(local_tmp, filename)
            uploaded_names.append(filename)
        except Exception as e:
            logger.exception("Upload failed for %s: %s", filename, e)
            errors.append({"filename": filename, "error": str(e)})
        finally:
            # optional: keep /tmp copy for quick reuse; do not delete here
            pass

    return jsonify(success=(len(errors) == 0), uploaded=uploaded_names, errors=errors)

@app.route("/api/set_active", methods=["POST"])
def api_set_active():
    data = request.get_json() or {}
    filename = data.get("filename")
    if not filename:
        return jsonify(success=False, error="filename missing"), 400

    try:
        # Ensure file exists in bucket (list_village_databases will show it)
        files = db.list_village_databases()
        if filename not in files:
            return jsonify(success=False, error="file not found"), 404

        # download to /tmp (so later operations use local copy)
        local_path = db.get_database_path(filename)  # this will download for cloud mode
        session["selected_file"] = filename
        session["village_name"] = filename.split(".")[0]
        return jsonify(success=True, filename=filename)
    except Exception as e:
        logger.exception("Failed to set active: %s", e)
        return jsonify(success=False, error=str(e)), 500

@app.route("/api/download_file/<filename>", methods=["GET"])
def api_download_file(filename: str):
    """Stream the file from /tmp (downloads first if needed)."""
    if not filename:
        return jsonify(success=False, error="filename missing"), 400
    try:
        local_path = db.get_database_path(filename)  # ensures downloaded copy exists
        if not os.path.exists(local_path):
            return jsonify(success=False, error=f"local copy missing: {local_path}"), 500
        # Use Flask send_file - set as attachment
        return send_file(local_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.exception("Download failed for %s: %s", filename, e)
        return jsonify(success=False, error=str(e)), 500

@app.route("/api/delete_file", methods=["POST"])
def api_delete_file():
    data = request.get_json() or {}
    filename = data.get("filename")
    if not filename:
        return jsonify(success=False, error="filename missing"), 400
    try:
        # Delete from GCS
        db.delete_sqlite_from_gcs(filename)
        # remove any /tmp copy
        try:
            local_tmp = f"/tmp/{filename}"
            if os.path.exists(local_tmp):
                os.remove(local_tmp)
        except Exception:
            logger.exception("Failed to remove tmp copy for %s", filename)
        # If the deleted file was active, clear session
        if session.get("selected_file") == filename:
            session.pop("selected_file", None)
            session.pop("village_name", None)
        return jsonify(success=True)
    except FileNotFoundError as e:
        return jsonify(success=False, error=str(e)), 404
    except Exception as e:
        logger.exception("Delete failed: %s", e)
        return jsonify(success=False, error=str(e)), 500

# -----------------------
# Existing app routes (payments / customers / posting reports)
# The rest of your original routes kept unchanged. For brevity I include the
# important ones used by your UI. Keep the rest of your routes from previous
# app.py (post_payment, submit_post_payment, get_all_postings, etc.) unchanged.
# -----------------------

@app.route("/post_payment", methods=["GET"])
def post_payment():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")
    return render_template("post_payment.html")

@app.route("/get_payments_data/<filename>")
def get_payments_data(filename: str):
    conn = None
    try:
        conn = connect_db(filename)
        if conn is None:
            return jsonify({"error": "Could not connect to database"})
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PAMT1")
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        return jsonify(data)
    except Exception as e:
        logger.exception("Error in get_payments_data: %s", e)
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route("/post_payment_report", methods=["GET"])
def post_payment_report():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return "Could not connect to database", 500
        cursor = conn.cursor()
        cursor.execute("SELECT ANO, PDT, AMT FROM PAMT1 ORDER BY CAST(ANO AS INTEGER)")
        rows = cursor.fetchall()
        payments = [[row["ANO"], row["PDT"], row["AMT"]] for row in rows]
        return render_template("post_payment_report.html", payments=payments)
    except Exception as e:
        logger.exception("Error loading post_payment_report page: %s", e)
        return "Could not load posting report page", 500
    finally:
        if conn:
            conn.close()

# (Keep the rest of your existing routes unchanged: add_customer, view_customers, search, etc.)
# For brevity those routes are not repeated here — include them unchanged in your final file.

# -----------------------
# Template filters & main
# -----------------------

@app.template_filter("format_rupee")
def format_rupee(value: Any) -> str:
    try:
        return "₹{:,.2f}".format(float(value))
    except Exception:
        return str(value)

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)))