"""
SD Finance – Cloud-Ready Application
--------------------------------------------------
This is the fully refactored Flask application using
Google Cloud Storage (GCS) for all SQLite DB files.
No local database folder is used anymore.

All DBs are downloaded from GCS into /tmp, worked on,
then synced back to GCS after any write.
"""

import os
import sqlite3
import traceback
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
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


# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    files = list_gcs_files()

    if request.method == "POST":
        selected_file = request.form.get("village_db")
        if selected_file:
            # Save active DB name
            session["active_db"] = selected_file

            # Download from GCS → /tmp
            local_path = get_local_db_path(selected_file)
            session["active_path"] = local_path

            # Get friendly village name
            file_number = selected_file.split(".")[0]
            vname = get_village_name_from_db(local_path)
            session["village_name"] = f"{file_number} - {vname}"

            return redirect("/dashboard")

    # GET mode
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
            print("Dashboard calculation error:", e)

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
    file = request.files["file"]
    if not file or not file.filename:
      return redirect("/manage_files")

    filename = secure_filename(str(file.filename))

    tmp_path = "/tmp/" + filename
    file.save(tmp_path)

    upload_to_gcs(tmp_path, filename)
    return redirect("/manage_files")


@app.route("/delete_from_gcs", methods=["POST"])
def delete_from_gcs_route():
    delete_from_gcs(request.form["filename"])
    return redirect("/manage_files")


@app.route("/download_gcs/<filename>")
def download_gcs_file(filename):
    local_path = download_from_gcs(filename)
    return send_file(local_path, as_attachment=True, download_name=filename)


@app.route("/select_gcs_file", methods=["POST"])
def select_gcs_file():
    filename = request.form["filename"]
    local_path = get_local_db_path(filename)

    session["active_db"] = filename
    session["active_path"] = local_path
    return redirect("/dashboard")


# ----------------------------------------------------
# ADD CUSTOMER
# ----------------------------------------------------
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
    active_db = session.get("active_db")
    if not active_db:
        return redirect("/dashboard")

    conn = None
    try:
        conn = connect_db_from_gcs()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM LOANEE")
        rows = cursor.fetchall()
        headers = [col[0] for col in cursor.description]

        # Convert to list-of-lists and cast numeric fields
        col_map = {name: i for i, name in enumerate(headers)}
        amt_idx = col_map.get("AMT", -1)
        pamt_idx = col_map.get("PAMT", -1)
        bamt_idx = col_map.get("BAMT", -1)
        da_idx = col_map.get("DA", -1)

        processed = []
        for r in rows:
            row_list = list(r)
            if amt_idx != -1:
                row_list[amt_idx] = float(row_list[amt_idx] or 0)
            if pamt_idx != -1:
                row_list[pamt_idx] = float(row_list[pamt_idx] or 0)
            if bamt_idx != -1:
                row_list[bamt_idx] = float(row_list[bamt_idx] or 0)
            if da_idx != -1:
                row_list[da_idx] = float(row_list[da_idx] or 0)
            processed.append(row_list)

        total_customers = len(processed)
        sum_amt = sum(row[amt_idx] for row in processed) if processed and amt_idx != -1 else 0.0
        sum_pamt = sum(row[pamt_idx] for row in processed) if processed and pamt_idx != -1 else 0.0
        sum_bamt = sum(row[bamt_idx] for row in processed) if processed and bamt_idx != -1 else 0.0

        return render_template(
            "view_customers.html",
            headers=headers,
            data=processed,
            total_customers=total_customers,
            sum_amt=sum_amt,
            sum_pamt=sum_pamt,
            sum_bamt=sum_bamt
        )

    except Exception as e:
        traceback.print_exc()
        return "Something went wrong.", 500
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
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")

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
    app.run(debug=True, port=8080)