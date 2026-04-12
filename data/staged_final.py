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
    ano, name, vid, start_date, end_date,
    total_amount, paid_amount, balance_amount,
    installment_amount, type, period, pano,
    created_at, aadhaar_number, notes, latitude, longitude, eid,
    status
)
SELECT
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
    ano, name, vid, start_date, end_date,
    total_amount, paid_amount, balance_amount,
    installment_amount, type, period, pano,
    created_at, aadhaar_number, notes, latitude, longitude, eid,
    status
)
SELECT
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
SELECT ano, eid FROM stage_customer WHERE balance_amount > 0;
""")

run("""
DROP TABLE IF EXISTS tmp_closed_customers;
CREATE TEMP TABLE tmp_closed_customers AS
SELECT ano, eid FROM stage_customer WHERE balance_amount <= 0;
""")

# ============================================================
# STEP 5 — PAYMENTS (OPEN CUSTOMERS)
# ============================================================

run("""
INSERT INTO payment (
    ano, payment_date, amt, created_at, eid, cid, vid, updated_at
)
SELECT
    sp.ano,
    sp.payment_date,
    sp.amt,
    sp.created_at,
    oc.eid,
    sp.cid,
    sp.vid,
    NULL
FROM stage_payment sp
JOIN tmp_open_customers oc ON sp.ano = oc.ano
""", "Payments (open customers) migrated")


# ============================================================
# STEP 6 — CLOSED CUSTOMER PAYMENTS
# ============================================================

run("""
INSERT INTO closed_cust_payment (
    ano, payment_date, amt, created_at, eid, cid, vid
)
SELECT
    sp.ano,
    sp.payment_date,
    sp.amt,
    sp.created_at,
    cc.eid,
    sp.cid,
    sp.vid
FROM stage_payment sp
JOIN tmp_closed_customers cc ON sp.ano = cc.ano
""", "Payments (closed customers) migrated")


# ============================================================
# FINAL COUNTS
# ============================================================

print("\n📊 FINAL COUNTS")
print("employee:", count("employee"))
print("village:", count("village"))
print("customer (open):", count("customer"))
print("closed customers:", count("closed_cust_account"))
print("payment:", count("payment"))
print("closed payments:", count("closed_cust_payment"))

print("\n🎯 FINAL MIGRATION COMPLETED")