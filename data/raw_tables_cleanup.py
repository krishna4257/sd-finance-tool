import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"
REPORT_DIR = Path.home() / "Desktop" / "data_quality_reports"

engine = create_engine(PG_URL, future=True)

print("🚀 TASK-1: RAW DATA CLEANUP STARTED")

# ============================================================
# HELPERS
# ============================================================

def read_report(name):
    path = REPORT_DIR / name
    if not path.exists():
        print(f"⚠️ {name} not found – skipping")
        return pd.DataFrame()
    return pd.read_excel(path, dtype=str)

def delete_customers(keys):
    if keys.empty:
        return 0

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM raw_payment rp
            USING raw_customer rc
            WHERE rp.source_file = rc.source_file
              AND rp.ano = rc.ano
              AND (rc.source_file, rc.ano) IN (
                  SELECT source_file, ano FROM tmp_keys
              )
        """))

        result = conn.execute(text("""
            DELETE FROM raw_customer
            WHERE (source_file, ano) IN (
                SELECT source_file, ano FROM tmp_keys
            )
        """))
    return result.rowcount

# ============================================================
# 1️⃣ CUSTOMER NULLS (pano allowed)
# ============================================================

customer_nulls = read_report("customer_nulls.xlsx")

if not customer_nulls.empty:
    required_cols = [
        "source_file", "ano", "name", "fdt", "tdt",
        "amt", "pamt", "bamt", "da", "dw", "ds"
    ]

    bad = customer_nulls[
        customer_nulls[required_cols].isnull().any(axis=1)
    ][["source_file", "ano"]].drop_duplicates()

    with engine.begin() as conn:
        bad.to_sql("tmp_keys", conn, index=False, if_exists="replace")

    deleted = delete_customers(bad)
    print(f"🧹 customer_nulls cleaned: {deleted} customers")

# ------------------------------------------------------------
# 2️⃣ DUPLICATE CUSTOMERS (delete ALL duplicates + payments)
# ------------------------------------------------------------

with engine.begin() as conn:
    # Delete payments first (FK safety)
    result_pay = conn.execute(text("""
        DELETE FROM raw_payment rp
        USING (
            SELECT source_file, ano
            FROM raw_customer
            GROUP BY source_file, ano
            HAVING COUNT(*) > 1
        ) dup
        WHERE rp.source_file = dup.source_file
          AND rp.ano = dup.ano
    """))
    
    # Delete customers
    result_cust = conn.execute(text("""
        DELETE FROM raw_customer rc
        USING (
            SELECT source_file, ano
            FROM raw_customer
            GROUP BY source_file, ano
            HAVING COUNT(*) > 1
        ) dup
        WHERE rc.source_file = dup.source_file
          AND rc.ano = dup.ano
    """))

print(f"🧹 duplicate payments removed: {result_pay.rowcount}")
print(f"🧹 duplicate customers removed: {result_cust.rowcount}")

# ============================================================
# 3️⃣ CUSTOMER PARSE ISSUES
# ============================================================

cust_parse = read_report("customer_parse_issues.xlsx")

if not cust_parse.empty:
    keys = cust_parse[["source_file", "ano"]].drop_duplicates()

    with engine.begin() as conn:
        keys.to_sql("tmp_keys", conn, index=False, if_exists="replace")

    deleted = delete_customers(keys)
    print(f"🧹 customer_parse_issues cleaned: {deleted}")

# ============================================================
# 4️⃣ PAYMENT PARSE ISSUES
# ============================================================

pay_parse = read_report("payment_parse_issues.xlsx")

if not pay_parse.empty:
    with engine.begin() as conn:
        pay_parse[["source_file", "ano", "payment_date", "amount"]] \
            .drop_duplicates() \
            .to_sql("tmp_pay", conn, index=False, if_exists="replace")

        # Delete bad payments
        deleted = conn.execute(text("""
            DELETE FROM raw_payment rp
            USING tmp_pay tp
            WHERE rp.source_file = tp.source_file
              AND rp.ano = tp.ano
              AND rp.payment_date = tp.payment_date
              AND rp.amt = tp.amount
        """)).rowcount

        # Recalculate customer aggregates
        conn.execute(text("""
           UPDATE raw_customer rc
           SET
              pamt = sub.total_paid,
              bamt = rc.amt::numeric - sub.total_paid
           FROM (
              SELECT
                 source_file,
                 ano,
                 SUM(amt::numeric) AS total_paid
            FROM raw_payment
            WHERE amt ~ '^[0-9]+(\\.[0-9]+)?$'
            GROUP BY source_file, ano
            ) sub
            WHERE rc.source_file = sub.source_file
              AND rc.ano = sub.ano
       """))

    print(f"🧹 payment_parse_issues cleaned: {deleted} payments")

# ============================================================
# FINISH
# ============================================================

print("✅ TASK-1 COMPLETED SUCCESSFULLY")
print("🔎 Raw tables are now consistent and ready for staging")