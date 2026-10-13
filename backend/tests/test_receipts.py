import pytest
from datetime import datetime, timezone, timedelta
from app.models.group import GroupOrder, GroupParticipant
from app.models.receipt import Receipt
from app.models.payment import PaymentAttempt, PaymentTransaction


def test_receipt_access_control_and_privacy_matrix(client, db_session):
    """
    Task 4 Security Test Matrix:
    1. Legitimate verified payment generates an immutable digital receipt.
    2. Shareable access token allows viewing the receipt without credentials.
    3. Accessing private receipt by ID, receipt number, or participant ID without credentials returns 401.
    4. Participant can access their own private receipt by ID/number/participant_id.
    5. Participant cannot access another participant's private receipt (403).
    6. Host can access participant receipts within their own group (200).
    7. Host from a different group cannot access another group's private receipt (403).
    8. Invalid/guessed tokens return 404.
    9. Revoked receipt tokens return 403.
    10. Expired receipt tokens return 410.
    11. Payment attempt status endpoint requires caller ownership or host authorization.
    12. Public group summary contains no private transaction references, receipt tokens, or banking secrets.
    """
    # 1. Setup Group A (Host A, Alice, Bob)
    grp_a = client.post("/api/v1/groups", json={
        "title": "Hostel Wing A Midnight Snacks",
        "delivery_location": "Block A, Room 302",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid_a = grp_a["id"]
    code_a = grp_a["invite_code"]
    host_a_token = grp_a["host_session_token"]
    host_a_part_id = grp_a["host_participant_id"]

    p_alice = client.post(f"/api/v1/groups/{code_a}/join", json={"display_name": "Alice"}).json()
    p_bob = client.post(f"/api/v1/groups/{code_a}/join", json={"display_name": "Bob"}).json()
    alice_token = p_alice["session_token"]
    bob_token = p_bob["session_token"]

    # 2. Setup Group B (Host B, Charlie)
    grp_b = client.post("/api/v1/groups", json={
        "title": "Hostel Wing B Order",
        "delivery_location": "Block B, Room 101",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid_b = grp_b["id"]
    code_b = grp_b["invite_code"]
    host_b_token = grp_b["host_session_token"]
    host_b_part_id = grp_b["host_participant_id"]

    p_charlie = client.post(f"/api/v1/groups/{code_b}/join", json={"display_name": "Charlie"}).json()
    charlie_token = p_charlie["session_token"]

    # 3. Add items for Alice in Group A
    client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": alice_token},
        json={"product_id": "p-maggi", "quantity": 2}
    )
    # Add items for Charlie in Group B
    client.post(
        f"/api/v1/groups/{gid_b}/cart/items",
        headers={"X-Session-Token": charlie_token},
        json={"product_id": "p-redbull", "quantity": 1}
    )

    # 4. Host A manually confirms Alice's payment in Group A
    confirm_alice = client.post("/api/v1/payments/host-manual-confirm", json={
        "participant_id": p_alice["id"],
        "host_participant_id": host_a_part_id,
        "upi_reference": "UPI-ALICE-12345"
    }, headers={"X-Session-Token": host_a_token})
    assert confirm_alice.status_code == 200
    alice_confirm_data = confirm_alice.json()
    alice_rcpt_token = alice_confirm_data["receipt_token"]
    alice_rcpt_id = alice_confirm_data["receipt_id"]
    alice_attempt_id = alice_confirm_data["payment_attempt_id"]

    # 5. Host B manually confirms Charlie's payment in Group B
    confirm_charlie = client.post("/api/v1/payments/host-manual-confirm", json={
        "participant_id": p_charlie["id"],
        "host_participant_id": host_b_part_id,
        "upi_reference": "UPI-CHARLIE-67890"
    }, headers={"X-Session-Token": host_b_token})
    assert confirm_charlie.status_code == 200
    charlie_confirm_data = confirm_charlie.json()
    charlie_rcpt_token = charlie_confirm_data["receipt_token"]
    charlie_rcpt_id = charlie_confirm_data["receipt_id"]

    # --- REQUIREMENT 1: Shareable token lookup works ---
    shareable_resp = client.get(f"/api/v1/receipts/{alice_rcpt_token}")
    assert shareable_resp.status_code == 200
    alice_receipt_data = shareable_resp.json()
    assert alice_receipt_data["participant_id"] == p_alice["id"]
    assert alice_receipt_data["receipt_number"].startswith("MM-")
    alice_rcpt_number = alice_receipt_data["receipt_number"]

    # --- REQUIREMENT 2: Lookup by internal ID / number without credentials returns 401 ---
    # Unauthenticated lookup by receipt ID -> 401
    assert client.get(f"/api/v1/receipts/{alice_rcpt_id}").status_code == 401
    # Unauthenticated lookup by receipt number -> 401
    assert client.get(f"/api/v1/receipts/{alice_rcpt_number}").status_code == 401
    # Unauthenticated lookup by participant ID -> 401
    assert client.get(f"/api/v1/receipts/{p_alice['id']}").status_code == 401

    # --- REQUIREMENT 3: Participant accessing their own receipt by ID/number/participant_id ---
    resp_owner_id = client.get(
        f"/api/v1/receipts/{alice_rcpt_id}",
        headers={"X-Session-Token": alice_token}
    )
    assert resp_owner_id.status_code == 200
    assert resp_owner_id.json()["id"] == alice_rcpt_id

    resp_owner_num = client.get(
        f"/api/v1/receipts/{alice_rcpt_number}",
        headers={"X-Session-Token": alice_token}
    )
    assert resp_owner_num.status_code == 200
    assert resp_owner_num.json()["receipt_number"] == alice_rcpt_number

    resp_owner_part = client.get(
        f"/api/v1/receipts/{p_alice['id']}",
        headers={"X-Session-Token": alice_token}
    )
    assert resp_owner_part.status_code == 200
    assert resp_owner_part.json()["participant_id"] == p_alice["id"]

    # --- REQUIREMENT 4: Another participant attempting to access Alice's receipt -> 403 ---
    # Bob (roommate in Group A) tries to access Alice's receipt by ID -> 403
    assert client.get(
        f"/api/v1/receipts/{alice_rcpt_id}",
        headers={"X-Session-Token": bob_token}
    ).status_code == 403

    # Charlie (participant in Group B) tries to access Alice's receipt by ID -> 403
    assert client.get(
        f"/api/v1/receipts/{alice_rcpt_id}",
        headers={"X-Session-Token": charlie_token}
    ).status_code == 403

    # --- REQUIREMENT 5: Host accessing receipts within their own group -> 200 ---
    resp_host_a = client.get(
        f"/api/v1/receipts/{alice_rcpt_id}",
        headers={"X-Session-Token": host_a_token}
    )
    assert resp_host_a.status_code == 200
    assert resp_host_a.json()["id"] == alice_rcpt_id

    # --- REQUIREMENT 6: Host attempting to access a different group's private receipt -> 403 ---
    # Host B tries to access Alice's receipt from Group A -> 403
    assert client.get(
        f"/api/v1/receipts/{alice_rcpt_id}",
        headers={"X-Session-Token": host_b_token}
    ).status_code == 403

    # Host A tries to access Charlie's receipt from Group B -> 403
    assert client.get(
        f"/api/v1/receipts/{charlie_rcpt_id}",
        headers={"X-Session-Token": host_a_token}
    ).status_code == 403

    # --- REQUIREMENT 7: Guessed or invalid tokens -> 404 ---
    assert client.get("/api/v1/receipts/non-existent-token-xyz-1234").status_code == 404

    # --- REQUIREMENT 8: Revoked receipt tokens -> 403 ---
    db_rcpt = db_session.query(Receipt).filter(Receipt.id == alice_rcpt_id).first()
    db_rcpt.is_revoked = True
    db_session.commit()

    revoked_resp = client.get(f"/api/v1/receipts/{alice_rcpt_token}")
    assert revoked_resp.status_code == 403
    assert "revoked" in revoked_resp.json()["detail"].lower()

    # Un-revoke for further testing
    db_rcpt.is_revoked = False
    db_session.commit()

    # --- REQUIREMENT 9: Expired receipt tokens -> 410 ---
    db_rcpt.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    expired_resp = client.get(f"/api/v1/receipts/{alice_rcpt_token}")
    assert expired_resp.status_code == 410
    assert "expired" in expired_resp.json()["detail"].lower()

    # --- REQUIREMENT 10: Payment attempt status authorization ---
    # Unauthenticated -> 401
    assert client.get(f"/api/v1/payments/attempt/{alice_attempt_id}/status").status_code == 401

    # Bob (different participant) -> 403
    assert client.get(
        f"/api/v1/payments/attempt/{alice_attempt_id}/status",
        headers={"X-Session-Token": bob_token}
    ).status_code == 403

    # Host B (foreign host) -> 403
    assert client.get(
        f"/api/v1/payments/attempt/{alice_attempt_id}/status",
        headers={"X-Session-Token": host_b_token}
    ).status_code == 403

    # Alice (attempt owner) -> 200
    alice_status = client.get(
        f"/api/v1/payments/attempt/{alice_attempt_id}/status",
        headers={"X-Session-Token": alice_token}
    )
    assert alice_status.status_code == 200
    assert alice_status.json()["status"] == "PAID"

    # Host A (matching group host) -> 200
    host_status = client.get(
        f"/api/v1/payments/attempt/{alice_attempt_id}/status",
        headers={"X-Session-Token": host_a_token}
    )
    assert host_status.status_code == 200

    # --- REQUIREMENT 11: Public group summary contains no private transaction details ---
    summary_resp = client.get(f"/api/v1/groups/{gid_a}/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # Aggregate metrics present
    assert "total_items_count" in summary
    assert "grouped_products" in summary
    assert "grand_total_paise" in summary
    assert "paid_participants_count" in summary
    assert summary["paid_participants_count"] >= 1

    # No private transaction reference or tokens exposed in group summary
    summary_str = str(summary)
    assert "UPI-ALICE-12345" not in summary_str
    assert "access_token" not in summary
    assert "transaction_ref" not in summary
    assert "receipt_number" not in summary


def test_receipt_enumeration_and_unauthorized_inspection(client, db_session):
    """
    Task 5 Negative Test:
    Demonstrates that sequential or pattern-based enumeration of receipts is blocked:
    - Attempting sequential numbers without credentials returns 401 or 404.
    - Guessing valid receipt numbers with an unauthorized participant or foreign host session returns 403.
    - Capability tokens are verified to have >= 256 bits of entropy (>= 43 characters).
    """
    # 1. Create a legitimate group and receipt
    grp = client.post("/api/v1/groups", json={
        "title": "Enumeration Guard Group",
        "delivery_location": "Block C",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    host_token = grp["host_session_token"]
    host_part_id = grp["host_participant_id"]

    member = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Target Member"}).json()
    member_token = member["session_token"]

    attacker = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Attacker Member"}).json()
    attacker_token = attacker["session_token"]

    # Confirm member's payment
    confirm_resp = client.post("/api/v1/payments/host-manual-confirm", json={
        "participant_id": member["id"],
        "host_participant_id": host_part_id,
        "upi_reference": "SECRET_UTR_TARGET"
    }, headers={"X-Session-Token": host_token}).json()

    valid_token = confirm_resp["receipt_token"]
    valid_rcpt_id = confirm_resp["receipt_id"]

    # Retrieve valid receipt to get its formatted number
    target_rcpt = client.get(f"/api/v1/receipts/{valid_token}").json()
    valid_number = target_rcpt["receipt_number"]

    # Verify capability token entropy (at least 43 characters urlsafe)
    assert len(valid_token) >= 43

    # Pattern enumeration attempt without credentials
    guessed_numbers = [
        "MM-2026-0001",
        "MM-2026-0002",
        "MM-2026-AAAA",
        "REC-1",
        "RECEIPT-0001",
        valid_number  # The actual valid number, attempted without credentials!
    ]
    for num in guessed_numbers:
        resp = client.get(f"/api/v1/receipts/{num}")
        # Must be rejected: 401 for valid number without credentials, 404 for nonexistent
        assert resp.status_code in [401, 404]

    # Attacker attempts to inspect target's valid receipt using attacker's valid session token
    # Attacker tries target's receipt ID -> 403
    assert client.get(
        f"/api/v1/receipts/{valid_rcpt_id}",
        headers={"X-Session-Token": attacker_token}
    ).status_code == 403

    # Attacker tries target's receipt number -> 403
    assert client.get(
        f"/api/v1/receipts/{valid_number}",
        headers={"X-Session-Token": attacker_token}
    ).status_code == 403

    # Attacker tries target's participant ID -> 403
    assert client.get(
        f"/api/v1/receipts/{member['id']}",
        headers={"X-Session-Token": attacker_token}
    ).status_code == 403

