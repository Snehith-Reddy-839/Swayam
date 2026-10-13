from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem
from app.models.audit import AuditLog
from app.schemas.dashboard import HostDashboardSummaryResponse, ActivityLogEntry
from app.services.billing_service import calculate_group_bill

router = APIRouter(prefix="/groups/{group_id}/dashboard", tags=["Host Management Dashboard"])


@router.get("", response_model=HostDashboardSummaryResponse)
def get_host_dashboard_summary(group_id: str, db: Session = Depends(get_db)):
    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        or_(
            GroupOrder.id == gid_clean,
            GroupOrder.id == gid_clean.lower(),
            GroupOrder.invite_code == gid_clean.upper()
        )
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group order not found")

    participants = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == group.id).all()
    all_items = db.query(CartItem).filter(CartItem.group_order_id == group.id).all()

    bill = calculate_group_bill(group, db)

    total_items_count = sum(it.quantity for it in all_items)
    paid_count = sum(1 for p in participants if p.payment_status == "PAID")
    unpaid_count = len(participants) - paid_count

    payment_completion_pct = 0.0
    if bill.grand_total_paise > 0:
        payment_completion_pct = min(100.0, round((bill.total_paid_paise / bill.grand_total_paise) * 100.0, 1))
    elif len(participants) > 0 and bill.grand_total_paise == 0:
        payment_completion_pct = 100.0

    recent_logs = db.query(AuditLog).filter(
        AuditLog.group_order_id == group.id
    ).order_by(AuditLog.created_at.desc()).limit(15).all()

    activities = [
        ActivityLogEntry(
            id=log.id,
            action=log.action,
            actor_type=log.actor_type,
            actor_name=log.actor_name,
            details=log.details_json,
            created_at=log.created_at
        )
        for log in recent_logs
    ]

    merchant_status = group.merchant_order.status if group.merchant_order else "NOT_PLACED"

    is_ready_to_order = (
        bill.is_fully_paid or
        (group.is_payment_required_before_finalize is False and len(all_items) > 0)
    )

    share_url = f"{settings.FRONTEND_URL}/group/{group.invite_code}"

    return HostDashboardSummaryResponse(
        group_id=group.id,
        group_title=group.title,
        invite_code=group.invite_code,
        share_url=share_url,
        delivery_location=group.delivery_location,
        cart_status=group.cart_status,
        cart_closing_time=group.cart_closing_time,
        participants_count=len(participants),
        paid_count=paid_count,
        unpaid_count=unpaid_count,
        total_items_count=total_items_count,
        grand_total_paise=bill.grand_total_paise,
        grand_total_inr=bill.grand_total_inr,
        total_collected_paise=bill.total_paid_paise,
        total_collected_inr=bill.total_paid_inr,
        outstanding_paise=bill.total_outstanding_paise,
        outstanding_inr=bill.total_outstanding_inr,
        payment_completion_pct=payment_completion_pct,
        is_ready_to_order=is_ready_to_order,
        merchant_order_status=merchant_status,
        participant_shares=bill.participant_shares,
        recent_activities=activities
    )
