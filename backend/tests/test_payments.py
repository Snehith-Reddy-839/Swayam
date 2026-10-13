import pytest
from app.models.group import GroupOrder, GroupParticipant
from app.models.payment import PaymentAttempt, PaymentTransaction
from app.schemas.payment import PaymentVerifyRequest
from app.services.payment_service import (
    create_or_get_payment_attempt,
    generate_upi_qr_details,
    process_payment_verification,
    verify_razorpay_signature,
    host_manual_confirm_upi_payment,
)


def test_upi_qr_generation(db_session):
    group = GroupOrder(invite_code="UPI001", title="Late Snack", host_name="Bhavya", delivery_location="Room 3")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="Bhavya", is_host=True)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 15000, "UPI_QR", "IDEMP-123", db_session)
    qr_data = generate_upi_qr_details(group, p, attempt)

    assert "upi://pay?" in qr_data.upi_uri
    assert "am=150.00" in qr_data.upi_uri
    assert "cu=INR" in qr_data.upi_uri
    assert qr_data.qr_data_url.startswith("data:image/png;base64,")
    assert qr_data.amount_paise == 15000
    assert qr_data.amount_inr == 150.00


def test_payment_idempotency(db_session):
    group = GroupOrder(invite_code="UPI002", title="Late Snack 2", host_name="Bhavya", delivery_location="Room 3")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="Bhavya", is_host=True)
    db_session.add(p)
    db_session.commit()

    key = "UNIQUE-IDEMP-KEY-999"
    att1 = create_or_get_payment_attempt(group, p, 5000, "UPI_QR", key, db_session)
    att2 = create_or_get_payment_attempt(group, p, 5000, "UPI_QR", key, db_session)

    # Must return exact same attempt instance, preventing duplicate attempts
    assert att1.id == att2.id


def test_demo_payment_verification(db_session):
    group = GroupOrder(invite_code="DEMO01", title="Demo Order", host_name="Sim User", delivery_location="Room 4")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="Sim User", is_host=True)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 8000, "DEMO", None, db_session)

    # 1. Test simulated failure
    req_fail = PaymentVerifyRequest(payment_attempt_id=attempt.id, payment_mode="DEMO", demo_outcome="FAILURE")
    resp_fail = process_payment_verification(attempt, req_fail, db_session)
    assert resp_fail.status == "FAILED"
    assert p.payment_status == "FAILED"

    # Cannot verify an already failed payment attempt directly
    with pytest.raises(ValueError, match="Cannot verify a failed payment attempt"):
        process_payment_verification(attempt, req_fail, db_session)

    # 2. Re-initiate new attempt for simulated success
    attempt2 = create_or_get_payment_attempt(group, p, 8000, "DEMO", "NEW-ATTEMPT-KEY", db_session)
    req_succ = PaymentVerifyRequest(payment_attempt_id=attempt2.id, payment_mode="DEMO", demo_outcome="SUCCESS")
    resp_succ = process_payment_verification(attempt2, req_succ, db_session)
    assert resp_succ.status == "PAID"
    assert p.payment_status == "PAID"
    assert p.amount_paid_paise == 8000
    assert resp_succ.receipt_id is not None
    assert resp_succ.is_simulated is True


def test_razorpay_signature_validation():
    # Valid signature check logic
    order_id = "order_12345"
    payment_id = "pay_67890"
    secret = "test_secret_key"
    import hmac, hashlib
    valid_sig = hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(order_id, payment_id, valid_sig, secret) is True
    assert verify_razorpay_signature(order_id, payment_id, "invalid_signature_hex", secret) is False
    # Empty secret must always fail
    assert verify_razorpay_signature(order_id, payment_id, valid_sig, "") is False


