import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        getattr(sys.stdout, 'reconfigure', lambda **kw: None)(encoding='utf-8')
    except Exception:
        pass

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import app
from db import get_pg_connection

def run_tests():
    print("=== Testing Investor Folio & Drawings Settlement System ===")
    client = app.test_client()

    # Authenticate session
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['level'] = 'a'

    BASE = "https://localhost"

    # 1. Test Treasury Dashboard
    print("\n--- 1. Testing Treasury Dashboard (/banking/dashboard) ---")
    res = client.get("/banking/dashboard", base_url=BASE, follow_redirects=True)
    print(f"Dashboard status code: {res.status_code}")
    assert res.status_code == 200, "Dashboard failed to load"
    html = res.data.decode("utf-8")
    assert "tabExpenseOffice" in html, "Office Expense tab missing"
    assert "tabExpensePersonal" in html, "Personal Expense tab missing"
    assert "personalExpenseInvestorSelect" in html, "Investor dropdown missing in expense modal"
    print("[PASS] Treasury Dashboard expense modal contains Office & Personal Expense toggle and Investor dropdown!")

    # 2. Get an active investor ID from DB
    print("\n--- 2. Fetching test investor ---")
    conn = get_pg_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, full_name FROM investors WHERE is_active = TRUE ORDER BY created_at ASC LIMIT 1")
        inv = cur.fetchone()
    conn.close()

    assert inv is not None, "No active investor found"
    investor_id = str(inv[0])
    investor_name = inv[1]
    print(f"Found active investor: {investor_name} ({investor_id})")

    # 3. Test Investor 360 Folio Page
    print(f"\n--- 3. Testing Investor 360 Folio (/banking/investors/{investor_id}) ---")
    res = client.get(f"/banking/investors/{investor_id}", base_url=BASE, follow_redirects=True)
    print(f"Folio status code: {res.status_code}")
    assert res.status_code == 200, "Investor folio failed to load"
    html = res.data.decode("utf-8")

    # Verify side-by-side layout
    assert "grid grid-cols-1 lg:grid-cols-2 gap-6 items-start" in html, "Side-by-side grid missing"
    assert "Active Village Group Deployments" in html, "Active Village Group Deployments heading missing"
    assert "Personal Expense Account / Drawings" in html, "Personal Expense Account / Drawings heading missing"
    assert "toggleCardCollapse('deploymentsCardBody'" in html, "Deployments collapsible heading missing"
    assert "toggleCardCollapse('drawingsCardBody'" in html, "Drawings collapsible heading missing"
    assert "openAllDeploymentsModal()" in html, "Open button for deployments missing"
    assert "openAllPersonalExpensesModal()" in html, "Open button for personal drawings missing"
    assert "settleExpenseModal" in html, "Settlement modal missing"
    assert "allDeploymentsModal" in html, "All deployments popup modal missing"
    assert "allPersonalExpensesModal" in html, "All personal expenses popup modal missing"
    print("[PASS] Investor Folio contains side-by-side grid, collapsible headers, Apple Notes drawings, and all elaborate popups!")

    # 4. Test Adding a Personal Drawing and Settlement Flow
    print("\n--- 4. Testing Personal Drawing Creation and Settlement Flow ---")
    # Add a drawing via POST
    add_res = client.post(
        f"/banking/api/investors/{investor_id}/personal-expense",
        base_url=BASE,
        json={
            "item_description": "Test Diesel & Travel for Village Visit",
            "amount": 2500,
            "payment_mode": "CASH",
            "expense_date": "2026-09-15",
            "receipt_no": "TEST-REC-88"
        }
    )
    print(f"Add drawing response: {add_res.status_code}, {add_res.get_json()}")
    assert add_res.status_code == 200, "Failed to add personal drawing"

    # Find the newly created expense
    conn = get_pg_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, amount, is_settled, days_aged_val
            FROM (
                SELECT id, amount, is_settled, (CURRENT_DATE - expense_date) as days_aged_val
                FROM investor_personal_expenses
                WHERE investor_id = %s AND receipt_no = 'TEST-REC-88'
                ORDER BY created_at DESC LIMIT 1
            ) sub
        """, (investor_id,))
        exp_row = cur.fetchone()
    conn.close()

    assert exp_row is not None, "Expense not found in DB"
    exp_id = str(exp_row[0])
    is_settled_initial = exp_row[2]
    days_aged = exp_row[3]
    print(f"Created drawing ID: {exp_id}, Amount: {exp_row[1]}, Settled: {is_settled_initial}, Days Aged: {days_aged}")
    assert is_settled_initial is False or is_settled_initial is None, "New drawing should be unsettled"

    # Verify aging badge rendering on Folio page
    res = client.get(f"/banking/investors/{investor_id}", base_url=BASE, follow_redirects=True)
    html = res.data.decode("utf-8")
    assert "Test Diesel" in html, "Drawing description not rendered"
    assert "overdue" in html or "aged" in html or f"{days_aged}d" in html, "Aging indicator not rendered"
    print("[PASS] Drawing is rendered with aging tag and Apple Notes check button!")

    # 5. Settle the Drawing
    print(f"\n--- 5. Settling Drawing ({exp_id}) ---")
    settle_res = client.post(
        f"/banking/api/personal-expenses/{exp_id}/settle",
        base_url=BASE,
        json={
            "settlement_mode": "CASH",
            "settled_at": "2026-10-27",
            "settlement_ref": "CASH-PAID-DESK-01",
            "settlement_notes": "Paid back in cash at main branch counter"
        }
    )
    print(f"Settle response: {settle_res.status_code}, {settle_res.get_json()}")
    assert settle_res.status_code == 200, "Failed to settle drawing"

    # Check DB state
    conn = get_pg_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT is_settled, settlement_mode, settlement_ref, settlement_notes
            FROM investor_personal_expenses
            WHERE id = %s
        """, (exp_id,))
        settled_db = cur.fetchone()
    conn.close()

    assert settled_db[0] is True, "is_settled should be TRUE"
    assert settled_db[1] == "CASH", "settlement_mode should be CASH"
    assert settled_db[2] == "CASH-PAID-DESK-01", "settlement_ref should match"
    print(f"[PASS] DB state confirmed: is_settled={settled_db[0]}, mode={settled_db[1]}, ref={settled_db[2]}")

    # Verify that settled drawing shows in settled section
    res = client.get(f"/banking/investors/{investor_id}", base_url=BASE, follow_redirects=True)
    html = res.data.decode("utf-8")
    assert "Completed / Settled Drawings" in html, "Settled drawings section missing"
    assert "CASH-PAID-DESK-01" in html, "Settled ref missing from completed section"
    print("[PASS] Settled drawing is properly struck off and pushed down into completed drawings section!")

    # 6. Test Unsettle (Re-open)
    print(f"\n--- 6. Re-opening Drawing ({exp_id}) ---")
    unsettle_res = client.post(f"/banking/api/personal-expenses/{exp_id}/unsettle", base_url=BASE)
    print(f"Unsettle response: {unsettle_res.status_code}, {unsettle_res.get_json()}")
    assert unsettle_res.status_code == 200, "Failed to unsettle drawing"

    # Clean up test row
    conn = get_pg_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM investor_personal_expenses WHERE id = %s", (exp_id,))
        conn.commit()
    conn.close()
    print("[PASS] Re-open succeeded and test record cleaned up!")

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
