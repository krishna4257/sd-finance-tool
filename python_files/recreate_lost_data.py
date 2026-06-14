import os
import re
import sys
import time
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, date, timedelta
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ANSI escape codes for pretty console output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_db_connection(config=None):
    if config:
        return psycopg2.connect(**config)
    
    db_config = {
        "host": os.environ.get("DB_HOST", "localhost").strip(),
        "database": os.environ.get("DB_NAME", "postgres").strip(),
        "user": os.environ.get("DB_USER", "postgres").strip(),
        "password": os.environ.get("DB_PASSWORD", "").strip(),
        "port": os.environ.get("DB_PORT", "5432").strip(),
    }
    return psycopg2.connect(**db_config)

def get_village_stats(cur, vid):
    """
    Retrieves the following stats for a village:
    - Most common payment type (W or M)
    - Dominant period if >= 90% of customers have it, otherwise None
    - Most common EID (employee ID)
    """
    # Most common payment type
    cur.execute("""
        SELECT type, COUNT(*)
        FROM (
            SELECT type FROM customer WHERE vid = %s AND type IS NOT NULL
            UNION ALL
            SELECT type FROM closed_cust_account WHERE vid = %s AND type IS NOT NULL
        ) t
        GROUP BY type
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """, (vid, vid))
    type_row = cur.fetchone()
    pmt_type = type_row[0] if type_row else 'W'

    # Most common period and its ratio
    cur.execute("""
        SELECT period, COUNT(*), (
            SELECT COUNT(*) FROM (
                SELECT period FROM customer WHERE vid = %s AND period IS NOT NULL
                UNION ALL
                SELECT period FROM closed_cust_account WHERE vid = %s AND period IS NOT NULL
            ) t_sub
        )
        FROM (
            SELECT period FROM customer WHERE vid = %s AND period IS NOT NULL
            UNION ALL
            SELECT period FROM closed_cust_account WHERE vid = %s AND period IS NOT NULL
        ) t
        GROUP BY period
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """, (vid, vid, vid, vid))
    period_row = cur.fetchone()
    dominant_period = None
    if period_row and period_row[2] > 0:
        ratio = period_row[1] / period_row[2]
        if ratio >= 0.90:
            dominant_period = period_row[0]

    # Most common EID
    cur.execute("""
        SELECT eid, COUNT(*)
        FROM (
            SELECT eid FROM customer WHERE vid = %s AND eid IS NOT NULL
            UNION ALL
            SELECT eid FROM closed_cust_account WHERE vid = %s AND eid IS NOT NULL
        ) e
        GROUP BY eid
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """, (vid, vid))
    eid_row = cur.fetchone()
    most_common_eid = eid_row[0] if eid_row else None

    return pmt_type, dominant_period, most_common_eid

def setup_database_schema(cur):
    """
    Creates historic_customer_data table and adds cid column to historic_payment_data if they don't exist.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historic_customer_data (
            cid bigint PRIMARY KEY,
            ano integer,
            name text,
            vid integer,
            start_date date,
            end_date date,
            total_amount numeric,
            paid_amount numeric,
            balance_amount numeric,
            installment_amount numeric,
            type character(1),
            period integer,
            pano text,
            created_at timestamp with time zone,
            aadhaar_number text,
            notes text,
            latitude numeric,
            longitude numeric,
            eid integer,
            status text,
            closed_at timestamp with time zone,
            phone_number text,
            customer_rating numeric,
            final_frozen_rating numeric,
            final_risk_level text,
            freeze_date timestamp with time zone,
            base_amount numeric,
            cutting_amount numeric,
            interest_amount numeric
        );
    """)
    
    cur.execute("""
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'historic_payment_data' AND column_name = 'cid';
    """)
    if not cur.fetchone():
        print(f"{Colors.WARNING}Adding 'cid' column to 'historic_payment_data' table...{Colors.ENDC}")
        cur.execute("ALTER TABLE historic_payment_data ADD COLUMN cid bigint;")

    # Ensure indexes exist for query speed
    cur.execute("CREATE INDEX IF NOT EXISTS idx_historic_payment_vid_ano ON historic_payment_data (vid, ano);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_closed_cust_payment_vid_ano ON closed_cust_payment (vid, ano);")


def get_max_cid(cur):
    """
    Finds the maximum CID across customer, closed_cust_account, and historic_customer_data.
    """
    cur.execute("""
        SELECT COALESCE(MAX(cid), 0) FROM (
            SELECT cid FROM customer
            UNION ALL
            SELECT cid FROM closed_cust_account
            UNION ALL
            SELECT cid FROM historic_customer_data
        ) t;
    """)
    return cur.fetchone()[0]

