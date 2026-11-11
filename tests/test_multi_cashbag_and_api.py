import unittest
from datetime import date
import db
import services.banking_calc_engine as bce

class TestMultiCashbagAndAPI(unittest.TestCase):
    def setUp(self):
        self.conn = db.get_pg_connection()
        self.cur = self.conn.cursor()

    def tearDown(self):
        self.cur.close()
        self.conn.close()

    def test_sappa_venkata_kalyan_cashbags(self):
        """Verify Sappa Venkata Kalyan has two separate cashbags: Main and Route M"""
        self.cur.execute("""
            SELECT name, village_codes 
            FROM village_cashbags 
            WHERE emp1 = 63 
            ORDER BY name ASC
        """)
        rows = self.cur.fetchall()
        self.assertEqual(len(rows), 2)
        
        cbs = {r[0]: r[1] for r in rows}
        self.assertIn("Main", cbs)
        self.assertIn("Route M", cbs)
        
        # Verify village assignment
        self.assertTrue(any(v in cbs["Main"] for v in ['PRG', 'SDNR', 'NGKL2', 'BTPR', 'KLPR2']))
        self.assertTrue(any(v in cbs["Route M"] for v in ['BTPR2-M', 'KLPR3-M', 'NGKL3-M', 'SDNR2-M']))

    def test_cashbag_transactions_insert_without_eid(self):
        """Verify adding an expense with RESERVATION and group_id inserts cleanly without column 'eid' error"""
        self.cur.execute("""
            INSERT INTO cashbag_transactions (
                emp1, emp2, txn, txn_sub, txn_type, amount, notes, created_by, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (63, None, 'EXPENSE', 'RESERVATION', 'CASH', 250.0, 'Test reservation expense', 'tester'))
        new_id = self.cur.fetchone()[0]
        self.conn.commit()

        # Clean up test row
        self.cur.execute("DELETE FROM cashbag_transactions WHERE id = %s", (new_id,))
        self.conn.commit()

    def test_interest_30_360_user_case(self):
        """100,000 at 24% from Jan 1, 2026 to Oct 31, 2026: 300 days -> 20,000"""
        d1 = date(2026, 1, 1)
        d2 = date(2026, 10, 31)
        days = bce.calculate_days_30_360(d1, d2)
        self.assertEqual(days, 300)
        res = bce.calculate_interest_30_360(100000, 24.0, d1, d2)
        self.assertEqual(round(res["interest"]), 20000)

    def test_mobile_cashbag_engine_harmony(self):
        """Verify services.cashbag_engine returns identical totals for Test Route Bank matching website"""
        from services.cashbag_engine import compute_cashbag_metrics, resolve_employee_cashbags
        from security.mobile_auth import generate_mobile_token
        from app import app

        # 1. Engine resolution for Employee 5 (has Test Route Bank and Route Bank 5)
        cbs = resolve_employee_cashbags(self.cur, 5, is_admin=True)
        self.assertTrue(len(cbs) >= 2)
        cb_ids = [c['id'] for c in cbs]
        self.assertIn('4a42da05-6570-4a5c-9bef-b76eec0a564f', cb_ids)

        # 2. Engine metrics for Test Route Bank
        metrics = compute_cashbag_metrics(self.cur, emp1=6, emp2=5, bank_id='4a42da05-6570-4a5c-9bef-b76eec0a564f')
        self.assertEqual(metrics['cashbag_total'], 484828.0)
        self.assertEqual(metrics['capital_deployed'], 800000.0)
        self.assertEqual(metrics['total_withdrawn'], 3000.0)
        self.assertEqual(metrics['installments'], 70844.0)
        self.assertEqual(metrics['loans_disbursed'], 469000.0)
        self.assertEqual(metrics['loan_commission'], 7817.0)
        self.assertEqual(metrics['interest_total'], 78167.0)
        self.assertEqual(metrics['interest_discount_total'], 2500.0)

        # 3. Mobile API endpoint returns exact same numbers
        token = generate_mobile_token(4, 5)
        with app.test_client() as client:
            res = client.get(
                '/api/mobile/cashbag?bank_id=4a42da05-6570-4a5c-9bef-b76eec0a564f',
                headers={'X-Mobile-Token': token},
                base_url='https://localhost'
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data['cashbag_total'], 484828.0)
            self.assertEqual(data['capital_deployed'], 800000.0)
            self.assertEqual(data['total_withdrawn'], 3000.0)
            self.assertEqual(data['installments'], 70844.0)
            self.assertEqual(data['loans_disbursed'], 469000.0)

if __name__ == '__main__':
    unittest.main()
