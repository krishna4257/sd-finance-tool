from __future__ import annotations
import os
import sqlite3
import sys
from typing import List

from config import RUN_MODE as CONFIG_RUN_MODE
from gcs_utils import list_sqlite_files as gcs_list, download_sqlite, upload_sqlite

# Read RUN_MODE from environment (fallback to config)
RUN_MODE = os.environ.get("RUN_MODE", CONFIG_RUN_MODE or "cloud")

print(f"🔧 database_manager.py loaded — RUN_MODE = {RUN_MODE}")

def _get_base_path():
    """Determine base path depending on PyInstaller or normal execution."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", None)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _get_base_path() or ""
SQLITE_FOLDER = os.path.join(BASE_DIR, "databases")


# ----------------------------
#  LIST FILES (LOCAL vs CLOUD)
# ----------------------------

def _extract_numeric_prefix(filename: str) -> int:
    stem = filename.split(".")[0]
    return int(stem) if stem.isdigit() else 10**9


def list_village_databases() -> List[str]:
    """List either local .sqlite files or GCS bucket files."""
    if RUN_MODE == "local":
        print("📂 RUN_MODE=local — Listing local DB files")
        if not os.path.exists(SQLITE_FOLDER):
            return []
        return sorted(
            [f for f in os.listdir(SQLITE_FOLDER) if f.endswith(".sqlite")],
            key=_extract_numeric_prefix
        )

    print("☁️ RUN_MODE=cloud — Listing GCS DB files")
    return gcs_list()


# ----------------------------
#  PATH HANDLING (LOCAL / TMP)
# ----------------------------

def get_database_path(filename: str):
    """Return actual database path depending on mode."""
    if RUN_MODE == "local":
        return os.path.join(SQLITE_FOLDER, filename)

    # CLOUD MODE — always use /tmp/
    local_path = f"/tmp/{filename}"
    if os.path.exists(local_path):
        return local_path

    # File not downloaded yet
    return download_sqlite(filename)


# ----------------------------
#  SQLITE CONNECT (NO PATCHING!)
# ----------------------------

def connect(filename: str):
    """
    Safe SQLite connect.
    No commit override (Cloud Run does not allow monkey patching builtins).
    """
    db_path = get_database_path(filename)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------
#  CONTEXT MANAGER (UPLOAD ON EXIT)
# ----------------------------

class get_db_connection:
    """
    Safe context manager.
    In CLOUD mode: commits and uploads the DB before closing.
    """
    def __init__(self, filename):
        self.filename = filename
        self.conn = None
        self.local_path = None

    def __enter__(self):
        self.conn = connect(self.filename)
        self.local_path = get_database_path(self.filename)
        return self.conn

    def __exit__(self, exc_type, exc_value, tb):
        if self.conn:
            try:
                self.conn.commit()
            except Exception as e:
                print("⚠️ Commit failed during exit:", e)

            self.conn.close()

        # Only upload in CLOUD mode
        if RUN_MODE == "cloud":
            try:
                print(f"☁️ Uploading {self.filename} → GCS")
                upload_sqlite(self.local_path, self.filename)
            except Exception as e:
                print(f"❌ Upload to GCS failed: {e}")


# ----------------------------
#  BALANCE UPDATE LOGIC
# ----------------------------

def update_loanee_balances(conn: sqlite3.Connection, ano: str) -> None:
    """Recalculate and persist paid and balance amounts."""
    cursor = conn.cursor()

    cursor.execute(
        "SELECT SUM(IFNULL(AMT, 0)) FROM PAMT1 WHERE ANO = ?",
        (ano,),
    )
    result = cursor.fetchone()
    total_paid = float(result[0]) if result and result[0] else 0.0

    cursor.execute("SELECT AMT FROM LOANEE WHERE ANO = ?", (ano,))
    row = cursor.fetchone()
    if row is None:
        return
    original_amount = float(row[0] or 0.0)

    new_balance = original_amount - total_paid

    cursor.execute(
        """
        UPDATE LOANEE
        SET PAMT = ?, BAMT = ?
        WHERE ANO = ?
        """,
        (total_paid, new_balance, ano),
    )


__all__ = [
    "list_village_databases",
    "get_database_path",
    "connect",
    "update_loanee_balances",
    "get_db_connection"
]