def scan_for_orphans(cur, vid=None):
    """
    Scans the database for (vid, ano) pairs that are present in the
    payment, closed_cust_payment, and historic_payment_data tables
    but NOT in customer, closed_cust_account, or historic_customer_data.
    """
    if vid is not None:
        query = """
            SELECT distinct_pmt.vid, distinct_pmt.ano
            FROM (
                SELECT DISTINCT vid, ano FROM payment WHERE vid = %s AND ano IS NOT NULL
                UNION
                SELECT DISTINCT vid, ano FROM closed_cust_payment WHERE vid = %s AND ano IS NOT NULL
                UNION
                SELECT DISTINCT vid, ano FROM historic_payment_data WHERE vid = %s AND ano IS NOT NULL
            ) distinct_pmt
            WHERE NOT EXISTS (
                SELECT 1 FROM customer c 
                WHERE c.vid = distinct_pmt.vid AND c.ano = distinct_pmt.ano
            )
            AND NOT EXISTS (
                SELECT 1 FROM closed_cust_account cc 
                WHERE cc.vid = distinct_pmt.vid AND cc.ano = distinct_pmt.ano
            )
            AND NOT EXISTS (
                SELECT 1 FROM historic_customer_data hc 
                WHERE hc.vid = distinct_pmt.vid AND hc.ano = distinct_pmt.ano
            )
            ORDER BY distinct_pmt.vid, distinct_pmt.ano;
        """
        cur.execute(query, (vid, vid, vid))
    else:
        query = """
            SELECT distinct_pmt.vid, distinct_pmt.ano
            FROM (
                SELECT DISTINCT vid, ano FROM payment WHERE vid IS NOT NULL AND ano IS NOT NULL
                UNION
                SELECT DISTINCT vid, ano FROM closed_cust_payment WHERE vid IS NOT NULL AND ano IS NOT NULL
                UNION
                SELECT DISTINCT vid, ano FROM historic_payment_data WHERE vid IS NOT NULL AND ano IS NOT NULL
            ) distinct_pmt
            WHERE NOT EXISTS (
                SELECT 1 FROM customer c 
                WHERE c.vid = distinct_pmt.vid AND c.ano = distinct_pmt.ano
            )
            AND NOT EXISTS (
                SELECT 1 FROM closed_cust_account cc 
                WHERE cc.vid = distinct_pmt.vid AND cc.ano = distinct_pmt.ano
            )
            AND NOT EXISTS (
                SELECT 1 FROM historic_customer_data hc 
                WHERE hc.vid = distinct_pmt.vid AND hc.ano = distinct_pmt.ano
            )
            ORDER BY distinct_pmt.vid, distinct_pmt.ano;
        """
        cur.execute(query)
        
    return cur.fetchall()

def get_payments_for_orphan(cur, vid, ano):
    """
    Gets all payments for a specific (vid, ano) pair.
    """
    cur.execute("""
        SELECT pid, payment_date, amt, created_at, eid
        FROM (
            SELECT pid, payment_date, amt, created_at, eid FROM payment WHERE vid = %s AND ano = %s
            UNION ALL
            SELECT pid, payment_date, amt, created_at, eid FROM closed_cust_payment WHERE vid = %s AND ano = %s
            UNION ALL
            SELECT pid, payment_date, amount AS amt, created_at, eid FROM historic_payment_data WHERE vid = %s AND ano = %s
        ) all_pmts
        ORDER BY payment_date ASC, created_at ASC;
    """, (vid, ano, vid, ano, vid, ano))
    return cur.fetchall()

def ask_yes_no(prompt, default='y'):
    valid = {"yes": True, "y": True, "no": False, "n": False}
    if default == 'y':
        prompt_suffix = " [Y/n]: "
    elif default == 'n':
        prompt_suffix = " [y/N]: "
    else:
        prompt_suffix = " [y/n]: "
        
    while True:
        choice = input(prompt + prompt_suffix).strip().lower()
        if choice == '' and default is not None:
            return valid[default]
        if choice in valid:
            return valid[choice]
        print("Please respond with 'yes'/'y' or 'no'/'n'.")

def clean_village_name(name):
    if not name:
        return ""
    name = re.sub(r'\d+$', '', name)
    return name.strip()

