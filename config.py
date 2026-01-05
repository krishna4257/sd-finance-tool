

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


# =========================
# Environment configuration
# =========================

# Environment mode:
#   local  -> use local SQLite files
#   cloud  -> use GCS (Cloud Run)
ENV_MODE = os.getenv("ENV_MODE", "local")

# Base directory of project (portable across Mac/Linux)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Local database directory
LOCAL_DB_DIR = os.path.join(BASE_DIR, "databases")