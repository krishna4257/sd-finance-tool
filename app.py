"""
Application entry point for SD Finance (package-aware).
This file expects package name SD_Accounting_Tool.
"""

from __future__ import annotations
from typing import cast
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any

from flask import Flask, render_template, request, redirect, session, jsonify, send_file

# package imports
from .config import SECRET_KEY, RUN_MODE, GCS_BUCKET_NAME
from . import database_manager as db
from . import gcs_utils

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
base_path = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(base_path, "templates")
static_folder = os.path.join(base_path, "static")

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.secret_key = SECRET_KEY


def safe_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def connect_db(filename: str) -> Optional[sqlite3.Connection]:
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
        # return names (not full meta) by default
        return db.list_village_databases(full_meta=False)
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


@app.context_processor
def inject_common_variables():
    return {
        "files": get_village_files(),
        "selected_file": session.get("selected_file", ""),
        "village_name": session.get("village_name", "")
    }


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
                with db.connect(selected_file) as conn:
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
# Manage files endpoints
# -----------------------

@app.route("/api/list_files", methods=["GET"])
def api_list_files():
    try:
        files = db.list_village_databases(full_meta=True)
        return jsonify(success=True, files=files)
    except Exception as e:
        logger.exception("Error listing files: %s", e)
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/upload_sqlite", methods=["POST"])
def api_upload_sqlite():

    # Supports both single "file" and multi "files" input
    uploaded_files = request.files.getlist("file") or request.files.getlist("files[]")

    if not uploaded_files:
        return jsonify(success=False, error="No files uploaded"), 400

    uploaded_names = []
    errors = []

    for f in uploaded_files:
        try:
            filename = cast(str, os.path.basename(f.filename or ""))
            if not filename:
                continue

            local_tmp = os.path.join("/tmp/sqlite_cache", filename)
            os.makedirs(os.path.dirname(local_tmp), exist_ok=True)

            f.save(local_tmp)

            # Upload to GCS through database_manager
            db.upload_sqlite(local_tmp, filename)

            uploaded_names.append(filename)

        except Exception as e:
            logger.exception("Upload failed for %s: %s", filename, e)
            errors.append({"file": filename, "error": str(e)})

    return jsonify(success=(len(errors) == 0), uploaded=uploaded_names, errors=errors)

@app.route("/api/set_active", methods=["POST"])
def api_set_active():
    data = request.get_json() or {}
    filename = data.get("filename")
    if not filename:
        return jsonify(success=False, error="filename missing"), 400
    try:
        files = db.list_village_databases(full_meta=False)
        if filename not in files:
            return jsonify(success=False, error="file not found"), 404
        # ensure local copy exists
        local_path = db.get_database_path(filename)
        session["selected_file"] = filename
        session["village_name"] = filename.split(".")[0]
        return jsonify(success=True, filename=filename)
    except Exception as e:
        logger.exception("Failed to set active: %s", e)
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/download_file/<filename>", methods=["GET"])
def api_download_file(filename: str):
    if not filename:
        return jsonify(success=False, error="filename missing"), 400
    try:
        local_path = db.get_database_path(filename)
        if not os.path.exists(local_path):
            return jsonify(success=False, error=f"local copy missing: {local_path}"), 500
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
        ok = db.delete_sqlite(filename)
        if not ok:
            return jsonify(success=False, error="file not found"), 404
        tmp = os.path.join("/tmp/sqlite_cache", filename)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            logger.exception("Failed to remove tmp copy %s", tmp)
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
# Example subset of existing routes used by UI
# (keep all your other routes from previous app unchanged when you add this file)
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


# Template filter
@app.template_filter("format_rupee")
def format_rupee(value: Any) -> str:
    try:
        return "₹{:,.2f}".format(float(value))
    except Exception:
        return str(value)


if __name__ == "__main__":
    app.run(debug=(RUN_MODE == "local"), port=int(os.environ.get("PORT", 8080)))