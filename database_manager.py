import os
import sqlite3
from typing import List, Dict, Any

from google.cloud import storage
from config import RUN_MODE, GCS_BUCKET_NAME

LOCAL_DB_FOLDER = os.path.join(os.path.dirname(__file__), "databases")

# ---------------------------
# Helper: Local DB path
# ---------------------------

def get_database_path(filename: str) -> str:
    """Return local DB file path."""
    return os.path.join(LOCAL_DB_FOLDER, filename)

# ---------------------------
# LIST FILES (CLOUD & LOCAL)
# ---------------------------

def list_village_databases() -> List[str]:
    """
    Returns list of filenames from LOCAL folder OR GCS bucket.
    Works based on RUN_MODE.
    """
    if RUN_MODE == "local":
        return [f for f in os.listdir(LOCAL_DB_FOLDER) if f.endswith(".sqlite")]

    # CLOUD MODE - pull from GCS
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    files = []
    for blob in bucket.list_blobs():
        if blob.name.endswith(".sqlite"):
            files.append(blob.name)

    return files

# ---------------------------
# GCS LIST for manage_files page
# ---------------------------

def gcs_list() -> List[Dict[str, Any]]:
    """Return file metadata for manage_files.html"""

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    results = []
    for blob in bucket.list_blobs():
        if not blob.name.endswith(".sqlite"):
            continue

        results.append({
            "name": blob.name,
            "size": blob.size or 0,
            "updated": blob.updated.isoformat() if blob.updated else ""
        })

    return results

# ---------------------------
# UPLOAD SQLITE to GCS
# ---------------------------

def upload_sqlite(local_path: str, filename: str) -> bool:
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    blob = bucket.blob(filename)
    blob.upload_from_filename(local_path)

    return True

# ---------------------------
# DOWNLOAD SQLITE TO LOCAL /tmp
# ---------------------------

def download_sqlite(filename: str, local_path: str) -> bool:
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    blob = bucket.blob(filename)
    if not blob.exists():
        return False

    blob.download_to_filename(local_path)
    return True

# ---------------------------
# DELETE SQLITE FROM GCS
# ---------------------------

def delete_sqlite(filename: str) -> bool:
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    blob = bucket.blob(filename)
    if not blob.exists():
        return False

    blob.delete()
    return True

# ---------------------------
# DB CONNECTION WRAPPER
# ---------------------------

def connect(filename: str) -> sqlite3.Connection:
    """Connect to local or downloaded DB."""

    db_path = get_database_path(filename)

    if RUN_MODE == "cloud":
        # Ensure local folder exists
        os.makedirs("/tmp/sqlite_cache", exist_ok=True)

        local_tmp = f"/tmp/sqlite_cache/{filename}"

        if not os.path.exists(local_tmp):
            download_sqlite(filename, local_tmp)

        return sqlite3.connect(local_tmp)

    # Local mode
    return sqlite3.connect(db_path)