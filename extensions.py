from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def mobile_rate_limit_key():
    from flask import request
    token = request.headers.get("X-Mobile-Token")
    if token:
        try:
            from security.mobile_auth import verify_mobile_token
            data = verify_mobile_token(token)
            if data:
                eid = data.get("eid")
                user_id = data.get("user_id")
                if eid:
                    return f"mobile-eid:{eid}"
                if user_id:
                    return f"mobile-user:{user_id}"
        except Exception:
            pass
    return get_remote_address()


limiter = Limiter(key_func=mobile_rate_limit_key)

