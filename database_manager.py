from __future__ import annotations
import datetime
import os
import logging
import sqlite3
import tempfile
from flask import jsonify
import sys
from typing import Iterable, List, Optional, Sequence, Tuple, Dict
import shutil
from google.cloud import storage
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from config import ENV_MODE, GCS_DEFAULT_BUCKET, AUTH_BUCKET, TEAM_BUCKETS,LOCAL_DB_DIR

# Ensure local database directory exists (local mode)
os.makedirs(LOCAL_DB_DIR, exist_ok=True)
# --- CONFIG ---
TMP_FOLDER = "/tmp/gcs_sqlite_files"
os.makedirs(TMP_FOLDER, exist_ok=True)


def _get_client() -> storage.Client:
    if ENV_MODE != "cloud":
        raise RuntimeError("GCS client requested in LOCAL mode")
    return storage.Client()

def _get_bucket(bucket_name: str | None):
    if ENV_MODE != "cloud":
        raise RuntimeError("GCS bucket access in LOCAL mode")
    if not bucket_name:
        if not GCS_DEFAULT_BUCKET:
            raise RuntimeError("No GCS bucket specified (no session bucket and GCS_DEFAULT_BUCKET unset).")
        bucket_name = GCS_DEFAULT_BUCKET
    client = _get_client()
    return client.bucket(bucket_name)

# -------------------------
# UPLOAD FILE TO GCS
# -------------------------
def upload_to_gcs(local_path: str, target_name: str, bucket: str | None = None) -> None:
    b = _get_bucket(bucket)
    blob = b.blob(target_name)
    # Use resumable upload for larger files
    blob.upload_from_filename(local_path)
    return

# -------------------------
# DOWNLOAD FILE FROM GCS
# -------------------------

def download_from_gcs(object_name: str, local_path: str | None = None, bucket: str | None = None) -> str:
    if ENV_MODE != "cloud":
        raise RuntimeError(
            "download_from_gcs() called in LOCAL mode — this should not happen"
        )
    b = _get_bucket(bucket)
    blob = b.blob(object_name)

    if local_path is None:
        # safe local path in /tmp
        safe_name = os.path.basename(object_name)
        local_path = os.path.join("/tmp", safe_name)

    # Create containing dir
    os.makedirs(os.path.dirname(local_path) or "/tmp", exist_ok=True)

    if not blob.exists():
        # If the object does not exist, raise to let caller handle.
        raise FileNotFoundError(f"Object {object_name} not found in bucket {b.name}")

    blob.download_to_filename(local_path)
    return local_path


# -------------------------
# DELETE FILE FROM GCS
# -------------------------
def delete_from_gcs(object_name: str, bucket: str | None = None) -> None:
    """Delete object from given bucket."""
    b = _get_bucket(bucket)
    blob = b.blob(object_name)
    if blob.exists():
        blob.delete()
    else:
        # silent if missing
        pass

# -------------------------
# LIST FILES IN GCS
# -------------------------
def list_gcs_files(bucket: str | None = None):
    if ENV_MODE != "cloud":
        raise RuntimeError("list_gcs_files called in LOCAL mode")
    """Return list of object names in bucket root (non-recursive)."""
    b = _get_bucket(bucket)
    # list_blobs returns an iterator; fetch names
    return [blob.name for blob in b.list_blobs()]

def list_local_db_files():
    """
    List local SQLite database files for LOCAL mode
    """
    return [
        f for f in os.listdir(SQLITE_FOLDER)
        if f.lower().endswith(".sqlite")
    ]

def get_local_db_path(filename: str, bucket: str | None = None) -> str:
    safe_name = os.path.basename(filename)

    if ENV_MODE == "local":
        local_path = os.path.join(SQLITE_FOLDER, safe_name)

        if not os.path.exists(local_path):
            raise FileNotFoundError(
                f"Local database not found: {local_path}"
            )

        return local_path
    
    """
    Download filename from GCS into /tmp and return path.
    Keep behaviour consistent with older helpers: returns /tmp/<filename>
    """
    local_path = os.path.join(TMP_FOLDER, safe_name)
    return download_from_gcs(safe_name, local_path, bucket=bucket)

