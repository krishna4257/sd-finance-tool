import unittest
from app import app
import db
import chit_calc_engine as ce

class TestPayoutDeletion(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_delete_payout_on_clean_schedule_returns_404(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_admin'
            sess['username'] = 'test_admin'
            sess['role'] = 'admin'
        
        # Month 10 on group A1-25M-5L has no payout
        chit_id = 'd9650e3e-425d-4561-a9d6-bff2a97ae9c3'
        res = self.client.delete(f'/chit/api/chitgroups/{chit_id}/month/10/payout', base_url='https://localhost')
        self.assertEqual(res.status_code, 404)

    def test_multi_recipient_payout_isolation_and_deletion(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_admin'
            sess['username'] = 'test_admin'
            sess['role'] = 'admin'

        chit_id = '987b8c46-d51b-4289-82e9-501a730f9e3d'
        # Clean slate for Month 8
        self.client.delete(f'/chit/api/chitgroups/{chit_id}/month/8/payout', base_url='https://localhost')

        # Get memberships for Karri and Kovvuri
        conn = db.get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT ms.id, m.full_name, ms.share_units
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s AND ms.has_lifted = FALSE
            ORDER BY ms.ticket_number ASC;
        """, (chit_id,))
        members = cur.fetchall()
        cur.close()
        conn.close()

        karri_row = next(m for m in members if 'KARRI' in m[1].upper())
        kovvuri_row = next(m for m in members if 'DURGA' in m[1].upper())

        karri_id = str(karri_row[0])
        kovvuri_id = str(kovvuri_row[0])
        kovvuri_shares = float(kovvuri_row[2])

        # 1. Record Karri (1 share)
        p1 = self.client.post(f'/chit/api/chitgroups/{chit_id}/month/8/payout', json={
            'membership_id': karri_id,
            'share_count': 1.0,
            'payout_date': '2026-11-05',
            'payout_status': 'paid'
        }, base_url='https://localhost')
        self.assertEqual(p1.status_code, 200)

        # 2. Record Kovvuri (using available shares)
        p2 = self.client.post(f'/chit/api/chitgroups/{chit_id}/month/8/payout', json={
            'membership_id': kovvuri_id,
            'share_count': kovvuri_shares,
            'payout_date': '2026-11-05',
            'payout_status': 'paid'
        }, base_url='https://localhost')
        self.assertEqual(p2.status_code, 200)

        # 3. Verify summary isolation
        summary_resp = self.client.get(f'/chit/api/chitgroups/{chit_id}/payouts-summary', base_url='https://localhost')
        self.assertEqual(summary_resp.status_code, 200)
        months = summary_resp.get_json()['months']
        m8 = next(m for m in months if m['month_index'] == 8)

        self.assertIn(m8['amount_received'], (360000.0, 1080000.0))
        self.assertEqual(len(m8['recipients']), 2)

        karri_rec = next(r for r in m8['recipients'] if r['membership_id'] == karri_id)
        kovvuri_rec = next(r for r in m8['recipients'] if r['membership_id'] == kovvuri_id)

        self.assertEqual(karri_rec['payout_amount'], 360000.0)
        self.assertEqual(kovvuri_rec['payout_amount'], 360000.0 * kovvuri_shares)

        # 4. Delete Kovvuri individually
        del_kovvuri = self.client.delete(f'/chit/api/chitgroups/{chit_id}/month/8/payout?membership_id={kovvuri_id}', base_url='https://localhost')
        self.assertEqual(del_kovvuri.status_code, 200)

        summary_after_del = self.client.get(f'/chit/api/chitgroups/{chit_id}/payouts-summary', base_url='https://localhost')
        m8_after = next(m for m in summary_after_del.get_json()['months'] if m['month_index'] == 8)
        self.assertEqual(len(m8_after['recipients']), 1)
        self.assertEqual(m8_after['recipients'][0]['membership_id'], karri_id)
        self.assertEqual(m8_after['recipients'][0]['payout_amount'], 360000.0)

        # 5. Delete Karri (the last remaining)
        del_karri = self.client.delete(f'/chit/api/chitgroups/{chit_id}/month/8/payout?membership_id={karri_id}', base_url='https://localhost')
        self.assertEqual(del_karri.status_code, 200)

        summary_final = self.client.get(f'/chit/api/chitgroups/{chit_id}/payouts-summary', base_url='https://localhost')
        m8_final = next(m for m in summary_final.get_json()['months'] if m['month_index'] == 8)
        self.assertFalse(m8_final['has_payout'])
        self.assertEqual(len(m8_final['recipients']), 0)
        self.assertEqual(m8_final['amount_received'], 360000.0)


    def test_split_share_payout_deletion_foreign_key_safety(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_admin'
            sess['username'] = 'test_admin'
            sess['role'] = 'admin'

        chit_id = '987b8c46-d51b-4289-82e9-501a730f9e3d'
        # Clean Month 7 first
        self.client.delete(f'/chit/api/chitgroups/{chit_id}/month/7/payout', base_url='https://localhost')

        # Find Kovvuri Durga Krishna Reddy (has 3 shares on Ticket 5)
        conn = db.get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT ms.id, ms.share_units
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s AND m.full_name ILIKE %s;
        """, (chit_id, '%Durga Krishna%'))
        kovvuri_row = cur.fetchone()
        cur.close()
        conn.close()

        kovvuri_id = str(kovvuri_row[0])
        initial_shares = float(kovvuri_row[1])

        # Record payout for only 1 share
        res_post = self.client.post(f'/chit/api/chitgroups/{chit_id}/month/7/payout', json={
            'membership_id': kovvuri_id,
            'share_count': 1.0,
            'payout_date': '2026-11-05',
            'payout_status': 'paid'
        }, base_url='https://localhost')
        self.assertEqual(res_post.status_code, 200)

        # Retrieve the newly split lifted membership id
        conn = db.get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.lifted_by_membership_id
            FROM chit_schedules s
            WHERE s.chit_group_id = %s AND s.month_index = 7;
        """, (chit_id,))
        lifted_ms_id = str(cur.fetchone()[0])
        cur.close()
        conn.close()

        # Delete the payout for this 1-share split
        res_del = self.client.delete(f'/chit/api/chitgroups/{chit_id}/month/7/payout?membership_id={lifted_ms_id}', base_url='https://localhost')
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()['success'])

        # Verify ticket was recombined back to full initial shares and unlifted
        conn = db.get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT ms.share_units, ms.has_lifted, ms.lifted_month_index
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s AND m.full_name ILIKE %s;
        """, (chit_id, '%Durga Krishna%'))
        recombined = cur.fetchall()
        self.assertEqual(len(recombined), 1)
        self.assertEqual(float(recombined[0][0]), initial_shares)
        self.assertFalse(recombined[0][1])
        self.assertIsNone(recombined[0][2])

        # Verify Month 7 schedule is completely reset and unlifted
        cur.execute("""
            SELECT lifted_by_membership_id, payout_date, payout_status
            FROM chit_schedules
            WHERE chit_group_id = %s AND month_index = 7;
        """, (chit_id,))
        sched_row = cur.fetchone()
        self.assertIsNone(sched_row[0])
        self.assertIsNone(sched_row[1])
        self.assertEqual(sched_row[2], 'pending')
        cur.close()
        conn.close()

if __name__ == '__main__':
    unittest.main()
