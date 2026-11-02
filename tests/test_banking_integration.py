"""
End-to-End Integration Test for Hierarchical Banking System
Tests the complete banking flow on local Replica DB:
1. Investor Onboarding & Capital Deposit
2. Village Group Bank Registration & Legacy Opening Setup
3. Capital Deployment with Cashbag OFFICE_CASH Bridge
4. Waterfall Withdrawal (Principal -> Interest -> Profit)
5. Investor Personal Draw Accounts
6. Central Office Operating Expenses & Days-Weighted Reallocation
7. Direct Individual Loans & Repayments
8. Chit Fund Inter-Bank Transfer
9. Transaction Soft Reversal
"""

import unittest
import os
import json
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
os.environ["DISABLE_SECURE_COOKIE"] = "1"

from app import app
from db import get_pg_connection
import banking_calc_engine as bce


class TestBankingSystemIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()
        cls.test_phone = f"98{int(datetime.now().timestamp()) % 100000000:08d}"

    def setUp(self):
        # Set admin session for test requests
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin_tester'
            sess['level'] = 'admin'

    def test_01_treasury_dashboard_loads(self):
        """Test GET /banking/dashboard renders with 200 OK"""
        resp = self.client.get('/banking/dashboard')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Treasury Dashboard', resp.data)
        self.assertIn(b'Live Pool', resp.data)

    def test_02_investor_onboarding_and_deposit(self):
        """Test creating an investor and depositing fresh capital"""
        payload = {
            "full_name": "Ramesh Kumar Sharma",
            "phone_number": self.test_phone,
            "email": f"ramesh_{self.test_phone}@example.com",
            "aadhaar_number": "123456789012",
            "global_share_pct": 25.0,
            "address": "Tanuku, Andhra Pradesh",
            "nominee_name": "Sita Sharma",
            "nominee_relation": "Wife",
            "nominee_phone": "9876543211"
        }
        resp = self.client.post('/banking/api/investors', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        inv_id = data['investor_id']
        inv_code = data['investor_code']
        self.assertTrue(inv_code.startswith('INV-'))

        # Deposit ₹10,00,000 cash
        dep_resp = self.client.post(f'/banking/api/investors/{inv_id}/deposit', json={
            "amount": 1000000.0,
            "payment_mode": "CASH",
            "txn_date": date.today().isoformat(),
            "notes": "Initial capital deposit"
        })
        self.assertEqual(dep_resp.status_code, 200)
        dep_data = dep_resp.get_json()
        self.assertTrue(dep_data['success'])

        # Check investor folio
        folio_resp = self.client.get(f'/banking/investors/{inv_id}')
        self.assertEqual(folio_resp.status_code, 200)
        self.assertIn(b'Ramesh Kumar Sharma', folio_resp.data)

    def test_03_village_group_registration_and_capital_deployment(self):
        """Test registering a route bank and deploying capital with Cashbag bridge"""
        # Register group
        group_code = f"ROUTE-TNK-{int(datetime.now().timestamp())}"
        resp = self.client.post('/banking/api/groups', json={
            "group_name": "Tanuku Main Route",
            "group_code": group_code,
            "emp1_id": 1,
            "collection_days_per_week": 5
        })
        self.assertEqual(resp.status_code, 200)
        grp_data = resp.get_json()
        self.assertTrue(grp_data['success'])
        group_id = grp_data['id']

        # Get the investor ID
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM investors WHERE phone_number = %s", (self.test_phone,))
            inv_id = str(cur.fetchone()[0])
        conn.close()

        # Deploy ₹2,00,000 to group
        alloc_resp = self.client.post(f'/banking/api/groups/{group_id}/allocate-capital', json={
            "investor_id": inv_id,
            "amount": 200000.0,
            "payment_mode": "CASH",
            "allocation_date": date.today().isoformat()
        })
        self.assertEqual(alloc_resp.status_code, 200)
        alloc_data = alloc_resp.get_json()
        self.assertTrue(alloc_data['success'])
        self.assertIn("OFFICE_CASH credited", alloc_data['message'])

        # Verify CAPITAL_DEPLOYED exists in cashbag_transactions
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT amount, txn, txn_type 
                FROM cashbag_transactions 
                WHERE emp1 = 1 AND txn = 'CAPITAL_DEPLOYED' AND amount = 200000.0
            """)
            cb_row = cur.fetchone()
            self.assertIsNotNone(cb_row)
            self.assertEqual(float(cb_row[0]), 200000.0)
            self.assertEqual(cb_row[1], 'CAPITAL_DEPLOYED')
        conn.close()

    def test_04_waterfall_withdrawal(self):
        """Test waterfall withdrawal from group cashbag back to investment pool"""
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM village_groups WHERE group_name = 'Tanuku Main Route' ORDER BY created_at DESC LIMIT 1")
            grp_id = str(cur.fetchone()[0])
        conn.close()

        # Execute withdrawal with Admin PIN
        wdr_resp = self.client.post(f'/banking/api/groups/{grp_id}/withdraw', json={
            "amount": 50000.0,
            "payment_mode": "CASH",
            "admin_pin": "1234",
            "withdrawal_date": date.today().isoformat()
        })
        self.assertEqual(wdr_resp.status_code, 200)
        wdr_data = wdr_resp.get_json()
        self.assertTrue(wdr_data['success'])
        self.assertIn("Waterfall withdrawal", wdr_data['message'])

    def test_05_investor_personal_expense_draw(self):
        """Test booking Amazon personal order against investor idle cash"""
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM investors WHERE phone_number = %s", (self.test_phone,))
            inv_id = str(cur.fetchone()[0])
        conn.close()

        resp = self.client.post('/banking/api/personal-expenses/add', json={
            "investor_id": inv_id,
            "amount": 2500.0,
            "payment_mode": "CASH",
            "item_description": "Amazon Delivery: Wireless Keyboard & Mouse delivered to office",
            "receipt_no": "AMZN-998811"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

    def test_06_central_office_expenses_and_settlement(self):
        """Test logging office expenses and executing annual days-weighted reallocation"""
        # Add an office expense
        exp_resp = self.client.post('/banking/api/expenses', json={
            "category": "RENT",
            "amount": 30000.0,
            "payment_mode": "CASH",
            "description": "Tanuku Head Office Month Rent",
            "expense_date": date.today().isoformat()
        })
        self.assertEqual(exp_resp.status_code, 200)
        self.assertTrue(exp_resp.get_json()['success'])

        # Execute annual settlement with Admin PIN
        settle_resp = self.client.post('/banking/api/expenses/settlement/execute', json={
            "admin_pin": "1234",
            "settlement_year": "FY-2026-27"
        })
        self.assertEqual(settle_resp.status_code, 200)
        s_data = settle_resp.get_json()
        self.assertTrue(s_data['success'])
        self.assertIn("Annual expense settlement", s_data['message'])

    def test_07_direct_individual_loans(self):
        """Test issuing direct loan from pool and logging repayment"""
        resp = self.client.post('/banking/api/direct-loans', json={
            "borrower_name": "Subba Rao",
            "phone_number": "9123456789",
            "principal_amount": 100000.0,
            "annual_interest_rate": 24.0,
            "payment_mode": "CASH",
            "repayment_type": "BULLET",
            "revenue_allocation": "POOLED",
            "notes": "Emergency micro-enterprise loan"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

        # Repay ₹20,000 principal + ₹2,000 interest
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM direct_individual_loans WHERE borrower_name = 'Subba Rao' ORDER BY created_at DESC LIMIT 1")
            loan_id = str(cur.fetchone()[0])
        conn.close()

        rep_resp = self.client.post(f'/banking/api/direct-loans/{loan_id}/repay', json={
            "principal_amount": 20000.0,
            "interest_amount": 2000.0,
            "payment_mode": "CASH"
        })
        self.assertEqual(rep_resp.status_code, 200)
        self.assertTrue(rep_resp.get_json()['success'])

    def test_08_interbank_transfer(self):
        """Test two-way liquidity transfer between Chit Fund and Investment Bank"""
        resp = self.client.post('/banking/api/interbank/transfer', json={
            "direction": "INVESTMENT_TO_CHIT",
            "amount": 50000.0,
            "payment_mode": "CASH",
            "reason": "Chit pot deficit liquidity bridge",
            "admin_pin": "1234"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

    def test_09_transaction_soft_reversal(self):
        """Test soft-reversing a transaction with admin PIN"""
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM investor_transactions WHERE txn_type = 'DEPOSIT' AND is_reversed = FALSE LIMIT 1")
            txn_id = str(cur.fetchone()[0])
        conn.close()

        resp = self.client.post(f'/banking/api/transactions/{txn_id}/reverse', json={
            "admin_pin": "1234",
            "reason": "Accidental duplicate test entry",
            "table": "investor_transactions"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

        # Verify is_reversed is True
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT is_reversed, reversed_by FROM investor_transactions WHERE id = %s", (txn_id,))
            rev, by = cur.fetchone()
            self.assertTrue(rev)
            self.assertEqual(by, 'admin_tester')
        conn.close()


if __name__ == '__main__':
    unittest.main()
