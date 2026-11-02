import unittest
from datetime import date
import db
import banking_calc_engine as bce

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

if __name__ == '__main__':
    unittest.main()
