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
    # STEP 3 — STAGE_CUSTOMER (MODIFIED WHERE clause)
    # ============================================================

    print("\n🔍 Checking invalid customer rows (before insert)")
    print("Invalid ANO:", scalar("""
    SELECT COUNT(*) FROM bad_customer_data
    WHERE regexp_replace(ano, '[^0-9]', '', 'g') !~ '^[0-9]+$'
    """))

    print("Invalid start dates:", scalar("""
    SELECT COUNT(*) FROM bad_customer_data
    WHERE safe_to_date(regexp_replace(fdt, '[^0-9]', '', 'g')) IS NULL
    AND regexp_replace(fdt, '[^0-9]', '', 'g') <> ''
    """))

    print("Invalid end dates:", scalar("""
    SELECT COUNT(*) FROM bad_customer_data
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
        regexp_replace(bcd.ano, '[^0-9]', '', 'g')::int,
        bcd.name,
        sv.vid,

        CASE
            WHEN regexp_replace(bcd.fdt, '[^0-9]', '', 'g') ~ '^[0-9]{8}$'
                 AND substring(regexp_replace(bcd.fdt, '[^0-9]', '', 'g') from 3 for 2)::int BETWEEN 1 AND 12
                 AND substring(regexp_replace(bcd.fdt, '[^0-9]', '', 'g') from 1 for 2)::int BETWEEN 1 AND 31
            THEN safe_to_date(regexp_replace(bcd.fdt, '[^0-9]', '', 'g'))
            ELSE NULL
        END,
        CASE
            WHEN regexp_replace(bcd.tdt, '[^0-9]', '', 'g') ~ '^[0-9]{8}$'
                 AND substring(regexp_replace(bcd.tdt, '[^0-9]', '', 'g') from 3 for 2)::int BETWEEN 1 AND 12
                 AND substring(regexp_replace(bcd.tdt, '[^0-9]', '', 'g') from 1 for 2)::int BETWEEN 1 AND 31
            THEN safe_to_date(regexp_replace(bcd.tdt, '[^0-9]', '', 'g'))
            ELSE NULL
        END,

        NULLIF(regexp_replace(bcd.amt, '[^0-9.]', '', 'g'), '')::numeric,
        NULLIF(regexp_replace(bcd.pamt, '[^0-9.]', '', 'g'), '')::numeric,
        NULLIF(regexp_replace(bcd.bamt, '[^0-9.]', '', 'g'), '')::numeric,
        NULLIF(regexp_replace(bcd.da, '[^0-9.]', '', 'g'), '')::numeric,
        bcd.dw,
        bcd.ds::int,
        bcd.pano,

        se.eid,

        NULL,  -- aadhaar_number
        NULL,  -- notes
        NULL,  -- latitude
        NULL   -- longitude

    FROM bad_customer_data bcd
    JOIN stage_village sv
      ON NULLIF(regexp_replace(bcd.source_file, '[^0-9]', '', 'g'), '')::int = sv.source_file
    LEFT JOIN stage_employee se
      ON se.eid = sv.emp1
    WHERE regexp_replace(bcd.ano, '[^0-9]', '', 'g') ~ '^[0-9]+$'

    -- skip NULL / empty critical fields
    AND bcd.name IS NOT NULL
    AND bcd.name <> ''

    -- skip invalid start_date
    AND safe_to_date(regexp_replace(bcd.fdt, '[^0-9]', '', 'g')) IS NOT NULL

    -- skip invalid end_date (if present)
    AND (
        regexp_replace(bcd.tdt, '[^0-9]', '', 'g') = ''
        OR safe_to_date(regexp_replace(bcd.tdt, '[^0-9]', '', 'g')) IS NOT NULL
    )

    -- skip invalid amounts
    AND NULLIF(regexp_replace(bcd.amt, '[^0-9.]', '', 'g'), '') IS NOT NULL

    -- allow duplicates but pick deterministic latest record
    AND NOT EXISTS (
        SELECT 1 FROM stage_customer sc
        WHERE sc.ano = regexp_replace(bcd.ano, '[^0-9]', '', 'g')::int
        AND sc.vid = sv.vid
    )
    """, "stage_customer loaded")

    print("stage_customer count:", count("stage_customer"))
    print("bad_customer_data remaining:", count("bad_customer_data"))

    run("""
    DELETE FROM bad_customer_data bcd
    WHERE EXISTS (
        SELECT 1 FROM stage_customer sc
        JOIN stage_village sv
          ON sv.vid = sc.vid
        WHERE sc.ano = regexp_replace(bcd.ano, '[^0-9]', '', 'g')::int
        AND sv.source_file = NULLIF(regexp_replace(bcd.source_file, '[^0-9]', '', 'g'), '')::int
    )
    """, "Cleaned processed bad_customer_data")



    # ============================================================
    # STEP 4 — STAGE_PAYMENT (FINAL FIXED VERSION, MODIFIED WHERE clause)
    # ============================================================

    run("SET synchronous_commit TO OFF")
    run("ALTER TABLE stage_payment SET UNLOGGED")

    print("\n🔍 RAW PAYMENT STATS")
    print("Total bad_payment rows:", count("bad_payment_data"))
    print("Valid payment_date rows:", scalar("""
    SELECT COUNT(*) FROM raw_payment
    WHERE safe_to_date(regexp_replace(payment_date, '[^0-9]', '', 'g')) IS NOT NULL
    """))
    print("Invalid payment_date rows:", scalar("""
    SELECT COUNT(*) FROM raw_payment
    WHERE safe_to_date(regexp_replace(payment_date, '[^0-9]', '', 'g')) IS NULL
    """))

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
        FROM bad_payment_data
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
    run("""
    ALTER TABLE stage_payment
    ADD COLUMN IF NOT EXISTS source_file_id INT
    """)

    #-- 4.2 Insert into stage_payment using pre-cleaned data (no repeated functions)
    run("""
    INSERT INTO stage_payment (
        ano,
        payment_date,
        amt,
        rn,
        source_file_id
    )
    SELECT
        ano,
        parsed_date AS payment_date,
        clean_amt,
        rn,
        source_file_id
    FROM tmp_clean_payment tcp
    WHERE parsed_date IS NOT NULL
    AND clean_amt IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM stage_payment sp
        WHERE sp.ano = tcp.ano
        AND sp.payment_date = parsed_date
        AND sp.amt = clean_amt
        AND sp.source_file_id = tcp.source_file_id
    )
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
    AND sp.source_file_id = tcp.source_file_id
    """, "VID & EID populated (STRICT + CORRECT)")

    print("NULL vid:", scalar("SELECT COUNT(*) FROM stage_payment WHERE vid IS NULL"))
    print("NULL eid:", scalar("SELECT COUNT(*) FROM stage_payment WHERE eid IS NULL"))

    # 4.3 Populate CID using (ano + vid)
    run("""
    UPDATE stage_payment sp
    SET cid = sc.cid
    FROM stage_customer sc
    WHERE sp.cid IS NULL
    AND sp.ano = sc.ano
    AND sp.vid = sc.vid
    """, "CID populated")

    print("NULL cid after retry:", scalar("SELECT COUNT(*) FROM stage_payment WHERE cid IS NULL"))

    run("ALTER TABLE stage_payment SET LOGGED")

    print("bad_payment_data remaining:", count("bad_payment_data"))

    run("""
    DELETE FROM bad_payment_data bpd
    WHERE EXISTS (
        SELECT 1 FROM stage_payment sp
        WHERE sp.ano = bpd.ano::int
        AND sp.source_file_id = REPLACE(bpd.source_file, '.sqlite','')::int
    )
    """, "Cleaned processed bad_payment_data")



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


    print("\n🎉 STAGING PIPELINE COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    main()