def test_upi_claim_never_automatically_verifies_paid(db_session):
    """
    Requirement 2: Clicking 'I Have Paid' must NEVER automatically mark payment as PAID.
    It transitions to PAYMENT_CLAIMED, leaving the participant pending until host confirms.
    """
    group = GroupOrder(invite_code="CLAIM01", title="Snack Pool", host_name="HostUser", delivery_location="Room 10")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="Claimer", is_host=False)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 12000, "UPI_QR", "KEY-CLAIM-1", db_session)

    # Participant clicks "I Have Paid" and submits a UTR
    verify_req = PaymentVerifyRequest(
        payment_attempt_id=attempt.id,
        payment_mode="UPI_QR",
        upi_reference="429182390192"
    )
    status_resp = process_payment_verification(attempt, verify_req, db_session)

    assert status_resp.status == "PAYMENT_CLAIMED"
    assert status_resp.receipt_id is None
    assert p.payment_status == "PAYMENT_CLAIMED"
    assert p.amount_paid_paise == 0  # Still zero paid!


def test_mode_switching_rejection(db_session):
    """
    Requirement 3: An attempt created in live mode (UPI_QR) must NEVER be verified as DEMO.
    """
    group = GroupOrder(invite_code="SWITCH01", title="Switch Test", host_name="HostUser", delivery_location="Room 10")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="Attacker", is_host=False)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 5000, "UPI_QR", "LIVE-ATTEMPT-KEY", db_session)

    # Attacker tries to pass DEMO mode in verify request to trick system
    switch_req = PaymentVerifyRequest(
        payment_attempt_id=attempt.id,
        payment_mode="DEMO",
        demo_outcome="SUCCESS"
    )
    with pytest.raises(ValueError, match="Payment mode mismatch"):
        process_payment_verification(attempt, switch_req, db_session)


def test_razorpay_forged_order_id_and_signature(db_session, monkeypatch):
    """
    Requirement 4: Verify server-side signature and match stored gateway_order_id.
    """
    from app.config import settings
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_key_123")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "super_secret_rzp_key")

    group = GroupOrder(invite_code="RZP001", title="Razorpay Order", host_name="HostUser", delivery_location="Room 10")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="CardPayer", is_host=False)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 10000, "RAZORPAY", "RZP-ATTEMPT-1", db_session)
    attempt.gateway_order_id = "order_expected_123"
    db_session.commit()

    # 1. Forged order id mismatch
    req_mismatch = PaymentVerifyRequest(
        payment_attempt_id=attempt.id,
        payment_mode="RAZORPAY",
        razorpay_order_id="order_attacker_fake",
        razorpay_payment_id="pay_999",
        razorpay_signature="dummy"
    )
    with pytest.raises(ValueError, match="Razorpay order ID mismatch"):
        process_payment_verification(attempt, req_mismatch, db_session)

    # Re-initiate fresh attempt
    attempt2 = create_or_get_payment_attempt(group, p, 10000, "RAZORPAY", "RZP-ATTEMPT-2", db_session)
    attempt2.gateway_order_id = "order_expected_123"
    db_session.commit()

    # 2. Invalid forged signature
    req_bad_sig = PaymentVerifyRequest(
        payment_attempt_id=attempt2.id,
        payment_mode="RAZORPAY",
        razorpay_order_id="order_expected_123",
        razorpay_payment_id="pay_999",
        razorpay_signature="forged_signature_hex"
    )
    with pytest.raises(ValueError, match="Payment signature verification failed"):
        process_payment_verification(attempt2, req_bad_sig, db_session)


