import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "development-secret-key")


ENV_MODE = os.getenv("ENV_MODE", "local")

# Base directory of project (portable across Mac/Linux)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Local database directory
LOCAL_DB_DIR = os.path.join(BASE_DIR, "databases")

# PostgreSQL (future use)
POSTGRES_DB = "sd_finance"
POSTGRES_USER = "sd_user"
POSTGRES_PASSWORD = "Krishna@3579"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

POSTGRES_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)