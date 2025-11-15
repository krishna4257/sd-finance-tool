import os
from google.cloud import storage
from config import GCS_BUCKET
import tempfile
from typing import List, Dict, Any, Optional
from google.api_core.exceptions import NotFound

# Configure this (or read from env)
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "sd-finance-db")

_client: Optional[storage.Client] = None

def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client

def list_sqlite_files() -> List[str]:
    """Return list of sqlite filenames in GCS bucket (simple list)."""
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blobs = client.list_blobs(bucket, prefix="", delimiter=None)
    files = [b.name for b in blobs if b.name.endswith(".sqlite")]
    return sorted(files, key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else 10**9)

def list_sqlite_files_detailed() -> List[Dict[str, Any]]:
    """
    Return list of dicts with metadata for UI (name, size, updated iso).
    """
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blobs = client.list_blobs(bucket)
    out = []
    for b in blobs:
        if not b.name.endswith(".sqlite"):
            continue
        out.append({
            "name": b.name,
            "size": b.size,
            "updated": b.updated.isoformat() if b.updated else None
        })
    # sort numeric prefix first
    out.sort(key=lambda x: int(x["name"].split(".")[0]) if x["name"].split(".")[0].isdigit() else 10**9)
    return out

def upload_sqlite(local_path: str, dest_filename: str) -> None:
    """Upload local_path -> GCS dest_filename."""
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(dest_filename)
    # Use resumable upload for larger files
    blob.upload_from_filename(local_path)

def download_sqlite(filename: str, dest_folder: str = "/tmp") -> str:
    """
    Download filename from GCS to a local tmp file and return local path.
    If file doesn't exist, raises NotFound.
    """
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    if not blob.exists():
        raise NotFound(f"Blob {filename} not found in bucket {GCS_BUCKET_NAME}")
    local_path = os.path.join(dest_folder, os.path.basename(filename))
    os.makedirs(dest_folder, exist_ok=True)
    blob.download_to_filename(local_path)
    return local_path

def delete_sqlite(filename: str) -> None:
    """Delete a blob from GCS."""
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.delete()