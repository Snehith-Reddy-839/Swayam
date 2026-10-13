import io
import base64
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
import qrcode
from sqlalchemy.orm import Session

from app.config import settings
from app.models.group import GroupOrder, GroupParticipant
from app.models.payment import PaymentAttempt, PaymentTransaction
from app.models.receipt import Receipt
from app.models.audit import AuditLog
from app.schemas.payment import (
    UPIQRDetailsResponse,
    RazorpayOrderResponse,
    PaymentVerifyRequest,
    PaymentStatusResponse,
)
from app.services.receipt_service import generate_receipt_for_payment


def create_or_get_payment_attempt(
    group: GroupOrder,
    participant: GroupParticipant,
    amount_paise: int,
    payment_mode: str,
    idempotency_key: Optional[str],
    db: Session
) -> PaymentAttempt:
    """Creates a new payment attempt or returns existing if idempotency key matches."""
    if not idempotency_key:
        idempotency_key = f"IDEMP-{uuid.uuid4().hex[:16]}"

    # Check for existing attempt with same idempotency key
    existing = db.query(PaymentAttempt).filter(PaymentAttempt.idempotency_key == idempotency_key).first()
    if existing:
        return existing

    attempt = PaymentAttempt(
        group_order_id=group.id,
        participant_id=participant.id,
        idempotency_key=idempotency_key,
        amount_paise=amount_paise,
        currency="INR",
        payment_mode=payment_mode,
        status="PENDING"
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def generate_upi_qr_details(
    group: GroupOrder,
    participant: GroupParticipant,
    attempt: PaymentAttempt
) -> UPIQRDetailsResponse:
    """
    Generates standard NPCI UPI payment URI and returns base64 PNG QR code data URL.
    UPI URI specification:
    upi://pay?pa=<vpa>&pn=<payee_name>&am=<amount>&cu=INR&tr=<ref>&tn=<note>
    """
    amount_inr = attempt.amount_paise / 100.0
    amount_str = f"{amount_inr:.2f}"
    txn_ref = f"MM{attempt.id.replace('-', '')[:16].upper()}"
    note = f"MunchMate {group.title[:20]} - {participant.display_name[:15]}"
    
    # URL encode parameters
    import urllib.parse
    encoded_pn = urllib.parse.quote(settings.UPI_PAYEE_NAME)
    encoded_tn = urllib.parse.quote(note)
    
    upi_uri = (
        f"upi://pay?pa={settings.UPI_VPA}&pn={encoded_pn}"
        f"&am={amount_str}&cu=INR&tr={txn_ref}&tn={encoded_tn}"
    )

    # Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1A1A1A", back_color="#FFFFFF")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_qr = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_data_url = f"data:image/png;base64,{b64_qr}"

    instructions = [
        f"1. Open any UPI App (Google Pay, PhonePe, Paytm, CRED).",
        f"2. Scan this QR code or tap 'Open UPI App' on mobile.",
        f"3. Verify recipient is '{settings.UPI_PAYEE_NAME}' ({settings.UPI_VPA}).",
        f"4. Confirm payment of ₹{amount_str}.",
        f"5. Once paid, click 'I Have Paid' below for instant confirmation.",
    ]

    return UPIQRDetailsResponse(
        payment_attempt_id=attempt.id,
        upi_uri=upi_uri,
        qr_data_url=qr_data_url,
        vpa=settings.UPI_VPA,
        payee_name=settings.UPI_PAYEE_NAME,
        amount_paise=attempt.amount_paise,
        amount_inr=amount_inr,
        transaction_ref=txn_ref,
        instructions=instructions
    )


def create_razorpay_order_payload(
    group: GroupOrder,
    participant: GroupParticipant,
    attempt: PaymentAttempt
) -> RazorpayOrderResponse:
    """Generates Razorpay order configuration."""
    if not settings.RAZORPAY_KEY_ID:
        # Mock Razorpay order ID in demo mode
        mock_order_id = f"order_demo_{uuid.uuid4().hex[:14]}"
        attempt.gateway_order_id = mock_order_id
        return RazorpayOrderResponse(
            payment_attempt_id=attempt.id,
            key_id="rzp_test_demo_mode_key",
            razorpay_order_id=mock_order_id,
            amount_paise=attempt.amount_paise,
            currency="INR",
            prefill_name=participant.display_name
        )

    # If live Razorpay keys are configured:
    import httpx
    auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    order_data = {
        "amount": attempt.amount_paise,
        "currency": "INR",
        "receipt": f"rcpt_{attempt.id[:10]}",
        "notes": {
            "group_order_id": group.id,
            "participant_id": participant.id,
            "group_title": group.title
        }
    }
    
    with httpx.Client() as client:
        resp = client.post("https://api.razorpay.com/v1/orders", json=order_data, auth=auth)
        if resp.status_code in [200, 201]:
            data = resp.json()
            order_id = data["id"]
            attempt.gateway_order_id = order_id
            return RazorpayOrderResponse(
                payment_attempt_id=attempt.id,
                key_id=settings.RAZORPAY_KEY_ID,
                razorpay_order_id=order_id,
                amount_paise=attempt.amount_paise,
                currency="INR",
                prefill_name=participant.display_name
            )
        else:
            raise Exception(f"Razorpay order creation failed: {resp.text}")


def verify_razorpay_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    secret: str
) -> bool:
    """Verifies HMAC SHA256 signature for Razorpay payment callback."""
    if not secret:
        # If in demo mode with test keys, accept demo signature
        return razorpay_signature.startswith("demo_sig_") or razorpay_signature == "valid"
        
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    generated = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated, razorpay_signature)


