from __future__ import annotations
import datetime
import os
import sqlite3
import tempfile
from flask import jsonify
import sys
from typing import Iterable, List, Optional, Sequence, Tuple, Dict
import shutil
from google.cloud import storage
from werkzeug.utils import secure_filename

# --- CONFIG ---
GCS_BUCKET = os.environ.get("GCS_BUCKET")        # required
TMP_FOLDER = "/tmp/gcs_sqlite_files"
os.makedirs(TMP_FOLDER, exist_ok=True)


# -------------------------
# INTERNAL HELPERS
# -------------------------
def _get_client():
    return storage.Client()


def _safe_tmp_path(filename):
    safe = secure_filename(filename)
    return os.path.join(TMP_FOLDER, safe)


# -------------------------
# LIST FILES IN GCS
# -------------------------
def list_gcs_files():
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET)

    files = []
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    for blob in bucket.list_blobs():
        # Determine "modified within 24 hours"
        updated = blob.updated.replace(tzinfo=datetime.timezone.utc)
        is_new = (now - updated).total_seconds() < 86400

        files.append(blob.name)

    return files


# -------------------------
# DOWNLOAD FILE FROM GCS
# -------------------------
def download_from_gcs(filename):
    if isinstance(filename, dict):
      filename = filename.get("name")

    filename = str(filename).strip()
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(filename)

    local_path = _safe_tmp_path(filename)
    blob.download_to_filename(local_path)

    os.chmod(local_path, 0o666)
    return local_path


# -------------------------
# UPLOAD FILE TO GCS
# -------------------------
def upload_to_gcs(local_path, filename=None):
    if filename is None:
        filename = os.path.basename(local_path)

    client = _get_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(filename)
    blob.upload_from_filename(local_path)

    return True


# -------------------------
# DELETE FILE FROM GCS
# -------------------------
def delete_from_gcs(filename):
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(filename)
    blob.delete()
    return True


# -------------------------
# GET LOCAL COPY OF SELECTED DB
# -------------------------
import os
from werkzeug.utils import secure_filename
from google.cloud import storage
import logging

TMP_FOLDER = "/tmp"


def get_local_db_path(filename):
    """
    Download filename from GCS to /tmp and return the full local path.
    Raises RuntimeError with clear message if download fails.
    """
    client = _get_client()
    bucket_name = os.environ.get("GCS_BUCKET")
    if not bucket_name:
        raise RuntimeError("Environment variable GCS_BUCKET not set")

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)

    safe = secure_filename(filename)
    local_path = os.path.join(TMP_FOLDER, safe)

    # Ensure tmp folder exists
    os.makedirs(TMP_FOLDER, exist_ok=True)

    try:
        # download_to_filename will raise a google.api_core.exceptions.NotFound if blob missing
        blob.download_to_filename(local_path)
    except Exception as e:
        logging.exception("Failed to download %s from bucket %s: %s", filename, bucket_name, e)
        raise RuntimeError(f"Failed to download {filename} from GCS: {e}")

    # sanity check file exists and size > 0
    if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
        raise RuntimeError(f"Downloaded file {local_path} missing or empty")

    return local_path


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