def test_host_manual_confirm_flow(db_session):
    """
    Requirement 2 & 5: Only authentic group host can confirm manual UPI payment.
    """
    group = GroupOrder(invite_code="CONFIRM01", title="Host Confirm Test", host_name="Bhavya", delivery_location="Room 5")
    db_session.add(group)
    db_session.flush()

    host_p = GroupParticipant(group_order_id=group.id, display_name="Bhavya", is_host=True)
    roommate_p = GroupParticipant(group_order_id=group.id, display_name="Rahul", is_host=False)
    db_session.add_all([host_p, roommate_p])
    db_session.flush()

    # Add cart item for roommate to have payable share
    from app.models.cart import CartItem
    from app.models.product import Product
    prod = db_session.query(Product).filter(Product.id == "p-maggi").first()
    assert prod is not None

    item = CartItem(
        group_order_id=group.id,
        participant_id=roommate_p.id,
        product_id=prod.id,
        quantity=2,
        unit_price_paise=prod.price_paise
    )
    db_session.add(item)
    db_session.commit()

    # Non-host cannot confirm
    with pytest.raises(ValueError, match="Only the group host can perform manual payment confirmation"):
        host_manual_confirm_upi_payment(
            group=group,
            participant=roommate_p,
            host_participant=roommate_p,
            upi_reference="UTR-12345",
            notes=None,
            db=db_session
        )

    # Legitimate host confirms
    resp = host_manual_confirm_upi_payment(
        group=group,
        participant=roommate_p,
        host_participant=host_p,
        upi_reference="UTR-12345",
        notes="Verified in host PhonePe app",
        db=db_session
    )
    assert resp.status == "PAID"
    assert resp.receipt_id is not None
    assert roommate_p.payment_status == "PAID"
    assert roommate_p.amount_paid_paise > 0


def test_duplicate_callback_idempotency(db_session):
    """
    Requirement 6: Duplicate verification calls do not create duplicate transactions or receipts.
    """
    group = GroupOrder(invite_code="DUP01", title="Dup Order", host_name="Sim Host", delivery_location="Room 6")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="Dup Payer", is_host=True)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 5000, "DEMO", "IDEMP-DUP-1", db_session)
    req = PaymentVerifyRequest(payment_attempt_id=attempt.id, payment_mode="DEMO", demo_outcome="SUCCESS")

    resp1 = process_payment_verification(attempt, req, db_session)
    assert resp1.status == "PAID"

    # Second identical callback
    resp2 = process_payment_verification(attempt, req, db_session)
    assert resp2.status == "PAID"
    assert resp2.receipt_id == resp1.receipt_id

    # Check database transactions count
    txns = db_session.query(PaymentTransaction).filter(PaymentTransaction.payment_attempt_id == attempt.id).all()
    assert len(txns) == 1


def test_razorpay_valid_signature_but_not_captured(db_session, monkeypatch):
    """
    Task 1B: Valid signature alone must not mark uncaptured or failed payment as PAID.
    """
    import hmac
    import hashlib
    from app.config import settings
    import app.services.payment_service as ps

    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_key_123")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "super_secret_rzp_key")

    group = GroupOrder(invite_code="UNCAP01", title="Uncaptured Order", host_name="HostUser", delivery_location="Room 10")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="CardPayer", is_host=False)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 10000, "RAZORPAY", "RZP-UNCAP-1", db_session)
    attempt.gateway_order_id = "order_rzp_uncaptured"
    db_session.commit()

    order_id = "order_rzp_uncaptured"
    pay_id = "pay_uncaptured_123"
    msg = f"{order_id}|{pay_id}".encode("utf-8")
    valid_sig = hmac.new("super_secret_rzp_key".encode("utf-8"), msg, hashlib.sha256).hexdigest()

    # Mock gateway returning payment status as "failed"
    monkeypatch.setattr(
        ps,
        "fetch_razorpay_payment_details",
        lambda pid: {
            "id": pid,
            "order_id": order_id,
            "status": "failed",
            "amount": 10000,
            "currency": "INR"
        }
    )

    req = PaymentVerifyRequest(
        payment_attempt_id=attempt.id,
        payment_mode="RAZORPAY",
        razorpay_order_id=order_id,
        razorpay_payment_id=pay_id,
        razorpay_signature=valid_sig
    )

    with pytest.raises(ValueError, match="Payment is not captured on gateway"):
        process_payment_verification(attempt, req, db_session)

    assert attempt.status == "FAILED"
    assert "not captured" in (attempt.failure_reason or "")


