import psycopg2
import os


def get_pg_connection():
    required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    for var in required_vars:
        if not os.environ.get(var):
            raise RuntimeError(f"Missing required environment variable: {var}")

    return psycopg2.connect(
        host=os.environ["DB_HOST"].strip(),
        database=os.environ["DB_NAME"].strip(),
        user=os.environ["DB_USER"].strip(),
        password=os.environ["DB_PASSWORD"].strip(),
        port=os.environ.get("DB_PORT", "5432").strip(),
    )