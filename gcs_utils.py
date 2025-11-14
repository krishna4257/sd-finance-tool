import os
from google.cloud import storage

# Default bucket, override via Cloud Run env var
BUCKET_NAME = os.getenv("GCS_BUCKET", "sd-finance-db")

def get_storage_client():
    """Return Google Cloud Storage client."""
    return storage.Client()

def list_sqlite_files():
    """List all .sqlite files in the bucket."""
    client = get_storage_client()
    blobs = client.list_blobs(BUCKET_NAME)
    return [b.name for b in blobs if b.name.endswith(".sqlite")]

def download_sqlite(filename):
    """Download SQLite file from GCS to /tmp and return local path."""
    local_path = f"/tmp/{filename}"
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.download_to_filename(local_path)
    return local_path

def upload_sqlite(local_path, filename):
    """Upload SQLite file back to GCS after commit."""
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_filename(local_path)