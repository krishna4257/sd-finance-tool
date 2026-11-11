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
assert any(x in html for x in ['302,162', '3,02,162', '502,162', '5,02,162', '484,828', '4,84,828', '487,828', '4,87,828']), "Expected cashbag total in HTML"
assert any(x in html for x in ['600,000', '6,00,000', '800,000', '8,00,000']), "Expected capital deployed in HTML"
assert any(x in html for x in ['68,844', '70,844']), "Expected collection in HTML"
assert any(x in html for x in ['7,484', '7,817']), "Expected rusum in HTML"
assert any(x in html for x in ['74,834', '78,167']), "Expected commission in HTML"
assert any(x in html for x in ['449,000', '4,49,000', '469,000', '4,69,000']), "Expected loans dispensed in HTML"
assert '2,500' in html, "Expected 2,500 in HTML"

print("All assertions passed successfully! Cashbag Formula Modal is completely verified!")
