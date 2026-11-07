import json
import time as pytime
import threading
import logging
from functools import wraps
from flask import request, session
from db import get_pg_connection

logger = logging.getLogger(__name__)


def _resolve_func(name, default_func):
    """
    Allow backwards-compatible mock patching where tests or callers patch `app.<name>`.
    If `app.<name>` exists and was replaced (e.g. by a MagicMock), use it instead.
    """
    try:
        import sys
        app_mod = sys.modules.get("app")
        if app_mod is not None and hasattr(app_mod, name):
            val = getattr(app_mod, name)
            if val is not default_func:
                return val
    except Exception:
        pass
    return default_func


def get_resolved_pg_conn():
    get_conn = _resolve_func("get_pg_connection", get_pg_connection)
    return get_conn()


class TTLMemoryCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                val, expires_at = self._cache[key]
                if pytime.time() < expires_at:
                    return val
                else:
                    del self._cache[key]
            return None

    def set(self, key, val, ttl_seconds):
        with self._lock:
            self._cache[key] = (val, pytime.time() + ttl_seconds)

    def clear(self):
        with self._lock:
            self._cache.clear()


global_ttl_cache = TTLMemoryCache()


def ttl_cache(ttl_seconds=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                body_data = request.get_json(silent=True)
                if body_data:
                    body_key = json.dumps(body_data, sort_keys=True)
                else:
                    body_key = ""
            except Exception:
                body_key = ""

            query_key = tuple(sorted(request.args.items()))
            session_vid = session.get("vid")
            session_uid = session.get("user_id")

            cache_key = (
                f.__name__,
                args,
                tuple(sorted(kwargs.items())),
                query_key,
                body_key,
                session_vid,
                session_uid
            )

            cached_val = global_ttl_cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            response = f(*args, **kwargs)

            is_cacheable = True
            if isinstance(response, tuple):
                if len(response) > 1 and isinstance(response[1], int) and response[1] != 200:
                    is_cacheable = False

            if is_cacheable:
                global_ttl_cache.set(cache_key, response, ttl_seconds)

            return response
        return wrapper
    return decorator


def is_village_monthly(vid, cur=None):
    """
    Check if a village operates on a monthly installment schedule ('M').
    Criteria:
      1. Village name or village code ends with '-M' or contains '-M'.
      2. OR majority of active customers in the village are type 'M'.
    """
    if not vid:
        return False

    close_cur = False
    conn = None
    if cur is None:
        conn = get_resolved_pg_conn()
        cur = conn.cursor()
        close_cur = True

    try:
        cur.execute("SELECT village_name, village_code FROM village WHERE vid = %s", (vid,))
        row = cur.fetchone()
        if not row:
            return False
        v_name, v_code = (row[0] or "").upper(), (row[1] or "").upper()
        if "-M" in v_name or "-M" in v_code:
            return True

        cur.execute("""
            SELECT COUNT(*) FILTER (WHERE type = 'M'), COUNT(*)
            FROM customer
            WHERE vid = %s
        """, (vid,))
        c_row = cur.fetchone()
        if c_row and c_row[1] and c_row[1] > 0:
            if (c_row[0] / c_row[1]) >= 0.5:
                return True

        return False
    except Exception as e:
        logger.error(f"Error checking if village {vid} is monthly: {e}")
        return False
    finally:
        if close_cur and cur is not None:
            cur.close()
            if conn is not None:
                conn.close()


def customer_exists_by_ano_and_vid(ano, vid):
    """Check if a customer with the given ano and vid exists in the database."""
    conn = get_resolved_pg_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 1
            FROM customer
            WHERE ano = %s AND vid = %s
            LIMIT 1
        """, (ano, vid))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()
