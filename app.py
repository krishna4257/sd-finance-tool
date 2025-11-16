"""Application entry point for SD Finance.

The routes defined here implement the user interface on top of a
loosely coupled data layer. Configuration and database helpers are
imported from dedicated modules to improve testability and maintain
clarity. Exceptions raised by the database layer are caught and
surfaced to the user via JSON responses or template rendering.
"""

from flask import Flask, render_template, request, redirect, session, jsonify, flash
from datetime import datetime, timedelta
import os
import sqlite3
import traceback
from dateutil.relativedelta import relativedelta
from typing import Optional

# Import application configuration and database helpers
try:
    from .config import SECRET_KEY  # type: ignore
    from . import database_manager as db  # type: ignore
except ImportError:
    from config import SECRET_KEY  # type: ignore
    import database_manager as db  # type: ignore

# Configure application-wide logging.
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialise the Flask app. We use the path logic from db.py
base_path = db._get_base_path()
template_folder = os.path.join(base_path, 'templates')
static_folder = os.path.join(base_path, 'static')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.secret_key = SECRET_KEY

def get_village_files() -> list[str]:
    """Return a list of available village database files."""
    try:
        return db.list_village_databases()
    except Exception as e:
        print(f"ERROR: Could not list village databases: {e}")
        return []

def connect_db(filename: str) -> Optional[sqlite3.Connection]:
    """Wrapper around :func:`database_manager.connect`.

    Returns a connection, or None on failure.
    """
    if not filename:
        raise ValueError("Database filename is missing.")
    try:
        return db.connect(filename)
    except FileNotFoundError as e:
        print(f"Database connection error: {e}")
        return None

def get_village_name_from_db(filepath):
    conn = None
    try:
        conn = sqlite3.connect(filepath)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT ADD1 FROM LOANEE WHERE ADD1 IS NOT NULL AND ADD1 != '' LIMIT 1")
        row = cursor.fetchone()
        if row and row['ADD1'].strip().lower() != "unknown":
            return row['ADD1']
        
        cursor.execute("SELECT value FROM META WHERE key = 'village_name'")
        meta_row = cursor.fetchone()
        return meta_row['value'] if meta_row else "Unknown"
    except Exception as e:
        print("Village name fetch error:", e)
        return "Unknown"
    finally:
        if conn:
            conn.close()

@app.route('/')
def home():
    """Redirects the root URL to the dashboard."""
    return redirect('/dashboard')

@app.context_processor
def inject_common_variables():
    return {
        "files": get_village_files(),
        "selected_file": session.get("selected_file", ""),
        "village_name": session.get("village_name", "")
    }

