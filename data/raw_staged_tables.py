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

def scalar(sql):
    with engine.begin() as conn:
        return conn.execute(text(sql)).scalar()

def count(table):
    with engine.begin() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

# ============================================================
# RESET STAGE TABLES
# ============================================================

print("\n🧹 RESETTING STAGE TABLES")

run("TRUNCATE stage_payment CASCADE")
run("TRUNCATE stage_customer CASCADE")
run("TRUNCATE stage_village CASCADE")
run("TRUNCATE stage_employee CASCADE")

print("✅ All stage tables truncated")

# ============================================================
# STEP 1 — STAGE_EMPLOYEE
# ============================================================

print("\n🚀 STEP 1: Loading stage_employee")

run("""
INSERT INTO stage_employee (
    eid,
    name,
    phone_number,
    city,
    joining_date,
    level,
    state
)
SELECT DISTINCT ON (emp_id)
    emp_id::int              AS eid,
    name,
    number                   AS phone_number,
    city,
    to_date(joining_year, 'DD-MM-YYYY') AS joining_date,
    LOWER(level)             AS level,
    state
FROM raw_employee
WHERE emp_id IS NOT NULL
""", "stage_employee loaded")

print("stage_employee count:", count("stage_employee"))

# ============================================================
# STEP 2 — STAGE_VILLAGE (UNCHANGED)
# ============================================================

print("\n🚀 STEP 1: Loading stage_employee")

run("""
INSERT INTO stage_employee (
    eid,
    name,
    phone_number,
    city,
    joining_date,
    level,
    state
)
SELECT DISTINCT ON (emp_id)
    emp_id::int              AS eid,
    name,
    number                   AS phone_number,
    city,
    to_date(joining_year, 'DD-MM-YYYY') AS joining_date,
    LOWER(level)             AS level,
    state
FROM raw_employee
WHERE emp_id IS NOT NULL
""", "stage_employee loaded")

print("stage_employee count:", count("stage_employee"))

# ============================================================
# STEP 3 — STAGE_CUSTOMER (UNCHANGED)
# ============================================================

print("\n🚀 STEP 3: Loading stage_customer")

run("""
INSERT INTO stage_customer (
    ano,
    name,
    vid,
    start_date,
    end_date,
    total_amount,
    paid_amount,
    balance_amount,
    installment_amount,
    type,
    period,
    pano,
    source_file,
    eid
)
SELECT
    rc.ano::int,
    rc.name,
    sv.vid,

    -- Dates (DD/MM/YYYY safe)
    to_date(rc.fdt, 'DD/MM/YYYY') AS start_date,
    to_date(rc.tdt, 'DD/MM/YYYY') AS end_date,

    rc.amt::numeric,
    rc.pamt::numeric,
    rc.bamt::numeric,
    rc.da::numeric,
    rc.dw,
    rc.ds::int,
    rc.pano,

    -- 🔥 NORMALIZED source_file (INT)
    REPLACE(rc.source_file, '.sqlite', '')::int AS source_file,

    se.eid
FROM raw_customer rc
JOIN stage_village sv
  ON REPLACE(rc.source_file, '.sqlite', '')::int = sv.source_file
LEFT JOIN stage_employee se
  ON se.eid = sv.emp1
""", "stage_customer loaded")

print("stage_customer count:", count("stage_customer"))

# ============================================================
# STEP 4 — STAGE_PAYMENT (FINAL FIXED VERSION)
# ============================================================

print("\n🚀 STEP 4: Loading stage_payment (SAFE MODE)")

# ano  
#-------
# 3186+
# 413.
# (2 rows)

run("""
    BEGIN
    UPDATE raw_payment
    SET ano = regexp_replace(ano, '[^0-9]', '', 'g')
    WHERE ano IN ('3186+', '413.');
    COMMIT;
""", "Cleaned special characters from ano in raw_payment")

# 4.1 Load ALL raw payments
run("""
INSERT INTO stage_payment (
    ano, payment_date, amt, source_file, cid, vid, eid, source_file_id
)
SELECT
    rp.ano::int,
    to_date(rp.payment_date, 'DD/MM/YYYY'),
    rp.amt::numeric,
    rp.source_file,
    NULL,
    NULL,
    NULL,
    rp.source_file_id
FROM raw_payment rp
""", "All raw payments loaded")

print("stage_payment count:", count("stage_payment"))

# 4.2 Populate VID + EID from raw_village
run("""
UPDATE stage_payment sp
SET
    vid = rv.vid,
    eid = rv.emp1::int
FROM raw_village rv
WHERE sp.source_file_id = rv.evid::int
""", "VID & EID populated")

# 4.3 Populate CID using (ano + vid)
run("""
UPDATE stage_payment sp
SET cid = sc.cid
FROM stage_customer sc
WHERE
    sp.cid IS NULL
    AND sp.ano = sc.ano
    AND sp.vid = sc.vid
""", "CID populated")

# ============================================================
# STEP 5 — MOVE UNMATCHED PAYMENTS
# ============================================================

print("\n🧺 Moving unmatched payments to old_stage_payment")

run("""
CREATE TABLE IF NOT EXISTS old_stage_payment
AS SELECT * FROM stage_payment WHERE false
""")

run("""
INSERT INTO old_stage_payment
SELECT * FROM stage_payment
WHERE cid IS NULL OR vid IS NULL OR eid IS NULL
""", "Unmatched rows archived")

run("""
DELETE FROM stage_payment
WHERE cid IS NULL OR vid IS NULL OR eid IS NULL
""", "Unmatched rows removed from stage_payment")

# ============================================================
# DATA QUALITY CHECKS
# ============================================================

print("\n🧪 DATA QUALITY CHECKS")

checks = {
    "stage_payment rows": "SELECT COUNT(*) FROM stage_payment",
    "old_stage_payment rows": "SELECT COUNT(*) FROM old_stage_payment",
    "NULL cid": "SELECT COUNT(*) FROM stage_payment WHERE cid IS NULL",
    "NULL vid": "SELECT COUNT(*) FROM stage_payment WHERE vid IS NULL",
    "NULL eid": "SELECT COUNT(*) FROM stage_payment WHERE eid IS NULL",
    "Orphan customer refs": """
        SELECT COUNT(*) FROM stage_payment sp
        LEFT JOIN stage_customer sc ON sp.cid = sc.cid
        WHERE sc.cid IS NULL
    """,
    "Orphan village refs": """
        SELECT COUNT(*) FROM stage_payment sp
        LEFT JOIN stage_village sv ON sp.vid = sv.vid
        WHERE sv.vid IS NULL
    """,
    "Orphan employee refs": """
        SELECT COUNT(*) FROM stage_payment sp
        LEFT JOIN stage_employee se ON sp.eid = se.eid
        WHERE se.eid IS NULL
    """
}

for name, sql in checks.items():
    print(f"{name}: {scalar(sql)}")

print("\n🎉 STAGING PIPELINE COMPLETED SUCCESSFULLY")