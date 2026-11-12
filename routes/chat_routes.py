"""
SD Finance: Real-time Internal Chat & Notification Controller
File: SD_Accounting_Tool/routes/chat_routes.py

Blueprint: /api/v1/chat
Provides:
1. Centrifugo JWT generation with channel subscription permissions.
2. Channel discovery & listing with unread counts and presence.
3. Message persistence in PostgreSQL with Telugu & English UTF-8 support.
4. Instant WebSocket broadcasting via Centrifugo loopback (<10ms).
5. Background push/SMS notifications via NotifKit.
6. WhatsApp-style delivery receipts (sent -> delivered -> read).
7. Audio and camera photo uploads with file-type whitelisting.
"""

import os
import time
import json
import uuid
import hmac
import hashlib
import base64
import logging
import requests
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, request, jsonify, session, g, current_app, render_template
from werkzeug.utils import secure_filename

from db import get_pg_connection
from services.notification_service import notify_chat_message

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/v1/chat")

# Allowed media extensions for chat
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_EXTS = {".m4a", ".aac", ".opus", ".mp3", ".ogg"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTS | ALLOWED_AUDIO_EXTS

DEFAULT_CENTRIFUGO_URL = "http://127.0.0.1:8001/api"
DEFAULT_WS_ENDPOINT = "wss://sivadurga.in/connection/websocket"
MEDIA_UPLOAD_DIR = "/var/www/sd-chat-media"


# ------------------------------------------------------------------------------
# HELPER: Zero-Dependency HS256 JWT Token Generator for Centrifugo
# ------------------------------------------------------------------------------
def generate_centrifugo_jwt(user_id, role, username, secret_key, ttl_seconds=86400):
    """Generates an RFC 7519 compliant HMAC-SHA256 JWT for Centrifugo authentication."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "info": {
            "username": username,
            "role": role
        },
        "exp": now + ttl_seconds,
        "iat": now
    }

    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


# ------------------------------------------------------------------------------
# AUTHENTICATION DECORATOR: Unified Session & Mobile Token Guard
# ------------------------------------------------------------------------------
def chat_auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 1. Try Web Session
        user_id = session.get("user_id")
        if user_id:
            raw_role = session.get("user_level") or session.get("level") or "staff"
            normalized_role = "admin" if raw_role in ("admin", "superadmin") else ("mgmt" if raw_role == "mgmt" else "staff")
            g.chat_user = {
                "id": int(user_id),
                "username": session.get("username", "web_user"),
                "role": normalized_role,
                "auth_type": "session"
            }
            return f(*args, **kwargs)

        # 2. Try Mobile Header Tokens (X-Mobile-Token or Authorization Bearer)
        mobile_token = request.headers.get("X-Mobile-Token")
        auth_header = request.headers.get("Authorization", "")
        if not mobile_token and auth_header.startswith("Bearer "):
            mobile_token = auth_header.split(" ", 1)[1].strip()

        if mobile_token:
            try:
                from security.mobile_auth import verify_mobile_token, get_active_mobile_user
                token_data = verify_mobile_token(mobile_token)
                if token_data:
                    user_record = get_active_mobile_user(token_data)
                    if user_record and user_record.get("is_active"):
                        raw_level = (user_record.get("level") or "").strip().lower()
                        normalized_role = "admin" if raw_level in ("admin", "superadmin") else ("mgmt" if raw_level == "mgmt" else "staff")
                        g.chat_user = {
                            "id": int(user_record["user_id"]),
                            "username": user_record.get("username", "mobile_user"),
                            "role": normalized_role,
                            "auth_type": "mobile_token"
                        }
                        return f(*args, **kwargs)
            except Exception as e:
                logger.error("[ChatAuth] Token verification failed: %s", e)

        return jsonify({"success": False, "error": "Authentication required"}), 401
    return wrapper


# ------------------------------------------------------------------------------
# ENDPOINT 0: Web Portal Dashboard View
# ------------------------------------------------------------------------------
@chat_bp.route("/", methods=["GET"])
@chat_bp.route("/web", methods=["GET"])
@chat_auth_required
def chat_web_view():
    """Renders the web chat management console."""
    user = g.chat_user
    return render_template(
        "chat.html",
        user=user,
        active_page="chat"
    )


# ------------------------------------------------------------------------------
# ENDPOINT 1: Centrifugo Connection Token
# ------------------------------------------------------------------------------
@chat_bp.route("/token", methods=["GET"])
@chat_auth_required
def get_connection_token():
    """Generates Centrifugo JWT for WebSockets."""
    user = g.chat_user
    secret = current_app.config.get("CENTRIFUGO_SECRET_KEY") or current_app.config.get("SECRET_KEY", "default-dev-secret")
    token = generate_centrifugo_jwt(
        user_id=user["id"],
        role=user["role"],
        username=user["username"],
        secret_key=secret
    )
    ws_endpoint = current_app.config.get("CENTRIFUGO_WS_ENDPOINT", DEFAULT_WS_ENDPOINT)

    return jsonify({
        "success": True,
        "token": token,
        "ws_endpoint": ws_endpoint,
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"]
    })


# ------------------------------------------------------------------------------
# ENDPOINT 2: Channel Listing with RBAC
# ------------------------------------------------------------------------------
@chat_bp.route("/channels", methods=["GET"])
@chat_auth_required
def get_user_channels():
    """Lists channels the current user belongs to, with unread counters and last message preview."""
    user = g.chat_user
    user_id = user["id"]
    is_staff = user["role"] == "staff"

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            # Query channels for this user
            cur.execute("""
                SELECT 
                    c.id,
                    c.channel_type,
                    c.name,
                    c.created_at,
                    m.last_read_message_id,
                    -- Other member details for direct chat
                    other_u.id AS other_user_id,
                    COALESCE(other_e.name, other_u.username) AS other_user_name,
                    LOWER(COALESCE(other_e.level, other_m.role, 'staff')) AS other_user_role,
                    -- Last message preview
                    last_msg.id AS last_msg_id,
                    last_msg.body AS last_msg_body,
                    last_msg.message_type AS last_msg_type,
                    last_msg.created_at AS last_msg_time,
                    last_msg.status AS last_msg_status,
                    last_msg.sender_id AS last_msg_sender_id,
                    -- Unread count
                    (
                        SELECT COUNT(*) 
                        FROM chat_messages unread 
                        WHERE unread.channel_id = c.id 
                          AND unread.sender_id != %s
                          AND unread.status != 'read'
                    ) AS unread_count
                FROM chat_channels c
                JOIN chat_channel_members m ON m.channel_id = c.id AND m.user_id = %s
                -- Join other party in 1:1 direct channels
                LEFT JOIN chat_channel_members other_m ON other_m.channel_id = c.id AND other_m.user_id != %s AND c.channel_type = 'direct'
                LEFT JOIN users other_u ON other_u.id = other_m.user_id
                LEFT JOIN employee other_e ON other_e.eid = other_u.employee_id
                -- Subquery for last message
                LEFT JOIN LATERAL (
                    SELECT lm.id, lm.body, lm.message_type, lm.created_at, lm.status, lm.sender_id
                    FROM chat_messages lm
                    WHERE lm.channel_id = c.id
                    ORDER BY lm.created_at DESC
                    LIMIT 1
                ) last_msg ON TRUE
                WHERE c.is_active = TRUE
                ORDER BY COALESCE(last_msg.created_at, c.created_at) DESC;
            """, (user_id, user_id, user_id))
            
            rows = cur.fetchall()
            channels = []
            for r in rows:
                c_id, c_type, c_name, c_created, last_read_id, o_uid, o_name, o_role, \
                lm_id, lm_body, lm_type, lm_time, lm_status, lm_sender, unread_cnt = r

                clean_role = (o_role or "").lower()
                # RBAC filter for staff: direct channels must be with admin or mgmt
                if is_staff and c_type == "direct" and not any(k in clean_role for k in ("admin", "mgmt", "superadmin", "management")):
                    continue

                if c_type == "broadcast":
                    display_title = c_name
                else:
                    if "superadmin" in clean_role:
                        role_suffix = " [SUPER ADMIN]"
                    elif "admin" in clean_role:
                        role_suffix = " [ADMIN]"
                    elif any(m in clean_role for m in ("mgmt", "management")):
                        role_suffix = " [MGMT]"
                    else:
                        role_suffix = ""
                    display_title = f"{o_name or 'User'}{role_suffix}"

                channels.append({
                    "channel_id": str(c_id),
                    "channel_type": c_type,
                    "title": display_title,
                    "other_user_id": o_uid,
                    "other_user_role": clean_role,
                    "unread_count": int(unread_cnt or 0),
                    "last_message": {
                        "id": str(lm_id) if lm_id else None,
                        "body": lm_body,
                        "type": lm_type,
                        "status": lm_status,
                        "is_me": lm_sender == user_id,
                        "created_at": lm_time.isoformat() if lm_time else None
                    } if lm_id else None,
                    "created_at": c_created.isoformat() if c_created else None
                })

            return jsonify({"success": True, "channels": channels})
    finally:
        conn.close()


# ------------------------------------------------------------------------------
# ENDPOINT 2B: Directory & Dynamic Direct Channel Creation
# ------------------------------------------------------------------------------
@chat_bp.route("/users", methods=["GET"])
@chat_auth_required
def get_chat_directory():
    """
    Returns directory of reachable users.
    Leadership users (admin, superadmin, mgmt) can see and message all users.
    Field staff can only see and message leadership users.
    """
    current_user = g.chat_user
    is_staff = current_user["role"] == "staff"

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    u.id, 
                    u.username, 
                    COALESCE(e.name, u.username) AS display_name,
                    LOWER(COALESCE(e.level, 'staff')) AS level
                FROM users u
                LEFT JOIN employee e ON e.eid = u.employee_id
                WHERE u.is_active = TRUE AND u.id != %s
                ORDER BY display_name ASC;
            """, (current_user["id"],))
            rows = cur.fetchall()

            directory = []
            for uid, uname, dname, raw_level in rows:
                clean_level = (raw_level or "").strip().lower()
                is_target_lead = any(k in clean_level for k in ("admin", "superadmin", "mgmt", "management"))
                
                # RBAC: Staff cannot see or message other staff
                if is_staff and not is_target_lead:
                    continue

                if "superadmin" in clean_level:
                    role_tag = "superadmin"
                elif "admin" in clean_level:
                    role_tag = "admin"
                elif any(k in clean_level for k in ("mgmt", "management")):
                    role_tag = "mgmt"
                else:
                    role_tag = "staff"

                directory.append({
                    "user_id": uid,
                    "username": uname,
                    "display_name": dname,
                    "role": role_tag
                })

            return jsonify({"success": True, "users": directory})
    finally:
        conn.close()


