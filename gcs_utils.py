"""
gcs_utils.py

Helpers for listing, downloading, uploading and deleting sqlite files
from a configured GCS bucket.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from google.cloud import storage
from google.api_core.exceptions import NotFound

from .config import GCS_BUCKET_NAME

logger = logging.getLogger(__name__)
logger.info("gcs_utils loaded - bucket=%s", GCS_BUCKET_NAME)

_client = storage.Client()  # will use default credentials in Cloud Run / local dev if configured


def _get_bucket():
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME not set in config")
    return _client.bucket(GCS_BUCKET_NAME)


def list_sqlite_files(full_meta: bool = False) -> List[Any]:
    """Return either list of names or list of metadata dicts (name,size,updated)."""
    bucket = _get_bucket()
    blobs = bucket.list_blobs()
    results: List[Any] = []
    for blob in blobs:
        if not blob.name.lower().endswith(".sqlite"):
            continue
        if full_meta:
            results.append({
                "name": blob.name,
                "size": blob.size or 0,
                "updated": blob.updated.isoformat() if blob.updated else ""
            })
        else:
            results.append(blob.name)
    # sort by numeric prefix if present else push to end
    def _sort_key(x):
        name = x["name"] if isinstance(x, dict) else x
        stem = os.path.splitext(name)[0]
        return int(stem) if stem.isdigit() else 10**9
    results.sort(key=_sort_key)
    return results


def download_sqlite(filename: str, local_path: Optional[str] = None) -> str:
    """Download blob to local_path (defaults to /tmp/<filename>). Returns local path."""
    bucket = _get_bucket()
    blob = bucket.blob(filename)
    if not blob.exists():
        logger.error("Blob not found: %s", filename)
        raise FileNotFoundError(f"Blob {filename} not found in bucket {GCS_BUCKET_NAME}")
    local_path = local_path or f"/tmp/sqlite_cache/{filename}"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)
    logger.info("Downloaded %s -> %s", filename, local_path)
    return local_path


def upload_sqlite(local_path: str, filename: str) -> bool:
    """Upload local file to GCS (overwrites)."""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file {local_path} not found for upload")
    bucket = _get_bucket()
    blob = bucket.blob(filename)
    blob.upload_from_filename(local_path)
    logger.info("Uploaded %s -> gs://%s/%s", local_path, GCS_BUCKET_NAME, filename)
    return True


def delete_sqlite(filename: str) -> bool:
    bucket = _get_bucket()
    blob = bucket.blob(filename)
    try:
        blob.delete()
        logger.info("Deleted gs://%s/%s", GCS_BUCKET_NAME, filename)
        return True
    except NotFound:
        logger.warning("Blob not found while deleting: %s", filename)
        raise FileNotFoundError(f"404 Blob {filename} not found in bucket {GCS_BUCKET_NAME}")