def test_razorpay_amount_and_currency_mismatch(db_session, monkeypatch):
    """
    Task 1B: Valid signature but amount or currency mismatch must be rejected.
    """
    import hmac
    import hashlib
    from app.config import settings
    import app.services.payment_service as ps

    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_key_123")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "super_secret_rzp_key")

    group = GroupOrder(invite_code="MISMATCH1", title="Mismatch Order", host_name="HostUser", delivery_location="Room 10")
    db_session.add(group)
    db_session.flush()

    p = GroupParticipant(group_order_id=group.id, display_name="CardPayer", is_host=False)
    db_session.add(p)
    db_session.commit()

    attempt = create_or_get_payment_attempt(group, p, 10000, "RAZORPAY", "RZP-MISMATCH-1", db_session)
    attempt.gateway_order_id = "order_rzp_mismatch"
    db_session.commit()

    order_id = "order_rzp_mismatch"
    pay_id = "pay_mismatch_123"
    msg = f"{order_id}|{pay_id}".encode("utf-8")
    valid_sig = hmac.new("super_secret_rzp_key".encode("utf-8"), msg, hashlib.sha256).hexdigest()

    # 1. Amount mismatch (expected 10000 paise, gateway returned 5000 paise)
    monkeypatch.setattr(
        ps,
        "fetch_razorpay_payment_details",
        lambda pid: {
            "id": pid,
            "order_id": order_id,
            "status": "captured",
            "amount": 5000,
            "currency": "INR"
        }
    )

    req_amt_mismatch = PaymentVerifyRequest(
        payment_attempt_id=attempt.id,
        payment_mode="RAZORPAY",
        razorpay_order_id=order_id,
        razorpay_payment_id=pay_id,
        razorpay_signature=valid_sig
    )

    with pytest.raises(ValueError, match="Payment amount mismatch"):
        process_payment_verification(attempt, req_amt_mismatch, db_session)

    # 2. Currency mismatch (attempt is INR, gateway is USD)
    attempt2 = create_or_get_payment_attempt(group, p, 10000, "RAZORPAY", "RZP-CURRENCY-2", db_session)
    attempt2.gateway_order_id = order_id
    db_session.commit()

    monkeypatch.setattr(
        ps,
        "fetch_razorpay_payment_details",
        lambda pid: {
            "id": pid,
            "order_id": order_id,
            "status": "captured",
            "amount": 10000,
            "currency": "USD"
        }
    )

    req_curr_mismatch = PaymentVerifyRequest(
        payment_attempt_id=attempt2.id,
        payment_mode="RAZORPAY",
        razorpay_order_id=order_id,
        razorpay_payment_id=pay_id,
        razorpay_signature=valid_sig
    )

    with pytest.raises(ValueError, match="Payment currency mismatch"):
        process_payment_verification(attempt2, req_curr_mismatch, db_session)


