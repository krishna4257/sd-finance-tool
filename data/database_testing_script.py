from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://user:password@localhost:5433/template1"
engine = create_engine(DB_URL, future=True)

def assert_zero(conn, sql, name):
    val = conn.execute(text(sql)).scalar()
    if val != 0:
        raise AssertionError(f"❌ {name}: {val}")
    print(f"✅ {name}: OK")

def assert_positive(conn, sql, name):
    val = conn.execute(text(sql)).scalar()
    if val <= 0:
        raise AssertionError(f"❌ {name}: {val}")
    print(f"✅ {name}: {val}")

with engine.begin() as conn:

    print("\n🔍 BASIC COUNTS")
    assert_positive(conn, "SELECT COUNT(*) FROM stage_payment", "stage_payment rows")
    assert_positive(conn, "SELECT COUNT(*) FROM stage_customer", "stage_customer rows")

    print("\n🔍 NULL CHECKS")
    assert_zero(conn, """
        SELECT COUNT(*) FROM stage_payment
        WHERE cid IS NULL OR vid IS NULL OR eid IS NULL
    """, "stage_payment NULL FK rows")

    print("\n🔍 FK ORPHAN CHECKS")

    assert_zero(conn, """
        SELECT COUNT(*) FROM stage_payment sp
        LEFT JOIN stage_customer sc ON sp.cid = sc.cid
        WHERE sc.cid IS NULL
    """, "customer FK orphans")

    assert_zero(conn, """
        SELECT COUNT(*) FROM stage_payment sp
        LEFT JOIN stage_employee se ON sp.eid = se.eid
        WHERE se.eid IS NULL
    """, "employee FK orphans")

    assert_zero(conn, """
        SELECT COUNT(*) FROM stage_payment sp
        LEFT JOIN stage_village sv ON sp.vid = sv.vid
        WHERE sv.vid IS NULL
    """, "village FK orphans")

    print("\n🔍 DUPLICATE PAYMENT CHECK")
    assert_zero(conn, """
        SELECT COUNT(*) FROM (
            SELECT ano, payment_date, amt, source_file
            FROM stage_payment
            GROUP BY ano, payment_date, amt, source_file
            HAVING COUNT(*) > 1
        ) x
    """, "duplicate payments")

    print("\n🔍 AMOUNT SANITY")
    assert_zero(conn, """
        SELECT COUNT(*) FROM stage_payment
        WHERE amt <= 0
    """, "non-positive payments")

    print("\n🎉 ALL DATA QUALITY CHECKS PASSED")