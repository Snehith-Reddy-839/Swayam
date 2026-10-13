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

    # 2. Test simulated success
    req_succ = PaymentVerifyRequest(payment_attempt_id=attempt.id, payment_mode="DEMO", demo_outcome="SUCCESS")
    resp_succ = process_payment_verification(attempt, req_succ, db_session)
    assert resp_succ.status == "PAID"
    assert p.payment_status == "PAID"
    assert p.amount_paid_paise == 8000
    assert resp_succ.receipt_id is not None


def test_razorpay_signature_validation():
    # Valid signature check logic
    order_id = "order_12345"
    payment_id = "pay_67890"
    secret = "test_secret_key"
    import hmac, hashlib
    valid_sig = hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(order_id, payment_id, valid_sig, secret) is True
    assert verify_razorpay_signature(order_id, payment_id, "invalid_signature_hex", secret) is False
