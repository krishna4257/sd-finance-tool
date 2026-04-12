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
    -- ensure deterministic pick
    -- (keeps first row per emp_id)
    emp_id::int              AS eid,
    name,
    number                   AS phone_number,
    city,
    CASE 
        WHEN length(regexp_replace(joining_year, '[^0-9]', '', 'g')) = 4 
        THEN to_date(regexp_replace(joining_year, '[^0-9]', '', 'g') || '-01-01', 'YYYY-MM-DD')
        WHEN length(regexp_replace(joining_year, '[^0-9]', '', 'g')) = 8 
        THEN to_date(regexp_replace(joining_year, '[^0-9]', '', 'g'), 'DDMMYYYY')
        ELSE NULL
    END AS joining_date,
    LOWER(level)             AS level,
    state
FROM raw_employee
WHERE emp_id IS NOT NULL
ORDER BY emp_id
""", "stage_employee loaded")

print("stage_employee count:", count("stage_employee"))
print("raw_employee remaining:", count("raw_employee"))

# ============================================================
# STEP 2 — STAGE_VILLAGE
# ============================================================

print("\n🚀 STEP 2: Loading stage_village")

run("""
INSERT INTO stage_village (
    vid,
    village_code,
    village_name,
    district,
    pincode,
    state,
    emp1,
    emp2,
    source_file
)
SELECT
    NULLIF(regexp_replace(vid::text, '[^0-9]', '', 'g'), '')::int,
    new_village_code AS village_code,
    new_village_name AS village_name,
    district,
    NULLIF(regexp_replace(pincode, '[^0-9]', '', 'g'), '')::int,
    state_name AS state,
    NULLIF(regexp_replace(emp1, '[^0-9]', '', 'g'), '')::int,
    NULLIF(regexp_replace(emp2, '[^0-9]', '', 'g'), '')::int,
    NULLIF(regexp_replace(evid, '[^0-9]', '', 'g'), '')::int AS source_file
FROM raw_village
WHERE NULLIF(regexp_replace(vid::text, '[^0-9]', '', 'g'), '') ~ '^[0-9]+$'
""", "stage_village loaded")

print("stage_village count:", count("stage_village"))
print("raw_village remaining:", count("raw_village"))

# ============================================================
# Add safe_to_date function before STEP 3
# ============================================================

run("""
CREATE OR REPLACE FUNCTION safe_to_date(input TEXT)
RETURNS DATE AS $$
BEGIN
    RETURN to_date(input, 'DDMMYYYY');
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""", "safe_to_date function created")

# ============================================================
# Add bad_customer_data table and insert bad customer rows
# ============================================================

run("""
CREATE TABLE IF NOT EXISTS bad_customer_data AS
SELECT * FROM raw_customer WHERE false
""")

run("""
INSERT INTO bad_customer_data
SELECT *
FROM raw_customer rc
WHERE
    regexp_replace(rc.ano, '[^0-9]', '', 'g') !~ '^[0-9]+$'
    OR rc.name IS NULL OR rc.name = ''
    OR safe_to_date(regexp_replace(rc.fdt, '[^0-9]', '', 'g')) IS NULL
    OR (
        regexp_replace(rc.tdt, '[^0-9]', '', 'g') <> ''
        AND safe_to_date(regexp_replace(rc.tdt, '[^0-9]', '', 'g')) IS NULL
    )
    OR NULLIF(regexp_replace(rc.amt, '[^0-9.]', '', 'g'), '') IS NULL
