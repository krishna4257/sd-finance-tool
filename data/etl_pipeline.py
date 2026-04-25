import time
import os
import shutil
from sqlalchemy import create_engine, text

import sqlite_pg
import raw_staged
import staged_final
import data_validation
import retry_bad_data
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

def check_disk():
    total, used, free = shutil.disk_usage("/")
    gb_free = free // (1024**3)
    print(f"💾 Free disk space: {gb_free} GB")
    if gb_free < 10:
        raise RuntimeError("❌ Not enough disk space to run pipeline")

def timed(label, func):
    start = time.time()
    func()
    print(f"⏱️ {label} completed in {round(time.time()-start,2)}s")

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
        if hasattr(sqlite_pg, "main"):
            sqlite_pg.main() # type: ignore
        else:
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
        if hasattr(raw_staged, "main"):
            raw_staged.main() # type: ignore
        else:
            runpy.run_path(raw_staged.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Transform failed: {e}")

def wait_for_retry_signal():
    print("\n⏸️ TRANSFORM COMPLETED")
    print("👉 Fix bad data in bad_customer_data / bad_payment_data")
    print("👉 Then type 'retry' to run retry pipeline and continue")
    print("👉 Type 'skip' to continue without retry")

    while True:
        user_input = input("\nEnter command (retry/skip): ").strip().lower()
        if user_input == "retry":
            print("\n🔁 RUNNING RETRY PIPELINE")
            try:
                if hasattr(retry_bad_data, "main"):
                    retry_bad_data.main()  # type: ignore
                else:
                    runpy.run_path(retry_bad_data.__file__, run_name="__main__")
            except Exception as e:
                raise RuntimeError(f"Retry failed: {e}")
            break
        elif user_input == "skip":
            print("⏭️ Skipping retry step")
            break
        else:
            print("❌ Invalid input. Type 'retry' or 'skip'.")

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
        if hasattr(staged_final, "main"):
            staged_final.main() # type: ignore
        else:
            runpy.run_path(staged_final.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Final load failed: {e}")

# ============================================================
# VALIDATION
# ============================================================

def validate():
    print("\n🧪 VALIDATION (using data_validation.py)")
    try:
        if hasattr(data_validation, "main"):
            data_validation.main() # type: ignore
        else:
            runpy.run_path(data_validation.__file__, run_name="__main__")
    except Exception as e:
        raise RuntimeError(f"Validation failed: {e}")

# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline():
    start = time.time()

    check_disk()

    timed("EXTRACT", extract_sqlite_parallel)

    if count("raw_payment") == 0:
        raise RuntimeError("❌ Extraction failed: No payment data loaded")

    print("\n📊 RAW TABLE COUNTS")
    print("Customers:", count("raw_customer"))
    print("Payments:", count("raw_payment"))
    print("Villages:", count("raw_village"))
    print("Employees:", count("raw_employee"))

    timed("TRANSFORM", transform_data)

    wait_for_retry_signal()

    print("\n📊 STAGE TABLE COUNTS")
    print("Customers:", count("stage_customer"))
    print("Payments:", count("stage_payment"))
    print("Villages:", count("stage_village"))
    print("Employees:", count("stage_employee"))

    timed("LOAD FINAL", load_final)

    print("\n📊 DATA FLOW SUMMARY (RAW → STAGE → FINAL)")
    print("="*100)
    print(f"{'Entity':<15}{'RAW':>12}{'STAGE':>12}{'FINAL':>12}{'R→S %LOSS':>15}{'S→F %LOSS':>15}")
    print("="*100)

    entities = [
        ("Customers", "raw_customer", "stage_customer", "customer"),
        ("Payments", "raw_payment", "stage_payment", "payment"),
        ("Villages", "raw_village", "stage_village", "village"),
        ("Employees", "raw_employee", "stage_employee", "employee"),
    ]

    for name, raw_t, stage_t, final_t in entities:
        raw_c = count(raw_t) or 0
        stage_c = count(stage_t) or 0
        final_c = count(final_t) or 0

        # % loss calculations (safe divide)
        rs_loss = ((raw_c - stage_c) / raw_c * 100) if raw_c > 0 else 0
        sf_loss = ((stage_c - final_c) / stage_c * 100) if stage_c > 0 else 0

        print(f"{name:<15}{raw_c:>12}{stage_c:>12}{final_c:>12}{rs_loss:>14.2f}%{sf_loss:>14.2f}%")

    print("="*100)

    timed("VALIDATION", validate)

    print(f"\n🎯 PIPELINE COMPLETED IN {round(time.time()-start,2)}s")


if __name__ == "__main__":
    run_pipeline()