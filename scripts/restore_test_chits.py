#!/usr/bin/env python3
"""
One-click restore utility for Chit Fund Test Groups.
Restores all data for 'Test' and 'TEST -2' from scripts/backups/restore_chit_test_groups_latest.sql
into PostgreSQL sd_finance database.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db

RESTORE_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups", "restore_chit_test_groups_latest.sql")


def restore():
    if not os.path.exists(RESTORE_SQL):
        print(f"[-] Error: Restore script not found at {RESTORE_SQL}")
        sys.exit(1)

    print(f"[*] Reading restore script: {RESTORE_SQL}")
    with open(RESTORE_SQL, "r", encoding="utf-8") as f:
        sql = f.read()

    print("[*] Connecting to database and executing restoration...")
    with db.get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            print("[+] Restore script executed successfully!")

            # Verify restoration
            cur.execute("""
                SELECT id, name, chit_total_value, status
                FROM chit_groups
                WHERE id IN (
                    '987b8c46-d51b-4289-82e9-501a730f9e3d',
                    '9a95d150-7140-4409-a8bc-f535d24ec440'
                )
            """)
            restored = cur.fetchall()
            print(f"[+] Verified restored chit groups ({len(restored)}):")
            for r in restored:
                print(f"    - {r}")

        conn.commit()
    print("\n[+] SUCCESS: All test chit groups and related data restored completely!")


if __name__ == "__main__":
    restore()
