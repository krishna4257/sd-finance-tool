# database_manager.py
from __future__ import annotations
import os
import sqlite3
import sys
import shutil
from typing import List

from config import RUN_MODE as CONFIG_RUN_MODE

# Import GCS helpers (they may not exist in local mode)
try:
    from gcs_utils import (
        list_sqlite_files as gcs_list,
        download_sqlite as gcs_download,
        upload_sqlite as gcs_upload,
        delete_sqlite as gcs_delete
    )
except Exception:
    gcs_list = None
    gcs_download = None
    gcs_upload = None
    gcs_delete = None

# Final RUN_MODE
RUN_MODE = os.environ.get("RUN_MODE", CONFIG_RUN_MODE or "cloud")

print(f"🔧 database_manager.py loaded — RUN_MODE = {RUN_MODE}")

def _get_base_path():
    """Detect PyInstaller bundle or normal local folder."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", None)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_path() or ""
SQLITE_FOLDER = os.path.join(BASE_DIR, "databases")

# Ensure folder exists in local mode
if RUN_MODE == "local":
    os.makedirs(SQLITE_FOLDER, exist_ok=True)


# -------------------------------------------------------
# LIST DATABASE FILES
# -------------------------------------------------------
def _extract_numeric_prefix(filename: str) -> int:
    stem = filename.split(".")[0]
    return int(stem) if stem.isdigit() else 10**9

def list_village_databases() -> List[str]:
    """Return list of .sqlite files either locally or from GCS."""
    if RUN_MODE == "local":
        if not os.path.exists(SQLITE_FOLDER):
            return []
        files = [f for f in os.listdir(SQLITE_FOLDER) if f.endswith(".sqlite")]
        return sorted(files, key=_extract_numeric_prefix)

    # CLOUD MODE
    if gcs_list:
        return sorted(gcs_list(), key=_extract_numeric_prefix)

    return []


# -------------------------------------------------------
# PATH HANDLING
# -------------------------------------------------------
def get_database_path(filename: str) -> str:
    """
    Return the actual local path of the sqlite file.
    Cloud Run: ensure file is downloaded to /tmp first.
    """
    if RUN_MODE == "local":
        return os.path.join(SQLITE_FOLDER, filename)

    # CLOUD MODE
    local_path = f"/tmp/{filename}"

    # If exists in /tmp – use it
    if os.path.exists(local_path):
        return local_path

    # Otherwise download from GCS
    if gcs_download:
        return gcs_download(filename)

    raise FileNotFoundError(f"GCS download_sqlite not available for {filename}")


# -------------------------------------------------------
# CONNECT
# -------------------------------------------------------
def connect(filename: str):
    """Return sqlite3.Connection with row_factory set."""
    db_path = get_database_path(filename)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------------
# UPLOAD
# -------------------------------------------------------
def upload_sqlite(local_path: str, filename: str):
    """
    Upload database file to permanent storage (local or GCS).
    """
    if RUN_MODE == "local":
        dest = os.path.join(SQLITE_FOLDER, filename)
        shutil.copy(local_path, dest)
        return dest

    # CLOUD MODE
    if gcs_upload:
        gcs_upload(local_path, filename)
        return True

    raise RuntimeError("upload_sqlite not available in cloud mode")


# -------------------------------------------------------
# DELETE (NEW)
# -------------------------------------------------------
def delete_sqlite(filename: str):
    """
    Delete SQLite file from permanent storage (local or GCS).
    """
    if RUN_MODE == "local":
        path = os.path.join(SQLITE_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    # CLOUD MODE
    if gcs_delete:
        gcs_delete(filename)
        return True

    raise RuntimeError("delete_sqlite not available in cloud mode")


# -------------------------------------------------------
# SAFE CONTEXT MANAGER (handles auto-upload in cloud)
# -------------------------------------------------------
class get_db_connection:
    """
    In LOCAL: normal commit+close.
    In CLOUD: commit+close + upload modified DB back to GCS.
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

        if RUN_MODE == "cloud":
            try:
                print(f"☁️ Uploading {self.filename} → GCS")
                if self.local_path is not None:
                    upload_sqlite(self.local_path, self.filename)
                else:
                    print(f"❌ Cannot upload: local_path for {self.filename} is None")
            except Exception as e:
                print(f"❌ Upload to GCS failed: {e}")


# -------------------------------------------------------
# BALANCE UPDATE
# -------------------------------------------------------
def update_loanee_balances(conn: sqlite3.Connection, ano: str):
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(IFNULL(AMT, 0)) FROM PAMT1 WHERE ANO = ?", (ano,))
    result = cursor.fetchone()
    total_paid = float(result[0]) if result and result[0] else 0.0

    cursor.execute("SELECT AMT FROM LOANEE WHERE ANO = ?", (ano,))
    row = cursor.fetchone()
    if row is None:
        return
    original_amount = float(row[0] or 0.0)

    new_balance = original_amount - total_paid

    cursor.execute(
        "UPDATE LOANEE SET PAMT = ?, BAMT = ? WHERE ANO = ?",
        (total_paid, new_balance, ano),
    )


__all__ = [
    "list_village_databases",
    "get_database_path",
    "connect",
    "upload_sqlite",
    "delete_sqlite",
    "update_loanee_balances",
    "get_db_connection",
]