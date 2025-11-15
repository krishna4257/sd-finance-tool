"""
Application entry point for SD Finance (robust package/script imports).

This file is written to work when run:
 - as a package (recommended: `gunicorn "SD_Accounting_Tool.app:app"`)
 - directly for local testing (`python -m SD_Accounting_Tool.app`)
It uses db.connect(...) from database_manager and locates templates/static
relative to the package base.
"""

from __future__ import annotations

import os
import sqlite3
import logging
import traceback
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Any

from flask import Flask, render_template, request, redirect, session, jsonify, flash, send_file

# Robust imports: prefer package-relative when running under a package,
# fallback to top-level imports if running as a script.
try:
    # when running as package (gunicorn with module path)
    from .config import SECRET_KEY, RUN_MODE, GCS_BUCKET_NAME  # type: ignore
    from . import database_manager as db  # type: ignore
except Exception:
    # fallback when running directly (python app.py)
    from config import SECRET_KEY, RUN_MODE, GCS_BUCKET_NAME  # type: ignore
    import database_manager as db  # type: ignore

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine base path for templates/static (uses database_manager helper if present)
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

# (keep the rest of your routes — for brevity I include the important ones used by the UI)
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

# Add the rest of your routes unchanged below (add_customer, view_customers, search etc.)

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
    # Local debug run
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)))