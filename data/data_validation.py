from sqlalchemy import create_engine, text

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"
engine = create_engine(PG_URL, future=True)

def db_count(table):
    with engine.begin() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

def fetch_df(query):
    with engine.begin() as conn:
        return pd.read_sql(query, conn)
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path.home() / "Desktop" / "files_out"
OUT_DIR = Path.home() / "Desktop" / "data_quality_reports"
OUT_DIR.mkdir(exist_ok=True)

CUSTOMER_FILES = sorted(BASE_DIR.glob("raw_customer_*.xlsx"))
PAYMENT_FILES  = sorted(BASE_DIR.glob("raw_payment_*.xlsx"))

# ============================================================
# HELPERS
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df

def write_excel_safe(df, path, chunk_size=1000000):
    if df.empty:
        return

    try:
        engine = "xlsxwriter"
        __import__("xlsxwriter")
    except ImportError:
        print("⚠️ xlsxwriter not installed, falling back to openpyxl")
        engine = "openpyxl"

    with pd.ExcelWriter(path, engine=engine) as writer:
        for i, start in enumerate(range(0, len(df), chunk_size)):
            chunk = df.iloc[start:start+chunk_size]
            sheet_name = f"part_{i+1}"
            chunk.to_excel(writer, sheet_name=sheet_name, index=False)