def run():
    print(f"{Colors.HEADER}=== Recreate Deleted Customers from Payments ==={Colors.ENDC}\n")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"{Colors.FAIL}Error connecting to database with default .env config: {e}{Colors.ENDC}")
        print("Please enter database connection details manually:")
        host = input("DB Host: ").strip()
        database = input("DB Name: ").strip()
        user = input("DB User: ").strip()
        password = input("DB Password: ").strip()
        port = input("DB Port [5432]: ").strip() or "5432"
        
        try:
            conn = get_db_connection({
                "host": host,
                "database": database,
                "user": user,
                "password": password,
                "port": port
            })
            cur = conn.cursor()
        except Exception as ex:
            print(f"{Colors.FAIL}Failed to connect: {ex}{Colors.ENDC}")
            sys.exit(1)

    is_test_mode = ask_yes_no("Would you like to run in Test Mode? (simulates two orphan accounts on a village with fake payments)", 'n')
    
    if not is_test_mode:
        setup_database_schema(cur)
        max_cid = get_max_cid(cur)
    else:
        max_cid = 9000000
    
    print(f"{Colors.OKGREEN}Starting CID allocation from: {max_cid + 1}{Colors.ENDC}\n")

    cur.execute("SELECT vid, village_code, village_name FROM village ORDER BY village_name;")
    villages_list = cur.fetchall()
    villages = {v[0]: (v[1], v[2]) for v in villages_list}

    if not villages_list:
        print(f"{Colors.FAIL}No villages found in the database. Please initialize the database first.{Colors.ENDC}")
        return

    selected_vid = None
    if not is_test_mode:
        print("\nAvailable Villages:")
        for vid, code, name in villages_list[:20]:
            print(f"  ID: {vid} | Code: {code} | Name: {name}")
        if len(villages_list) > 20:
            print(f"  ... and {len(villages_list) - 20} more villages.")
        
        selection = input("\nEnter Village ID to scan (or press Enter to scan all villages): ").strip()
        if selection:
            try:
                selected_vid = int(selection)
                if selected_vid not in villages:
                    print(f"{Colors.FAIL}Invalid Village ID {selected_vid}.{Colors.ENDC}")
                    return
            except ValueError:
                print(f"{Colors.FAIL}Invalid input. Please enter a valid number.{Colors.ENDC}")
                return
    else:
        selected_vid = villages_list[0][0]
        print(f"\n[Test Mode] Using village: {villages[selected_vid][1]} (ID: {selected_vid})")

    candidates = []
    if is_test_mode:
        candidates = [(selected_vid, 99991), (selected_vid, 99992)]
        print(f"\n[Test Mode] Faking two orphan account numbers: 99991 and 99992")
    else:
        print(f"\nScanning for orphan payments...")
        candidates = scan_for_orphans(cur, selected_vid)
        if not candidates:
            print(f"{Colors.WARNING}No orphan payments found in the database. All payments are linked to active/closed customers.{Colors.ENDC}")
            print("To see how the script works, try running in Test Mode.")
            return
        print(f"Found {len(candidates)} orphan account candidates.")

    # Fetch aggregates in bulk if there are many candidates to optimize speed
    recreated_profiles = []
    
    # Large scale optimization: If scanning all/many, fetch data in bulk
    use_bulk_aggregation = len(candidates) > 50 and not is_test_mode
    
    if use_bulk_aggregation:
        print("Optimizing: Fetching and aggregating payments in bulk...")
        # Create a temp cache of stats for all active villages
        village_stats = {}
        for v_id in villages.keys():
            village_stats[v_id] = get_village_stats(cur, v_id)
            
        cur.execute("""
            SELECT 
                t.vid, 
                t.ano, 
                COUNT(*) AS num_payments, 
                SUM(t.amt) AS total_amount, 
                MIN(t.payment_date) AS first_payment_date, 
                MAX(t.payment_date) AS last_payment_date,
                MIN(t.created_at) AS created_at,
                MIN(t.eid) AS first_eid
            FROM (
                SELECT vid, ano, payment_date, amt, created_at, eid FROM payment WHERE vid IS NOT NULL AND ano IS NOT NULL
                UNION ALL
                SELECT vid, ano, payment_date, amt, created_at, eid FROM closed_cust_payment WHERE vid IS NOT NULL AND ano IS NOT NULL
                UNION ALL
                SELECT vid, ano, payment_date, amount AS amt, created_at, eid FROM historic_payment_data WHERE vid IS NOT NULL AND ano IS NOT NULL
            ) t
            WHERE NOT EXISTS (SELECT 1 FROM customer c WHERE c.vid = t.vid AND c.ano = t.ano)
              AND NOT EXISTS (SELECT 1 FROM closed_cust_account cc WHERE cc.vid = t.vid AND cc.ano = t.ano)
              AND NOT EXISTS (SELECT 1 FROM historic_customer_data hc WHERE hc.vid = t.vid AND hc.ano = t.ano)
            GROUP BY t.vid, t.ano
            ORDER BY t.vid, t.ano;
        """)
        
        aggregated_rows = cur.fetchall()
        for idx, (vid, ano, num_payments, total_amount, first_payment_date, last_payment_date, created_at, first_eid) in enumerate(aggregated_rows):
            v_code, v_name = villages.get(vid, ("", f"Village {vid}"))
            pmt_type, dominant_period, most_common_eid = village_stats.get(vid, ('W', None, 1))
            
            period = dominant_period if dominant_period is not None else num_payments
            installment_amount = round(total_amount / period, 2) if period > 0 else Decimal('0.00')
            
            if pmt_type == 'W':
                start_date = first_payment_date - timedelta(days=7)
                end_date = start_date + timedelta(days=period * 7)
            else:
                start_date = first_payment_date - timedelta(days=30)
                end_date = start_date + timedelta(days=period * 30)
                
            recreated_profiles.append({
                "cid": max_cid + 1 + idx,
                "vid": vid,
                "village_name": v_name,
                "ano": ano,
                "payments_count": num_payments,
                "total_amount": total_amount,
                "pmt_type": pmt_type,
                "period": period,
                "period_desc": f"dominant ({period})" if dominant_period is not None else f"count ({period})",
                "installment_amount": installment_amount,
                "first_payment_date": first_payment_date,
                "last_payment_date": last_payment_date,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": created_at if created_at else datetime.now(),
                "eid": first_eid if first_eid else (most_common_eid or 1)
            })
    else:
        # Standard loop for small villages or test mode
        for idx, (vid, ano) in enumerate(candidates):
            v_code, v_name = villages[vid]
            
            if is_test_mode:
                if ano == 99991:
                    start_date_base = date(2026, 1, 8)
                    payments_data = []
                    for i in range(10):
                        p_date = start_date_base + timedelta(days=i * 7)
                        payments_data.append((100000 + i, p_date, Decimal('1000.00'), datetime.now(), 99))
                else:
                    start_date_base = date(2026, 5, 10)
                    payments_data = []
                    for i in range(5):
                        p_date = start_date_base + timedelta(days=i * 7)
                        payments_data.append((200000 + i, p_date, Decimal('2000.00'), datetime.now(), 99))
            else:
                payments_data = get_payments_for_orphan(cur, vid, ano)

            if not payments_data:
                continue
                
            pmt_type, dominant_period, most_common_eid = get_village_stats(cur, vid)
            total_amount = sum(Decimal(p[2]) for p in payments_data)
            num_payments = len(payments_data)
            
            period = dominant_period if dominant_period is not None else num_payments
            installment_amount = round(total_amount / period, 2) if period > 0 else Decimal('0.00')
            first_payment_date = payments_data[0][1]
            
            if pmt_type == 'W':
                start_date = first_payment_date - timedelta(days=7)
                end_date = start_date + timedelta(days=period * 7)
            else:
                start_date = first_payment_date - timedelta(days=30)
                end_date = start_date + timedelta(days=period * 30)
                
            created_at = payments_data[0][3] if payments_data[0][3] else datetime.now()
            eid = payments_data[0][4] if payments_data[0][4] else (most_common_eid or 1)
            
            recreated_profiles.append({
                "cid": max_cid + 1 + idx,
                "vid": vid,
                "village_name": v_name,
                "ano": ano,
                "payments_count": num_payments,
                "total_amount": total_amount,
                "pmt_type": pmt_type,
                "period": period,
                "period_desc": f"dominant ({period})" if dominant_period is not None else f"count ({period})",
                "installment_amount": installment_amount,
                "first_payment_date": first_payment_date,
                "last_payment_date": payments_data[-1][1],
                "start_date": start_date,
                "end_date": end_date,
                "created_at": created_at,
                "eid": eid
            })

    # Display Candidates (limit display to first 10 for sanity in bulk runs)
    print(f"\n{Colors.OKBLUE}=== Candidates for Reconstruction (showing first 10 of {len(recreated_profiles)}) ==={Colors.ENDC}")
    for idx, acc in enumerate(recreated_profiles[:10], 1):
        print(f"\n{Colors.BOLD}[{idx}] Village: {acc['village_name']} (ID: {acc['vid']}) | Account Number (ANO): {acc['ano']}{Colors.ENDC}")
        print(f"    Assigned CID: {acc['cid']}")
        print(f"    Total Amount: {acc['total_amount']} | Paid Amount: {acc['total_amount']} | Balance: 0.00")
        print(f"    Type: {acc['pmt_type']} | Period: {acc['period']} ({acc['period_desc']}) | Installment: {acc['installment_amount']}")
        print(f"    Start Date: {acc['start_date']} | End Date: {acc['end_date']}")
        print(f"    First Payment Date: {acc['first_payment_date']} | Last Payment Date: {acc['last_payment_date']}")
        print(f"    Employee ID (EID): {acc['eid']}")

    print(f"\n{Colors.HEADER}=== Interactive Validations ==={Colors.ENDC}")
    
    custom_name = "RTC"
    if ask_yes_no("Validation 1: Recreated customers will be named 'RTC'. Do you want to customize this name?"):
        custom_name = input("Enter custom name: ").strip() or "RTC"
        for acc in recreated_profiles:
            acc["name"] = custom_name
    else:
        for acc in recreated_profiles:
            acc["name"] = "RTC"

    if not ask_yes_no("Validation 2: Proceed with the automatic period/type rule (using 90% dominant or falling back to number of payments)?"):
        print(f"{Colors.FAIL}Aborted. You can re-run and customize the rules.{Colors.ENDC}")
        return

    if not ask_yes_no("Validation 3: Proceed with setting the start date to 1 week (or 1 month) before the first payment date?"):
        print(f"{Colors.FAIL}Aborted.{Colors.ENDC}")
        return

    print("\nSelect the action to perform:")
    print("  1. Generate SQL script file (recreated_customers.sql)")
    print("  2. Print SQL to console")
    print("  3. Directly insert into database (under transactions with progressive commits)")
    
    action_choice = input("Select option [1]: ").strip() or "1"
    
    if action_choice in ("1", "2"):
        # Bulk SQL Script construction
        sql_statements = []
        sql_statements.append("BEGIN;\n")
        sql_statements.append("""-- Ensure historic_customer_data table exists
CREATE TABLE IF NOT EXISTS historic_customer_data (
    cid bigint PRIMARY KEY,
    ano integer,
    name text,
    vid integer,
    start_date date,
    end_date date,
    total_amount numeric,
    paid_amount numeric,
    balance_amount numeric,
    installment_amount numeric,
    type character(1),
    period integer,
    pano text,
    created_at timestamp with time zone,
    aadhaar_number text,
    notes text,
    latitude numeric,
    longitude numeric,
    eid integer,
    status text,
    closed_at timestamp with time zone,
    phone_number text,
    customer_rating numeric,
    final_frozen_rating numeric,
    final_risk_level text,
    freeze_date timestamp with time zone,
    base_amount numeric,
    cutting_amount numeric,
    interest_amount numeric
);""")
        sql_statements.append("ALTER TABLE historic_payment_data ADD COLUMN IF NOT EXISTS cid bigint;\n")
        
        # Build bulk inserts in chunks of 5000 for SQL file safety
        chunk_size = 5000
        for i in range(0, len(recreated_profiles), chunk_size):
            chunk = recreated_profiles[i:i+chunk_size]
            values_list = []
            for acc in chunk:
                eid_val = str(acc['eid']) if acc['eid'] is not None else "NULL"
                start_str = acc['start_date'].strftime('%Y-%m-%d')
                end_str = acc['end_date'].strftime('%Y-%m-%d')
                created_str = acc['created_at'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(acc['created_at'], datetime) else str(acc['created_at'])
                values_list.append(f"({acc['cid']}, {acc['ano']}, '{acc['name']}', {acc['vid']}, {eid_val}, '{start_str}', '{end_str}', {acc['total_amount']}, {acc['total_amount']}, 0.0, {acc['installment_amount']}, '{acc['pmt_type']}', {acc['period']}, '{created_str}', 'Auto-recreated from orphan payment records', 'closed', '{end_str}', 100.0)")
            
            insert_stmt = """INSERT INTO historic_customer_data (
    cid, ano, name, vid, eid, start_date, end_date,
    total_amount, paid_amount, balance_amount, installment_amount,
    type, period, created_at, notes, status, closed_at, customer_rating
) VALUES \n""" + ",\n".join(values_list) + ";"
            sql_statements.append(insert_stmt)
            
        # Add bulk updates to end of script
        sql_statements.append("""
-- Bulk link payment tables
UPDATE payment p SET cid = hc.cid FROM historic_customer_data hc WHERE p.vid = hc.vid AND p.ano = hc.ano AND p.cid IS NULL;
UPDATE closed_cust_payment ccp SET cid = hc.cid FROM historic_customer_data hc WHERE ccp.vid = hc.vid AND ccp.ano = hc.ano AND ccp.cid IS NULL;
UPDATE historic_payment_data hpd SET cid = hc.cid FROM historic_customer_data hc WHERE hpd.vid = hc.vid AND hpd.ano = hc.ano AND hpd.cid IS NULL;
""")
        sql_statements.append("COMMIT;")
        
        full_sql = "\n\n".join(sql_statements)
        
        if action_choice == "1":
            output_file = "recreated_customers.sql"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(full_sql)
            print(f"\n{Colors.OKGREEN}[SUCCESS] SQL script successfully generated and saved to '{output_file}'!{Colors.ENDC}")
        else:
            print(f"\n{Colors.OKBLUE}=== Generated SQL Script ==={Colors.ENDC}")
            print(full_sql)

    elif action_choice == "3":
        print(f"\n{Colors.WARNING}[WARNING] Starting database transaction...{Colors.ENDC}")
        try:
            conn.autocommit = False
            
            # Step 1: Bulk insert into historic_customer_data
            insert_tuples = [
                (
                    acc['cid'], acc['ano'], acc['name'], acc['vid'], acc['eid'], 
                    acc['start_date'], acc['end_date'],
                    float(acc['total_amount']), float(acc['total_amount']), 0.0, float(acc['installment_amount']),
                    acc['pmt_type'], acc['period'], acc['created_at'], 
                    'Auto-recreated from orphan payment records', 'closed', acc['end_date'], 100.0
                )
                for acc in recreated_profiles
            ]
            
            print(f"Bulk inserting {len(insert_tuples)} historic customer records...")
            execute_values(cur, """
                INSERT INTO historic_customer_data (
                    cid, ano, name, vid, eid, start_date, end_date,
                    total_amount, paid_amount, balance_amount, installment_amount,
                    type, period, created_at, notes, status, closed_at, customer_rating
                ) VALUES %s
            """, insert_tuples)
            
            commit = ask_yes_no("Do you want to commit these changes to the database permanently?")
            if commit:
                conn.commit()
                print(f"\n{Colors.OKGREEN}[SUCCESS] Historic customer records committed successfully!{Colors.ENDC}")
                
                # Step 2: Progressive commits for payment table updates
                if not is_test_mode:
                    print("Bulk linking payment table CIDs...")
                    cur.execute("""
                        UPDATE payment p
                        SET cid = hc.cid
                        FROM historic_customer_data hc
                        WHERE p.vid = hc.vid AND p.ano = hc.ano AND p.cid IS NULL;
                    """)
                    conn.commit()
                    print(f"  Linked and committed {cur.rowcount} active payments.")
                    
                    print("Bulk linking closed_cust_payment table CIDs...")
                    cur.execute("""
                        UPDATE closed_cust_payment ccp
                        SET cid = hc.cid
                        FROM historic_customer_data hc
                        WHERE ccp.vid = hc.vid AND ccp.ano = hc.ano AND ccp.cid IS NULL;
                    """)
                    conn.commit()
                    print(f"  Linked and committed {cur.rowcount} closed payments.")
                    
                    print("Bulk linking historic_payment_data table CIDs...")
                    cur.execute("""
                        UPDATE historic_payment_data hpd
                        SET cid = hc.cid
                        FROM historic_customer_data hc
                        WHERE hpd.vid = hc.vid AND hpd.ano = hc.ano AND hpd.cid IS NULL;
                    """)
                    conn.commit()
                    print(f"  Linked and committed {cur.rowcount} historic payments.")
                else:
                    print("[Test Mode] Simulating payment updates completed.")
            else:
                conn.rollback()
                print(f"\n{Colors.WARNING}[ROLLED BACK] Transaction rolled back. No changes were saved.{Colors.ENDC}")
                
        except Exception as ex:
            if conn:
                conn.rollback()
            print(f"{Colors.FAIL}[ERROR] Database error encountered: {ex}{Colors.ENDC}")
            print(f"{Colors.WARNING}[ROLLED BACK] Transaction rolled back safely.{Colors.ENDC}")
            
    if conn:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run()
