from sqlalchemy import create_engine, text

# ============================================================
# CONFIG (same as your pipeline)
# ============================================================

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"
engine = create_engine(PG_URL, future=True)


def scalar(sql):
    with engine.begin() as conn:
        return conn.execute(text(sql)).scalar()


def fetchall(sql):
    with engine.begin() as conn:
        return conn.execute(text(sql)).fetchall()


def main():
    print("\n🔍 RUNNING FINAL VALIDATION (POST FIX)\n")

    # ============================================================
    # 1. Village mapping check
    # ============================================================
    res = fetchall("""
    SELECT source_file, COUNT(DISTINCT vid) AS village_count
    FROM stage_village
    GROUP BY source_file
    HAVING COUNT(DISTINCT vid) > 1
    """)
    print("1️⃣ Village mapping issues:", len(res))

    # ============================================================
    # 2. Payment → village consistency
    # ============================================================
    mismatched_vid = scalar("""
    SELECT COUNT(*)
    FROM stage_payment sp
    JOIN stage_village sv
      ON sp.source_file_id = sv.source_file
    WHERE sp.vid != sv.vid
    """)
    print("2️⃣ Mismatched VID:", mismatched_vid)

    # ============================================================
    # 3. CID correctness
    # ============================================================
    cid_mismatch = scalar("""
    SELECT COUNT(*)
    FROM stage_payment sp
    JOIN stage_customer sc
      ON sp.ano = sc.ano
     AND sp.vid = sc.vid
    WHERE sp.cid != sc.cid
    """)
    print("3️⃣ CID mismatch:", cid_mismatch)

    # ============================================================
    # 4. Lost payments (CRITICAL)
    # ============================================================
    recoverable = scalar("""
    SELECT COUNT(*)
    FROM old_stage_payment osp
    JOIN stage_customer sc
      ON osp.ano = sc.ano
     AND osp.vid = sc.vid
    """)
    print("4️⃣ Recoverable payments (BUG):", recoverable)

    # ============================================================
    # 5. NULL checks
    # ============================================================
    nulls = fetchall("""
    SELECT
      COUNT(*) FILTER (WHERE cid IS NULL),
      COUNT(*) FILTER (WHERE vid IS NULL),
      COUNT(*) FILTER (WHERE eid IS NULL)
    FROM stage_payment
    """)[0]

    print("5️⃣ NULL Checks:")
    print(f"   CID: {nulls[0]}, VID: {nulls[1]}, EID: {nulls[2]}")

    # ============================================================
    # 6. Duplicate customer keys
    # ============================================================
    duplicates = fetchall("""
    SELECT ano, vid, COUNT(*)
    FROM stage_customer
    GROUP BY ano, vid
    HAVING COUNT(*) > 1
    """)
    print("6️⃣ Duplicate (ano, vid):", len(duplicates))

    # ============================================================
    # 7. Source file integrity
    # ============================================================
    invalid_source = scalar("""
    SELECT COUNT(*)
    FROM stage_payment sp
    LEFT JOIN stage_village sv
      ON sp.source_file_id = sv.source_file
    WHERE sv.vid IS NULL
    """)
    print("7️⃣ Invalid source mapping:", invalid_source)

    # ============================================================
    # 8. Final loss metrics
    # ============================================================
    metrics = fetchall("""
    SELECT
      (SELECT COUNT(*) FROM raw_payment),
      (SELECT COUNT(*) FROM stage_payment),
      (SELECT COUNT(*) FROM old_stage_payment)
    """)[0]

    raw, stage, rejected = metrics

    print("\n📊 FINAL LOSS METRICS")
    print(f"Raw: {raw}")
    print(f"Stage: {stage}")
    print(f"Rejected: {rejected}")

    if raw:
        print(f"Good %: {(stage * 100.0 / raw):.2f}%")
        print(f"Bad %: {(rejected * 100.0 / raw):.2f}%")

    print("\n✅ VALIDATION COMPLETED\n")


if __name__ == "__main__":
    main()