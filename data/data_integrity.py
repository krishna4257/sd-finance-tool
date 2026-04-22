import psycopg2
import pandas as pd

# ============================================================
# CONFIG
# ============================================================


SOURCE_DB = {
    "host": "localhost",
    "port": 5433,
    "dbname": "template1",
    "user": "jayakrishnareddykarri",
    "password": "Jaya@3579"
}

TARGET_DB = {
    "host": "192.168.1.65",
    "port": 5432,
    "dbname": "sd_finance",
    "user": "sd_user",
    "password": "Jaya@3579"
}

src_conn = psycopg2.connect(**SOURCE_DB)
tgt_conn = psycopg2.connect(**TARGET_DB)

src_cur = src_conn.cursor()
tgt_cur = tgt_conn.cursor()
# ============================================================
# STEP 1: RAW AGGREGATION (MAC)
# ============================================================

def fetch_df(cursor, query):
    cursor.execute(query)
    cols = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=cols)


# ============================================================
# STEP 1: RAW AGGREGATION (MAC)
# ============================================================

raw_query = """
WITH mapped AS (
    SELECT
        rv.vid,
        rc.ano,
        CAST(rc.amt AS numeric) AS loan_amount,
        CAST(rc.pamt AS numeric) AS paid_amount,
        CAST(rc.bamt AS numeric) AS balance_amount
    FROM raw_customer rc
    JOIN raw_village rv
      ON CAST(REPLACE(rc.source_file, '.sqlite','') AS INT) = CAST(rv.evid AS INT)
)
SELECT
    vid,
    COUNT(*) AS total_customers,
    SUM(loan_amount) AS total_loan,
    SUM(paid_amount) AS total_paid,
    SUM(balance_amount) AS total_balance
FROM mapped
GROUP BY vid
"""

raw_df = fetch_df(src_cur, raw_query)


# ============================================================
# STEP 2: FINAL AGGREGATION (SERVER)
# ============================================================

final_query = """
WITH combined AS (
    SELECT
        vid,
        total_amount,
        paid_amount,
        balance_amount
    FROM customer

    UNION ALL

    SELECT
        vid,
        total_amount,
        paid_amount,
        balance_amount
    FROM closed_cust_account
)
SELECT
    vid,
    COUNT(*) AS total_customers,
    SUM(total_amount) AS total_loan,
    SUM(paid_amount) AS total_paid,
    SUM(balance_amount) AS total_balance
FROM combined
GROUP BY vid
"""

final_df = fetch_df(tgt_cur, final_query)


# ============================================================
# STEP 3: MERGE + COMPARE
# ============================================================

merged = raw_df.merge(
    final_df,
    on="vid",
    how="outer",
    suffixes=("_raw", "_final")
).fillna(0)


# ============================================================
# STEP 4: CALCULATE DIFFERENCES
# ============================================================

merged["cust_diff"] = merged["total_customers_raw"] - merged["total_customers_final"]
merged["loan_diff"] = merged["total_loan_raw"] - merged["total_loan_final"]
merged["paid_diff"] = merged["total_paid_raw"] - merged["total_paid_final"]
merged["balance_diff"] = merged["total_balance_raw"] - merged["total_balance_final"]


# ============================================================
# STEP 5: PRINT RESULTS
# ============================================================

print("\n📊 DATA INTEGRITY CHECK (RAW vs FINAL)\n")

# Overall totals
total_raw = merged[[
    "total_customers_raw",
    "total_loan_raw",
    "total_paid_raw",
    "total_balance_raw"
]].sum()

total_final = merged[[
    "total_customers_final",
    "total_loan_final",
    "total_paid_final",
    "total_balance_final"
]].sum()

print("🔹 TOTALS")
print("RAW:")
print(total_raw)
print("\nFINAL:")
print(total_final)

print("\n🔹 DIFFERENCE (RAW - FINAL)")
print(total_raw - total_final)


# ============================================================
# STEP 6: SHOW PROBLEMATIC VIDS
# ============================================================

issues = merged[
    (merged["cust_diff"] != 0) |
    (merged["loan_diff"] != 0) |
    (merged["paid_diff"] != 0) |
    (merged["balance_diff"] != 0)
]

print("\n🚨 VILLAGE LEVEL MISMATCHES:", len(issues))

if not issues.empty:
    print("\nTOP ISSUES:\n")
    print(issues.sort_values("loan_diff", key=abs, ascending=False).head(20))


# ============================================================
# DONE
# ============================================================

print("\n✅ DATA INTEGRITY CHECK COMPLETED\n")