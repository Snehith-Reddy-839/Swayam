import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import GroupOrder, GroupParticipant
from app.models.order import MerchantOrder
from app.models.audit import AuditLog
from app.schemas.order import (
    MerchantOrderCreateRequest,
    MerchantOrderStatusUpdateRequest,
    MerchantOrderResponse,
)
from app.services.websocket_manager import manager
from app.services.billing_service import calculate_group_bill

router = APIRouter(prefix="/groups/{group_id}/merchant-order", tags=["Merchant Order Tracking"])


@router.post("", response_model=MerchantOrderResponse)
async def record_merchant_order_placement(
    group_id: str,
    req: MerchantOrderCreateRequest,
    host_participant_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_host_participant

    group = db.query(GroupOrder).filter(GroupOrder.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Strictly authorize the host of this group
    host = resolve_host_participant(
        group_order_id=group.id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        host_participant_id_hint=host_participant_id,
        db=db
    )
    host_name = host.display_name

    # Check if merchant order already exists
    order = db.query(MerchantOrder).filter(MerchantOrder.group_order_id == group_id).first()
    now = datetime.now(timezone.utc)
    eta = now + timedelta(minutes=req.estimated_delivery_minutes)

    bill = calculate_group_bill(group, db)

    if not order:
        order = MerchantOrder(
            group_order_id=group_id,
            status="PLACED",
            platform_name=req.platform_name,
            external_order_id=req.external_order_id,
            placed_by_host_name=host_name,
            placed_at=now,
            estimated_delivery=eta,
            notes=req.notes,
            total_bill_paise=bill.grand_total_paise
        )
        db.add(order)
    else:
        order.status = "PLACED"
        order.platform_name = req.platform_name
        order.external_order_id = req.external_order_id
        order.placed_at = now
        order.estimated_delivery = eta
        order.notes = req.notes
        order.total_bill_paise = bill.grand_total_paise

    group.cart_status = "FINALIZED"

    audit = AuditLog(
        group_order_id=group_id,
        action="MERCHANT_ORDER_PLACED",
        actor_type="HOST",
        actor_id=host.id,
        actor_name=host_name,
        details_json=f'{{"platform": "{req.platform_name}", "ext_id": "{req.external_order_id or ""}", "eta_mins": {req.estimated_delivery_minutes}}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(order)

    await manager.broadcast_to_group(group_id, {
        "event": "order_status_changed",
        "merchant_order_status": order.status,
        "platform_name": order.platform_name,
        "external_order_id": order.external_order_id,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None
    })

    return MerchantOrderResponse(
        id=order.id,
        group_order_id=order.group_order_id,
        status=order.status,
        platform_name=order.platform_name,
        external_order_id=order.external_order_id,
        placed_by_host_name=order.placed_by_host_name,
        placed_at=order.placed_at,
        estimated_delivery=order.estimated_delivery,
        notes=order.notes,
        total_bill_paise=order.total_bill_paise,
        total_bill_inr=order.total_bill_paise / 100.0,
        updated_at=order.updated_at
    )


@router.patch("/status", response_model=MerchantOrderResponse)
async def update_merchant_order_status(
    group_id: str,
    req: MerchantOrderStatusUpdateRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_host_participant

    order = db.query(MerchantOrder).filter(MerchantOrder.group_order_id == group_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Merchant order not found for this group")

    # Strictly authorize the host of this group
    resolve_host_participant(
        group_order_id=group_id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )

    order.status = req.status
    if req.notes:
        order.notes = req.notes
    if req.external_order_id:
        order.external_order_id = req.external_order_id

    db.commit()
    db.refresh(order)

    await manager.broadcast_to_group(group_id, {
        "event": "order_status_changed",
        "merchant_order_status": order.status,
        "notes": order.notes
    })

    return MerchantOrderResponse(
        id=order.id,
        group_order_id=order.group_order_id,
        status=order.status,
        platform_name=order.platform_name,
        external_order_id=order.external_order_id,
        placed_by_host_name=order.placed_by_host_name,
        placed_at=order.placed_at,
        estimated_delivery=order.estimated_delivery,
        notes=order.notes,
        total_bill_paise=order.total_bill_paise,
        total_bill_inr=order.total_bill_paise / 100.0,
        updated_at=order.updated_at
    )


@router.get("", response_model=Optional[MerchantOrderResponse])
def get_merchant_order(group_id: str, db: Session = Depends(get_db)):
    order = db.query(MerchantOrder).filter(MerchantOrder.group_order_id == group_id).first()
    if not order:
        return None

    return MerchantOrderResponse(
        id=order.id,
        group_order_id=order.group_order_id,
        status=order.status,
        platform_name=order.platform_name,
        external_order_id=order.external_order_id,
        placed_by_host_name=order.placed_by_host_name,
        placed_at=order.placed_at,
        estimated_delivery=order.estimated_delivery,
        notes=order.notes,
        total_bill_paise=order.total_bill_paise,
        total_bill_inr=order.total_bill_paise / 100.0,
        updated_at=order.updated_at
    )
