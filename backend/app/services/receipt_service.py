import json
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem
from app.models.billing import BillAllocation
from app.models.payment import PaymentTransaction
from app.models.receipt import Receipt
from app.schemas.receipt import ReceiptResponse, ReceiptItemLine


def generate_receipt_for_payment(
    group: GroupOrder,
    participant: GroupParticipant,
    transaction: PaymentTransaction,
    db: Session
) -> Receipt:
    """Generates an immutable digital receipt record for a confirmed payment."""
    # Check if a receipt already exists for this transaction
    existing = db.query(Receipt).filter(Receipt.payment_transaction_id == transaction.id).first()
    if existing:
        return existing

    # Gather items snapshot
    cart_items = db.query(CartItem).filter(
        CartItem.group_order_id == group.id,
        CartItem.participant_id == participant.id
    ).all()

    items_list = []
    items_subtotal = 0
    for it in cart_items:
        line_total = it.unit_price_paise * it.quantity
        items_subtotal += line_total
        items_list.append({
            "product_name": it.product.name if it.product else "Snack Item",
            "quantity": it.quantity,
            "unit_price_paise": it.unit_price_paise,
            "unit_price_inr": it.unit_price_paise / 100.0,
            "total_price_paise": line_total,
            "total_price_inr": line_total / 100.0,
            "item_notes": it.item_notes
        })

    # Fetch billing allocation
    alloc = db.query(BillAllocation).filter(
        BillAllocation.group_order_id == group.id,
        BillAllocation.participant_id == participant.id
    ).first()

    shared_fees = alloc.shared_fees_share_paise if alloc else 0
    tax = alloc.tax_share_paise if alloc else 0
    discount = alloc.discount_share_paise if alloc else 0
    total_paid = transaction.amount_paise

    now = datetime.now(timezone.utc)
    receipt_num = f"MM-{now.year}-{secrets.token_hex(4).upper()}"
    access_token = secrets.token_urlsafe(32)

    receipt = Receipt(
        receipt_number=receipt_num,
        group_order_id=group.id,
        participant_id=participant.id,
        payment_transaction_id=transaction.id,
        access_token=access_token,
        items_snapshot_json=json.dumps(items_list),
        items_subtotal_paise=items_subtotal,
        shared_fees_paise=shared_fees,
        tax_paise=tax,
        discount_paise=discount,
        total_paid_paise=total_paid,
        payment_method=transaction.verified_by,
        transaction_ref=transaction.transaction_reference,
        issued_at=now,
        expires_at=now + timedelta(days=90),
        is_revoked=False
    )
    db.add(receipt)
    db.flush()
    return receipt


def format_receipt_response(receipt: Receipt, group: GroupOrder, participant: GroupParticipant) -> ReceiptResponse:
    """Formats a database Receipt model into a public ReceiptResponse."""
    items_data = json.loads(receipt.items_snapshot_json)
    items_lines = [ReceiptItemLine(**item) for item in items_data]

    merchant_status = group.merchant_order.status if group.merchant_order else "NOT_PLACED"

    return ReceiptResponse(
        id=receipt.id,
        receipt_number=receipt.receipt_number,
        group_order_id=group.id,
        group_title=group.title,
        delivery_location=group.delivery_location,
        participant_id=participant.id,
        participant_name=participant.display_name,
        access_token=receipt.access_token,
        items=items_lines,
        items_subtotal_paise=receipt.items_subtotal_paise,
        items_subtotal_inr=receipt.items_subtotal_paise / 100.0,
        shared_fees_paise=receipt.shared_fees_paise,
        shared_fees_inr=receipt.shared_fees_paise / 100.0,
        tax_paise=receipt.tax_paise,
        tax_inr=receipt.tax_paise / 100.0,
        discount_paise=receipt.discount_paise,
        discount_inr=receipt.discount_paise / 100.0,
        total_paid_paise=receipt.total_paid_paise,
        total_paid_inr=receipt.total_paid_paise / 100.0,
        payment_method=receipt.payment_method,
        transaction_ref=receipt.transaction_ref,
        issued_at=receipt.issued_at,
        merchant_order_status=merchant_status
    )
