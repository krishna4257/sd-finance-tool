#!/usr/bin/env python3
"""
Safe deletion utility for Chit Fund Test Groups.
Removes:
  - 'Test' (987b8c46-d51b-4289-82e9-501a730f9e3d)
  - 'TEST -2' (9a95d150-7140-4409-a8bc-f535d24ec440)
and their direct child records (payments, installments, schedules, memberships, audit logs).
Preserves ALL master chit members and ALL other active chit groups.
Supports --dry-run (default is dry-run unless --commit is passed).
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db

TEST_IDS = (
    "987b8c46-d51b-4289-82e9-501a730f9e3d",  # 'Test'
    "9a95d150-7140-4409-a8bc-f535d24ec440",  # 'TEST -2'
)

EXPECTED_COUNTS = {
    "chit_payments": 10,
    "chit_installments": 575,
    "chit_schedules": 45,
    "chit_memberships": 28,
    "chit_audit_logs": 13,
    "chit_groups": 2,
}


def delete_test_chits(commit=False):
    mode = "COMMIT" if commit else "DRY-RUN (ROLLBACK)"
    print(f"[*] Starting test chit groups removal in mode: {mode}")

    with db.get_pg_connection() as conn:
        with conn.cursor() as cur:
            # Check pre-deletion groups
            cur.execute("SELECT count(*) FROM chit_groups")
            total_groups_before = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM chit_members")
            total_members_before = cur.fetchone()[0]

            print(f"[*] Pre-deletion total chit groups: {total_groups_before}")
            print(f"[*] Pre-deletion total master members: {total_members_before}")

            # 1. Delete chit_payments
            cur.execute("""
                DELETE FROM chit_payments
                WHERE installment_id IN (
                    SELECT id FROM chit_installments WHERE chit_group_id IN %s
                )
            """, (TEST_IDS,))
            del_payments = cur.rowcount
            print(f"    - Deleted chit_payments: {del_payments} (expected {EXPECTED_COUNTS['chit_payments']})")

            # 2. Delete chit_installments
            cur.execute("""
                DELETE FROM chit_installments
                WHERE chit_group_id IN %s
            """, (TEST_IDS,))
            del_installments = cur.rowcount
            print(f"    - Deleted chit_installments: {del_installments} (expected {EXPECTED_COUNTS['chit_installments']})")

            # 3. Delete chit_schedules
            cur.execute("""
                DELETE FROM chit_schedules
                WHERE chit_group_id IN %s
            """, (TEST_IDS,))
            del_schedules = cur.rowcount
            print(f"    - Deleted chit_schedules: {del_schedules} (expected {EXPECTED_COUNTS['chit_schedules']})")

            # 4. Delete chit_memberships
            cur.execute("""
                DELETE FROM chit_memberships
                WHERE chit_group_id IN %s
            """, (TEST_IDS,))
            del_memberships = cur.rowcount
            print(f"    - Deleted chit_memberships: {del_memberships} (expected {EXPECTED_COUNTS['chit_memberships']})")

            # 5. Delete chit_audit_logs
            cur.execute("""
                DELETE FROM chit_audit_logs
                WHERE group_id IN %s OR entity_id IN %s
            """, (TEST_IDS, TEST_IDS))
            del_audit_logs = cur.rowcount
            print(f"    - Deleted chit_audit_logs: {del_audit_logs} (expected {EXPECTED_COUNTS['chit_audit_logs']})")

            # 6. Delete chit_groups
            cur.execute("""
                DELETE FROM chit_groups
                WHERE id IN %s
            """, (TEST_IDS,))
            del_groups = cur.rowcount
            print(f"    - Deleted chit_groups: {del_groups} (expected {EXPECTED_COUNTS['chit_groups']})")

            # Verify integrity
            cur.execute("SELECT count(*) FROM chit_groups")
            total_groups_after = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM chit_members")
            total_members_after = cur.fetchone()[0]

            print(f"[*] Post-deletion total chit groups: {total_groups_after}")
            print(f"[*] Post-deletion total master members: {total_members_after}")

            # Invariant assertions
            assert total_groups_before - total_groups_after == 2, "Expected exactly 2 groups removed!"
            assert total_members_before == total_members_after, "Master chit_members table must NOT lose any members!"

            if commit:
                conn.commit()
                print("[+] TRANSACTION COMMITTED SUCCESSFULLY!")
            else:
                conn.rollback()
                print("[*] DRY-RUN COMPLETE - TRANSACTION ROLLED BACK SAFELY.")


if __name__ == "__main__":
    should_commit = "--commit" in sys.argv
    delete_test_chits(commit=should_commit)
