#!/usr/bin/env python3
"""
Fleet Telemetry Controller: Production REST APIs for SD Finance
Implements:
  1. GET  /mobile_app                        - Unified Mobile App & Fleet Command Center
  2. GET  /api/admin/mobile_users/list       - Fleet users list & real-time presence
  3. POST /api/mobile/location/batch         - High-speed batch location ingestion (< 8ms)
  4. GET  /api/admin/fleet/status            - 30s AJAX polling endpoint
  5. GET  /api/admin/fleet/history/<user_id> - 10-day history with Douglas-Peucker simplification
  6. POST /api/admin/mobile_users/force_logout - Immediate device token revocation
  7. POST /api/admin/mobile_users/toggle_lock  - Credentials lock/unlock
  8. POST /api/admin/app/inspect_apk         - APK manifest inspection for OTA pipeline
  9. GET  /api/admin/app/qr/<version>        - Real-time QR code generation for APK downloads
"""

import os
import io
import json
import logging
import tempfile
from datetime import datetime, timezone, timedelta
import pytz
from flask import (
    request, jsonify, render_template, session, redirect,
    url_for, flash, send_file
)
from psycopg2.extras import execute_values

from db import get_pg_connection
from services.geocoding_service import reverse_geocode, init_geocache_table, batch_reverse_geocode
from services.telemetry_engine import (
    douglas_peucker, segment_trips_and_stops,
    find_nearest_village, haversine_km
)

try:
    from services import apk_signing
except ImportError:
    apk_signing = None

try:
    import qrcode
except ImportError:
    qrcode = None

logger = logging.getLogger(__name__)

def is_admin():
    """Verify administrator access level from session."""
    level = session.get("level")
    role = session.get("role")
    return level in ("admin", "superadmin") or role in ("admin", "superadmin")

