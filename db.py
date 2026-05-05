import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
for var in required_vars:
    if not os.environ.get(var):
        raise RuntimeError(f"Missing required environment variable: {var}")

DB_CONFIG = {
    "host": os.environ["DB_HOST"].strip(),
    "database": os.environ["DB_NAME"].strip(),
    "user": os.environ["DB_USER"].strip(),
    "password": os.environ["DB_PASSWORD"].strip(),
    "port": os.environ.get("DB_PORT", "5432").strip(),
}

# Industrial-grade PostgreSQL connection pool
pg_pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=40,
    **DB_CONFIG
)


class PooledConnection:
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool

    def __getattr__(self, item):
        return getattr(self._conn, item)

    def close(self):
        """
        Return connection back to pool
        instead of closing TCP socket.
        """
        if self._conn:
            self._pool.putconn(self._conn)
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_pg_connection():
    conn = pg_pool.getconn()
    conn.autocommit = False
    return PooledConnection(conn, pg_pool)


def get_pool_stats():
    """Return PostgreSQL connection pool statistics."""

    used_connections = len(getattr(pg_pool, "_used", {}))
    available_connections = len(getattr(pg_pool, "_pool", []))

    return {
        "used_connections": used_connections,
        "available_connections": available_connections,
        "max_connections": pg_pool.maxconn
    }