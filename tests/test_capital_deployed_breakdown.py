import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from app import app

client = app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['username'] = 'admin'
    sess['level'] = 'admin'

print("--- 1. Testing Cashbag HTML for bank_id and Capital Deployed Breakdown ---")
res_html = client.get('/cashbag?emp1=6&emp2=5&bank_id=4a42da05-6570-4a5c-9bef-b76eec0a564f', base_url='https://localhost')
assert res_html.status_code == 200, f"Expected 200, got {res_html.status_code}"
html = res_html.get_data(as_text=True)
assert 'capitalDeployedModal' in html, "capitalDeployedModal missing"
assert 'openCapitalDeployedModal' in html, "openCapitalDeployedModal missing"
assert 'Investor Code' in html, "Investor Code column missing from loadBreakdownData in HTML"
assert 'investorBadges' in html, "investorBadges missing from loadBreakdownData in HTML"
print("Cashbag HTML verification passed!")

print("\n--- 2. Testing API /api/cashbag/breakdown for type=capital_deployed ---")
res_api = client.get('/api/cashbag/breakdown?emp1=6&emp2=5&type=capital_deployed&bank_id=4a42da05-6570-4a5c-9bef-b76eec0a564f&end_day=3', base_url='https://localhost')
assert res_api.status_code == 200, f"Expected 200, got {res_api.status_code}"
data = json.loads(res_api.get_data(as_text=True))
assert data.get('success') is True, f"API failed: {data}"
tree = data.get('tree', [])
assert len(tree) > 0, "Tree is empty"

month = tree[0]
print("Month:", month.get('month_name'), "Total:", month.get('total_amount'))
assert month.get('total_amount') == 800000.0, f"Expected 800000.0, got {month.get('total_amount')}"

weeks = month.get('weeks', [])
assert len(weeks) > 0, "No weeks found"
week = weeks[0]
print("Week:", week.get('week_label'), "Total:", week.get('total_amount'))
assert week.get('total_amount') == 800000.0

days = week.get('days', [])
assert len(days) > 0, "No days found"
day = days[0]
print("Day:", day.get('day_date'), "Total:", day.get('total_amount'))
assert day.get('total_amount') == 800000.0
assert '01/08/2026' in day.get('day_date')

investors = day.get('investors', [])
print("Investors badge list:", investors)
assert any('INV-001' in inv for inv in investors), "INV-001 missing from investors badge list"
assert any('INV-002' in inv for inv in investors), "INV-002 missing from investors badge list"

txns = day.get('transactions', [])
print(f"Transactions count: {len(txns)}")
assert len(txns) == 2, f"Expected 2 transactions, got {len(txns)}"

for t in txns:
    print(f"  Investor: {t.get('investor_name')} ({t.get('investor_code')}) | Amount: ₹{t.get('amount'):,.0f} | Mode: {t.get('txn_type')} | Target: {t.get('group_code')} ({t.get('group_name')})")

inv_codes = {t.get('investor_code'): t.get('amount') for t in txns}
assert inv_codes.get('INV-001') == 200000.0, f"Expected 200000.0 for INV-001, got {inv_codes.get('INV-001')}"
assert inv_codes.get('INV-002') == 600000.0, f"Expected 600000.0 for INV-002, got {inv_codes.get('INV-002')}"

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