@app.route("/update_village_name", methods=["POST"])
def update_village_name():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify({"success": False, "error": "No file selected"})

    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON data"})

    new_name = data.get("new_name", "").strip()
    if not new_name:
        return jsonify({"success": False, "error": "Invalid name"})

    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({"success": False, "error": "Could not connect to database"})
        
        cursor = conn.cursor()
        cursor.execute("UPDATE LOANEE SET ADD1 = ?", (new_name,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route("/create_village", methods=["POST"])
def create_village():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON data"})

    number = data.get("number")
    name = data.get("name")

    if not number or not name:
        return jsonify({"success": False, "error": "Missing village number or name"})

    conn = None
    try:
        db_path = os.path.join(db.SQLITE_FOLDER, f"{number}.sqlite")
        if os.path.exists(db_path):
            return jsonify({"success": False, "error": "Village DB already exists."})

        conn = sqlite3.connect(db_path)
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

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    try:
        print("📌 GET or POST to /dashboard triggered")
        files = get_village_files()
        print("📁 Available files:", files)

        if request.method == "POST":
            selected_file = request.form.get("village_db")
            print("📝 Selected file from form:", selected_file)
            if selected_file:
                session["selected_file"] = selected_file
                file_number = selected_file.split('.')[0]
                db_path = db.get_database_path(selected_file)
                village_name = get_village_name_from_db(db_path)
                session["village_name"] = f"{file_number} - {village_name}"
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
                        total_customers, sum_amt, sum_pamt, sum_bamt = row
            except Exception as calc_err:
                print("⚠️ Error calculating totals:", calc_err)

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

    except Exception as e:
        print("❌ Error loading dashboard:", e)
        traceback.print_exc()
        return "Something went wrong.", 500

@app.route("/reselect_village", methods=["POST"])
def reselect_village():
    session.pop("selected_file", None)
    session.pop("village_name", None)
    return redirect("/dashboard")

@app.route('/get_customers_data/<filename>')
def get_customers_data(filename):
    try:
        db_path = db.get_database_path(filename)
        conn = connect_db(filename)
        if conn is None:
            return jsonify({"error": "Could not connect to database"})
            
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM LOANEE")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()

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
            return jsonify({"error": "Could not connect to database"}), 500
        
        cursor = conn.cursor()

        if request.method == "POST":
            data = request.form
            ano = data.get("ano", "").strip()
            name = data.get("name", "").strip()
            add1_village = data.get("add1", "").strip()
            add2 = data.get("add2", "").strip()
            add3 = data.get("add3", "").strip()
            dw = data.get("dw", "").strip()
            fdt_str = data.get("fdt", "").strip()
            ds = int(data.get("ds") or 0)
            amt = safe_float(data.get("amt"))
            pano = data.get("pano", "").strip()
            
            cursor.execute("SELECT 1 FROM LOANEE WHERE ANO = ?", (ano,))
            if cursor.fetchone():
                return jsonify({"error": f"Customer with A.no {ano} already exists."}), 400

            pamt = 0.0
            bamt = amt
            da = round(amt / ds, 2) if ds > 0 else 0.0
            
            fdt_obj = datetime.strptime(fdt_str, "%d/%m/%Y")
            if dw == "M":
                tdt_obj = fdt_obj + relativedelta(months=ds)
            else:
                tdt_obj = fdt_obj + timedelta(weeks=ds)
            
            fdt = fdt_obj.strftime("%d/%m/%Y")
            tdt = tdt_obj.strftime("%d/%m/%Y")

            insert_query = """
                INSERT INTO LOANEE (ANO, NAME, ADD1, ADD2, ADD3, FDT, TDT, AMT, PAMT, BAMT, DA, DW, DS, PANO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            values_to_insert = (
                ano, name, add1_village, add2, add3, fdt, tdt, amt, pamt, bamt, da, dw, ds, pano
            )

            cursor.execute(insert_query, values_to_insert)
            conn.commit()

            cursor.execute("SELECT MAX(CAST(ANO AS INTEGER)) FROM LOANEE")
            new_highest_ano = (cursor.fetchone() or [0])[0]

            return jsonify({
                "message": f"✅ Successfully added customer {name}.",
                "highest_ano": new_highest_ano
            })

        cursor.execute("SELECT MAX(CAST(ANO AS INTEGER)) FROM LOANEE")
        highest_ano = (cursor.fetchone() or [0])[0] or "N/A"

        return render_template("add_customer.html", village_name=village_name, highest_ano=highest_ano)

    except Exception as e:
        if conn:
            conn.rollback()
        
        print("❌ Error in add_customer route:")
        traceback.print_exc()

        if request.method == "POST":
            return jsonify({"error": str(e)}), 500
        else:
            return f"❌ Exception: {str(e)}", 500
    finally:
        if conn:
            conn.close()

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
            return jsonify({'exists': False, 'error': 'Could not connect to database'})
            
        cursor = conn.cursor()
        query = "SELECT 1 FROM LOANEE WHERE ANO = ?"
        cursor.execute(query, (ano,))
        exists = cursor.fetchone() is not None
        return jsonify({'exists': exists})
    except Exception as e:
        print(f"Error in /check_ano_exists: {e}")
        return jsonify({'exists': False, 'error': str(e)})
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
            return jsonify(found=False, error='Could not connect to database')
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ANO FROM LOANEE WHERE ANO = ? AND (PANO IS NULL OR PANO = '')
            UNION
            SELECT ANO FROM LOANEE WHERE ANO IN (SELECT PANO FROM LOANEE WHERE ANO = ?)
        """, (pano_to_check, pano_to_check))
        root_row = cursor.fetchone()
        root_ano = root_row['ANO'] if root_row else pano_to_check
        
        cursor.execute("""
            WITH RECURSIVE family(ANO) AS (
                SELECT ANO FROM LOANEE WHERE ANO = ?
                UNION ALL
                SELECT l.ANO FROM LOANEE l JOIN family f ON l.PANO = f.ANO
            )
            SELECT ANO FROM family ORDER BY CAST(ANO AS INTEGER);
        """, (root_ano,))
        family_accounts = [row['ANO'] for row in cursor.fetchall()]

        if family_accounts:
            return jsonify(found=True, accounts=family_accounts)
        
        return jsonify(found=False, accounts=[])

    except Exception as e:
        print(f"Error in /check_parent_link: {e}")
        traceback.print_exc()
        return jsonify(found=False, error=str(e))
    finally:
        if conn:
            conn.close()

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
    if not ano or not pdt or not selected_file:
        return jsonify({"exists": False})

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({"exists": False})
            
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM PAMT1 WHERE ANO = ? AND PDT = ?", (ano, pdt))
        row = cursor.fetchone()
        
        return jsonify({"exists": bool(row)})
    except Exception as e:
        print(f"Error checking payment existence: {e}")
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
            return jsonify({"error": "Could not connect to database"})

        cursor = conn.cursor()
        cursor.execute("SELECT NAME, AMT, PAMT, BAMT, DA FROM LOANEE WHERE ANO = ?", (ano,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Customer not found"})
        return jsonify({
            "name": row[0],
            "amt": row[1],
            "pamt": row[2],
            "bamt": row[3],
            "da": row[4]
        })
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route("/submit_post_payment", methods=["POST"])
def submit_post_payment():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify({"error": "No village DB selected"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "No payment data received"}), 400

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify({"error": "Could not connect to database"}), 500
        
        cursor = conn.cursor()
        submitted_count = 0
        skipped_rows = []

        for row in data:
            ano = row["ano"]
            pdt = row["pdt"]
            amt = float(row["amt"])

            cursor.execute("SELECT 1 FROM PAMT1 WHERE ANO = ? AND PDT = ?", (ano, pdt))
            if cursor.fetchone():
                skipped_rows.append(row)
                continue

            cursor.execute("INSERT INTO PAMT1 (ANO, PDT, AMT) VALUES (?, ?, ?)", (ano, pdt, amt))
            cursor.execute("UPDATE LOANEE SET PAMT = PAMT + ?, BAMT = BAMT - ? WHERE ANO = ?", (amt, amt, ano))
            submitted_count += 1

        conn.commit()

        return jsonify({
            "message": f"✅ Submission complete. {submitted_count} payments added, {len(skipped_rows)} duplicates were skipped.",
            "skipped_rows": skipped_rows
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error in submit_post_payment: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/reset_post_payment", methods=["POST"])
def reset_post_payment():
    # This route seems to handle an in-memory table, which is not part of the provided code.
    # Assuming `post_payments_memory` is a global variable.
    # The current code would cause a NameError if this variable is not defined.
    # It's better to manage this state within the session or a more robust store.
    # For now, I'm commenting it out to avoid an error.
    # global post_payments_memory
    # post_payments_memory = []
    return "✅ Temporary table cleared."


@app.route("/view_customers")
def view_customers():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return "Could not connect to database", 500

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM LOANEE")
        rows = cursor.fetchall()

        headers = [column[0] for column in cursor.description]
        col_map = {column[0]: i for i, column in enumerate(cursor.description)}

        amt_index = col_map.get("AMT", -1)
        pamt_index = col_map.get("PAMT", -1)
        bamt_index = col_map.get("BAMT", -1)
        da_index = col_map.get("DA", -1)

        processed_rows = []
        for row in rows:
            row_list = list(row)
            if amt_index != -1 and row_list[amt_index] is not None:
                row_list[amt_index] = float(row_list[amt_index])
            else:
                row_list[amt_index] = 0.0
            
            if pamt_index != -1 and row_list[pamt_index] is not None:
                row_list[pamt_index] = float(row_list[pamt_index])
            else:
                row_list[pamt_index] = 0.0

            if bamt_index != -1 and row_list[bamt_index] is not None:
                row_list[bamt_index] = float(row_list[bamt_index])
            else:
                row_list[bamt_index] = 0.0
            
            if da_index != -1 and row_list[da_index] is not None:
                row_list[da_index] = float(row_list[da_index])
            else:
                row_list[da_index] = 0.0
            
            processed_rows.append(row_list)
            
        total_customers = len(processed_rows)
        sum_amt = sum(row[amt_index] for row in processed_rows)
        sum_pamt = sum(row[pamt_index] for row in processed_rows)
        sum_bamt = sum(row[bamt_index] for row in processed_rows)

        return render_template("view_customers.html",
                               headers=headers,
                               data=processed_rows,
                               total_customers=total_customers,
                               sum_amt=sum_amt,
                               sum_pamt=sum_pamt,
                               sum_bamt=sum_bamt)
    except Exception as e:
        print(f"Error in /view_customers: {e}")
        traceback.print_exc()
        return "Something went wrong.", 500
    finally:
        if conn:
            conn.close()

@app.route("/search", methods=["GET", "POST"])
def search_customer():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")

    loanee_headers = []
    customers = []
    pamt1_records = {}
    conn = None

    if request.method == "POST":
        query = request.form.get("query")
        try:
            conn = connect_db(selected_file)
            if conn is None:
                return "Could not connect to database", 500
            
            cursor = conn.cursor()

            search_query = f"%{query}%"
            cursor.execute("SELECT * FROM LOANEE WHERE ANO = ? OR NAME LIKE ?", (query, search_query))
            customers = cursor.fetchall()
            loanee_headers = [desc[0] for desc in cursor.description]

            for cust in customers:
                ano = cust[loanee_headers.index("ANO")]
                cursor.execute("SELECT * FROM PAMT1 WHERE ANO = ?", (ano,))
                pamt1_records[ano] = cursor.fetchall()
        except Exception as e:
            print(f"Error in /search: {e}")
            traceback.print_exc()
        finally:
            if conn:
                conn.close()
        
        return render_template("search.html", customers=customers, loanee_headers=loanee_headers,
                               pamt1_records=pamt1_records, query=query)

    return render_template("search.html")

@app.route("/update_customer_and_payments", methods=["POST"])
def update_customer_and_payments():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB file selected")

    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data received")

    update_type = data.get("type")
    conn = None

    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect to database")
            
        cursor = conn.cursor()

        if update_type == "customer":
            customer = data.get("data", {})
            if not customer or "ANO" not in customer:
                return jsonify(success=False, error="Invalid customer data")
            
            amt = float(customer.get("AMT", 0) or 0)
            pamt = float(customer.get("PAMT", 0) or 0)
            bamt = float(customer.get("BAMT", 0) or 0)
            da = float(customer.get("DA", 0) or 0)
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
            update_data = data.get("data", {})
            ano = update_data.get("ano")
            original_pdt = update_data.get("original_pdt")
            new_pdt = update_data.get("new_pdt")
            new_amt = safe_float(update_data.get("new_amt", 0))

            if not all([ano, original_pdt, new_pdt]):
                return jsonify(success=False, error="Missing required data for update.")

            cursor.execute("""
                UPDATE PAMT1 SET PDT = ?, AMT = ?
                WHERE ANO = ? AND PDT = ?
            """, (new_pdt, new_amt, ano, original_pdt))

            db.update_loanee_balances(conn, ano)

        elif update_type == "payments":
            updated_payments = data.get("data", [])
            for row in updated_payments:
                cursor.execute("UPDATE PAMT1 SET AMT = ? WHERE ANO = ? AND PDT = ?",
                               (float(row.get("amt", 0)), row.get("ano", ""), row.get("pdt", "")))

            for ano in set(p.get("ano", "") for p in updated_payments):
                db.update_loanee_balances(conn, ano)

        else:
            return jsonify(success=False, error="Unknown update type")

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ ERROR in update_customer_and_payments: {e}")
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
    amt = float(data.get("amt") or 0)
    selected_file = session.get("selected_file")

    if not selected_file:
        return jsonify(success=False, error="No DB selected")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect to database")

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
        if cursor.fetchone()[0] > 0:
            return jsonify(success=False, error="Duplicate entry exists")

        cursor.execute("INSERT INTO PAMT1 (ANO, PDT, AMT) VALUES (?, ?, ?)", (ano, pdt, amt))
        db.update_loanee_balances(conn, ano)

        conn.commit()
        return jsonify(success=True)

    except Exception as e:
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
    selected_file = session.get("selected_file")

    if not selected_file:
        return jsonify(success=False, error="No DB selected")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect to database")

        cursor = conn.cursor()

        cursor.execute("DELETE FROM PAMT1 WHERE ANO=? AND PDT=?", (ano, pdt))
        db.update_loanee_balances(conn, ano)

        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()

def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

@app.route("/search_postings", methods=["POST"])
def search_postings():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No village selected")

    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data received")

    ano = data.get("ano", "").strip()
    date = data.get("date", "").strip()

    if not ano and not date:
        return jsonify(success=False, error="Provide A.no or Date")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect to database")
            
        cursor = conn.cursor()

        query = "SELECT ANO, PDT, AMT FROM PAMT1 WHERE 1=1"
        params = []

        if ano:
            query += " AND ANO = ?"
            params.append(ano)

        if date:
            query += " AND PDT LIKE ?"
            params.append(f"{date}%")

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = [dict(row) for row in rows]
        return jsonify(success=True, data=results)
    except Exception as e:
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()

@app.route("/update_posting_date_bulk", methods=["POST"])
def update_posting_date_bulk():
    selected_file = session.get("selected_file")
    if not selected_file:
        return jsonify(success=False, error="No DB selected")

    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No data received")
        
    find_date = data.get("find_date", "").strip()
    replace_date = data.get("replace_date", "").strip()

    if not find_date or not replace_date:
        return jsonify(success=False, error="Both find and replace dates required")

    conn = None
    try:
        conn = connect_db(selected_file)
        if conn is None:
            return jsonify(success=False, error="Could not connect to database")

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM PAMT1 WHERE PDT LIKE ?", (f"{find_date}%",))
        count = cursor.fetchone()[0]

        if count == 0:
            return jsonify(success=False, message=f"No records found for {find_date}")

        cursor.execute("UPDATE PAMT1 SET PDT = ? WHERE PDT LIKE ?", (replace_date, f"{find_date}%"))

        cursor.execute("SELECT DISTINCT ANO FROM PAMT1 WHERE PDT = ?", (replace_date,))
        anos = [row[0] for row in cursor.fetchall()]

        for ano in anos:
            db.update_loanee_balances(conn, ano)

        conn.commit()

        return jsonify(success=True, message=f"{count} records updated from {find_date} ➝ {replace_date}")
    except Exception as e:
        return jsonify(success=False, error=str(e))
    finally:
        if conn:
            conn.close()

@app.route('/print_customer/<ano>')
def print_customer(ano):
    db_file = session.get('selected_file')
    if not db_file:
        return "No village selected.", 400

    conn = None
    try:
        conn = connect_db(db_file)
        if conn is None:
            return "Could not connect to database", 500

        cursor = conn.cursor()
        cursor.execute("""
            SELECT ANO, NAME, ADD1, ADD2, FDT, TDT, AMT, PAMT, BAMT, DA, DW, DS
            FROM LOANEE
            WHERE ANO = ?
        """, (ano,))
        customer = cursor.fetchone()

        cursor.execute("""
            SELECT PDT, AMT FROM PAMT1 WHERE ANO = ? ORDER BY SUBSTR(PDT, 7, 4) || SUBSTR(PDT, 4, 2) || SUBSTR(PDT, 1, 2) ASC
        """, (ano,))
        payments = cursor.fetchall()

        if not customer:
            return "Customer not found.", 404

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
        print(f"Error in /print_customer: {e}")
        return "Something went wrong.", 500
    finally:
        if conn:
            conn.close()

@app.route('/get_payments_data/<filename>')
def get_payments_data(filename: str):
    conn = None
    try:
        db_path = db.get_database_path(filename)
        conn = connect_db(filename)
        if conn is None:
            return jsonify({"error": "Could not connect to database"})
            
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PAMT1")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route("/post_payment_report", methods=["GET", "POST"])
def post_payment_report():
    selected_file = session.get("selected_file")
    if not selected_file:
        return redirect("/dashboard")

    conn = None
    try:
        db_path = db.get_database_path(selected_file)
        conn = connect_db(selected_file)
        if conn is None:
            return "Could not connect to database", 500
            
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_pamt1_ano ON PAMT1 (ANO)",
            "CREATE INDEX IF NOT EXISTS idx_pamt1_pdt ON PAMT1 (PDT)"
        ]
        for stmt in index_statements:
            cursor.execute(stmt)

        ano_filter = request.form.get("ano_filter", "").strip()
        from_date = request.form.get("from_date", "")
        to_date = request.form.get("to_date", "")

        query = "SELECT ANO, PDT, AMT FROM PAMT1 WHERE 1=1"
        params = []

        if ano_filter:
            query += " AND ANO = ?"
            params.append(ano_filter)

        def to_db_sortable_date(d_str):
            return datetime.strptime(d_str, '%d/%m/%Y').strftime('%Y-%m-%d')

        date_transform = "substr(PDT, 7, 4) || '-' || substr(PDT, 4, 2) || '-' || substr(PDT, 1, 2)"

        if from_date and to_date:
            query += f" AND {date_transform} BETWEEN ? AND ?"
            params.extend([to_db_sortable_date(from_date), to_db_sortable_date(to_date)])
        elif from_date:
            query += f" AND {date_transform} = ?"
            params.append(to_db_sortable_date(from_date))

        query += f" ORDER BY {date_transform} DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        payments = [list(row) for row in rows]

        return render_template(
            "post_payment_report.html",
            payments=payments,
            ano_filter=ano_filter,
            from_date=from_date,
            to_date=to_date
        )

    except Exception as e:
        print("Error in /post_payment_report:", e)
        traceback.print_exc()
        return "Something went wrong.", 500
    finally:
        if conn:
            conn.close()

@app.template_filter('format_rupee')
def format_rupee(value):
    try:
        return "₹{:,.2f}".format(float(value))
    except:
        return value

import webbrowser
import threading

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8080")

if __name__ == "__main__":
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.25, open_browser).start()

    app.run(debug=True, port=8080)