from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem
from app.models.receipt import Receipt
from app.schemas.receipt import (
    ReceiptResponse,
    FinalCombinedOrderSummaryResponse,
    FinalCombinedProductGroup,
)
from app.services.receipt_service import format_receipt_response
from app.services.billing_service import calculate_group_bill

router = APIRouter(tags=["Receipts & Summaries"])


@router.get("/receipts/{token_or_id}", response_model=ReceiptResponse)
def get_receipt(token_or_id: str, db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(
        (Receipt.access_token == token_or_id) |
        (Receipt.id == token_or_id) |
        (Receipt.receipt_number == token_or_id) |
        (Receipt.participant_id == token_or_id)
    ).order_by(Receipt.issued_at.desc()).first()

    if not receipt:
        # Check by payment attempt ID
        from app.models.payment import PaymentTransaction
        tx = db.query(PaymentTransaction).filter(
            (PaymentTransaction.payment_attempt_id == token_or_id) |
            (PaymentTransaction.participant_id == token_or_id)
        ).order_by(PaymentTransaction.created_at.desc()).first()
        if tx and tx.receipt:
            receipt = tx.receipt

    if not receipt:
        raise HTTPException(status_code=404, detail="Digital receipt not found")

    group = db.query(GroupOrder).filter(GroupOrder.id == receipt.group_order_id).first()
    participant = db.query(GroupParticipant).filter(GroupParticipant.id == receipt.participant_id).first()

    if not group or not participant:
        raise HTTPException(status_code=404, detail="Receipt reference data missing")

    return format_receipt_response(receipt, group, participant)


@router.get("/groups/{group_id}/summary", response_model=FinalCombinedOrderSummaryResponse)
@router.get("/receipts/groups/{group_id}/summary", response_model=FinalCombinedOrderSummaryResponse)
def get_final_combined_order_summary(group_id: str, db: Session = Depends(get_db)):
    """
    Returns the consolidated final group order shopping list grouped by product,
    e.g. 'Maggi 2-Min Masala × 6', 'Red Bull × 4', ready for the host to place
    with Swiggy Instamart, Blinkit, Zepto, or Campus Canteen.
    """
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

    # Group items by product_id
    grouped_map: Dict[str, Dict] = {}
    total_items_count = 0

    for item in all_items:
        total_items_count += item.quantity
        pid = item.product_id
        p_name = item.participant.display_name if item.participant else "Unknown"

        if pid not in grouped_map:
            grouped_map[pid] = {
                "product_id": pid,
                "product_name": item.product.name if item.product else "Item",
                "category_name": item.product.category.name if (item.product and item.product.category) else "Snacks",
                "unit": item.product.unit if item.product else "pack",
                "total_quantity": 0,
                "unit_price_paise": item.unit_price_paise,
                "unit_price_inr": item.unit_price_paise / 100.0,
                "ordered_by": []
            }

        grouped_map[pid]["total_quantity"] += item.quantity
        if p_name not in grouped_map[pid]["ordered_by"]:
            grouped_map[pid]["ordered_by"].append(p_name)

    grouped_products = []
    for data in grouped_map.values():
        total_price_paise = data["total_quantity"] * data["unit_price_paise"]
        grouped_products.append(
            FinalCombinedProductGroup(
                product_id=data["product_id"],
                product_name=data["product_name"],
                category_name=data["category_name"],
                unit=data["unit"],
                total_quantity=data["total_quantity"],
                unit_price_paise=data["unit_price_paise"],
                unit_price_inr=data["unit_price_inr"],
                total_price_paise=total_price_paise,
                total_price_inr=total_price_paise / 100.0,
                ordered_by=data["ordered_by"]
            )
        )

    # Sort by total quantity descending
    grouped_products.sort(key=lambda x: x.total_quantity, reverse=True)

    paid_count = sum(1 for p in participants if p.payment_status == "PAID")

    merchant_status = group.merchant_order.status if group.merchant_order else "NOT_PLACED"
    platform = group.merchant_order.platform_name if group.merchant_order else None
    ext_id = group.merchant_order.external_order_id if group.merchant_order else None

    return FinalCombinedOrderSummaryResponse(
        group_id=group.id,
        group_title=group.title,
        invite_code=group.invite_code,
        delivery_location=group.delivery_location,
        cart_status=group.cart_status,
        merchant_order_status=merchant_status,
        platform_name=platform,
        external_order_id=ext_id,
        total_participants=len(participants),
        paid_participants_count=paid_count,
        total_items_count=total_items_count,
        grouped_products=grouped_products,
        items_subtotal_paise=bill.total_items_subtotal_paise,
        items_subtotal_inr=bill.total_items_subtotal_inr,
        shared_fees_paise=bill.total_shared_fees_paise,
        shared_fees_inr=bill.total_shared_fees_inr,
        tax_paise=bill.total_tax_paise,
        tax_inr=bill.total_tax_inr,
        grand_total_paise=bill.grand_total_paise,
        grand_total_inr=bill.grand_total_inr,
        total_paid_paise=bill.total_paid_paise,
        total_paid_inr=bill.total_paid_inr,
        remaining_unpaid_paise=bill.total_outstanding_paise,
        remaining_unpaid_inr=bill.total_outstanding_inr,
        is_fully_paid=bill.is_fully_paid
    )