def process_payment_verification(
    attempt: PaymentAttempt,
    verify_req: PaymentVerifyRequest,
    db: Session
) -> PaymentStatusResponse:
    """
    Idempotently verifies and confirms a payment attempt.
    Creates PaymentTransaction, updates Participant status to PAID,
    and generates an immutable Digital Receipt.
    """
    participant = db.query(GroupParticipant).filter(GroupParticipant.id == attempt.participant_id).first()
    group = db.query(GroupOrder).filter(GroupOrder.id == attempt.group_order_id).first()

    if not participant or not group:
        raise ValueError("Group or Participant not found")

    # If already paid, return existing receipt
    if attempt.status == "PAID":
        receipt = db.query(Receipt).filter(Receipt.participant_id == participant.id).first()
        return PaymentStatusResponse(
            payment_attempt_id=attempt.id,
            participant_id=participant.id,
            status="PAID",
            payment_mode=attempt.payment_mode,
            amount_paise=attempt.amount_paise,
            amount_inr=attempt.amount_paise / 100.0,
            receipt_id=receipt.id if receipt else None,
            receipt_token=receipt.access_token if receipt else None,
            verified_at=attempt.verified_at
        )

    # Check payment mode verification logic
    if attempt.payment_mode == "DEMO" or verify_req.payment_mode == "DEMO":
        if verify_req.demo_outcome == "FAILURE":
            attempt.status = "FAILED"
            attempt.failure_reason = "Simulated bank payment failure in demo mode"
            participant.payment_status = "FAILED"
            db.commit()
            return PaymentStatusResponse(
                payment_attempt_id=attempt.id,
                participant_id=participant.id,
                status="FAILED",
                payment_mode="DEMO",
                amount_paise=attempt.amount_paise,
                amount_inr=attempt.amount_paise / 100.0,
                failure_reason=attempt.failure_reason
            )
        elif verify_req.demo_outcome == "PENDING":
            attempt.status = "PROCESSING"
            participant.payment_status = "PROCESSING"
            db.commit()
            return PaymentStatusResponse(
                payment_attempt_id=attempt.id,
                participant_id=participant.id,
                status="PROCESSING",
                payment_mode="DEMO",
                amount_paise=attempt.amount_paise,
                amount_inr=attempt.amount_paise / 100.0
            )
        # Otherwise SUCCESS
        txn_ref = f"DEMO_TXN_{uuid.uuid4().hex[:12].upper()}"
        verifier = "DEMO_SIMULATION"
        verifier_identity = "System Demo Simulator"

    elif attempt.payment_mode == "RAZORPAY":
        if not verify_req.razorpay_payment_id or not verify_req.razorpay_order_id:
            raise ValueError("Missing Razorpay order_id or payment_id")

        is_valid = verify_razorpay_signature(
            verify_req.razorpay_order_id,
            verify_req.razorpay_payment_id,
            verify_req.razorpay_signature or "",
            settings.RAZORPAY_KEY_SECRET
        )

        if not is_valid:
            attempt.status = "FAILED"
            attempt.failure_reason = "Invalid gateway signature"
            db.commit()
            raise ValueError("Payment signature verification failed")

        attempt.gateway_payment_id = verify_req.razorpay_payment_id
        txn_ref = verify_req.razorpay_payment_id
        verifier = "GATEWAY_SIGNATURE"
        verifier_identity = f"Razorpay Payment Gateway ({txn_ref})"

    elif attempt.payment_mode == "UPI_QR":
        # In UPI QR mode: if user clicked "I Have Paid" or entered UTR,
        # we mark as PAID in demo mode or host-confirmed
        txn_ref = verify_req.upi_reference or f"UPI_UTR_{uuid.uuid4().hex[:12].upper()}"
        attempt.upi_reference = txn_ref
        verifier = "UPI_INTENT_USER_CONFIRMED"
        verifier_identity = f"User Confirmed UPI UTR: {txn_ref}"

    else:
        raise ValueError(f"Unsupported payment mode: {attempt.payment_mode}")

    # Mark as PAID transactionally
    now = datetime.now(timezone.utc)
    attempt.status = "PAID"
    attempt.verified_at = now

    # Create PaymentTransaction
    txn = PaymentTransaction(
        group_order_id=group.id,
        participant_id=participant.id,
        payment_attempt_id=attempt.id,
        amount_paise=attempt.amount_paise,
        transaction_reference=txn_ref,
        verified_by=verifier,
        verifier_identity=verifier_identity,
        created_at=now
    )
    db.add(txn)
    db.flush()

    # Update participant record
    participant.payment_status = "PAID"
    participant.amount_paid_paise = attempt.amount_paise

    # Generate Digital Receipt
    receipt = generate_receipt_for_payment(group, participant, txn, db)

    # Log audit event
    audit = AuditLog(
        group_order_id=group.id,
        action="PAYMENT_VERIFIED",
        actor_type="SYSTEM",
        actor_id=participant.id,
        actor_name=participant.display_name,
        details_json=f'{{"amount_paise": {attempt.amount_paise}, "mode": "{attempt.payment_mode}", "ref": "{txn_ref}", "verifier": "{verifier}"}}',
        created_at=now
    )
    db.add(audit)
    db.commit()

    return PaymentStatusResponse(
        payment_attempt_id=attempt.id,
        participant_id=participant.id,
        status="PAID",
        payment_mode=attempt.payment_mode,
        amount_paise=attempt.amount_paise,
        amount_inr=attempt.amount_paise / 100.0,
        receipt_id=receipt.id,
        receipt_token=receipt.access_token,
        verified_at=now
    )


