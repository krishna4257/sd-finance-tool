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

def main():
    # ============================================================
    # RESET STAGE TABLES
    # ============================================================

    print("\n🧹 RESETTING STAGE TABLES")

    run("TRUNCATE stage_payment CASCADE")
    run("TRUNCATE stage_customer CASCADE")
    run("TRUNCATE stage_village CASCADE")
    run("TRUNCATE stage_employee CASCADE")
    run("TRUNCATE old_stage_payment CASCADE")

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

    -- allow duplicates but pick deterministic latest record
    """, "stage_customer loaded")

    print("stage_customer count:", count("stage_customer"))
    print("raw_customer remaining:", count("raw_customer"))


    # ============================================================
    # STEP 4 — STAGE_PAYMENT (FINAL FIXED VERSION, MODIFIED WHERE clause)
    # ============================================================

    run("SET synchronous_commit TO OFF")
    run("ALTER TABLE stage_payment SET UNLOGGED")

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

    #-- 4.1 Pre-materialize cleaned payments into a temp table
    run("""
    DROP TABLE IF EXISTS tmp_clean_payment;
    CREATE TEMP TABLE tmp_clean_payment AS
    SELECT
        s.ano,
        s.clean_date,
        safe_to_date(s.clean_date) AS parsed_date,
        s.clean_amt,
        s.source_file_id,
        ROW_NUMBER() OVER (PARTITION BY s.ano, s.source_file_id ORDER BY s.clean_date, s.clean_amt) AS rn
    FROM (
        SELECT
            ano::int AS ano,
            regexp_replace(payment_date, '[^0-9]', '', 'g') AS clean_date,
            NULLIF(regexp_replace(amt::text, '[^0-9.]', '', 'g'), '')::numeric AS clean_amt,
            REPLACE(source_file, '.sqlite', '')::int AS source_file_id
        FROM raw_payment
        WHERE ano ~ '^[0-9]+$'
    ) s;
    """)

    #-- Optional: index temp table for faster downstream joins
    run("CREATE INDEX IF NOT EXISTS idx_tmp_clean_payment_ano_date ON tmp_clean_payment(ano, parsed_date)")

    #-- Ensure rn column exists in stage_payment
    run("""
    ALTER TABLE stage_payment
    ADD COLUMN IF NOT EXISTS rn INT
    """)

    #-- 4.2 Insert into stage_payment using pre-cleaned data (no repeated functions)
    run("""
    INSERT INTO stage_payment (
        ano,
        payment_date,
        amt,
        rn
    )
    SELECT
        ano,
        parsed_date AS payment_date,
        clean_amt,
        rn
    FROM tmp_clean_payment
    WHERE parsed_date IS NOT NULL
    AND clean_amt IS NOT NULL
    """, "All raw payments loaded (pre-materialized)")

    run("CREATE INDEX IF NOT EXISTS idx_raw_payment_ano ON raw_payment(ano)")
    run("CREATE INDEX IF NOT EXISTS idx_raw_payment_clean_date ON raw_payment((regexp_replace(payment_date, '[^0-9]', '', 'g'))) ")
    run("CREATE INDEX IF NOT EXISTS idx_stage_customer_ano_vid ON stage_customer(ano, vid)")
    run("CREATE INDEX IF NOT EXISTS idx_stage_village_source_file ON stage_village(source_file)")

    # 4.2 Populate VID + EID from raw_village
    run("""
    UPDATE stage_payment sp
    SET
        vid = sv.vid,
        eid = sv.emp1
    FROM tmp_clean_payment tcp
    JOIN stage_village sv
      ON tcp.source_file_id = sv.source_file
    WHERE sp.ano = tcp.ano
    AND sp.rn = tcp.rn
    """, "VID & EID populated (STRICT + CORRECT)")

    # 4.3 Populate CID using (ano + vid)
    run("""
    UPDATE stage_payment sp
    SET cid = sc.cid
    FROM stage_customer sc
    WHERE sp.cid IS NULL
    AND sp.ano = sc.ano
    AND sp.vid = sc.vid
    """, "CID populated")

    run("ALTER TABLE stage_payment SET LOGGED")

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
    # ADVANCED DATA QUALITY ANALYSIS (GOOD vs BAD PAYMENTS)
    # ============================================================

    print("\n📊 PAYMENT QUALITY ANALYSIS")

    total_raw = scalar("SELECT COUNT(*) FROM raw_payment")
    total_stage = scalar("SELECT COUNT(*) FROM stage_payment")
    total_old = scalar("SELECT COUNT(*) FROM old_stage_payment")

    good_pct = (total_stage * 100.0 / total_raw) if total_raw else 0 # type: ignore
    bad_pct = (total_old * 100.0 / total_raw) if total_raw else 0 # type: ignore

    print(f"Total Raw Payments: {total_raw}")
    print(f"Good Payments (stage): {total_stage} ({good_pct:.2f}%)")
    print(f"Bad Payments (old_stage): {total_old} ({bad_pct:.2f}%)")

    # ============================================================
    # ROOT CAUSE BREAKDOWN (WHY PAYMENTS FAILED)
    # ============================================================

    print("\n🔍 FAILURE BREAKDOWN")

    reasons = {
        "Missing CID": "SELECT COUNT(*) FROM old_stage_payment WHERE cid IS NULL",
        "Missing VID": "SELECT COUNT(*) FROM old_stage_payment WHERE vid IS NULL",
        "Missing EID": "SELECT COUNT(*) FROM old_stage_payment WHERE eid IS NULL",
        "CID exists but not in customer": """
            SELECT COUNT(*) 
            FROM old_stage_payment osp
            LEFT JOIN stage_customer sc ON osp.cid = sc.cid
            WHERE osp.cid IS NOT NULL AND sc.cid IS NULL
        """,
        "Recoverable (ano + vid match)": """
            SELECT COUNT(*) 
            FROM old_stage_payment osp
            JOIN stage_customer sc 
            ON osp.ano = sc.ano AND osp.vid = sc.vid
        """
    }

    for name, sql in reasons.items():
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

if __name__ == "__main__":
    main()