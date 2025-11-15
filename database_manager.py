"""
database_manager.py

Small abstraction for local vs cloud DB path management and simple helpers.
This uses gcs_utils under the hood for cloud mode.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional

from config import RUN_MODE, GCS_BUCKET_NAME
import gcs_utils

BASE_DIR = os.path.dirname(__file__)
LOCAL_DB_FOLDER = os.path.join(BASE_DIR, "databases")
TMP_CACHE = "/tmp/sqlite_cache"


def _ensure_local_folder():
    os.makedirs(LOCAL_DB_FOLDER, exist_ok=True)
    os.makedirs(TMP_CACHE, exist_ok=True)


def get_database_path(filename: str) -> str:
    """Return path where the database file can be accessed locally.

    In local mode this is the local databases folder.
    In cloud mode this will download the file into /tmp/sqlite_cache and return that path.
    """
    _ensure_local_folder()
    if RUN_MODE == "local":
        return os.path.join(LOCAL_DB_FOLDER, filename)

    # cloud mode: use /tmp cache
    local_tmp = os.path.join(TMP_CACHE, filename)
    if not os.path.exists(local_tmp):
        # download into temporary cache
        gcs_utils.download_sqlite(filename, local_tmp)
    return local_tmp


def list_village_databases(full_meta: bool = False) -> List[Any]:
    """
    Return list of files.
    If RUN_MODE=local returns filenames (or metadata dicts if full_meta True)
    If RUN_MODE=cloud calls gcs_utils.list_sqlite_files(full_meta=full_meta)
    """
    _ensure_local_folder()
    if RUN_MODE == "local":
        files = [f for f in os.listdir(LOCAL_DB_FOLDER) if f.endswith(".sqlite")]
        if full_meta:
            result = []
            for f in files:
                path = os.path.join(LOCAL_DB_FOLDER, f)
                stat = os.stat(path)
                result.append({
                    "name": f,
                    "size": stat.st_size,
                    "updated": ""
                })
            return sorted(result, key=lambda x: int(os.path.splitext(x["name"])[0]) if os.path.splitext(x["name"])[0].isdigit() else 10**9)
        return sorted(files, key=lambda n: int(os.path.splitext(n)[0]) if os.path.splitext(n)[0].isdigit() else 10**9)

    # cloud
    return gcs_utils.list_sqlite_files(full_meta=full_meta)


def upload_sqlite(local_path: str, filename: str) -> bool:
    """Upload file to GCS (cloud) or copy to local folder (local)."""
    _ensure_local_folder()
    if RUN_MODE == "local":
        dest = os.path.join(LOCAL_DB_FOLDER, filename)
        # overwrite
        import shutil
        shutil.copyfile(local_path, dest)
        return True
    return gcs_utils.upload_sqlite(local_path, filename)


def download_sqlite(filename: str, local_path: Optional[str] = None) -> bool:
    """Download from GCS (cloud) or copy from local folder (local)."""
    _ensure_local_folder()
    if RUN_MODE == "local":
        src = os.path.join(LOCAL_DB_FOLDER, filename)
        if not os.path.exists(src):
            return False
        dest = local_path or src
        import shutil
        shutil.copyfile(src, dest)
        return True

    # cloud mode
    try:
        gcs_utils.download_sqlite(filename, local_path)
        return True
    except FileNotFoundError:
        return False


def delete_sqlite(filename: str) -> bool:
    """Delete from GCS (cloud) or remove from local folder (local)."""
    _ensure_local_folder()
    if RUN_MODE == "local":
        path = os.path.join(LOCAL_DB_FOLDER, filename)
        if not os.path.exists(path):
            return False
        os.remove(path)
        return True

    return gcs_utils.delete_sqlite(filename)


def connect(filename: str) -> sqlite3.Connection:
    """Return a sqlite3.Connection to a local DB file (downloads if necessary)."""
    path = get_database_path(filename)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn