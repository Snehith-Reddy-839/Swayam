from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import GroupOrder
from app.schemas.billing import BillCalculationResponse, UpdateFeePolicyRequest
from app.services.billing_service import calculate_group_bill
from app.services.websocket_manager import manager

router = APIRouter(prefix="/groups/{group_id}/billing", tags=["Smart Bill Splitter"])


@router.get("", response_model=BillCalculationResponse)
def get_group_billing(group_id: str, db: Session = Depends(get_db)):
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

    return calculate_group_bill(group, db)


@router.post("/policy", response_model=BillCalculationResponse)
async def update_billing_policy(
    group_id: str,
    req: UpdateFeePolicyRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_host_participant

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

    # Host Authorization
    resolve_host_participant(
        group_order_id=group.id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )

    if req.fee_policy not in ["EQUAL_SPLIT", "PROPORTIONAL", "HOST_COVERS", "CUSTOM"]:
        raise HTTPException(status_code=400, detail="Invalid fee allocation policy")

    group.fee_policy = req.fee_policy
    if req.delivery_fee_paise is not None:
        group.delivery_fee_paise = req.delivery_fee_paise
    if req.platform_fee_paise is not None:
        group.platform_fee_paise = req.platform_fee_paise
    if req.packaging_fee_paise is not None:
        group.packaging_fee_paise = req.packaging_fee_paise
    if req.discount_paise is not None:
        group.discount_paise = req.discount_paise

    db.commit()

    bill_result = calculate_group_bill(group, db)

    await manager.broadcast_to_group(group_id, {
        "event": "bill_updated",
        "fee_policy": group.fee_policy,
        "grand_total_paise": bill_result.grand_total_paise,
        "grand_total_inr": bill_result.grand_total_inr
    })

    return bill_result
