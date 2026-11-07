"""
Security and authentication package for SD Accounting Tool.
Provides session-based web authentication and token/HMAC-based mobile API authentication.
"""

from security.auth import is_ajax_request, login_required, admin_required
from security.mobile_auth import (
    generate_mobile_token,
    verify_mobile_token,
    get_active_mobile_user,
    check_user_village_access,
    mobile_auth_required,
    get_mobile_queue_hmac_secret,
    compute_canonical_envelope_hmac,
    verify_queue_integrity,
    register_mobile_request_integrity,
    parse_mobile_timestamp,
)

__all__ = [
    "is_ajax_request",
    "login_required",
    "admin_required",
    "generate_mobile_token",
    "verify_mobile_token",
    "get_active_mobile_user",
    "check_user_village_access",
    "mobile_auth_required",
    "get_mobile_queue_hmac_secret",
    "compute_canonical_envelope_hmac",
    "verify_queue_integrity",
    "register_mobile_request_integrity",
    "parse_mobile_timestamp",
]
