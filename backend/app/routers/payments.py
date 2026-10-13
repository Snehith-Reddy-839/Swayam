from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import GroupOrder, GroupParticipant
from app.models.payment import PaymentAttempt
from app.schemas.payment import (
    PaymentInitiateRequest,
    UPIQRDetailsResponse,
    RazorpayOrderResponse,
    PaymentVerifyRequest,
    PaymentStatusResponse,
    ManualUPIConfirmRequest,
)
from app.services.billing_service import calculate_group_bill
from app.services.payment_service import (
    create_or_get_payment_attempt,
    generate_upi_qr_details,
    create_razorpay_order_payload,
    process_payment_verification,
    host_manual_confirm_upi_payment,
)
from app.services.websocket_manager import manager

router = APIRouter(prefix="/payments", tags=["Payments & Checkout"])


@router.post("/initiate")
def initiate_payment(
    req: PaymentInitiateRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_caller_participant, resolve_caller_identity

    participant = db.query(GroupParticipant).filter(GroupParticipant.id == req.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    group = db.query(GroupOrder).filter(GroupOrder.id == participant.group_order_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group order not found")

    # Authorize caller
    user, guest = resolve_caller_identity(
        authorization=authorization,
        session_token=req.session_token,
        x_session_token=x_session_token,
        db=db
    )
    if user or guest:
        resolve_caller_participant(
            group_order_id=group.id,
            authorization=authorization,
            session_token=req.session_token,
            x_session_token=x_session_token,
            participant_id_hint=participant.id,
            db=db
        )
    else:
        if participant.guest_session_id or participant.user_id:
            raise HTTPException(
                status_code=401,
                detail="Authentication required: Valid session token required to initiate payment for this participant"
            )

    # Calculate exact bill share
    bill_summary = calculate_group_bill(group, db)
    p_share = next((s for s in bill_summary.participant_shares if s.participant_id == participant.id), None)
    if not p_share or p_share.total_payable_paise <= 0:
        raise HTTPException(status_code=400, detail="No payable amount for this participant")

    amount_paise = p_share.total_payable_paise

    attempt = create_or_get_payment_attempt(
        group=group,
        participant=participant,
        amount_paise=amount_paise,
        payment_mode=req.payment_mode,
        idempotency_key=req.idempotency_key,
        db=db
    )

    if req.payment_mode == "UPI_QR":
        qr_details = generate_upi_qr_details(group, participant, attempt)
        return {
            "mode": "UPI_QR",
            "attempt_id": attempt.id,
            "data": qr_details
        }
    elif req.payment_mode == "RAZORPAY":
        razorpay_details = create_razorpay_order_payload(group, participant, attempt)
        return {
            "mode": "RAZORPAY",
            "attempt_id": attempt.id,
            "data": razorpay_details
        }
    elif req.payment_mode == "DEMO":
        qr_details = generate_upi_qr_details(group, participant, attempt)
        return {
            "mode": "DEMO",
            "attempt_id": attempt.id,
            "amount_paise": attempt.amount_paise,
            "amount_inr": attempt.amount_paise / 100.0,
            "data": qr_details,
            "demo_notice": "DEMONSTRATION MODE: Simulated instant or delayed payment. No real money will be deducted."
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment mode")


@router.post("/verify", response_model=PaymentStatusResponse)
async def verify_payment(
    req: PaymentVerifyRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    attempt = db.query(PaymentAttempt).filter(PaymentAttempt.id == req.payment_attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

    participant = db.query(GroupParticipant).filter(GroupParticipant.id == attempt.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Requirement B: Authenticate and authorize payment-verification requests.
    # The participant identity must come from validated server-side credentials, not merely a participant ID.
    if req.participant_id and req.participant_id != participant.id:
        raise HTTPException(status_code=403, detail="Unauthorized: Participant ID mismatch with payment attempt")

    from app.services.auth_service import decode_access_token
    from app.models.user import GuestSession
    caller_authenticated = False
    
    # 1. Check guest session token if participant has a guest session
    token_to_check = req.session_token or x_session_token
    if not token_to_check and authorization and authorization.startswith("Guest "):
        token_to_check = authorization.split(" ")[1]

    if token_to_check:
        guest_sess = db.query(GuestSession).filter(GuestSession.session_token == token_to_check).first()
        if not guest_sess:
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid guest session token")
        if participant.guest_session_id and participant.guest_session_id != guest_sess.id:
            raise HTTPException(status_code=403, detail="Unauthorized: Session does not own this payment attempt")
        if participant.guest_session_id == guest_sess.id:
            caller_authenticated = True

    # 2. Check registered user bearer token if provided
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization.split(" ")[1])
        if not payload or "sub" not in payload:
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid bearer token")
        if participant.user_id and participant.user_id != payload["sub"]:
            raise HTTPException(status_code=403, detail="Unauthorized: User account mismatch with payment attempt")
        if participant.user_id == payload["sub"]:
            caller_authenticated = True

    # If the participant has an associated guest_session_id or user_id, verification MUST be authenticated
    if (participant.guest_session_id or participant.user_id) and not caller_authenticated:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Valid caller authentication required to verify this payment attempt"
        )

    try:
        status_resp = process_payment_verification(attempt, req, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcast status change
    await manager.broadcast_to_group(attempt.group_order_id, {
        "event": "payment_status_changed",
        "participant_id": attempt.participant_id,
        "payment_status": status_resp.status,
        "amount_paise": status_resp.amount_paise,
        "payment_mode": status_resp.payment_mode,
        "receipt_id": status_resp.receipt_id
    })

    return status_resp


@router.post("/host-manual-confirm", response_model=PaymentStatusResponse)
async def host_confirm_upi(
    req: ManualUPIConfirmRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    participant = db.query(GroupParticipant).filter(GroupParticipant.id == req.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    host_participant = db.query(GroupParticipant).filter(GroupParticipant.id == req.host_participant_id).first()
    if not host_participant:
        raise HTTPException(status_code=404, detail="Host participant not found")

    if not host_participant.is_host:
        raise HTTPException(status_code=400, detail="Only the group host can perform manual payment confirmation")

    if host_participant.group_order_id != participant.group_order_id:
        raise HTTPException(status_code=400, detail="Participant and host do not belong to the same group")

    # Requirement B: Authenticate host session or token strictly
    from app.services.auth_service import decode_access_token
    from app.models.user import GuestSession
    host_authenticated = False

    host_token = req.session_token or x_session_token
    if not host_token and authorization and authorization.startswith("Guest "):
        host_token = authorization.split(" ")[1]

    if host_token:
        guest_sess = db.query(GuestSession).filter(GuestSession.session_token == host_token).first()
        if not guest_sess:
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid host session token")
        if host_participant.guest_session_id and host_participant.guest_session_id != guest_sess.id:
            raise HTTPException(status_code=403, detail="Unauthorized: Caller session does not match host session")
        if host_participant.guest_session_id == guest_sess.id:
            host_authenticated = True

    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization.split(" ")[1])
        if not payload or "sub" not in payload:
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid host token")
        if host_participant.user_id and host_participant.user_id != payload["sub"]:
            raise HTTPException(status_code=403, detail="Unauthorized: User does not match host account")
        if host_participant.user_id == payload["sub"]:
            host_authenticated = True

    # If the host participant has an associated guest_session_id or user_id, confirmation MUST be authenticated
    if (host_participant.guest_session_id or host_participant.user_id) and not host_authenticated:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Valid host authentication required to confirm payments"
        )

    group = db.query(GroupOrder).filter(GroupOrder.id == participant.group_order_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    try:
        status_resp = host_manual_confirm_upi_payment(
            group=group,
            participant=participant,
            host_participant=host_participant,
            upi_reference=req.upi_reference,
            notes=req.notes,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await manager.broadcast_to_group(group.id, {
        "event": "payment_status_changed",
        "participant_id": participant.id,
        "payment_status": "PAID",
        "amount_paise": status_resp.amount_paise,
        "payment_mode": "UPI_MANUAL",
        "verified_by_host": True,
        "receipt_id": status_resp.receipt_id
    })

    return status_resp


@router.get("/attempt/{attempt_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(
    attempt_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_caller_identity

    attempt = db.query(PaymentAttempt).filter(PaymentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

    # Authorize caller: must be the attempt's participant OR the group host
    user, guest = resolve_caller_identity(
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )
    if not (user or guest):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view payment attempt status"
        )

    part = attempt.participant
    is_owner = (user and part.user_id is not None and part.user_id == user.id) or (guest and part.guest_session_id is not None and part.guest_session_id == guest.id)
    is_host = False
    if user:
        is_host = bool(db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == attempt.group_order_id,
            GroupParticipant.user_id == user.id,
            GroupParticipant.is_host == True
        ).first())
    elif guest:
        is_host = bool(db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == attempt.group_order_id,
            GroupParticipant.guest_session_id == guest.id,
            GroupParticipant.is_host == True
        ).first())

    if not is_owner and not is_host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You cannot access payment status for another participant"
        )

    from app.models.receipt import Receipt
    receipt = db.query(Receipt).filter(Receipt.participant_id == attempt.participant_id).first()

    return PaymentStatusResponse(
        payment_attempt_id=attempt.id,
        participant_id=attempt.participant_id,
        status=attempt.status,
        payment_mode=attempt.payment_mode,
        amount_paise=attempt.amount_paise,
        amount_inr=attempt.amount_paise / 100.0,
        receipt_id=receipt.id if receipt else None,
        receipt_token=receipt.access_token if receipt else None,
        failure_reason=attempt.failure_reason,
        verified_at=attempt.verified_at
    )
