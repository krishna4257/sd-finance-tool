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
    sess['vid'] = 110102

print("--- 1. Testing Village Dashboard HTML route ---")
res_dash = client.get('/dashboard', base_url='https://localhost')
print("Status:", res_dash.status_code)
assert res_dash.status_code == 200, f"Dashboard returned {res_dash.status_code}"
dash_html = res_dash.get_data(as_text=True)
assert 'tileInterestDiscount' in dash_html, "tileInterestDiscount missing from dashboard.html"
assert 'lblTotalInterestDiscount' in dash_html, "lblTotalInterestDiscount missing from dashboard.html"
print("Dashboard HTML verified: Tile 4 is present in dashboard.html.")

print("\n--- 2. Testing Village Dashboard Analytics API ---")
res_analytics = client.get('/api/dashboard/analytics/110102', base_url='https://localhost')
print("Status:", res_analytics.status_code)
assert res_analytics.status_code == 200
body_analytics = json.loads(res_analytics.get_data(as_text=True))
data_analytics = body_analytics.get('data', {})
int_disc = data_analytics.get('current', {}).get('interest_discount', {})
print("Interest discount metrics:", int_disc)
assert int_disc.get('total') == 2500.0, f"Expected total 2500.0, got {int_disc.get('total')}"
assert int_disc.get('accounts') == 1, f"Expected 1 account, got {int_disc.get('accounts')}"
print("Village Dashboard Analytics API verified: returns total 2500 and 1 account.")

print("\n--- 3. Testing Cashbag HTML route ---")
res_cb = client.get('/cashbag?emp1=6&emp2=5', base_url='https://localhost')
print("Status:", res_cb.status_code)
assert res_cb.status_code == 200, f"Cashbag returned {res_cb.status_code}"
cb_html = res_cb.get_data(as_text=True)
assert 'openInterestDiscountModal' in cb_html, "openInterestDiscountModal missing from cashbag.html"
assert 'interestDiscountModal' in cb_html, "interestDiscountModal missing from cashbag.html"
assert 'Interest Discount' in cb_html, "Interest Discount label missing from cashbag.html"
assert '₹2,500' in cb_html, "Expected formatted ₹2,500 in cashbag HTML"
print("Cashbag HTML verified: Interest Discount card and modal present, displays whole number ₹2,500.")

print("\n--- 4. Testing Cashbag Breakdown API for interest_discount ---")
res_breakdown = client.get('/api/cashbag/breakdown?emp1=6&emp2=5&type=interest_discount&end_day=3', base_url='https://localhost')
print("Status:", res_breakdown.status_code)
assert res_breakdown.status_code == 200
data_breakdown = json.loads(res_breakdown.get_data(as_text=True))
print("Success:", data_breakdown.get('success'))
tree = data_breakdown.get('tree', [])
print("Number of months in tree:", len(tree))
assert len(tree) > 0, "Tree should not be empty"
print("Month 0 name:", tree[0].get('month_name'))
print("Month 0 total:", tree[0].get('total_amount'))
assert tree[0].get('total_amount') == 2500.0, f"Expected 2500.0, got {tree[0].get('total_amount')}"
weeks = tree[0].get('weeks', [])
if weeks:
    print("Week 0 label:", weeks[0].get('week_label'))
    print("Week 0 total:", weeks[0].get('total_amount'))
    days = weeks[0].get('days', [])
    if days:
        print("Day 0 date:", days[0].get('day_date'))
        print("Day 0 customers count:", len(days[0].get('customers', [])))
        print("Customer 0:", days[0].get('customers')[0])
        assert days[0].get('customers')[0]['name'] == 'VENKAT'
        assert days[0].get('customers')[0]['amount'] == 2500.0
print("Cashbag Breakdown API verified.")

print("\nALL 4 VERIFICATIONS PASSED SUCCESSFULLY!")
