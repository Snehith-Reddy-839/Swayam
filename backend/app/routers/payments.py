from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
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
def initiate_payment(req: PaymentInitiateRequest, db: Session = Depends(get_db)):
    participant = db.query(GroupParticipant).filter(GroupParticipant.id == req.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    group = db.query(GroupOrder).filter(GroupOrder.id == participant.group_order_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group order not found")

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
async def verify_payment(req: PaymentVerifyRequest, db: Session = Depends(get_db)):
    attempt = db.query(PaymentAttempt).filter(PaymentAttempt.id == req.payment_attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

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
async def host_confirm_upi(req: ManualUPIConfirmRequest, db: Session = Depends(get_db)):
    participant = db.query(GroupParticipant).filter(GroupParticipant.id == req.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    host_participant = db.query(GroupParticipant).filter(GroupParticipant.id == req.host_participant_id).first()
    if not host_participant:
        host_participant = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == participant.group_order_id,
            GroupParticipant.is_host == True
        ).first()

    if not host_participant:
        raise HTTPException(status_code=404, detail="Host participant not found")

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
def get_payment_status(attempt_id: str, db: Session = Depends(get_db)):
    attempt = db.query(PaymentAttempt).filter(PaymentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

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