def host_manual_confirm_upi_payment(
    group: GroupOrder,
    participant: GroupParticipant,
    host_participant: GroupParticipant,
    upi_reference: Optional[str],
    notes: Optional[str],
    db: Session
) -> PaymentStatusResponse:
    """
    Host manually marks a participant's UPI payment as received on their phone.
    Explicitly labeled as manual confirmation, logged with timestamp and host name.
    """
    if not host_participant.is_host:
        raise ValueError("Only the group host can perform manual payment confirmation")

    # Get participant's bill allocation to know exact amount
    from app.services.billing_service import calculate_group_bill
    bill_summary = calculate_group_bill(group, db)
    p_share = next((s for s in bill_summary.participant_shares if s.participant_id == participant.id), None)
    
    amount_paise = p_share.total_payable_paise if p_share else 0
    if amount_paise <= 0:
        raise ValueError("Participant has zero payable amount")

    # Create PaymentAttempt if not exists
    attempt = db.query(PaymentAttempt).filter(
        PaymentAttempt.group_order_id == group.id,
        PaymentAttempt.participant_id == participant.id,
        PaymentAttempt.status == "PENDING"
    ).first()

    if not attempt:
        attempt = PaymentAttempt(
            group_order_id=group.id,
            participant_id=participant.id,
            idempotency_key=f"MANUAL-{uuid.uuid4().hex[:16]}",
            amount_paise=amount_paise,
            currency="INR",
            payment_mode="UPI_MANUAL",
            status="PENDING"
        )
        db.add(attempt)
        db.flush()

    now = datetime.now(timezone.utc)
    ref = upi_reference or f"MANUAL_CONFIRM_{uuid.uuid4().hex[:10].upper()}"
    attempt.status = "PAID"
    attempt.verified_at = now
    attempt.upi_reference = ref

    txn = PaymentTransaction(
        group_order_id=group.id,
        participant_id=participant.id,
        payment_attempt_id=attempt.id,
        amount_paise=amount_paise,
        transaction_reference=ref,
        verified_by="HOST_MANUAL",
        verifier_identity=f"Host: {host_participant.display_name} (Manual UPI check)",
        created_at=now
    )
    db.add(txn)
    db.flush()

    participant.payment_status = "PAID"
    participant.amount_paid_paise = amount_paise

    receipt = generate_receipt_for_payment(group, participant, txn, db)

    audit = AuditLog(
        group_order_id=group.id,
        action="PAYMENT_CONFIRMED_MANUALLY_BY_HOST",
        actor_type="HOST",
        actor_id=host_participant.id,
        actor_name=host_participant.display_name,
        details_json=f'{{"amount_paise": {amount_paise}, "ref": "{ref}", "notes": "{notes or ""}"}}',
        created_at=now
    )
    db.add(audit)
    db.commit()

    return PaymentStatusResponse(
        payment_attempt_id=attempt.id,
        participant_id=participant.id,
        status="PAID",
        payment_mode="UPI_MANUAL",
        amount_paise=amount_paise,
        amount_inr=amount_paise / 100.0,
        receipt_id=receipt.id,
        receipt_token=receipt.access_token,
        verified_at=now
    )