def main():
    print("\n🔍 DATABASE VALIDATION (RAW → STAGE → FINAL)")

    db_summary = pd.DataFrame([
        ["raw_customer", db_count("raw_customer")],
        ["stage_customer", db_count("stage_customer")],
        ["customer", db_count("customer")],
        ["raw_payment", db_count("raw_payment")],
        ["stage_payment", db_count("stage_payment")],
        ["payment", db_count("payment")],
    ], columns=["table", "count"])

    write_excel_safe(db_summary, OUT_DIR / "db_table_counts.xlsx")

    print("🔎 Running cross-table validation...")

    # Orphan payments (no matching customer)
    orphan_payments = fetch_df("""
        SELECT sp.*
        FROM stage_payment sp
        LEFT JOIN stage_customer sc
        ON sp.ano = sc.ano AND sp.vid = sc.vid
        WHERE sc.ano IS NULL
        LIMIT 100000
    """)

    if not orphan_payments.empty:
        write_excel_safe(orphan_payments, OUT_DIR / "orphan_payments.xlsx")

    # Missing VID/EID/CID in stage_payment
    missing_fk = fetch_df("""
        SELECT * FROM stage_payment
        WHERE vid IS NULL OR eid IS NULL OR cid IS NULL
        LIMIT 100000
    """)

    if not missing_fk.empty:
        write_excel_safe(missing_fk, OUT_DIR / "missing_foreign_keys.xlsx")

    consistency = pd.DataFrame([
        ["Customer loss RAW→STAGE", db_count("raw_customer") - db_count("stage_customer")], # type: ignore
        ["Customer loss STAGE→FINAL", db_count("stage_customer") - db_count("customer")], # type: ignore
        ["Payment loss RAW→STAGE", db_count("raw_payment") - db_count("stage_payment")], # type: ignore
        ["Payment loss STAGE→FINAL", db_count("stage_payment") - db_count("payment")], # type: ignore
    ], columns=["metric", "count"])

    write_excel_safe(consistency, OUT_DIR / "pipeline_loss_analysis.xlsx")

    # ============================================================
    # LOAD DATA
    # ============================================================

    customer_df = pd.concat(
        [normalize_columns(pd.read_excel(f, dtype=str)) for f in CUSTOMER_FILES],
        ignore_index=True
    )

    payment_df = pd.concat(
        [normalize_columns(pd.read_excel(f, dtype=str)) for f in PAYMENT_FILES],
        ignore_index=True
    )

    # ============================================================
    # TYPE PARSING
    # ============================================================

    numeric_cols = ["ano", "amt", "pamt", "bamt", "da", "ds"]
    date_cols = ["fdt", "tdt"]

    parsed = customer_df.copy()

    for col in numeric_cols:
        if col in parsed.columns:
            parsed[f"{col}_num"] = pd.to_numeric(parsed[col], errors="coerce")

    for col in date_cols:
        if col in parsed.columns:
            parsed[f"{col}_date"] = pd.to_datetime(
                parsed[col],
                errors="coerce",
                dayfirst=True
            )

    amount_col = "amount" if "amount" in payment_df.columns else "amt"

    payment_df["amount_num"] = pd.to_numeric(
        payment_df.get(amount_col),
        errors="coerce"
    )

    payment_df["payment_date_dt"] = pd.to_datetime(
        payment_df.get("payment_date"),
        errors="coerce",
        dayfirst=True
    )

    # ============================================================
    # 1️⃣ CUSTOMER NULL CHECKS (pano allowed)
    # ============================================================

    mandatory_cols = ["ano", "name", "fdt", "amt", "dw", "ds"]

    customer_nulls = parsed[
        parsed[mandatory_cols].isnull().any(axis=1)
    ]

    write_excel_safe(customer_nulls, OUT_DIR / "customer_nulls.xlsx")

    # ============================================================
    # 2️⃣ CUSTOMER PARSE ISSUES
    # ============================================================

    parse_issues = []

    for col in numeric_cols:
        if col in parsed.columns:
            bad = parsed[
                parsed[col].notna() &
                parsed[f"{col}_num"].isna()
            ]
            if not bad.empty:
                bad = bad.assign(issue=f"Failed numeric parse: {col}")
                parse_issues.append(bad)

    for col in date_cols:
        if col in parsed.columns:
            bad = parsed[
                parsed[col].notna() &
                parsed[f"{col}_date"].isna()
            ]
            if not bad.empty:
                bad = bad.assign(issue=f"Invalid date format: {col}")
                parse_issues.append(bad)

    if parse_issues:
        write_excel_safe(pd.concat(parse_issues), OUT_DIR / "customer_parse_issues.xlsx")

    # ============================================================
    # 3️⃣ CUSTOMER OUTLIERS (THRESHOLD-BASED)
    # ============================================================

    da_outliers = parsed[parsed["da_num"] > 10000]
    if not da_outliers.empty:
        write_excel_safe(da_outliers, OUT_DIR / "customer_outlier_da_high.xlsx")

    amt_outliers = parsed[parsed["amt_num"] > 200000]
    if not amt_outliers.empty:
        write_excel_safe(amt_outliers, OUT_DIR / "customer_outlier_amt_high.xlsx")

    # ============================================================
    # 4️⃣ CUSTOMER RULE ISSUES
    # ============================================================

    negative_balance = parsed[parsed["bamt_num"] < -3000]
    if not negative_balance.empty:
        write_excel_safe(negative_balance, OUT_DIR / "customer_rule_negative_balance.xlsx")

    # ============================================================
    # 5️⃣ PAYMENT NULLS & PARSE ISSUES
    # ============================================================

    payment_nulls = payment_df[payment_df.isnull().any(axis=1)]
    write_excel_safe(payment_nulls, OUT_DIR / "payment_nulls.xlsx")

    payment_parse_issues = []

    amount_col = "amount" if "amount" in payment_df.columns else "amt"

    bad_amt = payment_df[
        payment_df[amount_col].notna() &
        payment_df["amount_num"].isna()
    ]
    if not bad_amt.empty:
        payment_parse_issues.append(
            bad_amt.assign(issue="Failed numeric parse: amount")
        )

    bad_date = payment_df[
        payment_df["payment_date"].notna() &
        payment_df["payment_date_dt"].isna()
    ]
    if not bad_date.empty:
        payment_parse_issues.append(
            bad_date.assign(issue="Invalid payment_date")
        )

    if payment_parse_issues:
        write_excel_safe(pd.concat(payment_parse_issues), OUT_DIR / "payment_parse_issues.xlsx")

    # ============================================================
    # 6️⃣ PAYMENT OUTLIERS (ONLY ONE RULE)
    # ============================================================

    payment_high_amt = payment_df[payment_df["amount_num"] > 50000]
    if not payment_high_amt.empty:
        write_excel_safe(payment_high_amt, OUT_DIR / "payment_outlier_high_amount.xlsx")

    # ============================================================
    # 7️⃣ DUPLICATES
    # ============================================================

    duplicates = []

    dup_cust = customer_df[
        customer_df.duplicated(["source_file", "ano"], keep=False)
    ]
    if not dup_cust.empty:
        duplicates.append(
            dup_cust.assign(issue="Duplicate customer key")
        )

    amount_col = "amount" if "amount" in payment_df.columns else "amt"

    dup_pay = payment_df[
        payment_df.duplicated(
            ["source_file", "ano", "payment_date", amount_col],
            keep=False
        )
    ]
    if not dup_pay.empty:
        duplicates.append(
            dup_pay.assign(issue="Duplicate payment")
        )

    if duplicates:
        write_excel_safe(pd.concat(duplicates), OUT_DIR / "duplicates.xlsx")

    # ============================================================
    # 8️⃣ SUMMARY
    # ============================================================

    summary = pd.DataFrame([
        ["Customers", len(customer_df)],
        ["Customer null rows", len(customer_nulls)],
        ["Customer parse issues", sum(len(x) for x in parse_issues)],
        ["DA high outliers", len(da_outliers)],
        ["AMT high outliers", len(amt_outliers)],
        ["Negative balance issues", len(negative_balance)],
        ["Payments", len(payment_df)],
        ["Payment null rows", len(payment_nulls)],
        ["Payment parse issues", sum(len(x) for x in payment_parse_issues)],
        ["High payment outliers", len(payment_high_amt)],
    ])

    summary.columns = ["metric", "count"]
    write_excel_safe(summary, OUT_DIR / "summary_report.xlsx")

    print("✅ Data quality analysis completed")
    print("📁 Reports saved to:", OUT_DIR)

if __name__ == "__main__":
    main()