def register_fleet_telemetry_routes(app, csrf):
    """Register all fleet management and telemetry routes onto the main Flask application."""

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Page Route: /mobile_app
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/mobile_app", methods=["GET"])
    def mobile_app_page():
        """Renders the unified Mobile App Control Center."""
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in to access the Mobile App Command Center.", "warning")
            return redirect(url_for("login"))

        if not is_admin():
            flash("Access denied: Administrator privileges required.", "danger")
            return redirect(url_for("village_page"))

        # Read version data
        version_data = {}
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        version_json_path = os.path.join(root_dir, "apk_releases", "version.json")
        if os.path.isfile(version_json_path):
            try:
                with open(version_json_path, "r", encoding="utf-8") as f:
                    version_data = json.load(f)
            except Exception as e:
                logger.warning("Could not read version.json: %s", e)

        # Read keystore vault info if available
        vault_info = {}
        if apk_signing and hasattr(apk_signing, "get_keystore_vault_info"):
            try:
                vault_info = apk_signing.get_keystore_vault_info()
            except Exception as e:
                logger.warning("Could not read vault info: %s", e)

        return render_template(
            "mobile_app.html",
            version_data=version_data,
            vault_info=vault_info
        )

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Admin: List Fleet Users & Real-time Presence
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/admin/mobile_users/list", methods=["GET"])
    def admin_mobile_users_list():
        """Returns all mobile users with presence, battery, hardware, and assigned villages."""
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            # 1. Fetch users and employee profiles
            cur.execute("""
                SELECT 
                    u.id,
                    u.username,
                    u.employee_id,
                    u.is_active,
                    u.created_at,
                    u.session_revoked_at,
                    e.eid,
                    e.name,
                    e.level,
                    e.phone_number,
                    NULL as photo
                FROM users u
                LEFT JOIN employee e ON e.eid = u.employee_id
                ORDER BY u.id ASC;
            """)
            user_rows = cur.fetchall()

            if not user_rows:
                return jsonify({"success": True, "users": [], "summary": {}})

            user_ids = [r[0] for r in user_rows]

            # 2. Batch fetch active or locked devices ordered by last_active, keyed by unique physical device_id
            cur.execute("""
                SELECT DISTINCT ON (user_id, device_id)
                    user_id, 
                    device_id, 
                    device_model, 
                    last_active, 
                    is_active,
                    latest_latitude,
                    latest_longitude,
                    latest_speed,
                    latest_heading,
                    latest_accuracy,
                    latest_battery_pct,
                    is_charging,
                    gps_status,
                    COALESCE(is_locked, FALSE) as is_locked
                FROM user_devices
                WHERE user_id = ANY(%s) AND (is_active = TRUE OR is_locked = TRUE) AND device_id != 'PENDING'
                ORDER BY user_id, device_id, last_active DESC NULLS LAST, id DESC;
            """, (user_ids,))

            devices_by_user = {}
            for row in cur.fetchall():
                uid = row[0]
                devices_by_user.setdefault(uid, []).append({
                    "device_id": row[1],
                    "device_model": row[2] or "Mobile Device",
                    "last_active": row[3],
                    "is_active": row[4],
                    "latest_latitude": row[5],
                    "latest_longitude": row[6],
                    "latest_speed": row[7] or 0.0,
                    "latest_heading": row[8] or 0.0,
                    "latest_accuracy": row[9],
                    "latest_battery_pct": row[10],
                    "is_charging": row[11] or False,
                    "gps_status": row[12] or "active",
                    "is_locked": bool(row[13]) if len(row) > 13 else False
                })

            # Check PENDING binding slot for users who do NOT yet have an active physical device
            cur.execute("""
                SELECT user_id, id FROM user_devices
                WHERE user_id = ANY(%s) AND device_id = 'PENDING' AND is_active = TRUE
            """, (user_ids,))
            for pend_uid, pend_id in cur.fetchall():
                if not devices_by_user.get(pend_uid):
                    devices_by_user.setdefault(pend_uid, []).append({
                        "device_id": "PENDING",
                        "device_model": "Pending Hardware Bind",
                        "last_active": None,
                        "is_active": True,
                        "latest_latitude": None,
                        "latest_longitude": None,
                        "latest_speed": 0.0,
                        "latest_heading": 0.0,
                        "latest_accuracy": None,
                        "latest_battery_pct": None,
                        "is_charging": False,
                        "gps_status": "pending"
                    })

            # 3. Batch fetch village access
            cur.execute("""
                SELECT uva.user_id, v.vid, v.village_name
                FROM user_village_access uva
                JOIN village v ON v.vid = uva.village_id
                WHERE uva.user_id = ANY(%s)
                ORDER BY v.village_name ASC;
            """, (user_ids,))

            villages_by_user = {}
            for uid, vid, vname in cur.fetchall():
                villages_by_user.setdefault(uid, []).append({"vid": vid, "name": vname})

            # 4. Construct user payload & calculate presence
            ist = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.now(ist)

            users_list = []
            online_count = 0
            active_today_count = 0
            locked_count = 0
            pending_count = 0
            total_devices_count = 0

            for row in user_rows:
                uid = row[0]
                username = row[1]
                emp_id = row[2]
                credentials_active = row[3]
                emp_name = row[7] or username
                emp_level = row[8] or "j"
                emp_phone = row[9] or "-"
                emp_photo = row[10]

                raw_devs = devices_by_user.get(uid, [])
                formatted_devs = []
                user_is_online = False
                user_is_active_today = False
                user_is_active_recently = False
                has_physical_device = False
                has_pending_device = False

                for d in raw_devs:
                    dev_id = d["device_id"]
                    dev_is_pending = (dev_id == "PENDING")
                    dev_model = d["device_model"] or ("Pending Hardware Bind" if dev_is_pending else "Mobile Device")
                    dev_is_active = d["is_active"]
                    dev_is_locked = d.get("is_locked", False)

                    if not dev_is_pending:
                        has_physical_device = True
                        if dev_is_active and not dev_is_locked:
                            total_devices_count += 1
                    else:
                        has_pending_device = True

                    d_last_act = d["last_active"]
                    d_formatted_last_act = "Never"
                    d_relative_str = "Never logged in"
                    d_presence = "offline"
                    d_seconds_ago = None

                    if dev_is_locked:
                        d_presence = "locked"
                        d_relative_str = "Device Locked by Admin"
                        d_formatted_last_act = "Locked Hardware"
                    elif not dev_is_active:
                        d_presence = "inactive"
                        d_relative_str = "Device Inactive / Reset"
                        d_formatted_last_act = "Deactivated"
                    elif dev_is_pending:
                        d_presence = "pending"
                        d_relative_str = "Pending Hardware Bind"
                        d_formatted_last_act = "Pending Hardware Bind"
                    elif d_last_act:
                        if d_last_act.tzinfo is None:
                            d_act_ist = ist.localize(d_last_act)
                        else:
                            d_act_ist = d_last_act.astimezone(ist)

                        d_formatted_last_act = d_act_ist.strftime("%d %b %Y, %I:%M %p")
                        diff = now_ist - d_act_ist
                        d_seconds_ago = max(0, int(diff.total_seconds()))

                        if d_seconds_ago < 300:
                            mins = int(d_seconds_ago // 60)
                            d_relative_str = "Active just now" if mins == 0 else f"Active {mins} min{'s' if mins > 1 else ''} ago"
                            d_presence = "online"
                            user_is_online = True
                        elif d_seconds_ago < 86400:
                            hours = int(d_seconds_ago // 3600)
                            d_relative_str = f"Active {hours} hour{'s' if hours > 1 else ''} ago"
                            d_presence = "active_today"
                            user_is_active_today = True
                        elif d_seconds_ago < 172800:
                            d_relative_str = "Active 1 day ago"
                            d_presence = "active_recently"
                            user_is_active_recently = True
                        elif d_seconds_ago < 604800:
                            days = int(d_seconds_ago // 86400)
                            d_relative_str = f"Active {days} days ago"
                            d_presence = "offline"
                        else:
                            d_relative_str = f"Active on {d_act_ist.strftime('%d %b %Y')}"
                            d_presence = "offline"

                    formatted_devs.append({
                        "device_id": dev_id,
                        "device_model": dev_model,
                        "is_active": dev_is_active,
                        "is_locked": dev_is_locked,
                        "is_pending": dev_is_pending,
                        "last_active": d_formatted_last_act,
                        "relative_last_active": d_relative_str,
                        "seconds_ago": d_seconds_ago,
                        "presence": d_presence,
                        "latest_latitude": d.get("latest_latitude"),
                        "latest_longitude": d.get("latest_longitude"),
                        "latest_speed": d.get("latest_speed", 0.0) or 0.0,
                        "latest_heading": d.get("latest_heading", 0.0) or 0.0,
                        "latest_accuracy": d.get("latest_accuracy"),
                        "latest_battery_pct": d.get("latest_battery_pct"),
                        "is_charging": d.get("is_charging", False) or False,
                        "gps_status": d.get("gps_status", "active") or "active"
                    })

                # Determine primary device for summary & backward compatibility
                primary_dev = None
                for d in formatted_devs:
                    if not d["is_pending"]:
                        primary_dev = d
                        break
                if not primary_dev and formatted_devs:
                    primary_dev = formatted_devs[0]

                # Overall user presence
                if not credentials_active:
                    user_presence = "locked"
                    locked_count += 1
                    user_relative_str = "Credentials Locked"
                    user_formatted_last_active = "Locked by Administrator"
                elif user_is_online:
                    user_presence = "online"
                    online_count += 1
                    user_relative_str = primary_dev["relative_last_active"] if primary_dev else "Online"
                    user_formatted_last_active = primary_dev["last_active"] if primary_dev else "Online"
                elif user_is_active_today:
                    user_presence = "active_today"
                    active_today_count += 1
                    user_relative_str = primary_dev["relative_last_active"] if primary_dev else "Active Today"
                    user_formatted_last_active = primary_dev["last_active"] if primary_dev else "Active Today"
                elif user_is_active_recently:
                    user_presence = "active_recently"
                    user_relative_str = primary_dev["relative_last_active"] if primary_dev else "Active Recently"
                    user_formatted_last_active = primary_dev["last_active"] if primary_dev else "Active Recently"
                elif has_pending_device and not has_physical_device:
                    user_presence = "pending"
                    pending_count += 1
                    user_relative_str = "Pending Hardware Bind"
                    user_formatted_last_active = "Pending Hardware Bind"
                elif primary_dev:
                    user_presence = primary_dev["presence"]
                    user_relative_str = primary_dev["relative_last_active"]
                    user_formatted_last_active = primary_dev["last_active"]
                else:
                    user_presence = "offline"
                    user_relative_str = "No Hardware Registered"
                    user_formatted_last_active = "Never"

                users_list.append({
                    "id": uid,
                    "username": username,
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "employee_level": emp_level,
                    "phone": emp_phone,
                    "photo": emp_photo,
                    "credentials_active": credentials_active,
                    "has_device": has_physical_device,
                    "is_pending": has_pending_device and not has_physical_device,
                    "device_id": primary_dev["device_id"] if primary_dev else "-",
                    "device_model": primary_dev["device_model"] if primary_dev else "-",
                    "device_count": len([d for d in formatted_devs if not d["is_pending"]]),
                    "devices": formatted_devs,
                    "last_active": user_formatted_last_active,
                    "relative_last_active": user_relative_str,
                    "seconds_ago": primary_dev.get("seconds_ago") if primary_dev else None,
                    "presence": user_presence,
                    "villages": villages_by_user.get(uid, []),
                    # Primary Device Telemetry for quick reference
                    "latest_latitude": primary_dev.get("latest_latitude") if primary_dev else None,
                    "latest_longitude": primary_dev.get("latest_longitude") if primary_dev else None,
                    "latest_speed": primary_dev.get("latest_speed", 0.0) if primary_dev else 0.0,
                    "latest_heading": primary_dev.get("latest_heading", 0.0) if primary_dev else 0.0,
                    "latest_accuracy": primary_dev.get("latest_accuracy") if primary_dev else None,
                    "latest_battery_pct": primary_dev.get("latest_battery_pct") if primary_dev else None,
                    "is_charging": primary_dev.get("is_charging", False) if primary_dev else False,
                    "gps_status": primary_dev.get("gps_status", "active") if primary_dev else "active",
                })

            summary = {
                "online_now": online_count,
                "active_today": active_today_count,
                "total_devices": total_devices_count,
                "locked": locked_count,
                "pending_bind": pending_count
            }

            return jsonify({
                "success": True,
                "users": users_list,
                "summary": summary
            }), 200

        except Exception as e:
            logger.error("admin_mobile_users_list error: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Mobile API: Batch Location Ingestion (Sub-8ms, Zero WSGI Thread Lockup)
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/mobile/location/batch", methods=["POST"])
    @csrf.exempt
    def mobile_location_batch():
        """
        Ingest mobile location breadcrumbs in compressed batches.
        Updates user_devices snapshot and inserts into user_locations.
        """
        token = request.headers.get("X-Mobile-Token")
        if not token:
            return jsonify({"success": False, "error": "Missing X-Mobile-Token header"}), 401

        from security.mobile_auth import verify_mobile_token
        token_data = verify_mobile_token(token)
        if not token_data:
            return jsonify({"success": False, "error": "Invalid or expired token"}), 401

        user_id = token_data.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "Invalid token payload"}), 400

        body = request.get_json(silent=True) or {}
        device_id = body.get("device_id") or "UNKNOWN_DEVICE"
        locations = body.get("locations") or []

        # Instant Security Enforcement: Check if user or device is locked / revoked
        conn_sec = get_pg_connection()
        try:
            with conn_sec.cursor() as cur_sec:
                cur_sec.execute("""
                    SELECT u.is_active, ud.is_active
                    FROM users u
                    LEFT JOIN user_devices ud ON ud.user_id = u.id AND ud.device_id = %s
                    WHERE u.id = %s;
                """, (device_id, user_id))
                sec_row = cur_sec.fetchone()
                if not sec_row or not sec_row[0]: # user account locked
                    return jsonify({
                        "success": False,
                        "error": "Account credentials locked by administrator.",
                        "action": "wipe_and_lock"
                    }), 403
                if sec_row[1] is not None and not sec_row[1]: # device deactivated / locked
                    return jsonify({
                        "success": False,
                        "error": "Device access or session revoked by administrator.",
                        "action": "wipe_and_lock"
                    }), 403
        finally:
            conn_sec.close()

        if not locations:
            return jsonify({"success": True, "inserted": 0, "msg": "No coordinates supplied"}), 200

        # Safety cap: maximum 50 points per batch to prevent memory saturation
        if len(locations) > 50:
            locations = locations[:50]

        ist = pytz.timezone("Asia/Kolkata")
        now_dt = datetime.now(timezone.utc)

        # Prepare batch tuples for execute_values
        rows_to_insert = []
        latest_pt = None

        for loc in locations:
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            if lat is None or lng is None:
                continue

            try:
                lat = float(lat)
                lng = float(lng)
            except (ValueError, TypeError):
                continue

            acc = float(loc.get("accuracy")) if loc.get("accuracy") is not None else None
            spd = float(loc.get("speed")) if loc.get("speed") is not None else 0.0
            hdg = float(loc.get("heading")) if loc.get("heading") is not None else 0.0
            bat = int(loc.get("battery_pct")) if loc.get("battery_pct") is not None else None
            chg = bool(loc.get("is_charging", False))
            act = str(loc.get("activity", "unknown"))[:20]

            rec_str = loc.get("recorded_at")
            if rec_str:
                try:
                    rec_dt = datetime.fromisoformat(rec_str.replace("Z", "+00:00"))
                except Exception:
                    rec_dt = now_dt
            else:
                rec_dt = now_dt

            point_tuple = (
                user_id,
                device_id[:64],
                lat,
                lng,
                acc,
                spd,
                hdg,
                bat,
                chg,
                act,
                rec_dt
            )
            rows_to_insert.append(point_tuple)
            latest_pt = point_tuple

        if not rows_to_insert:
            return jsonify({"success": True, "inserted": 0, "msg": "No valid coordinates"}), 200

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            # 1. High-speed multi-row insert into user_locations (< 4ms)
            execute_values(
                cur,
                """
                INSERT INTO user_locations (
                    user_id, device_id, latitude, longitude, accuracy,
                    speed, heading, battery_pct, is_charging, activity_type,
                    recorded_at
                ) VALUES %s;
                """,
                rows_to_insert
            )

            # 2. Update single-row cache in user_devices (< 2ms)
            if latest_pt:
                cur.execute("""
                    UPDATE user_devices
                    SET latest_latitude = %s,
                        latest_longitude = %s,
                        latest_speed = %s,
                        latest_heading = %s,
                        latest_accuracy = %s,
                        latest_battery_pct = %s,
                        is_charging = %s,
                        last_active = NOW(),
                        gps_status = 'active'
                    WHERE user_id = %s AND device_id = %s;
                """, (
                    latest_pt[2],  # lat
                    latest_pt[3],  # lng
                    latest_pt[5],  # spd
                    latest_pt[6],  # hdg
                    latest_pt[4],  # acc
                    latest_pt[7],  # bat
                    latest_pt[8],  # chg
                    user_id,
                    device_id[:64]
                ))
                if cur.rowcount == 0:
                    cur.execute("""
                        UPDATE user_devices
                        SET latest_latitude = %s,
                            latest_longitude = %s,
                            latest_speed = %s,
                            latest_heading = %s,
                            latest_accuracy = %s,
                            latest_battery_pct = %s,
                            is_charging = %s,
                            last_active = NOW(),
                            gps_status = 'active'
                        WHERE user_id = %s AND is_active = TRUE;
                    """, (
                        latest_pt[2],
                        latest_pt[3],
                        latest_pt[5],
                        latest_pt[6],
                        latest_pt[4],
                        latest_pt[7],
                        latest_pt[8],
                        user_id
                    ))

            conn.commit()
            return jsonify({
                "success": True,
                "inserted": len(rows_to_insert),
                "timestamp": now_dt.isoformat()
            }), 200

        except Exception as e:
            conn.rollback()
            logger.error("mobile_location_batch insert error: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Admin API: 30s AJAX Polling Endpoint (Lightweight Live Snapshot)
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/admin/fleet/status", methods=["GET"])
    def admin_fleet_status():
        """Serves 30-second AJAX polling for the web command center. Completes in < 4ms."""
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        target_uid = request.args.get("user_id", type=int)
        target_device_id = (request.args.get("device_id") or "").strip()

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            ist = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.now(ist)

            query = """
                SELECT 
                    ud.user_id,
                    u.username,
                    COALESCE(e.name, u.username) as employee_name,
                    ud.device_model,
                    ud.latest_latitude,
                    ud.latest_longitude,
                    ud.latest_speed,
                    ud.latest_heading,
                    ud.latest_accuracy,
                    ud.latest_battery_pct,
                    ud.is_charging,
                    ud.gps_status,
                    ud.last_active,
                    ud.device_id
                FROM user_devices ud
                JOIN users u ON u.id = ud.user_id
                LEFT JOIN employee e ON e.eid = u.employee_id
                WHERE ud.is_active = TRUE AND ud.device_id != 'PENDING'
            """
            params = []
            if target_uid:
                query += " AND ud.user_id = %s"
                params.append(target_uid)
            if target_device_id:
                query += " AND ud.device_id = %s"
                params.append(target_device_id)

            query += " ORDER BY ud.last_active DESC NULLS LAST;"
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            fleet = []
            for r in rows:
                uid, uname, ename, model, lat, lng, spd, hdg, acc, bat, chg, gps, last_act, dev_id = r
                
                seconds_ago = None
                presence = "offline"
                formatted_time = "Never"

                if last_act:
                    if last_act.tzinfo is None:
                        act_ist = ist.localize(last_act)
                    else:
                        act_ist = last_act.astimezone(ist)
                    
                    diff = now_ist - act_ist
                    seconds_ago = max(0, int(diff.total_seconds()))
                    formatted_time = act_ist.strftime("%I:%M:%S %p")

                    if seconds_ago < 300:
                        presence = "online"
                    elif seconds_ago < 86400:
                        presence = "active_today"

                fleet.append({
                    "user_id": uid,
                    "username": uname,
                    "employee_name": ename,
                    "device_id": dev_id,
                    "device_model": model or "Mobile Device",
                    "latitude": lat,
                    "longitude": lng,
                    "speed": spd or 0.0,
                    "heading": hdg or 0.0,
                    "accuracy": acc,
                    "battery_pct": bat,
                    "is_charging": chg or False,
                    "gps_status": gps or "active",
                    "presence": presence,
                    "seconds_ago": seconds_ago,
                    "last_active": formatted_time
                })

            return jsonify({
                "success": True,
                "timestamp": now_ist.strftime("%I:%M:%S %p"),
                "fleet": fleet
            }), 200

        except Exception as e:
            logger.error("admin_fleet_status error: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Admin API: 10-Day Route History with Douglas-Peucker Simplification
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/admin/fleet/history/<int:user_id>", methods=["GET"])
    def admin_fleet_history(user_id):
        """
        Returns simplified journey polyline and detected village stops.
        Applies Ramer-Douglas-Peucker algorithm to compress ~1200 coordinates down to ~90 points.
        """
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        ist = pytz.timezone("Asia/Kolkata")
        date_str = request.args.get("date")
        if not date_str:
            target_date = datetime.now(ist).date()
        else:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            # 1. Fetch raw coordinates for target user on target date (with optional device_id filter)
            target_device_id = (request.args.get("device_id") or "").strip()
            hist_params = [user_id, target_date]
            device_clause = ""
            if target_device_id:
                device_clause = " AND device_id = %s "
                hist_params.append(target_device_id)

            cur.execute(f"""
                SELECT latitude, longitude, speed, heading, recorded_at, battery_pct, activity_type
                FROM user_locations
                WHERE user_id = %s 
                  AND (recorded_at AT TIME ZONE 'Asia/Kolkata')::date = %s
                  {device_clause}
                ORDER BY recorded_at ASC;
            """, tuple(hist_params))
            raw_rows = cur.fetchall()

            if not raw_rows:
                return jsonify({
                    "success": True,
                    "user_id": user_id,
                    "date": target_date.strftime("%Y-%m-%d"),
                    "points": [],
                    "trips": [],
                    "stops": [],
                    "summary": {
                        "total_distance_km": 0.0,
                        "travel_minutes": 0,
                        "stop_minutes": 0,
                        "stop_count": 0
                    }
                }), 200

            # Convert to point records with localized IST timestamp
            points_for_rdp = []
            for r in raw_rows:
                lat, lng, spd, hdg, rec_at, bat, act = r
                if rec_at.tzinfo is None:
                    rec_ist = ist.localize(rec_at)
                else:
                    rec_ist = rec_at.astimezone(ist)
                points_for_rdp.append([lat, lng, spd or 0.0, hdg or 0.0, rec_ist, bat, act])

            # 2. Run Douglas-Peucker Simplification (epsilon = 0.00008 deg ~ 8.9m)
            simplified_points = douglas_peucker(points_for_rdp, epsilon=0.00008)

            # 3. Detect Stops and Trips with Centroid Clustering
            trips, stops = segment_trips_and_stops(points_for_rdp, min_stop_minutes=5, cluster_radius_km=0.08)

            # 4. High-Precision Parallel Batch Reverse Geocoding with Caching
            init_geocache_table(conn)

            coords_to_geocode = [(s["latitude"], s["longitude"]) for s in stops]
            for t in trips:
                if t.get("start_lat") is not None and t.get("start_lng") is not None:
                    coords_to_geocode.append((t["start_lat"], t["start_lng"]))
                if t.get("end_lat") is not None and t.get("end_lng") is not None:
                    coords_to_geocode.append((t["end_lat"], t["end_lng"]))

            geo_map = batch_reverse_geocode(conn, cur, coords_to_geocode, fallback_nearest_village_func=find_nearest_village)

            for s in stops:
                k = (round(float(s["latitude"]), 4), round(float(s["longitude"]), 4))
                geo = geo_map.get(k, {})
                s["place_name"] = geo.get("place_name") or "Recorded Location"
                s["place_subtitle"] = geo.get("subtitle") or ""
                s["village_name"] = s["place_name"]
                s["arrival_formatted"] = s["arrival_time"].strftime("%I:%M %p")
                s["departure_formatted"] = s["departure_time"].strftime("%I:%M %p")

            # Format and geocode trip start & end points
            total_distance = 0.0
            total_travel_minutes = 0
            for t in trips:
                total_distance += t["distance_km"]
                total_travel_minutes += t["duration_minutes"]
                t["start_formatted"] = t["start_time"].strftime("%I:%M %p")
                t["end_formatted"] = t["end_time"].strftime("%I:%M %p")
                
                k_start = (round(float(t["start_lat"]), 4), round(float(t["start_lng"]), 4)) if t.get("start_lat") else None
                k_end = (round(float(t["end_lat"]), 4), round(float(t["end_lng"]), 4)) if t.get("end_lat") else None
                start_geo = geo_map.get(k_start, {}) if k_start else {}
                end_geo = geo_map.get(k_end, {}) if k_end else {}
                t["start_location"] = start_geo.get("place_name") or "Trip Start"
                t["end_location"] = end_geo.get("place_name") or "Trip Destination"

            total_stop_minutes = sum(s["duration_minutes"] for s in stops)

            # Build unified chronological timeline (Interleaving Trips and Stops)
            timeline_items = []
            driving_km = 0.0
            driving_mins = 0
            motorcycle_km = 0.0
            motorcycle_mins = 0

            for t in trips:
                is_car = (t.get("avg_speed_kmh", 0) > 35.0)
                mode = "driving" if is_car else "motorcycling"
                t["mode"] = mode
                if is_car:
                    driving_km += t["distance_km"]
                    driving_mins += t["duration_minutes"]
                else:
                    motorcycle_km += t["distance_km"]
                    motorcycle_mins += t["duration_minutes"]

                timeline_items.append({
                    "type": "trip",
                    "_sort_time": t["start_time"],
                    "trip_number": t.get("trip_number", 1),
                    "mode": mode,
                    "title": "Driving" if is_car else "Motorcycling",
                    "subtitle": f"{t.get('start_location', 'Start')} → {t.get('end_location', 'End')}",
                    "distance_km": t["distance_km"],
                    "duration_minutes": t["duration_minutes"],
                    "time_range": f"{t['start_formatted']} – {t['end_formatted']}",
                    "icon": "car" if is_car else "motorcycle",
                    "avg_speed": t.get("avg_speed_kmh", 0.0),
                    "coords": t.get("coords", []),
                    "start_location": t.get("start_location"),
                    "end_location": t.get("end_location"),
                    "start_lat": t.get("start_lat"),
                    "start_lng": t.get("start_lng"),
                    "end_lat": t.get("end_lat"),
                    "end_lng": t.get("end_lng"),
                    "start_time_str": t["start_formatted"],
                    "end_time_str": t["end_formatted"]
                })

            stop_icons = ["store", "building", "house", "hospital", "landmark", "bag-shopping", "briefcase"]
            for idx, s in enumerate(stops):
                place_name = s.get("place_name") or s.get("village_name") or f"Location Visit #{idx + 1}"
                sub = f"Stayed {s['duration_minutes']} min"
                if s.get("place_subtitle"):
                    sub = f"{s['place_subtitle']} • Stayed {s['duration_minutes']} min"

                timeline_items.append({
                    "type": "stop",
                    "_sort_time": s["arrival_time"],
                    "stop_index": idx + 1,
                    "title": place_name,
                    "subtitle": sub,
                    "arrival": s["arrival_formatted"],
                    "departure": s["departure_formatted"],
                    "duration_minutes": s["duration_minutes"],
                    "latitude": s["latitude"],
                    "longitude": s["longitude"],
                    "icon": stop_icons[idx % len(stop_icons)]
                })

            # Sort strictly chronologically by timestamp
            timeline_items.sort(key=lambda item: item["_sort_time"])
            for item in timeline_items:
                del item["_sort_time"]

            timeline = timeline_items

            # Cleanup non-serializable datetime objects in trips and stops
            for s in stops:
                if "arrival_time" in s:
                    del s["arrival_time"]
                if "departure_time" in s:
                    del s["departure_time"]

            for t in trips:
                if "start_time" in t:
                    del t["start_time"]
                if "end_time" in t:
                    del t["end_time"]

            # Export simplified polyline as lightweight [lat, lng, speed, heading, time_str, bat]
            export_points = [
                [
                    round(p[0], 6),
                    round(p[1], 6),
                    round(p[2], 1),
                    round(p[3], 1),
                    p[4].strftime("%I:%M %p"),
                    p[5]
                ]
                for p in simplified_points
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "date": target_date.strftime("%Y-%m-%d"),
                "raw_count": len(raw_rows),
                "simplified_count": len(export_points),
                "compression_ratio": f"{round((1.0 - (len(export_points)/max(1, len(raw_rows)))) * 100, 1)}%",
                "points": export_points,
                "trips": trips,
                "stops": stops,
                "summary": {
                    "total_distance_km": round(total_distance, 2),
                    "travel_minutes": total_travel_minutes,
                    "stop_minutes": total_stop_minutes,
                    "stop_count": len(stops),
                    "driving_km": round(driving_km, 1),
                    "driving_minutes": driving_mins,
                    "motorcycle_km": round(motorcycle_km, 1),
                    "motorcycle_minutes": motorcycle_mins,
                    "visits_count": len(stops),
                    "start_time": points_for_rdp[0][4].strftime("%I:%M %p"),
                    "last_time": points_for_rdp[-1][4].strftime("%I:%M %p"),
                    "battery_start": points_for_rdp[0][5],
                    "battery_end": points_for_rdp[-1][5]
                },
                "timeline": timeline
            }), 200

        except Exception as e:
            logger.error("admin_fleet_history error: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Admin Actions: Force Logout & Credentials Lock
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/admin/mobile_users/force_logout", methods=["POST"])
    def admin_force_logout():
        """Immediately revokes mobile session token and unbinds hardware."""
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE users 
                SET session_revoked_at = NOW() 
                WHERE id = %s;
            """, (user_id,))
            cur.execute("""
                UPDATE user_devices 
                SET is_active = FALSE 
                WHERE user_id = %s;
            """, (user_id,))
            conn.commit()
            return jsonify({"success": True, "message": "User session revoked and device logged out."}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    @app.route("/api/admin/mobile_users/lock_device", methods=["POST"])
    def admin_mobile_users_lock_device():
        """Locks or unlocks an individual physical device by hardware device_id."""
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        device_id = data.get("device_id")
        should_lock = bool(data.get("is_locked", True))

        if not user_id or not device_id:
            return jsonify({"success": False, "error": "user_id and device_id are required"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                ALTER TABLE user_devices ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;
            """)
            if should_lock:
                cur.execute("""
                    UPDATE user_devices 
                    SET is_locked = TRUE, is_active = FALSE 
                    WHERE user_id = %s AND device_id = %s;
                """, (user_id, device_id))
            else:
                cur.execute("""
                    UPDATE user_devices 
                    SET is_locked = FALSE, is_active = TRUE 
                    WHERE user_id = %s AND device_id = %s;
                """, (user_id, device_id))

            conn.commit()
            action_str = "locked" if should_lock else "unlocked"
            return jsonify({
                "success": True,
                "message": f"Hardware device {action_str} successfully. {'Login prohibited for this device.' if should_lock else 'Device can now be used.'}",
                "is_locked": should_lock
            }), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    @app.route("/api/admin/mobile_users/toggle_lock", methods=["POST"])
    def admin_toggle_lock():
        """Toggles user account active/locked status."""
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        new_status = data.get("is_active")

        if user_id is None or new_status is None:
            return jsonify({"success": False, "error": "user_id and is_active are required"}), 400

        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE users 
                SET is_active = %s 
                WHERE id = %s;
            """, (bool(new_status), user_id))
            if not new_status:
                cur.execute("""
                    UPDATE user_devices 
                    SET is_active = FALSE 
                    WHERE user_id = %s;
                """, (user_id,))
            conn.commit()
            return jsonify({"success": True, "is_active": bool(new_status)}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Admin OTA: Inspect Uploaded APK Metadata
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/admin/app/inspect_apk", methods=["POST"])
    def admin_inspect_apk():
        """Inspects uploaded APK manifest extracting version_name and version_code."""
        if not is_admin():
            return jsonify({"success": False, "error": "Admin access required"}), 403

        if "apk_file" not in request.files:
            return jsonify({"success": False, "error": "No apk_file in request"}), 400

        file = request.files["apk_file"]
        if not file or not file.filename or not file.filename.endswith(".apk"):
            return jsonify({"success": False, "error": "Invalid APK file"}), 400

        # Save temporarily to inspect metadata
        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)

        try:
            metadata = {}
            if apk_signing and hasattr(apk_signing, "extract_apk_metadata"):
                metadata = apk_signing.extract_apk_metadata(tmp_path)

            v_name = metadata.get("version_name") or ""
            v_code = int(metadata.get("version_code") or 0)
            pkg_name = metadata.get("package_name") or "com.sdfinance.mobile"
            min_sdk = int(metadata.get("min_sdk") or 0)

            return jsonify({
                "success": True,
                "version_name": v_name,
                "version_code": v_code,
                "min_version_code": v_code,
                "min_sdk": min_sdk,
                "package_name": pkg_name,
                "sha256": metadata.get("sha256", ""),
                "size_bytes": os.path.getsize(tmp_path)
            }), 200
        except Exception as e:
            logger.error("inspect_apk error: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Admin OTA: QR Code Generator
    # ──────────────────────────────────────────────────────────────────────────
    @app.route("/api/admin/app/qr/<version>", methods=["GET"])
    def admin_app_qr(version):
        """Generates a downloadable QR code linking to the mobile APK direct download."""
        if not is_admin():
            return jsonify({"error": "Admin access required"}), 403

        if not qrcode:
            return jsonify({"error": "qrcode package not installed"}), 500

        download_url = f"https://sivadurga.in/api/mobile/app/download/{version}"
        img = qrcode.make(download_url)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)

        if request.args.get("raw") == "1" or request.accept_mimetypes.best == "image/png":
            return send_file(buf, mimetype="image/png")

        import base64
        b64_qr = base64.b64encode(buf.getvalue()).decode("ascii")
        return jsonify({
            "success": True,
            "version": version,
            "download_url": download_url,
            "qr_data_url": f"data:image/png;base64,{b64_qr}"
        }), 200
