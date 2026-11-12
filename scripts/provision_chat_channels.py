#!/usr/bin/env python3
"""
SD Finance: Chat Channel Provisioning Utility
File: SD_Accounting_Tool/scripts/provision_chat_channels.py

Automatically provisions:
1. "Company Announcements" broadcast channel (Admin/Mgmt publish, Staff listen).
2. Direct 1-on-1 channels between Leadership users (Admin, Superadmin, Mgmt).
3. Direct 1-on-1 channels between each Leadership user and every Field Staff member.
4. Synchronizes user phone numbers into user_notification_settings for NotifKit.
5. Strictly prevents direct channels between two field staff members (RBAC rule).
"""

import os
import sys
import argparse
import psycopg2

# Add parent directory to sys.path so we can import db
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from db import get_pg_connection


def apply_migration(conn):
    """Executes phase6_internal_chat.sql to guarantee tables exist."""
    migration_path = os.path.join(APP_DIR, "sql_scripts", "phase6_internal_chat.sql")
    if not os.path.isfile(migration_path):
        raise FileNotFoundError(f"Migration file not found at: {migration_path}")
    
    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()

    print("[*] Applying database migration: phase6_internal_chat.sql ...")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("[+] Migration successfully verified/applied.")


def ensure_direct_channel(cur, user_a_id, user_a_role, user_b_id, user_b_role, admin_id):
    """Checks if a direct channel exists between user A and user B, creating one if not."""
    cur.execute("""
        SELECT c.id 
        FROM chat_channels c
        JOIN chat_channel_members m1 ON m1.channel_id = c.id AND m1.user_id = %s
        JOIN chat_channel_members m2 ON m2.channel_id = c.id AND m2.user_id = %s
        WHERE c.channel_type = 'direct';
    """, (user_a_id, user_b_id))
    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO chat_channels (channel_type, created_by, is_active)
            VALUES ('direct', %s, TRUE)
            RETURNING id;
        """, (admin_id,))
        new_channel_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO chat_channel_members (channel_id, user_id, role)
            VALUES (%s, %s, %s);
        """, (new_channel_id, user_a_id, user_a_role))

        cur.execute("""
            INSERT INTO chat_channel_members (channel_id, user_id, role)
            VALUES (%s, %s, %s);
        """, (new_channel_id, user_b_id, user_b_role))

        return True
    return False


