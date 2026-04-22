from sqlalchemy import create_engine, text

# ============================================================
# CONFIG
# ============================================================

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"
engine = create_engine(PG_URL, future=True)

def run(sql, msg=None):
    with engine.begin() as conn:
        conn.execute(text(sql))
    if msg:
        print(f"✅ {msg}")

def count(table):
    with engine.begin() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

def main():
    print("\n🚀 STARTING FINAL MIGRATION")

    # ============================================================
    # DEV MODE — CLEAN FINAL TABLES
    # ============================================================

    print("\n🧹 TRUNCATING FINAL TABLES (DEV MODE)")

    run("TRUNCATE payment CASCADE")
    run("TRUNCATE closed_cust_payment CASCADE")
    run("TRUNCATE customer CASCADE")
    run("TRUNCATE closed_cust_account CASCADE")
    run("TRUNCATE village CASCADE")
    run("TRUNCATE employee CASCADE")

    print("✅ Final tables truncated")

    # ============================================================
    # PERFORMANCE INDEXES
    # ============================================================

    run("CREATE INDEX IF NOT EXISTS idx_stage_customer_ano ON stage_customer(ano)")
    run("CREATE INDEX IF NOT EXISTS idx_stage_payment_ano ON stage_payment(ano)")
    run("CREATE INDEX IF NOT EXISTS idx_stage_customer_balance ON stage_customer(balance_amount)")

    run("CREATE INDEX IF NOT EXISTS idx_stage_payment_ano_vid ON stage_payment(ano, vid)")
    run("CREATE INDEX IF NOT EXISTS idx_stage_customer_ano_vid ON stage_customer(ano, vid)")

    # ============================================================
    # STEP 1 — EMPLOYEE
    # ============================================================

    run("""
    INSERT INTO employee (eid, name, phone_number, city, joining_date, level, state, is_active)
    SELECT 
        eid,
        name,
        phone_number,
        city,
        joining_date,
        level,
        state,
        TRUE
    FROM stage_employee
    ON CONFLICT (eid) DO NOTHING
    """, "Employees migrated")


    # ============================================================
    # STEP 2 — VILLAGE
    # ============================================================

    run("""
    INSERT INTO village (
        vid, village_code, village_name, district, pincode, state, emp1, emp2, source_file, status
    )
    SELECT
        vid,
        village_code,
        village_name,
        district,
        pincode,
        state,
        emp1,
        emp2,
        source_file,
        'active'
    FROM stage_village
    """, "Villages migrated")


    # ============================================================
    # STEP 3 — OPEN CUSTOMERS (balance > 0)
    # ============================================================

    run("""
    INSERT INTO customer (
        cid,
        ano, name, vid, start_date, end_date,
        total_amount, paid_amount, balance_amount,
        installment_amount, type, period, pano,
        created_at, aadhaar_number, notes, latitude, longitude, eid,
        status
    )
    SELECT
        cid,
        ano, name, vid, start_date, end_date,
        total_amount, paid_amount, balance_amount,
        installment_amount, type, period, pano,
        created_at, aadhaar_number, notes, latitude, longitude, eid,
        'open'
    FROM stage_customer
    WHERE balance_amount > 0
    """, "Open customers migrated")


    # ============================================================
    # STEP 4 — CLOSED / DEFAULTED CUSTOMERS
    # ============================================================

    run("""
    INSERT INTO closed_cust_account (
        cid,
        ano, name, vid, start_date, end_date,
        total_amount, paid_amount, balance_amount,
        installment_amount, type, period, pano,
        created_at, aadhaar_number, notes, latitude, longitude, eid,
        status
    )
    SELECT
        cid,
        ano, name, vid, start_date, end_date,
        total_amount, paid_amount, balance_amount,
        installment_amount, type, period, pano,
        created_at, aadhaar_number, notes, latitude, longitude, eid,
        CASE 
            WHEN balance_amount = 0 THEN 'closed'
            WHEN balance_amount < 0 THEN 'defaulted'
        END
    FROM stage_customer
    WHERE balance_amount <= 0
    """, "Closed/defaulted customers migrated")


    # ============================================================
    # TEMP TABLES FOR FAST JOINS
    # ============================================================

    run("""
    DROP TABLE IF EXISTS tmp_open_customers;
    CREATE TEMP TABLE tmp_open_customers AS
    SELECT ano, vid, eid 
    FROM stage_customer 
    WHERE balance_amount > 0;
    """)

    run("CREATE INDEX IF NOT EXISTS idx_tmp_open_customers_ano ON tmp_open_customers(ano)")

    run("""
    DROP TABLE IF EXISTS tmp_closed_customers;
    CREATE TEMP TABLE tmp_closed_customers AS
    SELECT ano, vid, eid 
    FROM stage_customer 
    WHERE balance_amount <= 0;
    """)

    run("CREATE INDEX IF NOT EXISTS idx_tmp_closed_customers_ano ON tmp_closed_customers(ano)")

    run("SET synchronous_commit TO OFF")
    run("ALTER TABLE payment SET UNLOGGED")
    run("ALTER TABLE closed_cust_payment SET UNLOGGED")

    # ============================================================
    # STEP 5 — PAYMENTS (OPEN CUSTOMERS)
    # ============================================================

    run("""
    CREATE TEMP TABLE tmp_payment_open AS
    SELECT
        sp.ano::bigint AS ano,
        sp.payment_date,
        sp.amt,
        sp.created_at,
        c.eid,
        sp.cid,
        sp.vid,
        NULL::timestamp AS updated_at
    FROM stage_payment sp
    JOIN customer c
      ON sp.cid = c.cid;
    """)

    run("""
    INSERT INTO payment (
        ano, payment_date, amt, created_at, eid, cid, vid, updated_at
    )
    SELECT
        ano,
        payment_date,
        amt,
        created_at,
        eid,
        cid,
        vid,
        updated_at
    FROM tmp_payment_open;
    """, "Payments (open customers) migrated")


    # ============================================================
    # STEP 6 — CLOSED CUSTOMER PAYMENTS
    # ============================================================

    run("""
    CREATE TEMP TABLE tmp_payment_closed AS
    SELECT
        sp.ano::bigint AS ano,
        sp.payment_date,
        sp.amt,
        sp.created_at,
        cc.eid,
        sp.cid,
        sp.vid
    FROM stage_payment sp
    JOIN closed_cust_account cc
      ON sp.cid = cc.cid;
    """)

    run("""
    INSERT INTO closed_cust_payment (
        ano, payment_date, amt, created_at, eid, cid, vid
    )
    SELECT
        ano,
        payment_date,
        amt,
        created_at,
        eid,
        cid,
        vid
    FROM tmp_payment_closed;
    """, "Payments (closed customers) migrated")

    run("ALTER TABLE payment SET LOGGED")
    run("ALTER TABLE closed_cust_payment SET LOGGED")

    # ============================================================
    # FINAL COUNTS
    # ============================================================

    print("\n📊 FINAL COUNTS (TABLE)")
    print("="*50)
    print(f"{'Table':<25}{'Rows':>15}")
    print("="*50)
    print(f"{'employee':<25}{count('employee'):>15}")
    print(f"{'village':<25}{count('village'):>15}")
    print(f"{'customer (open)':<25}{count('customer'):>15}")
    print(f"{'closed_cust_account':<25}{count('closed_cust_account'):>15}")
    print(f"{'payment':<25}{count('payment'):>15}")
    print(f"{'closed_cust_payment':<25}{count('closed_cust_payment'):>15}")
    print("="*50)

if __name__ == "__main__":
    main()