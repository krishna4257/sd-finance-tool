import os
import sys
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timezone

# Ensure tool directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from db import get_pg_connection
from security.mobile_auth import (
    generate_mobile_token,
    get_mobile_queue_hmac_secret,
    _canonical_json,
)

def make_signed_envelope(req_type, eid, vid, inner_payload):
    secret = get_mobile_queue_hmac_secret()
    nonce = uuid.uuid4().hex
    ts = datetime.now(timezone.utc).isoformat()
    idemp = uuid.uuid4().hex

    signed_payload = {
        "type": req_type,
        "eid": eid,
        "vid": vid,
        "nonce": nonce,
        "timestamp": ts,
        "idempotency_key": idemp,
        "payload": inner_payload,
    }
    canonical = _canonical_json(signed_payload)
    sig = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    envelope = {
        **signed_payload,
        "local_uuid": str(uuid.uuid4()),
        "device_id": "test_device",
        "signature": sig,
    }
    return envelope

def run_tests():
    print("==================================================")
    print("STARTING TEST VILLAGE (110102) VERIFICATION")
    print("==================================================")

    test_vid = 110102
    test_ano = 1
    test_date = "2026-11-12"
    test_uuid = "7354b5e8-14c0-4a77-ad3a-80a35b90b121"
    test_eid = 5
    test_user_id = 4

    client = app.test_client()

    # Step 0: Ping Endpoint
    print("\n--- Test 0: Testing /api/mobile/ping ---")
    ping_resp = client.get("/api/mobile/ping")
    assert ping_resp.status_code == 200, f"Ping returned {ping_resp.status_code}"
    ping_data = ping_resp.get_json()
    assert ping_data.get("status") == "ok", f"Ping unexpected payload: {ping_data}"
    print(f"PASSED: Ping returned 200 OK -> {ping_data}")

    # Generate mobile token for EID 5
    mobile_token = generate_mobile_token(test_user_id, test_eid)
    auth_headers = {
        "X-Mobile-Token": mobile_token
    }

    # Step 1: Mobile Payment Update
    print("\n--- Test 1: Mobile Payment Update (1440 -> 5000) for Ano 1, VID 110102 ---")
    update_payload = {
        "vid": test_vid,
        "eid": test_eid,
        "device_id": "test_device",
        "payments": [
            {
                "local_uuid": test_uuid,
                "ano": test_ano,
                "vid": test_vid,
                "eid": test_eid,
                "amt": 5000.0,
                "cash_amount": 5000.0,
                "upi_amount": 0.0,
                "payment_date": test_date,
                "payment_type": "cash",
                "is_updated": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    resp = client.post(
        "/api/mobile/payment_feed_batch",
        headers={**auth_headers, "Content-Type": "application/json"},
        json=update_payload
    )
    print(f"Update response status: {resp.status_code}")
    print(f"Update response data: {resp.get_json()}")
    assert resp.status_code == 200, f"Expected 200 but got {resp.status_code}: {resp.data}"

    # Verify Database state for Item 8811
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT feed_payment_id, status, local_uuid, payload 
        FROM payment_feed_items 
        WHERE (payload->>'vid')::int = %s AND (payload->>'ano')::int = %s AND (payload->>'payment_date') = %s
    """, (test_vid, test_ano, test_date))
    rows = cur.fetchall()
    print(f"Database pending rows matching Ano 1, VID 110102, Date {test_date}: {len(rows)}")
    assert len(rows) == 1, f"Expected exactly 1 pending row, found {len(rows)}"
    feed_pid, status, luuid, db_payload = rows[0]
    print(f"Row {feed_pid}: amt={db_payload.get('amt')}, is_updated={db_payload.get('is_updated')}, updated_at={db_payload.get('updated_at')}")
    assert float(db_payload.get("amt")) == 5000.0, f"Expected 5000.0, got {db_payload.get('amt')}"
    assert db_payload.get("is_updated") is True, "Expected is_updated to be True"
    assert db_payload.get("updated_at") is not None, "Expected updated_at to be populated"

    # Verify payment_feed_edits table
    cur.execute("SELECT edit_id, local_uuid, edit_status, edited_payload FROM payment_feed_edits WHERE local_uuid = %s", (test_uuid,))
    edit_row = cur.fetchone()
    print(f"Payment feed edit record: {edit_row[0] if edit_row else None}, status: {edit_row[2] if edit_row else None}")
    assert edit_row is not None, "Expected record in payment_feed_edits"
    print("PASSED: Database updated successfully to 5000 with is_updated=True")

    # Step 2: Website Feed Page Rendering
    print("\n--- Test 2: Website Feed Page Rendering (/feed) ---")
    with client.session_transaction() as sess:
        sess["user_id"] = test_user_id
        sess["username"] = "chinna"
        sess["level"] = "admin"
        sess["eid"] = test_eid
        sess["vid"] = test_vid

    web_resp = client.get(f"/feed?vid={test_vid}")
    assert web_resp.status_code == 200, f"Expected 200 for /feed, got {web_resp.status_code}"
    html_content = web_resp.data.decode("utf-8", errors="ignore")

    # Check for Account 1 amount 5000
    assert "5000" in html_content or "5,000" in html_content, "Updated amount 5000 not found in feed HTML"
    # Check for blue glowing dot
    assert 'class="row-warn-dot updated"' in html_content, "Updated dot <span class='row-warn-dot updated'> not found in feed HTML"
    assert 'title="Updated on' in html_content or 'title="Updated"' in html_content, "Updated on tooltip not found in dot"
    # Check CSS animation and styling in HTML
    assert '.row-warn-dot.updated' in html_content, "CSS class .row-warn-dot.updated missing in feed CSS"
    assert '#0ea5e9' in html_content, "Blue glow color #0ea5e9 missing in feed CSS"
    print("PASSED: Website feed rendered Account #1 with 5000 and glowing blue dot with 'Updated on' tooltip!")

    # Step 3: Exact Duplicate Payment Prevention
    print("\n--- Test 3: Exact Duplicate Payment Prevention ---")
    dup_payload = {
        "vid": test_vid,
        "eid": test_eid,
        "device_id": "test_device",
        "payments": [
            {
                "local_uuid": "some-new-duplicate-uuid-9999",
                "ano": test_ano,
                "vid": test_vid,
                "eid": test_eid,
                "amt": 5000.0,
                "cash_amount": 5000.0,
                "upi_amount": 0.0,
                "payment_date": test_date,
                "payment_type": "cash",
                "is_updated": False  # Not an update! An accidental duplicate submission
            }
        ]
    }
    dup_resp = client.post(
        "/api/mobile/payment_feed_batch",
        headers={**auth_headers, "Content-Type": "application/json"},
        json=dup_payload
    )
    print(f"Duplicate post response status: {dup_resp.status_code}")
    # Verify no duplicate was added to payment_feed_items
    cur.execute("""
        SELECT count(*) FROM payment_feed_items 
        WHERE (payload->>'vid')::int = %s AND (payload->>'ano')::int = %s AND (payload->>'payment_date') = %s
    """, (test_vid, test_ano, test_date))
    count = cur.fetchone()[0]
    print(f"Total pending items for Ano 1, VID 110102 on {test_date}: {count}")
    assert count == 1, f"Expected duplicate to be rejected/skipped, but count is {count}"
    print("PASSED: Duplicate payment was safely rejected/skipped; count remains 1")

    # Step 4: Customer Duplicate Prevention
    print("\n--- Test 4: Customer Duplicate Prevention ---")
    cust_inner = {
        "vid": test_vid,
        "eid": test_eid,
        "ano": 1,  # Ano 1 already exists in village 110102!
        "name": "Duplicate Tester",
        "base_amount": 10000,
        "total_amount": 12000,
        "phone_number": "9999999999"
    }
    envelope = make_signed_envelope("customer", test_eid, test_vid, cust_inner)
    cust_resp = client.post(
        "/api/mobile/customer_feed",
        headers=auth_headers,
        data={"payload": json.dumps(envelope)}
    )
    print(f"Duplicate customer response status: {cust_resp.status_code}, data: {cust_resp.get_json()}")
    assert cust_resp.status_code == 409, f"Expected 409 Conflict, got {cust_resp.status_code}"
    assert "already exists in Village" in cust_resp.get_json().get("error", ""), "Expected duplicate error message"
    print("PASSED: Duplicate customer blocked with HTTP 409 Conflict")

    # Step 5: Account Closure Duplicate Prevention
    print("\n--- Test 5: Account Closure Duplicate Prevention ---")
    # In Village 110102, check for closed account or create duplicate pending test
    cur.execute("SELECT ano FROM closed_cust_account WHERE vid = %s LIMIT 1", (test_vid,))
    closed_row = cur.fetchone()
    if closed_row:
        closed_ano = closed_row[0]
        close_inner = {"ano": closed_ano, "vid": test_vid, "eid": test_eid}
        close_env = make_signed_envelope("close_account", test_eid, test_vid, close_inner)
        close_resp = client.post(
            "/api/mobile/close_account_feed",
            headers=auth_headers,
            data={"payload": json.dumps(close_env)}
        )
        print(f"Closed account closure response: {close_resp.status_code}, data: {close_resp.get_json()}")
        assert close_resp.status_code == 409, f"Expected 409 Conflict for already closed account, got {close_resp.status_code}"
        print(f"PASSED: Duplicate closure for already closed Ano {closed_ano} blocked with HTTP 409 Conflict")
    else:
        # Check duplicate pending closure
        cur.execute("SELECT ano FROM customer WHERE vid = %s AND status = 'open' LIMIT 1", (test_vid,))
        open_cust = cur.fetchone()
        if open_cust:
            open_ano = open_cust[0]
            # Insert a temporary pending closure
            cur.execute("""
                INSERT INTO account_closure_feed (local_uuid, vid, ano, eid, status, created_at)
                VALUES ('temp-test-close-uuid', %s, %s, %s, 'pending', NOW())
                ON CONFLICT DO NOTHING
            """, (test_vid, open_ano, test_eid))
            conn.commit()
            
            close_inner = {"ano": open_ano, "vid": test_vid, "eid": test_eid}
            close_env = make_signed_envelope("close_account", test_eid, test_vid, close_inner)
            close_resp = client.post(
                "/api/mobile/close_account_feed",
                headers=auth_headers,
                data={"payload": json.dumps(close_env)}
            )
            print(f"Pending closure duplicate response: {close_resp.status_code}, data: {close_resp.get_json()}")
            assert close_resp.status_code == 409, f"Expected 409 Conflict for duplicate pending closure, got {close_resp.status_code}"
            
            # Clean up temporary test closure
            cur.execute("DELETE FROM account_closure_feed WHERE local_uuid = 'temp-test-close-uuid'")
            conn.commit()
            print("PASSED: Duplicate pending closure blocked with HTTP 409 Conflict")

    conn.close()
    print("\n==================================================")
    print("ALL 6 TESTS PASSED STRICTLY FOR TEST VILLAGE 110102!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