def provision_channels(conn):
    """Provisions broadcast, leadership-to-leadership, and leadership-to-staff channels."""
    with conn.cursor() as cur:
        # 1. Fetch Leadership (Admin, Superadmin, Mgmt)
        cur.execute("""
            SELECT 
                u.id, 
                u.username, 
                COALESCE(e.name, u.username) AS display_name, 
                LOWER(COALESCE(e.level, 'mgmt')) AS level,
                e.phone_number
            FROM users u
            LEFT JOIN employee e ON e.eid = u.employee_id
            WHERE u.is_active = TRUE 
              AND (
                  LOWER(COALESCE(e.level, '')) IN ('admin', 'superadmin', 'mgmt', 'management') 
                  OR LOWER(u.username) IN ('admin', 'superadmin')
              )
            ORDER BY u.id ASC;
        """)
        leadership_users = cur.fetchall()

        if not leadership_users:
            print("[-] Warning: No active Admin or Management users found. Cannot provision channels.")
            return

        primary_admin = leadership_users[0]
        admin_id = primary_admin[0]
        print(f"[*] Found {len(leadership_users)} leadership user(s):")
        for lu in leadership_users:
            clean_lvl = lu[3]
            role_tag = 'SUPER ADMIN' if 'superadmin' in clean_lvl else ('ADMIN' if 'admin' in clean_lvl else 'MGMT')
            print(f"    - ID {lu[0]}: {lu[2]} ({lu[1]}) [Role: {role_tag}]")

        # 2. Fetch Field Staff
        cur.execute("""
            SELECT 
                u.id, 
                u.username, 
                COALESCE(e.name, u.username) AS display_name, 
                LOWER(COALESCE(e.level, 'staff')) AS level,
                e.phone_number
            FROM users u
            LEFT JOIN employee e ON e.eid = u.employee_id
            WHERE u.is_active = TRUE 
              AND LOWER(COALESCE(e.level, '')) NOT IN ('admin', 'superadmin', 'mgmt', 'management')
              AND LOWER(u.username) NOT IN ('admin', 'superadmin')
            ORDER BY u.id ASC;
        """)
        staff_users = cur.fetchall()
        print(f"[*] Found {len(staff_users)} active field staff user(s).")

        # 3. Provision or Retrieve Company Announcements Broadcast Channel
        cur.execute("""
            SELECT id FROM chat_channels 
            WHERE channel_type = 'broadcast' AND name = 'Company Announcements'
            LIMIT 1;
        """)
        broadcast_row = cur.fetchone()
        if broadcast_row:
            broadcast_id = broadcast_row[0]
            print(f"[+] Broadcast channel exists: 'Company Announcements' (ID: {broadcast_id})")
        else:
            cur.execute("""
                INSERT INTO chat_channels (channel_type, name, created_by, is_active)
                VALUES ('broadcast', 'Company Announcements', %s, TRUE)
                RETURNING id;
            """, (admin_id,))
            broadcast_id = cur.fetchone()[0]
            print(f"[+] Created new broadcast channel: 'Company Announcements' (ID: {broadcast_id})")

        # Ensure all leadership members are added as admin/mgmt
        for lead in leadership_users:
            lead_id = lead[0]
            role = 'admin' if any(k in lead[3] for k in ('admin', 'superadmin')) else 'mgmt'
            cur.execute("""
                INSERT INTO chat_channel_members (channel_id, user_id, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (channel_id, user_id) DO NOTHING;
            """, (broadcast_id, lead_id, role))

        # Ensure all field staff are added to announcements as staff
        for staff in staff_users:
            staff_id = staff[0]
            cur.execute("""
                INSERT INTO chat_channel_members (channel_id, user_id, role)
                VALUES (%s, %s, 'staff')
                ON CONFLICT (channel_id, user_id) DO NOTHING;
            """, (broadcast_id, staff_id))

        # 4. Provision Direct Channels Between Leadership Users Themselves (Admin <-> Mgmt, Admin <-> Admin)
        leadership_direct_count = 0
        for i in range(len(leadership_users)):
            for j in range(i + 1, len(leadership_users)):
                user_a = leadership_users[i]
                user_b = leadership_users[j]
                role_a = 'admin' if any(k in user_a[3] for k in ('admin', 'superadmin')) else 'mgmt'
                role_b = 'admin' if any(k in user_b[3] for k in ('admin', 'superadmin')) else 'mgmt'
                
                if ensure_direct_channel(cur, user_a[0], role_a, user_b[0], role_b, admin_id):
                    leadership_direct_count += 1

        print(f"[+] Provisioned {leadership_direct_count} new direct channel(s) between Leadership users.")

        # 5. Provision Direct Channels Between EVERY Leadership User and EVERY Field Staff Member
        staff_direct_count = 0
        for lead in leadership_users:
            lead_id = lead[0]
            lead_role = 'admin' if any(k in lead[3] for k in ('admin', 'superadmin')) else 'mgmt'

            for staff in staff_users:
                staff_id = staff[0]
                if ensure_direct_channel(cur, lead_id, lead_role, staff_id, 'staff', admin_id):
                    staff_direct_count += 1

        print(f"[+] Provisioned {staff_direct_count} new direct staff-to-leadership channel(s).")

        # 6. Populate Notification Settings for NotifKit
        all_users = leadership_users + staff_users
        notif_upserted = 0
        for u in all_users:
            uid = u[0]
            phone = (u[4] or "").strip()
            cur.execute("""
                INSERT INTO user_notification_settings (user_id, phone_number)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET 
                    phone_number = COALESCE(NULLIF(EXCLUDED.phone_number, ''), user_notification_settings.phone_number),
                    updated_at = NOW();
            """, (uid, phone if phone else None))
            notif_upserted += 1

        print(f"[+] Synchronized {notif_upserted} user notification profile(s).")

    conn.commit()
    print("[✓] Provisioning complete: Leadership can now message everyone (admins, mgmt, and staff)!")


def main():
    parser = argparse.ArgumentParser(description="Provision SD Finance internal chat channels and notification profiles.")
    parser.add_argument("--migrate", action="store_true", help="Execute phase6_internal_chat.sql before provisioning.")
    args = parser.parse_args()

    try:
        conn = get_pg_connection()
        if args.migrate:
            apply_migration(conn)
        provision_channels(conn)
    except Exception as e:
        print(f"[-] Error executing provisioning: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