# -------------------------
# GET LOCAL COPY OF SELECTED DB
# -------------------------
def get_auth_db_path(local_path: str | None = None, bucket: str | None = None):
    """
    Use /tmp/auth.sqlite by default. If you want a persistent project-local copy use other folder.
    """
    if local_path:
        return local_path
    return os.path.join("/tmp", "auth.sqlite")


def _safe_tmp_path(filename):
    safe = secure_filename(filename)
    return os.path.join(TMP_FOLDER, safe)


# -------------------------
# LOGIN / AUTH TABLES
# -------------------------
def init_auth_db():
    """
    Creates auth.sqlite in GCS if missing.
    """
    local_path = "/tmp/auth.sqlite"
    try:
        download_from_gcs("auth.sqlite", local_path) # type: ignore
    except Exception:
        pass  # File does not exist, we will create it

    conn = sqlite3.connect(local_path)
    c = conn.cursor()

    c.execute("""
CREATE TABLE IF NOT EXISTS USERS (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    system_id TEXT,
    notes TEXT,
    role TEXT DEFAULT 'user'
)
""")

    conn.commit()
    conn.close()

    upload_to_gcs(local_path, "auth.sqlite")


# -------------------------
# CREATE A NEW EMPTY SQLITE DB
# -------------------------
def create_new_db(filename):
    local_path = _safe_tmp_path(filename)
    open(local_path, "a").close()         # create empty sqlite file
    upload_to_gcs(local_path, filename)
    return filename
# This function determines the correct base path for the application,
# whether it's running from source or from a PyInstaller executable.
def _get_base_path():
    """Get the correct base path for the application."""
    if getattr(sys, 'frozen', False):
        # The application is frozen (PyInstaller). `sys._MEIPASS` is where
        # bundled files are extracted.
        # Pylance will warn about this attribute, but it is available at runtime
        return sys._MEIPASS # type: ignore
    else:
        # We are running in a normal Python script
        return os.path.dirname(os.path.abspath(__file__))

# Define the SQLITE_FOLDER relative to the application's base path
SQLITE_FOLDER = os.path.join(_get_base_path(), 'databases')

def _extract_numeric_prefix(filename: str) -> int:
  
    stem = filename.split(".")[0]
    return int(stem) if stem.isdigit() else 10**9


def list_village_databases() -> List[str]:
    if ENV_MODE == "local":
        return [
            f for f in os.listdir(LOCAL_DB_DIR)
            if f.endswith(".sqlite")
        ]
   
    # Create the folder if it doesn't exist to avoid FileNotFoundError
    os.makedirs(SQLITE_FOLDER, exist_ok=True)
    
    candidates: List[str] = [
        f for f in os.listdir(SQLITE_FOLDER)
        if os.path.isfile(os.path.join(SQLITE_FOLDER, f))
        and f.lower().endswith((".db", ".sqlite"))
    ]
    candidates.sort(key=_extract_numeric_prefix)
    return candidates


def get_database_path(filename: str) -> str:
    if ENV_MODE == "local":
        return os.path.join(LOCAL_DB_DIR, f"{village_id}.sqlite") # type: ignore
    return os.path.join(SQLITE_FOLDER, filename)


def connect(filename: str) -> sqlite3.Connection:
    path = get_database_path(filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database file not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


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

    # Note: do not commit here; let the caller decide on transaction
    # boundaries.

class get_db_connection:
   
    def __init__(self, filename):
        self.filename = filename
        self.conn = None
    
    def __enter__(self):
        self.conn = connect(self.filename)
        return self.conn
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.conn:
            self.conn.close()


__all__ = [
    "list_village_databases",
    "get_database_path",
    "connect",
    "update_loanee_balances",
    "get_db_connection"
]