@chat_bp.route("/direct-channel", methods=["POST"])
@chat_auth_required
def open_direct_channel():
    """
    Finds or provisions a 1-to-1 direct channel between current user and target user.
    Admins, superadmins, and management can open a channel with anyone.
    Staff can only open a channel with leadership.
    """
    current_user = g.chat_user
    current_uid = current_user["id"]
    current_role = current_user["role"]

    data = request.get_json(silent=True) or {}
    target_uid = data.get("target_user_id")
    if not target_uid:
        return jsonify({"success": False, "error": "target_user_id is required"}), 400

    try:
        target_uid = int(target_uid)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid target_user_id"}), 400

    if current_uid == target_uid:
        return jsonify({"success": False, "error": "Cannot message yourself"}), 400

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.username, COALESCE(e.name, u.username) AS name,
                       LOWER(COALESCE(e.level, 'staff')) AS level
                FROM users u
                LEFT JOIN employee e ON e.eid = u.employee_id
                WHERE u.id = %s AND u.is_active = TRUE;
            """, (target_uid,))
            target = cur.fetchone()
            if not target:
                return jsonify({"success": False, "error": "Target user not found"}), 404

            t_id, t_uname, t_name, t_level = target
            clean_t_level = (t_level or "").strip().lower()
            t_is_lead = any(k in clean_t_level for k in ("admin", "superadmin", "mgmt", "management"))
            target_role = "admin" if any(k in clean_t_level for k in ("admin", "superadmin")) else ("mgmt" if any(k in clean_t_level for k in ("mgmt", "management")) else "staff")

            # RBAC Enforcement: Staff cannot message staff
            if current_role == "staff" and not t_is_lead:
                return jsonify({"success": False, "error": "Staff-to-staff direct channels are prohibited"}), 403

            # Check if direct channel exists
            cur.execute("""
                SELECT c.id 
                FROM chat_channels c
                JOIN chat_channel_members m1 ON m1.channel_id = c.id AND m1.user_id = %s
                JOIN chat_channel_members m2 ON m2.channel_id = c.id AND m2.user_id = %s
                WHERE c.channel_type = 'direct'
                LIMIT 1;
            """, (current_uid, target_uid))
            existing = cur.fetchone()

            if existing:
                channel_id = str(existing[0])
            else:
                # Create direct channel
                cur.execute("""
                    INSERT INTO chat_channels (channel_type, created_by, is_active)
                    VALUES ('direct', %s, TRUE)
                    RETURNING id;
                """, (current_uid,))
                channel_id = str(cur.fetchone()[0])

                cur.execute("""
                    INSERT INTO chat_channel_members (channel_id, user_id, role)
                    VALUES (%s, %s, %s), (%s, %s, %s);
                """, (channel_id, current_uid, current_role, channel_id, target_uid, target_role))
                conn.commit()

            return jsonify({
                "success": True,
                "channel_id": channel_id,
                "target_user": {
                    "id": t_id,
                    "name": t_name,
                    "role": target_role
                }
            })
    finally:
        conn.close()


# ------------------------------------------------------------------------------
# ENDPOINT 3: Message History with Pagination
# ------------------------------------------------------------------------------
@chat_bp.route("/history/<channel_id>", methods=["GET"])
@chat_auth_required
def get_channel_history(channel_id):
    """Loads paginated chat history for a channel."""
    user = g.chat_user
    limit = min(int(request.args.get("limit", 50)), 100)
    before_ts = request.args.get("before")

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            # Verify membership
            cur.execute("""
                SELECT 1 FROM chat_channel_members 
                WHERE channel_id = %s AND user_id = %s;
            """, (channel_id, user["id"]))
            if not cur.fetchone():
                return jsonify({"success": False, "error": "Access denied to channel"}), 403

            query = """
                SELECT 
                    m.id,
                    m.client_uuid,
                    m.sender_id,
                    COALESCE(e.name, u.username) AS sender_name,
                    m.message_type,
                    m.body,
                    m.media_url,
                    m.media_duration_sec,
                    m.latitude,
                    m.longitude,
                    m.status,
                    m.created_at
                FROM chat_messages m
                JOIN users u ON u.id = m.sender_id
                LEFT JOIN employee e ON e.eid = u.employee_id
                WHERE m.channel_id = %s
            """
            params = [channel_id]

            if before_ts:
                query += " AND m.created_at < %s"
                params.append(before_ts)

            query += " ORDER BY m.created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            messages = []
            for r in rows:
                m_id, c_uuid, s_id, s_name, m_type, body, media_url, dur, lat, lng, status, c_at = r
                messages.append({
                    "id": str(m_id),
                    "client_uuid": c_uuid,
                    "channel_id": str(channel_id),
                    "sender_id": s_id,
                    "sender_name": s_name,
                    "is_me": s_id == user["id"],
                    "message_type": m_type,
                    "body": body,
                    "media_url": media_url,
                    "media_duration_sec": dur,
                    "latitude": float(lat) if lat is not None else None,
                    "longitude": float(lng) if lng is not None else None,
                    "status": status,
                    "created_at": c_at.isoformat() if c_at else None
                })

            # Reverse to chronological order for client display
            messages.reverse()
            return jsonify({"success": True, "messages": messages})
    finally:
        conn.close()


# ------------------------------------------------------------------------------
# ENDPOINT 4: Send Message (Instant WebSocket + DB + Background Push)
# ------------------------------------------------------------------------------
@chat_bp.route("/send", methods=["POST"])
@chat_auth_required
def send_message():
    """Ingests a message, saves it idempotently, and broadcasts via Centrifugo."""
    user = g.chat_user
    user_id = user["id"]
    data = request.get_json(silent=True) or {}

    client_uuid = data.get("client_uuid")
    channel_id = data.get("channel_id")
    msg_type = data.get("type", "text")
    body = (data.get("body") or "").strip()
    media_url = data.get("media_url")
    duration = data.get("media_duration_sec")
    lat = data.get("latitude")
    lng = data.get("longitude")

    if not client_uuid or not channel_id:
        return jsonify({"success": False, "error": "client_uuid and channel_id are required"}), 400

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            # 1. Verify channel membership & retrieve other members
            cur.execute("""
                SELECT m.user_id, m.role, c.channel_type
                FROM chat_channel_members m
                JOIN chat_channels c ON c.id = m.channel_id
                WHERE m.channel_id = %s;
            """, (channel_id,))
            members = cur.fetchall()
            
            my_membership = [m for m in members if m[0] == user_id]
            if not my_membership:
                return jsonify({"success": False, "error": "You are not a member of this channel"}), 403

            channel_type = members[0][2]

            # 2. RBAC Guard: If user is staff in a broadcast channel, they cannot post
            if user["role"] == "staff" and channel_type == "broadcast":
                return jsonify({"success": False, "error": "Only Admin and Management can post in broadcast channels"}), 403

            # 3. RBAC Guard: If user is staff in direct channel, verify other member is leadership
            if user["role"] == "staff" and channel_type == "direct":
                other_members = [m for m in members if m[0] != user_id]
                has_leadership = any(m[1] in ("admin", "mgmt") for m in other_members)
                if not has_leadership:
                    return jsonify({"success": False, "error": "Staff may only message Admin or Management"}), 403

            # 4. Idempotent insertion using client_uuid
            cur.execute("""
                INSERT INTO chat_messages (
                    client_uuid, channel_id, sender_id, message_type,
                    body, media_url, media_duration_sec, latitude, longitude, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'sent')
                ON CONFLICT (client_uuid) DO UPDATE 
                    SET status = EXCLUDED.status,
                        updated_at = NOW()
                RETURNING id, created_at, status;
            """, (client_uuid, channel_id, user_id, msg_type, body, media_url, duration, lat, lng))
            
            row = cur.fetchone()
            msg_id, created_at, status = row
            conn.commit()

        # 5. Broadcast in real-time via Centrifugo (<10ms)
        centrifugo_url = current_app.config.get("CENTRIFUGO_API_URL", DEFAULT_CENTRIFUGO_URL)
        api_key = current_app.config.get("CENTRIFUGO_API_KEY", "sdfinance-centrifugo-api-key-2026")
        
        publish_url = f"{centrifugo_url.rstrip('/')}/publish" if not centrifugo_url.endswith("/publish") else centrifugo_url
        centrifugo_payload = {
            "channel": f"chat:{channel_id}",
            "data": {
                "event": "new_message",
                "id": str(msg_id),
                "client_uuid": client_uuid,
                "channel_id": str(channel_id),
                "sender_id": user_id,
                "sender_name": user["username"],
                "message_type": msg_type,
                "body": body,
                "media_url": media_url,
                "media_duration_sec": duration,
                "latitude": float(lat) if lat is not None else None,
                "longitude": float(lng) if lng is not None else None,
                "status": "sent",
                "created_at": created_at.isoformat()
            }
        }
        try:
            requests.post(
                publish_url,
                headers={
                    "X-API-Key": api_key,
                    "Authorization": f"apikey {api_key}",
                    "Content-Type": "application/json"
                },
                json=centrifugo_payload,
                timeout=1.0
            )
        except Exception as e:
            logger.warning("[Centrifugo] Instant publish failed (client offline): %s", e)

        # 6. Trigger NotifKit background push for offline recipients
        recipient_ids = [m[0] for m in members if m[0] != user_id]
        for rid in recipient_ids:
            notify_chat_message(
                recipient_id=rid,
                sender_name=user["username"],
                channel_id=channel_id,
                message_preview=body,
                message_type=msg_type
            )

        return jsonify({
            "success": True,
            "message_id": str(msg_id),
            "client_uuid": client_uuid,
            "status": status,
            "created_at": created_at.isoformat()
        })
    except Exception as ex:
        logger.error("[ChatSend] Failed to store or process message: %s", ex, exc_info=True)
        return jsonify({"success": False, "error": str(ex)}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------------------
# ENDPOINT 5: WhatsApp-Style Status Acknowledgment (Delivered & Read Ticks)
# ------------------------------------------------------------------------------
@chat_bp.route("/ack", methods=["POST"])
@chat_auth_required
def acknowledge_message_status():
    """Updates message status to 'delivered' or 'read' and broadcasts tick update."""
    data = request.get_json(silent=True) or {}
    message_id = data.get("message_id")
    channel_id = data.get("channel_id")
    new_status = data.get("status")  # 'delivered' or 'read'

    if not message_id or not channel_id or new_status not in ("delivered", "read"):
        return jsonify({"success": False, "error": "Invalid acknowledgment payload"}), 400

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            if new_status == "delivered":
                cur.execute("""
                    UPDATE chat_messages 
                    SET status = 'delivered', delivered_at = NOW() 
                    WHERE id = %s AND status = 'sent';
                """, (message_id,))
            elif new_status == "read":
                cur.execute("""
                    UPDATE chat_messages 
                    SET status = 'read', read_at = NOW() 
                    WHERE id = %s AND status IN ('sent', 'delivered');
                """, (message_id,))
            conn.commit()

        # Broadcast status update event to Centrifugo v5
        centrifugo_url = current_app.config.get("CENTRIFUGO_API_URL", DEFAULT_CENTRIFUGO_URL)
        api_key = current_app.config.get("CENTRIFUGO_API_KEY", "sdfinance-centrifugo-api-key-2026")
        publish_url = f"{centrifugo_url.rstrip('/')}/publish" if not centrifugo_url.endswith("/publish") else centrifugo_url
        try:
            requests.post(
                publish_url,
                headers={
                    "X-API-Key": api_key,
                    "Authorization": f"apikey {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": f"chat:{channel_id}",
                    "data": {
                        "event": "status_update",
                        "message_id": str(message_id),
                        "status": new_status,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                timeout=1.0
            )
        except Exception as e:
            logger.warning("[Centrifugo] Status update publish failed: %s", e)

        return jsonify({"success": True, "message_id": str(message_id), "status": new_status})
    finally:
        conn.close()


# ------------------------------------------------------------------------------
# ENDPOINT 6: Upload Media (Photos & Voice Notes)
# ------------------------------------------------------------------------------
@chat_bp.route("/upload-media", methods=["POST"])
@chat_auth_required
def upload_chat_media():
    """Receives compressed photos or audio notes, saves them, and returns media URL."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"success": False, "error": f"Unsupported media type: {ext}"}), 400

    # Ensure upload directory exists (fallback to local uploads in development)
    target_dir = MEDIA_UPLOAD_DIR
    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception:
            target_dir = os.path.join(current_app.root_path, "static", "uploads", "chat_media")
            os.makedirs(target_dir, exist_ok=True)

    # Generate random collision-free filename
    unique_filename = f"chat_{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(target_dir, unique_filename)
    file.save(dest_path)

    media_url = f"/chat-media/{unique_filename}"
    return jsonify({
        "success": True,
        "media_url": media_url,
        "filename": unique_filename,
        "is_audio": ext in ALLOWED_AUDIO_EXTS
    })


# ------------------------------------------------------------------------------
# ENDPOINT 7: Register FCM Push Notification Token
# ------------------------------------------------------------------------------
@chat_bp.route("/register-push-token", methods=["POST"])
@chat_auth_required
def register_push_token():
    """Saves or updates FCM push notification token for mobile client."""
    user = g.chat_user
    data = request.get_json(silent=True) or {}
    token = data.get("fcm_token")

    if not token:
        return jsonify({"success": False, "error": "fcm_token is required"}), 400

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_notification_settings (user_id, fcm_token, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE 
                    SET fcm_token = EXCLUDED.fcm_token, updated_at = NOW();
            """, (user["id"], token))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()
