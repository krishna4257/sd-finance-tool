

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


SQLITE_FOLDER = os.environ.get(
    "SQLITE_FOLDER",
    os.path.join(BASE_DIR, "databases"),
)
AUTH_BUCKET = "sd-auth-db"
TEAM_BUCKETS = {
    "teamA": "sd-finance-db",
    "teamB": "ext_1"
}

GCS_DEFAULT_BUCKET = "sd-finance-db"

SECRET_KEY = os.environ.get("SECRET_KEY", "development-secret-key")