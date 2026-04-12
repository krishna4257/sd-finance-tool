import time
import os
from sqlalchemy import create_engine, text

import sqlite_pg
import raw_staged
import staged_final
import data_validation
import runpy

PG_URL = "postgresql+psycopg2://jayakrishnareddykarri@localhost:5433/template1"
engine = create_engine(PG_URL, future=True)

# ============================================================
# HELPERS
# ============================================================

def run(sql, msg=None):
    start = time.time()
    with engine.begin() as conn:
        conn.execute(text(sql))
    if msg:
        print(f"✅ {msg} ({round(time.time()-start,2)}s)")

def count(table):
    with engine.begin() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

def print_table_counts(stage):
    print(f"\n📊 {stage.upper()} COUNTS")
    tables = ["employee", "village", "customer", "payment"]
    for t in tables:
        try:
            print(f"{t}: {count(t)}")
        except:
            pass

# ============================================================
# E — EXTRACT
# ============================================================

def extract_sqlite_parallel():
    print("\n🚀 EXTRACTING SQLITE → EXCEL (customers + payments only)")

    SQLITE_FOLDER = "/Users/jayakrishnareddykarri/Desktop/files"

    files = [
        os.path.join(SQLITE_FOLDER, f)
        for f in os.listdir(SQLITE_FOLDER)
        if f.endswith(".sqlite")
    ]

    if not files:
        print("⚠️ No sqlite files found in folder:", SQLITE_FOLDER)
        return

    print(f"📂 Found {len(files)} sqlite files")

    try:
        # Run sqlite_pg script directly (preserves original logic)
        runpy.run_path(sqlite_pg.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Extraction failed: {e}")

    print("\n📊 EXTRACTION SUMMARY (SQLITE → RAW)")
    print("Customers:", count("raw_customer"))
    print("Payments:", count("raw_payment"))

    print("\nℹ️ NOTE:")
    print("Village & Employee data are NOT extracted from sqlite.")
    print("They will be loaded from directory Excel files in next stage.")

# ============================================================
# T — TRANSFORM
# ============================================================

def transform_data():
    print("\n🧹 TRANSFORMING DATA (using raw_staged.py)")
    try:
        runpy.run_path(raw_staged.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Transform failed: {e}")

# ============================================================
# LOAD TO STAGE
# ============================================================

def load_stage():
    print("\n🚀 LOADING TO STAGE (handled in transform step)")

# ============================================================
# LOAD TO FINAL
# ============================================================

def load_final():
    print("\n🚀 LOADING TO FINAL (using staged_final.py)")
    try:
        runpy.run_path(staged_final.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Final load failed: {e}")

# ============================================================
# VALIDATION
# ============================================================

def validate():
    print("\n🧪 VALIDATION (using data_validation.py)")
    try:
        runpy.run_path(data_validation.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Validation failed: {e}")

# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline():
    start = time.time()

    extract_sqlite_parallel()

    print("\n📊 RAW TABLE COUNTS")
    print("Customers:", count("raw_customer"))
    print("Payments:", count("raw_payment"))
    print("Villages:", count("raw_village"))
    print("Employees:", count("raw_employee"))

    transform_data()

    print("\n📊 STAGE TABLE COUNTS")
    print("Customers:", count("stage_customer"))
    print("Payments:", count("stage_payment"))
    print("Villages:", count("stage_village"))
    print("Employees:", count("stage_employee"))

    load_final()

    print("\n📊 FINAL TABLE COUNTS")
    print("Customers:", count("customer"))
    print("Payments:", count("payment"))
    print("Villages:", count("village"))
    print("Employees:", count("employee"))

    validate()

    print(f"\n🎯 PIPELINE COMPLETED IN {round(time.time()-start,2)}s")


if __name__ == "__main__":
    run_pipeline()