"""
SD Finance: Unified Notification Dispatcher Service
File: SD_Accounting_Tool/services/notification_service.py

Connects Flask to NotifKit on 127.0.0.1:4000 for:
- Chat Push Notifications (FCM) & SMS fallbacks
- Customer loan & chit payment SMS receipts
- Management audit alerts & daily collection digests
"""

import os
import json
import logging
import requests
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

DEFAULT_NOTIFKIT_URL = "http://127.0.0.1:4000/api/v1/notify"
DEFAULT_NOTIFKIT_SECRET = "sdfinance-notifkit-secret-2026"


def get_notifkit_config():
    """Retrieve NotifKit URL and secret key from config or environment."""
    url = os.environ.get("NOTIFKIT_URL", DEFAULT_NOTIFKIT_URL)
    secret = os.environ.get("NOTIFKIT_API_SECRET", DEFAULT_NOTIFKIT_SECRET)

    if has_app_context():
        url = current_app.config.get("NOTIFKIT_URL", url)
        secret = current_app.config.get("NOTIFKIT_API_SECRET", secret)

    return url, secret


def trigger_notification(event_type, recipient_id, payload, priority="normal"):
    """
    Dispatches a notification event to NotifKit.
    Fails safely with a timeout so Flask request cycles are never delayed.
    """
    url, secret = get_notifkit_config()
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
        "User-Agent": "SDFinance-Backend/1.0"
    }
    body = {
        "eventType": event_type,
        "recipientId": str(recipient_id),
        "priority": priority,
        "data": payload
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=1.5)
        if resp.status_code in (200, 201, 202):
            return True, resp.json()
        logger.warning("[NotifKit] Dispatch returned status %s: %s", resp.status_code, resp.text)
        return False, f"Status {resp.status_code}"
    except requests.exceptions.Timeout:
        logger.warning("[NotifKit] Notification dispatch timed out (URL: %s)", url)
        return False, "Timeout"
    except Exception as e:
        logger.warning("[NotifKit] Failed to dispatch notification: %s", e)
        return False, str(e)


def notify_chat_message(recipient_id, sender_name, channel_id, message_preview, message_type="text"):
    """Trigger an internal chat push notification with auto SMS fallback."""
    preview = message_preview if message_type == "text" else f"Sent an attachment: {message_type}"
    payload = {
        "title": f"Message from {sender_name}",
        "body": preview,
        "channel_id": str(channel_id),
        "message_type": message_type,
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
    }
    return trigger_notification("internal_chat_message", recipient_id, payload, priority="high")


def notify_payment_receipt(customer_phone, customer_name, amount, account_no, remaining_balance=None):
    """Trigger a payment SMS receipt for loan/chit collections."""
    payload = {
        "customer_name": customer_name,
        "phone_number": customer_phone,
        "amount": str(amount),
        "account_no": account_no,
        "balance": str(remaining_balance) if remaining_balance is not None else ""
    }
    return trigger_notification("loan_payment_receipt", customer_phone, payload, priority="normal")


def notify_audit_alert(mgmt_user_id, action, details):
    """Trigger an urgent audit/security notification to management."""
    payload = {
        "title": "Security & Audit Alert",
        "action": action,
        "details": details
    }
    return trigger_notification("security_audit_alert", mgmt_user_id, payload, priority="high")