def test_payment_verify_endpoint_authorization(client):
    """
    Task 1B: Verify caller authentication:
    - Missing or invalid caller credentials rejected
    - Participant attempting to confirm another participant's payment rejected
    """
    # 1. Create group and two participants
    grp = client.post("/api/v1/groups", json={
        "title": "Auth Security Group",
        "delivery_location": "Hostel B",
        "fee_policy": "EQUAL_SPLIT"
    }).json()

    p1 = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Alice"}).json()
    p2 = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Bob"}).json()

    client.post(
        f"/api/v1/groups/{grp['id']}/cart/items?participant_id={p1['id']}",
        headers={"X-Session-Token": p1["session_token"]},
        json={"product_id": "p-maggi", "quantity": 1}
    )

    # Initiate payment attempt for Alice
    init_resp = client.post(
        "/api/v1/payments/initiate",
        headers={"X-Session-Token": p1["session_token"]},
        json={
            "participant_id": p1["id"],
            "session_token": p1["session_token"],
            "payment_mode": "DEMO"
        }
    ).json()
    attempt_id = init_resp["attempt_id"]

    # Call with missing credentials -> 403
    resp_no_auth = client.post("/api/v1/payments/verify", json={
        "payment_attempt_id": attempt_id,
        "payment_mode": "DEMO",
        "participant_id": p1["id"],
        "demo_outcome": "SUCCESS"
    })
    assert resp_no_auth.status_code == 403
    assert "caller authentication required" in resp_no_auth.json()["detail"].lower()

    # Call with wrong session token (invalid token) -> 403
    resp_bad_token = client.post("/api/v1/payments/verify", json={
        "payment_attempt_id": attempt_id,
        "payment_mode": "DEMO",
        "participant_id": p1["id"],
        "session_token": "completely_fake_token_12345",
        "demo_outcome": "SUCCESS"
    })
    assert resp_bad_token.status_code == 403

    # Bob attempts to confirm Alice's payment with Bob's valid session token -> 403
    resp_impersonate = client.post("/api/v1/payments/verify", json={
        "payment_attempt_id": attempt_id,
        "payment_mode": "DEMO",
        "participant_id": p1["id"],
        "session_token": p2["session_token"],
        "demo_outcome": "SUCCESS"
    })
    assert resp_impersonate.status_code == 403

    # Alice confirms her own payment with her valid session token -> 200
    resp_valid = client.post("/api/v1/payments/verify", json={
        "payment_attempt_id": attempt_id,
        "payment_mode": "DEMO",
        "participant_id": p1["id"],
        "session_token": p1["session_token"],
        "demo_outcome": "SUCCESS"
    })
    assert resp_valid.status_code == 200
    assert resp_valid.json()["status"] == "PAID"


