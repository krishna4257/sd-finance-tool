import logging
from functools import wraps
from flask import request, session, jsonify, redirect, url_for, flash

logger = logging.getLogger(__name__)


def is_ajax_request():
    """Detect whether incoming request is an AJAX, fetch, or API request."""
    # If Sec-Fetch-Mode is present, verify if it is not a document navigation
    fetch_mode = request.headers.get("Sec-Fetch-Mode")
    if fetch_mode:
        return fetch_mode != "navigate"

    # Fallback for older browsers, custom API clients, and crawlers
    return (
        request.path.startswith("/api/")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
        or "application/json" in request.headers.get("Accept", "")
    )


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            # --- SESSION DIAGNOSTIC LOG ---
            try:
                import datetime as _dt
                _ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _ip = request.headers.get("X-Forwarded-For", request.remote_addr)
                _ua = request.headers.get("User-Agent", "unknown")
                _url = request.url
                _method = request.method
                _cookie_hdr = request.headers.get("Cookie", "")
                _has_session_cookie = "sivadurga_session" in _cookie_hdr
                _session_keys = list(session.keys())
                _log_line = (
                    f"[{_ts}] UNEXPECTED_LOGOUT "
                    f"ip={_ip} method={_method} url={_url} "
                    f"cookie_present={_has_session_cookie} "
                    f"session_keys={_session_keys} "
                    f"ua={_ua}\n"
                )
                log_path = "/tmp/sd_session_debug.log"
                with open(log_path, "a") as _lf:
                    _lf.write(_log_line)
                logger.warning(_log_line.strip())
            except Exception:
                pass
            # --- END DIAGNOSTIC LOG ---
            # IMPORTANT: Mark session as unmodified so Flask does NOT send a
            # Set-Cookie header in this redirect response.
            session.modified = False

            # API / AJAX / Fetch requests should receive 401 Unauthorized instead of a 302
            # redirect to /login. This prevents the browser fetch engine from fetching
            # /login in the background and generating a sparse session cookie that
            # overwrites the user's valid session cookie.
            if is_ajax_request():
                return jsonify(success=False, error="Session expired. Please login again.", session_expired=True), 401

            return redirect("/login")

        user_level = session.get("level")
        if user_level in ("j", "m", "s"):
            allowed_paths = ("/app/portal", "/app/download-action", "/logout")
            if request.path not in allowed_paths:
                if session.get("download_authorized") is True:
                    return redirect("/app/portal")
                else:
                    session.clear()
                    flash("Access denied.")
                    return redirect("/login")

        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        level = session.get("level")

        if not user_id:
            session.modified = False
            if is_ajax_request():
                return jsonify(success=False, error="Session expired. Please login again.", session_expired=True), 401
            flash("Please login", "danger")
            return redirect(url_for("login"))

        # Only admin and mgmt allowed
        if level not in ["admin", "mgmt"]:
            if is_ajax_request():
                return jsonify(success=False, error="Access denied."), 403
            flash("Access denied", "danger")
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)
    return wrapper
