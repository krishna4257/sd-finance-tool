import json
import logging
from flask import session, request, g, has_request_context, has_app_context
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



def audit_log(
    action,
    entity_type=None,
    entity_id=None,
    details=None,
    status="success",
    cur=None
):
    """
    Structured audit logging for security and operational actions.
    Transaction-aware: if an active cursor `cur` is supplied, logs within that transaction.
    Otherwise, uses an isolated pooled database connection.
    """
    try:
        user_id = None
        employee_id = None
        username = None
        req_ip = None
        req_method = None
        req_path = None
        req_ua = None

        if has_request_context():
            user_id = session.get("user_id") if session else None
            employee_id = (session.get("employee_id") or session.get("eid")) if session else None
            username = session.get("username") if session else None
            req_ip = request.remote_addr
            req_method = request.method
            req_path = request.path
            req_ua = request.headers.get("User-Agent")

        if has_app_context() and hasattr(g, "mobile_user") and g.mobile_user:
            user_id = user_id or g.mobile_user.get("user_id")
            employee_id = employee_id or g.mobile_user.get("eid")
            username = username or g.mobile_user.get("username")

        sql = """
            INSERT INTO audit_log (
                action,
                entity_type,
                entity_id,
                user_id,
                employee_id,
                username,
                ip_address,
                request_method,
                request_path,
                user_agent,
                details,
                status
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s
            )
        """
        params = (
            action,
            entity_type,
            str(entity_id) if entity_id is not None else None,
            user_id,
            employee_id,
            username,
            req_ip,
            req_method,
            req_path,
            req_ua,
            json.dumps(details or {}, default=str),
            status
        )

        # 1. Transaction-aware: If caller provided an active cursor, execute on it directly
        if cur is not None:
            cur.execute(sql, params)
            return

        # 2. Standalone audit log (isolated connection)
        conn = None
        standalone_cur = None
        try:
            get_conn = _resolve_func("get_pg_connection", get_pg_connection)
            conn = get_conn()
            standalone_cur = conn.cursor()
            standalone_cur.execute(sql, params)
            conn.commit()
        except Exception as e:
            logger.warning("Standalone audit log failed: %s", e)
            if conn:
                conn.rollback()
        finally:
            if standalone_cur:
                standalone_cur.close()
            if conn:
                conn.close()

    except Exception as e:
        logger.warning("Audit log failed: %s", e)