""", "Bad customer rows captured")

# ============================================================
# STEP 3 — STAGE_CUSTOMER (MODIFIED WHERE clause)
# ============================================================

print("\n🔍 Checking invalid customer rows (before insert)")
print("Invalid ANO:", scalar("""
SELECT COUNT(*) FROM raw_customer
WHERE regexp_replace(ano, '[^0-9]', '', 'g') !~ '^[0-9]+$'
"""))

print("Invalid start dates:", scalar("""
SELECT COUNT(*) FROM raw_customer
WHERE safe_to_date(regexp_replace(fdt, '[^0-9]', '', 'g')) IS NULL
AND regexp_replace(fdt, '[^0-9]', '', 'g') <> ''
"""))

print("Invalid end dates:", scalar("""
SELECT COUNT(*) FROM raw_customer
WHERE safe_to_date(regexp_replace(tdt, '[^0-9]', '', 'g')) IS NULL
AND regexp_replace(tdt, '[^0-9]', '', 'g') <> ''
"""))

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
    eid,
    aadhaar_number,
    notes,
    latitude,
    longitude
)
SELECT
    regexp_replace(rc.ano, '[^0-9]', '', 'g')::int,
    rc.name,
    sv.vid,

    CASE
        WHEN regexp_replace(rc.fdt, '[^0-9]', '', 'g') ~ '^[0-9]{8}$'
             AND substring(regexp_replace(rc.fdt, '[^0-9]', '', 'g') from 3 for 2)::int BETWEEN 1 AND 12
             AND substring(regexp_replace(rc.fdt, '[^0-9]', '', 'g') from 1 for 2)::int BETWEEN 1 AND 31
        THEN safe_to_date(regexp_replace(rc.fdt, '[^0-9]', '', 'g'))
        ELSE NULL
    END,
    CASE
        WHEN regexp_replace(rc.tdt, '[^0-9]', '', 'g') ~ '^[0-9]{8}$'
             AND substring(regexp_replace(rc.tdt, '[^0-9]', '', 'g') from 3 for 2)::int BETWEEN 1 AND 12
             AND substring(regexp_replace(rc.tdt, '[^0-9]', '', 'g') from 1 for 2)::int BETWEEN 1 AND 31
        THEN safe_to_date(regexp_replace(rc.tdt, '[^0-9]', '', 'g'))
        ELSE NULL
    END,

    NULLIF(regexp_replace(rc.amt, '[^0-9.]', '', 'g'), '')::numeric,
    NULLIF(regexp_replace(rc.pamt, '[^0-9.]', '', 'g'), '')::numeric,
    NULLIF(regexp_replace(rc.bamt, '[^0-9.]', '', 'g'), '')::numeric,
    NULLIF(regexp_replace(rc.da, '[^0-9.]', '', 'g'), '')::numeric,
    rc.dw,
    rc.ds::int,
    rc.pano,

    se.eid,

    NULL,  -- aadhaar_number
    NULL,  -- notes
    NULL,  -- latitude
    NULL   -- longitude

FROM raw_customer rc
JOIN stage_village sv
  ON NULLIF(regexp_replace(rc.source_file, '[^0-9]', '', 'g'), '')::int = sv.source_file
LEFT JOIN stage_employee se
  ON se.eid = sv.emp1
WHERE regexp_replace(rc.ano, '[^0-9]', '', 'g') ~ '^[0-9]+$'

-- skip NULL / empty critical fields
AND rc.name IS NOT NULL
AND rc.name <> ''

-- skip invalid start_date
AND safe_to_date(regexp_replace(rc.fdt, '[^0-9]', '', 'g')) IS NOT NULL

-- skip invalid end_date (if present)
AND (
    regexp_replace(rc.tdt, '[^0-9]', '', 'g') = ''
    OR safe_to_date(regexp_replace(rc.tdt, '[^0-9]', '', 'g')) IS NOT NULL
)

-- skip invalid amounts
AND NULLIF(regexp_replace(rc.amt, '[^0-9.]', '', 'g'), '') IS NOT NULL

-- skip duplicate customers (same ano + source_file)
AND (regexp_replace(rc.ano, '[^0-9]', '', 'g'), rc.source_file) IN (
    SELECT ano_clean, source_file
    FROM (
        SELECT 
            regexp_replace(ano, '[^0-9]', '', 'g') AS ano_clean,
            source_file,
            COUNT(*) AS cnt
        FROM raw_customer
        GROUP BY ano_clean, source_file
        HAVING COUNT(*) = 1
    ) t
)
""", "stage_customer loaded")

print("stage_customer count:", count("stage_customer"))
print("raw_customer remaining:", count("raw_customer"))


# ============================================================
# STEP 4 — STAGE_PAYMENT (FINAL FIXED VERSION, MODIFIED WHERE clause)
# ============================================================

run("CREATE INDEX IF NOT EXISTS idx_raw_payment_ano ON raw_payment(ano)")
run("CREATE INDEX IF NOT EXISTS idx_raw_payment_clean_date ON raw_payment((regexp_replace(payment_date, '[^0-9]', '', 'g'))) ")
run("CREATE INDEX IF NOT EXISTS idx_stage_customer_ano_vid ON stage_customer(ano, vid)")
run("CREATE INDEX IF NOT EXISTS idx_stage_village_source_file ON stage_village(source_file)")

