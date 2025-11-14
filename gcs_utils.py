import os
from google.cloud import storage
from config import GCS_BUCKET

client = storage.Client()
bucket = client.bucket(GCS_BUCKET)

def list_sqlite_files():
    """List .sqlite files from GCS bucket."""
    files = []
    for blob in bucket.list_blobs():
        if blob.name.endswith(".sqlite"):
            files.append(os.path.basename(blob.name))
    return sorted(files)

def download_sqlite(filename):
    """Download DB from GCS → /tmp/filename"""
    local_path = f"/tmp/{filename}"
    blob = bucket.blob(filename)
    blob.download_to_filename(local_path)
    return local_path

def upload_sqlite(local_path, filename):
    """Upload DB back to GCS"""
    blob = bucket.blob(filename)
    blob.upload_from_filename(local_path)