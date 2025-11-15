from __future__ import annotations
import os
import sqlite3
import sys
import logging
from typing import List, Dict, Any

from config import RUN_MODE as CONFIG_RUN_MODE, GCS_BUCKET_NAME
from gcs_utils import list_sqlite_files as gcs_list, download_sqlite, upload_sqlite, delete_sqlite

RUN_MODE = os.environ.get("RUN_MODE", CONFIG_RUN_MODE or "cloud")
logger = logging.getLogger(__name__)
logger.info("database_manager loaded — RUN_MODE=%s", RUN_MODE)

def _get_base_path():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", None)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_path() or ""
SQLITE_FOLDER = os.path.join(BASE_DIR, "databases")
if not os.path.exists(SQLITE_FOLDER):
    try:
        os.makedirs(SQLITE_FOLDER, exist_ok=True)
    except Exception:
        pass

def _extract_numeric_prefix(filename: str) -> int:
    stem = filename.split(".")[0]
    return int(stem) if stem.isdigit() else 10**9

def list_village_databases(full_meta: bool = False) -> List[Any]:
    """Return list of filenames (or metadata dicts if full_meta=True)."""
    if RUN_MODE == "local":
        names = sorted([f for f in os.listdir(SQLITE_FOLDER) if f.endswith(".sqlite")], key=_extract_numeric_prefix)
        if full_meta:
            # build basic meta
            return [{"name": n, "size": os.path.getsize(os.path.join(SQLITE_FOLDER, n)), "uploaded": None} for n in names]
        return names

    # cloud mode
    if full_meta:
        return gcs_list(full_meta=True)
    return gcs_list()

def get_database_path(filename: str) -> str:
    """Return path to a usable copy of DB. In cloud mode, ensures /tmp copy exists."""
    if RUN_MODE == "local":
        return os.path.join(SQLITE_FOLDER, filename)

    local_path = f"/tmp/{filename}"
    if os.path.exists(local_path):
        return local_path

    # download from GCS to /tmp
    downloaded = download_sqlite(filename, local_path=local_path)
    if not downloaded:
        raise FileNotFoundError(f"Could not download {filename} from GCS")
    return local_path

def connect(filename: str):
    db_path = get_database_path(filename)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

class get_db_connection:
    """Context manager that uploads file back to GCS on exit if RUN_MODE=cloud."""
    def __init__(self, filename: str):
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
                logger.exception("Commit failed during exit: %s", e)
            try:
                self.conn.close()
            except Exception:
                pass

        if RUN_MODE == "cloud":
            try:
                logger.info("Uploading %s back to GCS", self.filename)
                if self.local_path is None:
                    raise ValueError(f"local_path is None for file {self.filename}")
                upload_sqlite(self.local_path, self.filename)
            except Exception:
                logger.exception("Upload back to GCS failed for %s", self.filename)

def update_loanee_balances(conn: sqlite3.Connection, ano: str) -> None:
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
    cursor.execute("UPDATE LOANEE SET PAMT = ?, BAMT = ? WHERE ANO = ?", (total_paid, new_balance, ano))

# helper wrappers for gcs utils
def upload_sqlite_local_or_cloud(local_path: str, filename: str):
    if RUN_MODE == "local":
        dest = os.path.join(SQLITE_FOLDER, filename)
        os.replace(local_path, dest)
        return True
    # cloud mode: call the imported upload_sqlite() from gcs_utils
    return upload_sqlite(local_path, filename)# defined in gcs_utils; keep import alias

def delete_sqlite_from_gcs(filename: str):
    if RUN_MODE == "local":
        path = os.path.join(SQLITE_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        raise FileNotFoundError(f"Local file {filename} not found")
    # cloud:
    return delete_sqlite(filename)

__all__ = [
    "list_village_databases",
    "get_database_path",
    "connect",
    "get_db_connection",
    "update_loanee_balances",
    "upload_sqlite",
    "delete_sqlite_from_gcs"
]