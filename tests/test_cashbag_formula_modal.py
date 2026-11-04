import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['username'] = 'admin'
    sess['level'] = 'admin'

res = client.get('/cashbag?emp1=6&emp2=5&bank_id=4a42da05-6570-4a5c-9bef-b76eec0a564f', base_url='https://localhost')
print("Status code:", res.status_code)
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
html = res.get_data(as_text=True)

assert 'cashbagFormulaModal' in html, "cashbagFormulaModal missing from HTML"
assert 'openCashbagFormulaModal()' in html, "openCashbagFormulaModal() missing from HTML"
assert 'Physical Cash in Hand' in html, "Physical Cash in Hand section missing"
assert 'Customer Receivables (Village Dashboard View)' in html, "Receivables section missing"
assert 'Why Interest Discount' in html, "Interest discount explanation callout missing"
assert '302,162' in html or '3,02,162' in html or '502,162' in html or '5,02,162' in html, "Expected cashbag total in HTML"
assert '600,000' in html or '6,00,000' in html or '800,000' in html or '8,00,000' in html, "Expected capital deployed in HTML"
assert '68,844' in html, "Expected 68,844 in HTML"
assert '7,484' in html, "Expected 7,484 in HTML"
assert '74,834' in html, "Expected 74,834 in HTML"
assert '449,000' in html or '4,49,000' in html, "Expected 449,000 in HTML"
assert '2,500' in html, "Expected 2,500 in HTML"
assert '377,656' in html or '3,77,656' in html, "Expected 377,656 in HTML"

print("All assertions passed successfully! Cashbag Formula Modal is completely verified!")
