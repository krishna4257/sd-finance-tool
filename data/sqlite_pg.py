import sqlite3
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import psycopg2
from psycopg2.extras import execute_values

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path.home() / "Desktop" / "files"
OUT_DIR = Path.home() / "Desktop" / "files_out"
OUT_DIR.mkdir(exist_ok=True)

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"

CHUNK_SIZE_XLSX = 1_000_000
CHUNK_SIZE_PG = 5000

EMPLOYEE_XLSX = OUT_DIR / "EMPLOYEE_DIRECTORY.xlsx"
VILLAGE_XLSX  = OUT_DIR / "VILLAGE_DIRECTORY.xlsx"

engine = create_engine(PG_URL, future=True, pool_pre_ping=True)

# ============================================================
# ================== STEP 1: SQLITE → XLSX ====================
# ============================================================

customers_rows = []
payments_rows = []
villages_rows = []
meta_rows = []
villages_seen = set()


def table_exists(cur, table_name):
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def safe(v):
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None


def write_xlsx_chunks(rows, base_name):
    if not rows:
        return

    df = pd.DataFrame(rows)
    part = 1

    for start in range(0, len(df), CHUNK_SIZE_XLSX):
        chunk = df.iloc[start:start + CHUNK_SIZE_XLSX]
        out_file = OUT_DIR / f"{base_name}_{part:02d}.xlsx"
        chunk.to_excel(out_file, index=False)
        print(f"✅ {base_name} → {out_file.name}")
        part += 1


def extract_sqlite():
    print("\n🚀 STEP 1: Extracting SQLite → XLSX")

    for db_file in sorted(BASE_DIR.glob("*.sqlite")):
        print(f"📄 {db_file.name}")

        try:
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()

            if not table_exists(cur, "LOANEE"):
                continue

            cur.execute("SELECT ADD1 FROM LOANEE WHERE ADD1 IS NOT NULL LIMIT 1")
            row = cur.fetchone()
            village = safe(row[0]) if row else None

            if village and village not in villages_seen:
                villages_seen.add(village)
                villages_rows.append({
                    "village_name": village,
                    "source_file": db_file.stem
                })

            # Customers
            cur.execute("""
                SELECT ANO, NAME, FDT, TDT, AMT, PAMT, BAMT, DA, DW, DS, PANO
                FROM LOANEE
            """)
            for r in cur.fetchall():
                customers_rows.append({
                    "ano": safe(r[0]),
                    "name": safe(r[1]),
                    "fdt": safe(r[2]),
                    "tdt": safe(r[3]),
                    "amt": safe(r[4]),
                    "pamt": safe(r[5]),
                    "bamt": safe(r[6]),
                    "da": safe(r[7]),
                    "dw": safe(r[8]),
                    "ds": safe(r[9]),
                    "pano": safe(r[10]),
                    "source_file": f"{db_file.stem}.sqlite"
                })

            # Payments
            if table_exists(cur, "PAMT1"):
                cur.execute("SELECT ANO, PDT, AMT FROM PAMT1")
                for p in cur.fetchall():
                    payments_rows.append({
                        "ano": safe(p[0]),
                        "payment_date": safe(p[1]),
                        "amt": safe(p[2]),
                        "source_file": f"{db_file.stem}.sqlite"
                    })

            conn.close()

        except Exception as e:
            print(f"❌ {db_file.name}: {e}")

    write_xlsx_chunks(customers_rows, "raw_customer")
    write_xlsx_chunks(payments_rows, "raw_payment")

    pd.DataFrame(villages_rows).to_excel(OUT_DIR / "raw_village.xlsx", index=False)
    pd.DataFrame(meta_rows).to_excel(OUT_DIR / "meta_files.xlsx", index=False)

    print("\n📊 EXTRACTION SUMMARY")
    print(f"Total customers extracted: {len(customers_rows)}")
    print(f"Total payments extracted: {len(payments_rows)}")
    print(f"Total villages extracted: {len(villages_rows)}")

    print("✅ STEP 1 DONE")


# ============================================================
# ================== STEP 2: XLSX → POSTGRES ==================
# ============================================================

def bulk_insert_fast(table_name, df):
    if df.empty:
        return

    conn = psycopg2.connect(PG_URL.replace("postgresql+psycopg2://", "postgresql://"))
    cur = conn.cursor()

    execute_values(
        cur,
        f"INSERT INTO {table_name} ({','.join(df.columns)}) VALUES %s",
        [tuple(x) for x in df.to_numpy()],
        page_size=CHUNK_SIZE_PG
    )

    conn.commit()
    cur.close()
    conn.close()


def normalize(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


def load_to_pg():
    print("\n🚀 STEP 2: Loading XLSX → PostgreSQL")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE raw_customer, raw_payment, raw_employee, raw_village"))

    # Customers
    for f in sorted(OUT_DIR.glob("raw_customer_*.xlsx")):
        df = pd.read_excel(f, dtype=str)
        df = normalize(df)
        # 🔧 FIX: Clean ANO (remove .0 or trailing decimals)
        if "ano" in df.columns:
            df["ano"] = (
                df["ano"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.replace(r"\..*$", "", regex=True)
                .str.strip()
            )
        bulk_insert_fast("raw_customer", df)
        print(f"📥 {f.name}")

    # Payments
    for f in sorted(OUT_DIR.glob("raw_payment_*.xlsx")):
        df = pd.read_excel(f, dtype=str)
        df = normalize(df)
        # 🔧 FIX: Clean ANO (remove .0 or trailing decimals)
        if "ano" in df.columns:
            df["ano"] = (
                df["ano"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.replace(r"\..*$", "", regex=True)
                .str.strip()
            )
        bulk_insert_fast("raw_payment", df)
        print(f"📥 {f.name}")

    # Employee
    df = pd.read_excel(EMPLOYEE_XLSX, dtype=str)
    df = normalize(df)

    # 🔧 FIX: Remove unwanted columns (like id) that don't exist in DB
    if "id" in df.columns:
        df = df.rename(columns={"id": "emp_id"})
    # 🔧 FIX: Rename columns to match DB schema
    if "joining_date" in df.columns:
        df = df.rename(columns={"joining_date": "joining_year"})

    bulk_insert_fast("raw_employee", df)

    # Village
    df = pd.read_excel(VILLAGE_XLSX, dtype=str)
    df = normalize(df)

    # 🔧 FIX: Keep only columns that exist in raw_village table
    valid_columns = [
        "village_code", "new_village_code",
        "village_name", "new_village_name",
        "district", "pincode", "state_name",
        "emp1", "emp2", "vid", "evid", "source_file"
    ]

    df = df[[col for col in df.columns if col in valid_columns]]

    # 🔧 FIX: Clean integer columns to avoid "integer out of range" / invalid values
    int_cols = ["vid", "evid", "emp1", "emp2"]

    for col in int_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[^0-9]", "", regex=True)
                .replace("", None)
            )

    bulk_insert_fast("raw_village", df)

    print("✅ STEP 2 DONE")


# ============================================================
# ========================== MAIN =============================
# ============================================================


def main():
    extract_sqlite()
    load_to_pg()
    print("\n🎉 ALL DONE (SQLite → Excel → PostgreSQL)")


if __name__ == "__main__":
    main()