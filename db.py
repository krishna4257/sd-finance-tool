import os
import time
import psycopg2
from psycopg2.pool import ThreadedConnectionPool, PoolError
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

DB_POOL_MIN = int(os.environ.get("DB_POOL_MIN", "2").strip())
DB_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "12").strip())

# Process-safe lazy connection pool wrapper to prevent socket sharing across Gunicorn pre-forked workers
_pg_pool = None
_pool_pid = None

def get_pool():
    global _pg_pool, _pool_pid
    current_pid = os.getpid()
    if _pg_pool is None or _pool_pid != current_pid:
        min_conn = int(os.environ.get("DB_POOL_MIN", str(DB_POOL_MIN)).strip())
        max_conn = int(os.environ.get("DB_POOL_MAX", str(DB_POOL_MAX)).strip())
        _pg_pool = ThreadedConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            **DB_CONFIG
        )
        _pool_pid = current_pid
        print(f"[DB] Initialized ThreadedConnectionPool (min={min_conn}, max={max_conn}) for process {current_pid}")
    return _pg_pool


# Custom exception for pool exhaustion
class DatabasePoolExhausted(Exception):
    """Raised when PostgreSQL connection pool is exhausted."""
    pass


class PooledConnection:
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool

    def __getattr__(self, item):
        if self._conn is None:
            raise RuntimeError(
                "Connection already returned to pool"
            )
        return getattr(self._conn, item)

    def close(self):
        """
        Return connection back to pool
        instead of closing TCP socket.

        Always rollback before returning to pool
        so no dirty transaction/session state leaks
        to the next borrower.
        """
        if self._conn:
            try:
                # Reset any open transaction state
                self._conn.rollback()
            except Exception:
                # Ignore rollback failures on already-closed/bad connections
                pass

            self._pool.putconn(self._conn)
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_pg_connection():
    last_error = None
    pool = get_pool()

    for _ in range(5):
        conn = None
        try:
            conn = pool.getconn()
            try:
                conn.rollback()
            except Exception:
                pass

            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

                return PooledConnection(conn, pool)

            except Exception:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
                last_error = RuntimeError(
                    "Connection validation failed"
                )
                time.sleep(0.2)

        except PoolError as e:
            raise DatabasePoolExhausted(
                "PostgreSQL connection pool exhausted"
            ) from e

        except Exception as e:
            last_error = e
            print(f"[DB] Dead connection detected: {e}")

            if conn is not None:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
            time.sleep(0.2)

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "Failed to obtain PostgreSQL connection after 5 attempts"
    )


def get_pool_stats():
    """Return PostgreSQL connection pool statistics."""
    pool = get_pool()
    used_connections = len(getattr(pool, "_used", {}))
    available_connections = len(getattr(pool, "_pool", []))
    max_conn = getattr(pool, "maxconn", DB_POOL_MAX)
    utilization_pct = round((used_connections / max_conn) * 100, 1) if max_conn > 0 else 0.0

    return {
        "pid": os.getpid(),
        "used_connections": used_connections,
        "available_connections": available_connections,
        "max_connections": max_conn,
        "utilization_pct": utilization_pct
    }
