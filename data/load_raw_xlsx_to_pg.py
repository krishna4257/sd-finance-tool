import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# ============================================================
# CONFIG
# ============================================================

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"

BASE_DIR = Path.home() / "Desktop" / "files_out"
CHUNK_SIZE = 5000

EMPLOYEE_XLSX = BASE_DIR / "EMPLOYEE_DIRECTORY.xlsx"
VILLAGE_XLSX  = BASE_DIR / "VILLAGE_DIRECTORY.xlsx"

engine = create_engine(
    PG_URL,
    future=True,
    pool_pre_ping=True
)

# ============================================================
# BULK INSERT HELPER
# ============================================================

def bulk_insert_fast(table_name: str, df: pd.DataFrame):
    if df.empty:
        return

    conn = psycopg2.connect(PG_URL.replace("postgresql+psycopg2://", "postgresql://"))
    cur = conn.cursor()

    columns = list(df.columns)
    values = [tuple(x) for x in df.to_numpy()]

    query = f"""
        INSERT INTO {table_name} ({",".join(columns)})
        VALUES %s
    """

    execute_values(cur, query, values, page_size=CHUNK_SIZE)

    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# RAW TABLE COLUMN DEFINITIONS (EXACT MATCH)
# ============================================================

RAW_CUSTOMER_COLUMNS = [
    "source_file",
    "ano",
    "name",
    "fdt",
    "tdt",
    "amt",
    "pamt",
    "bamt",
    "da",
    "dw",
    "ds",
    "pano",
]

RAW_PAYMENT_COLUMNS = [
    "source_file",
    "ano",
    "payment_date",
    "amt",
]

RAW_EMPLOYEE_COLUMNS = [
    "emp_id",
    "name",
    "number",
    "city",
    "joining_year",
    "level",
    "state",
]

RAW_VILLAGE_COLUMNS = [
    "evid",
    "village_code",
    "new_village_code",
    "village_name",
    "new_village_name",
    "district",
    "pincode",
    "state_name",
    "emp1",
    "emp2",
    "vid",
]

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


def drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep_cols: list[str] = [
        c for c in df.columns
        if not c.lower().startswith("unnamed")
    ]
    return pd.DataFrame(df[keep_cols]).copy()

def year_to_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    df[col] = (
        df[col]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
        .apply(lambda x: f"01-01-{x}" if pd.notna(x) else None)
    )
    return df

def align_columns(df: pd.DataFrame, required_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    return pd.DataFrame(df[required_cols])


def nan_to_none(df: pd.DataFrame) -> pd.DataFrame:
    return df.where(pd.notnull(df), None)

# ============================================================
# TRUNCATE ALL RAW TABLES (FRESH START)
# ============================================================

def truncate_raw_tables():
    print("🧹 Truncating RAW tables")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE raw_customer"))
        conn.execute(text("TRUNCATE TABLE raw_payment"))
        conn.execute(text("TRUNCATE TABLE raw_employee"))
        conn.execute(text("TRUNCATE TABLE raw_village"))
    print("✅ RAW tables truncated")

# ============================================================
# LOAD RAW CUSTOMER
# ============================================================

def load_raw_customer():
    customer_files = sorted(BASE_DIR.glob("raw_customer_*.xlsx"))
    total_rows = 0

    for xlsx in customer_files:
        print(f"📥 Loading customers: {xlsx.name}")

        df = pd.read_excel(xlsx, dtype=str)
        df = normalize_columns(df)
        df = drop_unnamed_columns(df)
        df = align_columns(df, RAW_CUSTOMER_COLUMNS)
        df = nan_to_none(df)

        rows = len(df)
        total_rows += rows

        bulk_insert_fast("raw_customer", df)

        print(f"   ↳ inserted {rows} rows")

    print(f"✅ raw_customer loaded ({total_rows} rows total)")

# ============================================================
# LOAD RAW PAYMENT
# ============================================================

def load_raw_payment():
    payment_files = sorted(BASE_DIR.glob("raw_payment_*.xlsx"))

    total_rows = 0

    for xlsx in payment_files:
        print(f"📥 Loading payments: {xlsx.name}")

        df = pd.read_excel(xlsx, dtype=str)

        df = normalize_columns(df)
        df = drop_unnamed_columns(df)

        # ✅ CLEAN ano column (IMPORTANT FIX)
        if "ano" in df.columns:
            df["ano"] = (
                df["ano"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)   # remove .0
                .str.replace(r"\.$", "", regex=True)    # remove trailing .
                .str.strip()
            )

        # ✅ pdt → payment_date
        if "pdt" in df.columns:
            df["payment_date"] = df["pdt"]

        # ✅ amount → amt  🔥 THIS WAS MISSING
        if "amount" in df.columns:
            df["amt"] = df["amount"]

        df = align_columns(df, RAW_PAYMENT_COLUMNS)
        df = nan_to_none(df)

        rows = len(df)
        total_rows += rows

        bulk_insert_fast("raw_payment", df)

        print(f"   ↳ inserted {rows} rows")

    print(f"✅ raw_payment loaded ({total_rows} rows total)")

# ============================================================
# LOAD RAW EMPLOYEE
# ============================================================

EMPLOYEE_COL_MAP = {
    "id": "emp_id",
    "empid": "emp_id",
    "employee_id": "emp_id",
    "joining_date": "joining_year",
}

def load_raw_employee():
    print("📥 Loading raw_employee")

    df = pd.read_excel(EMPLOYEE_XLSX, dtype=str)

    df = normalize_columns(df)
    df = drop_unnamed_columns(df)
    df = df.rename(columns=EMPLOYEE_COL_MAP)

    # ✅ ONLY transformation in RAW: year → 01-01-year
    if "joining_year" in df.columns:
        df = year_to_date(df, "joining_year")

    df = align_columns(df, RAW_EMPLOYEE_COLUMNS)
    df = nan_to_none(df)

    bulk_insert_fast("raw_employee", df)

    print(f"✅ raw_employee loaded ({len(df)} rows)")

# ============================================================
# LOAD RAW VILLAGE
# ============================================================

def load_raw_village():
    print("📥 Loading raw_village")

    df = pd.read_excel(VILLAGE_XLSX, dtype=str)
    df = normalize_columns(df)
    df = drop_unnamed_columns(df)
    df = align_columns(df, RAW_VILLAGE_COLUMNS)
    df = nan_to_none(df)

    bulk_insert_fast("raw_village", df)

    print(f"✅ raw_village loaded ({len(df)} rows)")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    truncate_raw_tables()
    load_raw_customer()
    load_raw_payment()
    load_raw_employee()
    load_raw_village()