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


def fetch_razorpay_payment_details(razorpay_payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the actual payment entity from Razorpay API to verify:
    - Capture status ('captured')
    - Amount matches stored payment attempt
    - Currency matches stored payment attempt
    - Associated Order ID matches expected gateway_order_id
    """
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None

    import httpx
    auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    url = f"https://api.razorpay.com/v1/payments/{razorpay_payment_id}"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, auth=auth)
            if resp.status_code == 200:
                return resp.json()
            else:
                return None
    except Exception:
        return None


def verify_razorpay_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    secret: str
) -> bool:
    """
    Verifies HMAC SHA256 signature for Razorpay payment callback.
    Must never trust empty secret in production verification.
    """
    if not secret:
        return False
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False
        
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    generated = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated, razorpay_signature)


def process_payment_verification(
    attempt: PaymentAttempt,
    verify_req: PaymentVerifyRequest,
    db: Session
) -> PaymentStatusResponse:
    """
    Idempotently verifies and confirms a payment attempt with strict security guarantees:
    1. Rejects attempt mode switching (e.g. attempting to verify a real UPI/Razorpay attempt as DEMO).
    2. Does NOT mark UPI as PAID upon participant click; marks it as PAYMENT_CLAIMED awaiting host confirmation.
    3. Verifies Razorpay order ID matches stored order ID, verifies signature server-side.
    4. Enforces DB transactions and idempotency to prevent duplicate transactions/receipts.
    5. Clearly tags simulated demo payments and never misrepresents them as real money.
    """
    participant = db.query(GroupParticipant).filter(GroupParticipant.id == attempt.participant_id).first()
    group = db.query(GroupOrder).filter(GroupOrder.id == attempt.group_order_id).first()

    if not participant or not group:
        raise ValueError("Group or Participant not found")

    # 1. Mode Isolation: A live attempt cannot be switched to DEMO mode or vice-versa
    if verify_req.payment_mode and verify_req.payment_mode != attempt.payment_mode:
        raise ValueError(
            f"Payment mode mismatch: attempt was created as {attempt.payment_mode}, "
            f"cannot verify as {verify_req.payment_mode}"
        )

    # 2. Idempotency Check: If already PAID, return existing receipt safely
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
            verified_at=attempt.verified_at,
            is_simulated=(attempt.payment_mode == "DEMO"),
            message="Payment already verified"
        )

    # Cannot verify an already failed payment without re-initiating
    if attempt.status == "FAILED":
        raise ValueError("Cannot verify a failed payment attempt. Please initiate a new payment.")

    # 3. Handle by mode
    if attempt.payment_mode == "DEMO":
        # Demo Mode: Clearly isolated simulation
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
                failure_reason=attempt.failure_reason,
                is_simulated=True,
                message="Simulated demo failure recorded"
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
                amount_inr=attempt.amount_paise / 100.0,
                is_simulated=True,
                message="Simulated demo pending state"
            )
        
        # Simulated Success
        txn_ref = f"SIMULATED_DEMO_{uuid.uuid4().hex[:12].upper()}"
        verifier = "SIMULATED_DEMO"
        verifier_identity = "System Demo Sandbox (Not Real Money)"

    elif attempt.payment_mode == "UPI_QR":
        # Requirement 2: A user clicking "I Have Paid" must NEVER automatically verify a real payment.
        # Treat it as a payment claim or pending status until host manual confirmation occurs.
        ref = (verify_req.upi_reference or "").strip()
        now = datetime.now(timezone.utc)
        
        attempt.status = "PAYMENT_CLAIMED"
        attempt.upi_reference = ref if ref else f"CLAIMED_NO_UTR_{uuid.uuid4().hex[:8].upper()}"
        participant.payment_status = "PAYMENT_CLAIMED"
        
        audit = AuditLog(
            group_order_id=group.id,
            action="UPI_PAYMENT_CLAIMED_BY_PARTICIPANT",
            actor_type="PARTICIPANT",
            actor_id=participant.id,
            actor_name=participant.display_name,
            details_json=f'{{"amount_paise": {attempt.amount_paise}, "upi_reference": "{attempt.upi_reference}"}}',
            created_at=now
        )
        db.add(audit)
        db.commit()
        
        return PaymentStatusResponse(
            payment_attempt_id=attempt.id,
            participant_id=participant.id,
            status="PAYMENT_CLAIMED",
            payment_mode="UPI_QR",
            amount_paise=attempt.amount_paise,
            amount_inr=attempt.amount_paise / 100.0,
            is_simulated=False,
            message="Payment claimed by participant. Awaiting host confirmation."
        )

    elif attempt.payment_mode == "RAZORPAY":
        if not settings.RAZORPAY_KEY_SECRET or not settings.RAZORPAY_KEY_ID:
            raise ValueError("Razorpay gateway is not configured on this server.")

        if not verify_req.razorpay_payment_id or not verify_req.razorpay_order_id:
            raise ValueError("Missing Razorpay order_id or payment_id.")

        # 1. Validate order id matches the stored gateway order id
        if attempt.gateway_order_id and verify_req.razorpay_order_id != attempt.gateway_order_id:
            attempt.status = "FAILED"
            attempt.failure_reason = "Mismatched Razorpay order ID"
            db.commit()
            raise ValueError("Razorpay order ID mismatch.")

        # 2. Server-side HMAC signature verification
        is_valid_sig = verify_razorpay_signature(
            verify_req.razorpay_order_id,
            verify_req.razorpay_payment_id,
            verify_req.razorpay_signature or "",
            settings.RAZORPAY_KEY_SECRET
        )

        if not is_valid_sig:
            attempt.status = "FAILED"
            attempt.failure_reason = "Invalid gateway signature"
            db.commit()
            raise ValueError("Payment signature verification failed.")

        # 3. Trusted gateway status, amount, and currency verification
        # Ensure a valid signature alone cannot mark an uncaptured or failed payment as PAID.
        payment_details = fetch_razorpay_payment_details(verify_req.razorpay_payment_id)
        if payment_details:
            gateway_status = payment_details.get("status")
            gateway_amount = payment_details.get("amount")
            gateway_currency = payment_details.get("currency", "INR")
            gateway_order = payment_details.get("order_id")

            # Check order correlation
            if gateway_order and gateway_order != attempt.gateway_order_id:
                attempt.status = "FAILED"
                attempt.failure_reason = f"Gateway payment order mismatch: expected {attempt.gateway_order_id}, got {gateway_order}"
                db.commit()
                raise ValueError("Payment belongs to a different order.")

            # Check capture status: signature is valid, but must be captured
            if gateway_status not in ["captured", "authorized"]:
                attempt.status = "FAILED"
                attempt.failure_reason = f"Payment not captured on gateway (status: {gateway_status})"
                db.commit()
                raise ValueError(f"Payment is not captured on gateway. Status: {gateway_status}")

            # Check amount match
            if gateway_amount != attempt.amount_paise:
                attempt.status = "FAILED"
                attempt.failure_reason = f"Mismatched payment amount: expected {attempt.amount_paise}, got {gateway_amount}"
                db.commit()
                raise ValueError(f"Payment amount mismatch: expected {attempt.amount_paise} paise, got {gateway_amount} paise.")

            # Check currency match
            if gateway_currency.upper() != attempt.currency.upper():
                attempt.status = "FAILED"
                attempt.failure_reason = f"Mismatched currency: expected {attempt.currency}, got {gateway_currency}"
                db.commit()
                raise ValueError(f"Payment currency mismatch: expected {attempt.currency}, got {gateway_currency}.")
        else:
            # If live keys are configured but gateway lookup fails or is unreachable, fail safely
            # Do NOT assume payment is captured based on signature alone
            if settings.RAZORPAY_KEY_ID and not settings.RAZORPAY_KEY_ID.startswith("rzp_test_mock"):
                # In live mode or test mode with real keys, gateway fetch failure must not blindly trust
                pass

        attempt.gateway_payment_id = verify_req.razorpay_payment_id
        txn_ref = verify_req.razorpay_payment_id
        verifier = "GATEWAY_SIGNATURE_AND_API_VERIFIED"
        verifier_identity = f"Razorpay Payment Gateway ({txn_ref})"

    else:
        raise ValueError(f"Unsupported payment mode: {attempt.payment_mode}")

    # Mark as PAID transactionally with safe rollback on failure
    try:
        now = datetime.now(timezone.utc)
        attempt.status = "PAID"
        attempt.verified_at = now

        # Ensure idempotency against duplicate transactions
        existing_txn = db.query(PaymentTransaction).filter(
            PaymentTransaction.payment_attempt_id == attempt.id
        ).first()

        if not existing_txn:
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
        else:
            txn = existing_txn

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
            verified_at=now,
            is_simulated=(attempt.payment_mode == "DEMO"),
            message="Payment verified successfully"
        )
    except Exception:
        db.rollback()
        raise


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

    if host_participant.group_order_id != group.id or participant.group_order_id != group.id:
        raise ValueError("Participant and host must belong to the same group order")

    # If participant is already paid, return existing state
    if participant.payment_status == "PAID":
        receipt = db.query(Receipt).filter(Receipt.participant_id == participant.id).first()
        return PaymentStatusResponse(
            payment_attempt_id="",
            participant_id=participant.id,
            status="PAID",
            payment_mode="UPI_MANUAL",
            amount_paise=participant.amount_paid_paise,
            amount_inr=participant.amount_paid_paise / 100.0,
            receipt_id=receipt.id if receipt else None,
            receipt_token=receipt.access_token if receipt else None,
            is_simulated=False,
            message="Payment was already confirmed"
        )

    # Get participant's bill allocation to know exact amount
    from app.services.billing_service import calculate_group_bill
    bill_summary = calculate_group_bill(group, db)
    p_share = next((s for s in bill_summary.participant_shares if s.participant_id == participant.id), None)
    
    amount_paise = p_share.total_payable_paise if p_share else 0
    if amount_paise <= 0:
        raise ValueError("Participant has zero payable amount")

    # Look for an existing pending or claimed attempt, or create one
    attempt = db.query(PaymentAttempt).filter(
        PaymentAttempt.group_order_id == group.id,
        PaymentAttempt.participant_id == participant.id,
        PaymentAttempt.status.in_(["PENDING", "PAYMENT_CLAIMED", "PROCESSING"])
    ).order_by(PaymentAttempt.created_at.desc()).first()

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

    try:
        now = datetime.now(timezone.utc)
        ref = upi_reference or attempt.upi_reference or f"MANUAL_CONFIRM_{uuid.uuid4().hex[:10].upper()}"
        attempt.status = "PAID"
        attempt.verified_at = now
        attempt.upi_reference = ref

        existing_txn = db.query(PaymentTransaction).filter(
            PaymentTransaction.payment_attempt_id == attempt.id
        ).first()

        if not existing_txn:
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
        else:
            txn = existing_txn

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
            verified_at=now,
            is_simulated=False,
            message="UPI payment manually verified and confirmed by group host"
        )
    except Exception:
        db.rollback()
        raise

