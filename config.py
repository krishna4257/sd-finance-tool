import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUN_MODE = os.environ.get("RUN_MODE", "cloud")  # cloud OR local

SQLITE_FOLDER = os.path.join(BASE_DIR, "databases")

SECRET_KEY = os.environ.get("SECRET_KEY", "development-key")

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "sd-finance-db")