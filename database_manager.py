from __future__ import annotations
import os
import sqlite3
import sys
from typing import List
from config import RUN_MODE
from gcs_utils import list_sqlite_files as gcs_list, download_sqlite, upload_sqlite

RUN_MODE = os.environ.get("RUN_MODE", "cloud")  # default = cloud

if RUN_MODE == "local":
    print("🔵 Running in LOCAL mode — using local files only.")

    def list_sqlite_files() -> List[str]:
        folder = SQLITE_FOLDER
        return [f for f in os.listdir(folder) if f.endswith(".sqlite")]

    def download_sqlite(filename):
        return os.path.join(SQLITE_FOLDER, filename)

    def upload_sqlite(local_path, filename):
        return  # No upload in local mode

else:
    print("🟣 Running in CLOUD mode — using GCS.")
    from gcs_utils import list_sqlite_files, download_sqlite, upload_sqlite

def _get_base_path():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", None)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_path() or ""
SQLITE_FOLDER = os.path.join(BASE_DIR, "databases")

def _extract_numeric_prefix(filename: str) -> int:
    stem = filename.split(".")[0]
    return int(stem) if stem.isdigit() else 10**9

def list_village_databases() -> List[str]:
    """Switch between local and GCS based on RUN_MODE."""
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

def get_database_path(filename: str):
    """Return actual database path depending on mode."""
    if RUN_MODE == "local":
        return os.path.join(SQLITE_FOLDER, filename)

    # CLOUD MODE
    local_path = f"/tmp/{filename}"
    if os.path.exists(local_path):
        return local_path

    return download_sqlite(filename)

def connect(filename: str):
    """Return SQLite connection with optional cloud upload."""
    db_path = get_database_path(filename)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if RUN_MODE == "local":
        return conn

    # CLOUD MODE — wrap commit to upload file
    original_commit = conn.commit

    def commit_and_upload(*args, **kwargs):
        original_commit()
        upload_sqlite(db_path, filename)

    conn.commit = commit_and_upload
    return conn

class get_db_connection:
    def __init__(self, filename):
        self.filename = filename
        self.conn = None

    def __enter__(self):
        self.conn = connect(self.filename)
        return self.conn

    def __exit__(self, exc_type, exc_value, tb):
        if self.conn:
            self.conn.close()


def update_loanee_balances(conn: sqlite3.Connection, ano: str) -> None:
    cursor = conn.cursor()

    # Calculate the total paid amount for the account. Use IFNULL to
    # coerce NULLs into zeros so SUM operates as expected.
    cursor.execute(
        "SELECT SUM(IFNULL(AMT, 0)) FROM PAMT1 WHERE ANO = ?",
        (ano,),
    )
    result = cursor.fetchone()
    total_paid: float = float(result[0]) if result and result[0] is not None else 0.0

    # Fetch the original loan amount from the LOANEE table.
    cursor.execute("SELECT AMT FROM LOANEE WHERE ANO = ?", (ano,))
    row = cursor.fetchone()
    if row is None:
        # Nothing to update if the loan is missing. Silent return.
        return
    original_amount: float = float(row[0] or 0.0)

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