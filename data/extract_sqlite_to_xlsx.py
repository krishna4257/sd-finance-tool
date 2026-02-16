import sqlite3
import pandas as pd
from pathlib import Path

# ================= CONFIG =================
BASE_DIR = Path.home() / "Desktop" / "files"
OUT_DIR = Path.home() / "Desktop" / "files_out"
OUT_DIR.mkdir(exist_ok=True)

CHUNK_SIZE = 1000_000

# ================= DATA HOLDERS =================
customers_rows = []
payments_rows = []
villages_rows = []
meta_rows = []

villages_seen = set()

# ================= HELPERS =================
def table_exists(cur, table_name):
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None


def safe(v):
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None


def write_xlsx_chunks(rows, out_dir, base_name, chunk_size=100_000):
    if not rows:
        print(f"⚠️ No rows for {base_name}, skipping.")
        return

    df = pd.DataFrame(rows)
    total = len(df)
    part = 1

    for start in range(0, total, chunk_size):
        end = start + chunk_size
        chunk_df = df.iloc[start:end]

        out_file = out_dir / f"{base_name}_{part:02d}.xlsx"
        chunk_df.to_excel(out_file, index=False)

        print(f"✅ Wrote {len(chunk_df):,} rows → {out_file.name}")
        part += 1


# ================= MAIN =================
for db_file in sorted(BASE_DIR.glob("*.sqlite")):
    print(f"\n📄 Reading {db_file.name}")

    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        if not table_exists(cur, "LOANEE"):
            print("  ⏭ LOANEE table missing, skipping")
            conn.close()
            continue

        # ---------- VILLAGE ----------
        cur.execute("SELECT ADD1 FROM LOANEE WHERE ADD1 IS NOT NULL LIMIT 1")
        row = cur.fetchone()
        if not row:
            conn.close()
            continue

        village = safe(row[0])

        if village and village not in villages_seen:
            villages_seen.add(village)
            villages_rows.append({
                "village_name": village,
                "source_file": db_file.stem
            })

        # ---------- CUSTOMERS ----------
        cust_count = 0
        cur.execute("""
            SELECT
                ANO,
                NAME,
                FDT,
                TDT,
                AMT,
                PAMT,
                BAMT,
                DA,
                DW,
                DS,
                PANO
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
                "DA": safe(r[7]),  
                "DW": safe(r[8]),                
                "DS": safe(r[9]),              
                "pano": safe(r[10]),              
                "source_file": f"{db_file.stem}.sqlite"
            })
            cust_count += 1

        # ---------- PAYMENTS ----------
        pay_count = 0
        if table_exists(cur, "PAMT1"):
            cur.execute("SELECT ANO, PDT, AMT FROM PAMT1")
            for p in cur.fetchall():
                payments_rows.append({
                    "ano": safe(p[0]),
                    "payment_date": safe(p[1]),
                    "amount": safe(p[2]),
                    "source_file": f"{db_file.stem}.sqlite"
                })
                pay_count += 1

        # ---------- META ----------
        meta_rows.append({
            "source_file": f"{db_file.stem}.sqlite",
            "village_name": village,
            "customers_count": cust_count,
            "payments_count": pay_count
        })

        conn.close()

    except Exception as e:
        print(f"❌ Error in {db_file.name}: {e}")


# ================= WRITE OUTPUT =================
print("\n📝 Writing XLSX files (chunked)…")

write_xlsx_chunks(
    customers_rows,
    OUT_DIR,
    base_name="raw_customer",
    chunk_size=CHUNK_SIZE
)

write_xlsx_chunks(
    payments_rows,
    OUT_DIR,
    base_name="raw_payment",
    chunk_size=CHUNK_SIZE
)

# Villages (small)
pd.DataFrame(villages_rows).drop_duplicates(
    subset=["source_file"]
).to_excel(
    OUT_DIR / "raw_village.xlsx",
    index=False
)

# Meta (small)
pd.DataFrame(meta_rows).to_excel(
    OUT_DIR / "meta_files.xlsx",
    index=False
)

print("\n✅ DONE — all SQLite data extracted safely")
print("📂 Output folder:", OUT_DIR)


# ========================#
#📝 Writing XLSX files (chunked)…
#✅ Wrote 48,909 rows → raw_customer_01.xlsx
#✅ Wrote 1,000,000 rows → raw_payment_01.xlsx
#✅ Wrote 1,000,000 rows → raw_payment_02.xlsx
#✅ Wrote 1,000,000 rows → raw_payment_03.xlsx
#✅ Wrote 1,000,000 rows → raw_payment_04.xlsx
#✅ Wrote 532,520 rows → raw_payment_05.xlsx
#===========
