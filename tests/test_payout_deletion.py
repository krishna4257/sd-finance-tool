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

if __name__ == '__main__':
    unittest.main()
