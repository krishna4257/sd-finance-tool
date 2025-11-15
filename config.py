# config.py — simple environment-backed config for SD_Accounting_Tool

import os

# SECRET_KEY for Flask sessions (override in env for production)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

# RUN_MODE: "local" or "cloud"
RUN_MODE = os.environ.get("RUN_MODE", "cloud")

# GCS bucket name used when RUN_MODE == "cloud"
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "sd-finance-db")

# Port to run locally
PORT = int(os.environ.get("PORT", 8080))
