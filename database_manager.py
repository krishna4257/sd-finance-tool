from __future__ import annotations
import datetime
import os
import sqlite3
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
    """Extract a numeric prefix from a filename.

    Village database files are named with a numeric prefix (e.g. "12.db" or
    "3.sqlite"). This helper isolates that number for sorting. Non
    numeric prefixes are treated as zero so they appear last when
    sorting.

    Parameters
    ----------
    filename: str
        The file name to parse.

    Returns
    -------
    int
        The integer value of the numeric prefix, or a large number if
        no numeric prefix is found.
    """
    stem = filename.split(".")[0]
    return int(stem) if stem.isdigit() else 10**9


def list_village_databases() -> List[str]:
    """Return a sorted list of available village database file names.

    Files ending with ``.db`` or ``.sqlite`` in the configured
    :data:`~.config.SQLITE_FOLDER` directory are considered village
    databases. Results are sorted by their numeric prefix so that
    '10.db' appears after '2.db'. Hidden files and directories are
    ignored. In case the configured directory does not exist, an empty
    list is returned.

    Returns
    -------
    List[str]
        Sorted list of database file names.
    """
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
    """Construct the absolute path to a database given its file name.

    Parameters
    ----------
    filename: str
        The base file name of the database (e.g. ``"12.db"``).

    Returns
    -------
    str
        An absolute path to the database file.
    """
    return os.path.join(SQLITE_FOLDER, filename)


def connect(filename: str) -> sqlite3.Connection:
    """Establish a connection to the specified SQLite database.

    This function validates that the requested database exists under
    :data:`~.config.SQLITE_FOLDER` and returns a connection with a row
    factory configured to behave like a dictionary for convenient
    column access by name. The caller is responsible for closing the
    returned connection when finished.

    Parameters
    ----------
    filename: str
        The base file name of the database to connect to.

    Raises
    ------
    FileNotFoundError
        If the specified database file does not exist.

    Returns
    -------
    sqlite3.Connection
        A connection object ready for use.
    """
    path = get_database_path(filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database file not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def update_loanee_balances(conn: sqlite3.Connection, ano: str) -> None:
    """Recalculate and persist a loan's paid and balance amounts.

    Given an account number, this helper sums all payments in the
    ``PAMT1`` table for that account, then updates the corresponding
    ``PAMT`` (paid amount) and ``BAMT`` (balance amount) fields in the
    ``LOANEE`` table. It does not commit the transaction; the caller
    must commit to persist the changes.

    Parameters
    ----------
    conn: sqlite3.Connection
        An open database connection. The connection should be in a
        transaction context if multiple updates are performed.
    ano: str
        Account number whose balances need updating.

    Raises
    ------
    sqlite3.Error
        If an underlying database operation fails.
    """
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
    """
    A context manager for SQLite connections.
    It handles opening and closing the connection automatically.
    """
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