print("\n🔍 RAW PAYMENT STATS")
print("Total raw_payment rows:", count("raw_payment"))
print("Valid payment_date rows:", scalar("""
SELECT COUNT(*) FROM raw_payment
WHERE safe_to_date(regexp_replace(payment_date, '[^0-9]', '', 'g')) IS NOT NULL
"""))
print("Invalid payment_date rows:", scalar("""
SELECT COUNT(*) FROM raw_payment
WHERE safe_to_date(regexp_replace(payment_date, '[^0-9]', '', 'g')) IS NULL
"""))

run("""
CREATE TABLE IF NOT EXISTS bad_payment_data AS
SELECT * FROM raw_payment WHERE false
""")

run("""
INSERT INTO bad_payment_data (
    ano,
    payment_date,
    amt,
    source_file
)
SELECT
    ano,
    payment_date,
    amt,
    source_file
FROM raw_payment
WHERE safe_to_date(regexp_replace(payment_date, '[^0-9]', '', 'g')) IS NULL
""", "Bad payment rows captured")

print("\n🚀 STEP 4: Loading stage_payment (SAFE MODE)")

# ano  
#-------
# 3186+
# 413.
# (2 rows)

run("""
INSERT INTO stage_payment (
    ano,
    payment_date,
    amt
)
SELECT DISTINCT
    rp.ano::int,
    safe_to_date(clean_date),
    NULLIF(regexp_replace(rp.amt::text, '[^0-9.]', '', 'g'), '')::numeric
FROM (
    SELECT 
        ano,
        regexp_replace(payment_date, '[^0-9]', '', 'g') AS clean_date,
        amt,
        source_file
    FROM raw_payment
    WHERE ano ~ '^[0-9]+$'
) rp
WHERE clean_date ~ '^[0-9]{8}$'
AND safe_to_date(clean_date) IS NOT NULL
AND NULLIF(regexp_replace(rp.amt::text, '[^0-9.]', '', 'g'), '') IS NOT NULL
""", "All raw payments loaded")

print("Loaded into stage_payment:", count("stage_payment"))


# 4.2 Populate VID + EID from raw_village
run("""
UPDATE stage_payment sp
SET
    vid = sv.vid,
    eid = sv.emp1
FROM (
    SELECT 
        rp.ano::int AS ano,
        safe_to_date(regexp_replace(rp.payment_date, '[^0-9]', '', 'g')) AS payment_date,
        REPLACE(rp.source_file, '.sqlite', '')::int AS source_file
    FROM raw_payment rp
    WHERE rp.ano ~ '^[0-9]+$'
) rp_clean
JOIN stage_village sv
  ON rp_clean.source_file = sv.source_file
WHERE
    sp.ano = rp_clean.ano
    AND sp.payment_date = rp_clean.payment_date
""", "VID & EID populated")

# 4.3 Populate CID using (ano + vid)
run("""
UPDATE stage_payment sp
SET cid = sc.cid
FROM stage_customer sc
WHERE sp.cid IS NULL
AND sp.ano = sc.ano
""", "CID populated")

print("raw_payment remaining:", count("raw_payment"))

# ============================================================
# STEP 5 — MOVE UNMATCHED PAYMENTS
# ============================================================

print("\n🧺 Moving unmatched payments to old_stage_payment")

run("""
CREATE TABLE IF NOT EXISTS old_stage_payment
AS SELECT * FROM stage_payment WHERE false
""")

run("""
INSERT INTO old_stage_payment (
    ano,
    payment_date,
    amt,
    vid,
    eid,
    cid
)
SELECT
    ano,
    payment_date,
    amt,
    vid,
    eid,
    cid
FROM stage_payment
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
    "NULL eid": "SELECT COUNT(*) FROM stage_payment WHERE eid IS NULL"
}

for name, sql in checks.items():
    print(f"{name}: {scalar(sql)}")

# ============================================================
# FINAL TABLE COUNTS (RAW vs STAGE)
# ============================================================

print("\n📊 FINAL ROW COUNTS")

tables = [
    ("raw_employee", "stage_employee"),
    ("raw_village", "stage_village"),
    ("raw_customer", "stage_customer"),
    ("raw_payment", "stage_payment")
]

for raw_tbl, stage_tbl in tables:
    raw_cnt = count(raw_tbl)
    stage_cnt = count(stage_tbl)
    print(f"{raw_tbl}: {raw_cnt} | {stage_tbl}: {stage_cnt}")

print("\n🎉 STAGING PIPELINE COMPLETED SUCCESSFULLY")