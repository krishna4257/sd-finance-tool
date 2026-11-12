#!/usr/bin/env python3
"""
Pre-deletion backup utility for Chit Fund Test Groups.
Exports all rows from:
  - chit_groups
  - chit_memberships
  - chit_schedules
  - chit_installments
  - chit_payments
  - chit_audit_logs
belonging to test chit groups ('Test' and 'TEST -2') into:
  1. A structured JSON snapshot.
  2. A standalone reversible SQL restore script with ON CONFLICT DO NOTHING.
"""

import os
import sys
import json
import uuid
from datetime import datetime, date
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db

TEST_IDS = (
    "987b8c46-d51b-4289-82e9-501a730f9e3d",  # 'Test'
    "9a95d150-7140-4409-a8bc-f535d24ec440",  # 'TEST -2'
)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def serialize_val(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, uuid.UUID):
        return str(val)
    return val


def sql_quote(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    if isinstance(val, (dict, list)):
        dumped = json.dumps(val, ensure_ascii=False).replace("'", "''")
        return f"'{dumped}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"


def run_backup():
    with db.get_pg_connection() as conn:
        with conn.cursor() as cur:
            backup_data = {}
            sql_lines = [
                "-- ========================================================",
                "-- REVERSIBLE RESTORE SCRIPT FOR TEST CHIT GROUPS",
                f"-- Generated: {datetime.now().isoformat()}",
                "-- Target Database: sd_finance",
                "-- Groups: 'Test' (987b8c46-d51b-4289-82e9-501a730f9e3d)",
                "--         'TEST -2' (9a95d150-7140-4409-a8bc-f535d24ec440)",
                "-- ========================================================",
                "BEGIN;\n"
            ]

            # 1. chit_groups
            cur.execute("""
                SELECT * FROM chit_groups WHERE id IN %s ORDER BY created_at
            """, (TEST_IDS,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            backup_data["chit_groups"] = {
                "columns": cols,
                "rows": [[serialize_val(c) for c in r] for r in rows]
            }
            sql_lines.append(f"-- 1. Restore chit_groups ({len(rows)} records)")
            for r in rows:
                val_strs = [sql_quote(v) for v in r]
                sql_lines.append(f"INSERT INTO chit_groups ({', '.join(cols)}) VALUES ({', '.join(val_strs)}) ON CONFLICT (id) DO NOTHING;")
            sql_lines.append("")

            # 2. chit_memberships
            cur.execute("""
                SELECT * FROM chit_memberships WHERE chit_group_id IN %s ORDER BY created_at
            """, (TEST_IDS,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            backup_data["chit_memberships"] = {
                "columns": cols,
                "rows": [[serialize_val(c) for c in r] for r in rows]
            }
            sql_lines.append(f"-- 2. Restore chit_memberships ({len(rows)} records)")
            for r in rows:
                val_strs = [sql_quote(v) for v in r]
                sql_lines.append(f"INSERT INTO chit_memberships ({', '.join(cols)}) VALUES ({', '.join(val_strs)}) ON CONFLICT (id) DO NOTHING;")
            sql_lines.append("")

            # 3. chit_schedules
            cur.execute("""
                SELECT * FROM chit_schedules WHERE chit_group_id IN %s ORDER BY chit_group_id, month_index
            """, (TEST_IDS,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            backup_data["chit_schedules"] = {
                "columns": cols,
                "rows": [[serialize_val(c) for c in r] for r in rows]
            }
            sql_lines.append(f"-- 3. Restore chit_schedules ({len(rows)} records)")
            for r in rows:
                val_strs = [sql_quote(v) for v in r]
                sql_lines.append(f"INSERT INTO chit_schedules ({', '.join(cols)}) VALUES ({', '.join(val_strs)}) ON CONFLICT (id) DO NOTHING;")
            sql_lines.append("")

            # 4. chit_installments
            cur.execute("""
                SELECT * FROM chit_installments WHERE chit_group_id IN %s ORDER BY chit_group_id, month_index
            """, (TEST_IDS,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            backup_data["chit_installments"] = {
                "columns": cols,
                "rows": [[serialize_val(c) for c in r] for r in rows]
            }
            sql_lines.append(f"-- 4. Restore chit_installments ({len(rows)} records)")
            for r in rows:
                val_strs = [sql_quote(v) for v in r]
                sql_lines.append(f"INSERT INTO chit_installments ({', '.join(cols)}) VALUES ({', '.join(val_strs)}) ON CONFLICT (id) DO NOTHING;")
            sql_lines.append("")

            # 5. chit_payments
            cur.execute("""
                SELECT p.* FROM chit_payments p
                JOIN chit_installments i ON p.installment_id = i.id
                WHERE i.chit_group_id IN %s
                ORDER BY p.payment_date, p.created_at
            """, (TEST_IDS,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            backup_data["chit_payments"] = {
                "columns": cols,
                "rows": [[serialize_val(c) for c in r] for r in rows]
            }
            sql_lines.append(f"-- 5. Restore chit_payments ({len(rows)} records)")
            for r in rows:
                val_strs = [sql_quote(v) for v in r]
                sql_lines.append(f"INSERT INTO chit_payments ({', '.join(cols)}) VALUES ({', '.join(val_strs)}) ON CONFLICT (id) DO NOTHING;")
            sql_lines.append("")

            # 6. chit_audit_logs
            cur.execute("""
                SELECT * FROM chit_audit_logs
                WHERE group_id IN %s OR entity_id IN %s
                ORDER BY created_at
            """, (TEST_IDS, TEST_IDS))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            backup_data["chit_audit_logs"] = {
                "columns": cols,
                "rows": [[serialize_val(c) for c in r] for r in rows]
            }
            sql_lines.append(f"-- 6. Restore chit_audit_logs ({len(rows)} records)")
            for r in rows:
                val_strs = [sql_quote(v) for v in r]
                sql_lines.append(f"INSERT INTO chit_audit_logs ({', '.join(cols)}) VALUES ({', '.join(val_strs)}) ON CONFLICT (id) DO NOTHING;")
            sql_lines.append("\nCOMMIT;")

            # Write JSON backup
            json_file = os.path.join(BACKUP_DIR, f"chit_test_backup_{timestamp}.json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            print(f"[+] JSON Snapshot created: {json_file}")
            print(f"    - chit_groups: {len(backup_data['chit_groups']['rows'])} records")
            print(f"    - chit_memberships: {len(backup_data['chit_memberships']['rows'])} records")
            print(f"    - chit_schedules: {len(backup_data['chit_schedules']['rows'])} records")
            print(f"    - chit_installments: {len(backup_data['chit_installments']['rows'])} records")
            print(f"    - chit_payments: {len(backup_data['chit_payments']['rows'])} records")
            print(f"    - chit_audit_logs: {len(backup_data['chit_audit_logs']['rows'])} records")

            # Write SQL restore script
            sql_file = os.path.join(BACKUP_DIR, f"restore_chit_test_groups_{timestamp}.sql")
            with open(sql_file, "w", encoding="utf-8") as f:
                f.write("\n".join(sql_lines))
            print(f"[+] SQL Reversible Restore Script created: {sql_file}")

            # Also create standard latest symlink/copy for ease of access
            latest_json = os.path.join(BACKUP_DIR, "chit_test_backup_latest.json")
            latest_sql = os.path.join(BACKUP_DIR, "restore_chit_test_groups_latest.sql")
            with open(latest_json, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            with open(latest_sql, "w", encoding="utf-8") as f:
                f.write("\n".join(sql_lines))
            print(f"[+] Latest copies saved as {latest_json} and {latest_sql}")

            return {
                "json_file": json_file,
                "sql_file": sql_file,
                "counts": {
                    "chit_groups": len(backup_data["chit_groups"]["rows"]),
                    "chit_memberships": len(backup_data["chit_memberships"]["rows"]),
                    "chit_schedules": len(backup_data["chit_schedules"]["rows"]),
                    "chit_installments": len(backup_data["chit_installments"]["rows"]),
                    "chit_payments": len(backup_data["chit_payments"]["rows"]),
                    "chit_audit_logs": len(backup_data["chit_audit_logs"]["rows"]),
                }
            }


if __name__ == "__main__":
    run_backup()