def test_host_confirmation_cross_group_rejected(client):
    """
    Task 1B: A host attempting confirmation in a different group must be rejected.
    """
    # Group A with Host A
    grp_a = client.post("/api/v1/groups", json={
        "title": "Group A",
        "delivery_location": "Hostel A",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    parts_a = client.get(f"/api/v1/groups/{grp_a['id']}/participants").json()
    host_a = parts_a[0]

    # Group B with Host B and Participant B
    grp_b = client.post("/api/v1/groups", json={
        "title": "Group B",
        "delivery_location": "Hostel B",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    parts_b = client.get(f"/api/v1/groups/{grp_b['id']}/participants").json()
    host_b = parts_b[0]

    part_b = client.post(f"/api/v1/groups/{grp_b['invite_code']}/join", json={"display_name": "Member B"}).json()
    client.post(f"/api/v1/groups/{grp_b['id']}/cart/items?participant_id={part_b['id']}", json={
        "product_id": "p-maggi",
        "quantity": 1
    })

    # Host A attempts to confirm Member B's payment in Group B using Host A's session token -> 400 or 403
    resp = client.post("/api/v1/payments/host-manual-confirm", json={
        "participant_id": part_b["id"],
        "host_participant_id": host_a["id"],
        "session_token": grp_a["host_session_token"],
        "upi_reference": "UTR_CROSS_123"
    })
    assert resp.status_code in [400, 403]
    assert "do not belong to the same group" in resp.json()["detail"].lower()


def test_forged_payment_success_and_duplicate_processing_security(client, monkeypatch):
    """
    Task 5 Negative Security Test:
    1. Forged mode switching (verifying live UPI attempt with demo_outcome='SUCCESS') is rejected.
    2. Forged Razorpay signature or missing gateway order is rejected.
    3. Non-host participant calling host-manual-confirm is rejected (400/403).
    4. Duplicate verify requests for the same attempt are completely idempotent.
    """
    from app.config import settings

    # Setup group
    grp = client.post("/api/v1/groups", json={
        "title": "Payment Security Group",
        "delivery_location": "Block D",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid = grp["id"]
    code = grp["invite_code"]
    host_token = grp["host_session_token"]
    host_part_id = grp["host_participant_id"]

    member = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "Test Payer"}).json()
    member_token = member["session_token"]
    member_id = member["id"]

    # Member adds items
    client.post(
        f"/api/v1/groups/{gid}/cart/items",
        headers={"X-Session-Token": member_token},
        json={"product_id": "p-maggi", "quantity": 1}
    )

    # 1. Initiate live UPI payment
    upi_init = client.post(
        "/api/v1/payments/initiate",
        headers={"X-Session-Token": member_token},
        json={"participant_id": member_id, "payment_mode": "UPI_QR"}
    )
    assert upi_init.status_code == 200
    upi_attempt_id = upi_init.json()["attempt_id"]

    # Member tries to verify live UPI attempt by pretending it's a DEMO success -> 400
    forged_demo = client.post(
        "/api/v1/payments/verify",
        headers={"X-Session-Token": member_token},
        json={
            "payment_attempt_id": upi_attempt_id,
            "payment_mode": "DEMO",
            "participant_id": member_id,
            "demo_outcome": "SUCCESS"
        }
    )
    assert forged_demo.status_code == 400
    assert "mismatch" in forged_demo.json()["detail"].lower()

    # 2. Member tries to self-confirm payment via host-manual-confirm -> 400 or 403
    self_confirm = client.post(
        "/api/v1/payments/host-manual-confirm",
        headers={"X-Session-Token": member_token},
        json={
            "participant_id": member_id,
            "host_participant_id": member_id,
            "upi_reference": "FORGED_CONFIRM"
        }
    )
    assert self_confirm.status_code in [400, 403]

    # 3. Razorpay forged signature test
    rzp_init = client.post(
        "/api/v1/payments/initiate",
        headers={"X-Session-Token": member_token},
        json={"participant_id": member_id, "payment_mode": "RAZORPAY"}
    )
    assert rzp_init.status_code == 200
    rzp_attempt_id = rzp_init.json()["attempt_id"]
    rzp_order_id = rzp_init.json()["data"]["razorpay_order_id"]

    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_mock_123")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "super_secret_rzp")

    # Forged signature -> 400
    forged_sig = client.post(
        "/api/v1/payments/verify",
        headers={"X-Session-Token": member_token},
        json={
            "payment_attempt_id": rzp_attempt_id,
            "payment_mode": "RAZORPAY",
            "participant_id": member_id,
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": "pay_fake_999",
            "razorpay_signature": "0000000000000000000000000000000000000000000000000000000000000000"
        }
    )
    assert forged_sig.status_code == 400
    assert "signature" in forged_sig.json()["detail"].lower()

    # 4. Idempotent duplicate verification for DEMO mode
    demo_init = client.post(
        "/api/v1/payments/initiate",
        headers={"X-Session-Token": member_token},
        json={"participant_id": member_id, "payment_mode": "DEMO"}
    )
    assert demo_init.status_code == 200
    demo_attempt_id = demo_init.json()["attempt_id"]

    # First verify call
    v1 = client.post(
        "/api/v1/payments/verify",
        headers={"X-Session-Token": member_token},
        json={
            "payment_attempt_id": demo_attempt_id,
            "payment_mode": "DEMO",
            "participant_id": member_id,
            "demo_outcome": "SUCCESS"
        }
    )
    assert v1.status_code == 200
    assert v1.json()["status"] == "PAID"
    rcpt1 = v1.json()["receipt_id"]

    # Second duplicate verify call
    v2 = client.post(
        "/api/v1/payments/verify",
        headers={"X-Session-Token": member_token},
        json={
            "payment_attempt_id": demo_attempt_id,
            "payment_mode": "DEMO",
            "participant_id": member_id,
            "demo_outcome": "SUCCESS"
        }
    )
    assert v2.status_code == 200
    assert v2.json()["status"] == "PAID"
    assert v2.json()["receipt_id"] == rcpt1


