from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import GroupOrder, GroupParticipant
from app.models.product import Product
from app.models.cart import CartItem
from app.models.audit import AuditLog
from app.schemas.cart import (
    CartItemAddRequest,
    CartItemUpdateRequest,
    CartItemResponse,
    ParticipantCartResponse,
    CombinedCartResponse,
)
from app.schemas.product import ProductResponse
from app.services.websocket_manager import manager
from app.services.billing_service import calculate_group_bill

router = APIRouter(prefix="/groups/{group_id}/cart", tags=["Collaborative Cart"])


@router.post("/items", response_model=CartItemResponse)
async def add_item_to_cart(
    group_id: str,
    participant_id: Optional[str] = None,
    req: CartItemAddRequest = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_caller_participant, resolve_caller_identity

    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        or_(
            GroupOrder.id == gid_clean,
            GroupOrder.id == gid_clean.lower(),
            GroupOrder.invite_code == gid_clean.upper()
        )
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.cart_status != "OPEN":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add items. Cart status is currently '{group.cart_status}'."
        )

    # Enforce strict caller authentication
    user, guest = resolve_caller_identity(
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )
    if not (user or guest):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Valid session token or credentials required"
        )

    # Derive participant identity from validated server-issued credentials
    participant = resolve_caller_participant(
        group_order_id=group.id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        participant_id_hint=participant_id,
        db=db
    )

    # Fetch trusted product from backend database
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product or not product.is_available:
        raise HTTPException(status_code=400, detail="Product is not available")

    # Check if this participant already has this product in cart
    existing_item = db.query(CartItem).filter(
        CartItem.group_order_id == group.id,
        CartItem.participant_id == participant.id,
        CartItem.product_id == req.product_id
    ).first()

    if existing_item:
        new_quantity = existing_item.quantity + req.quantity
        if new_quantity > 50:
            raise HTTPException(
                status_code=400,
                detail="Total quantity for a single product in cart cannot exceed 50"
            )
        existing_item.quantity = new_quantity
        if req.item_notes:
            existing_item.item_notes = req.item_notes
        item = existing_item
        event_type = "cart_item_updated"
    else:
        item = CartItem(
            group_order_id=group.id,
            participant_id=participant.id,
            product_id=product.id,
            quantity=req.quantity,
            unit_price_paise=product.price_paise,
            item_notes=req.item_notes
        )
        db.add(item)
        event_type = "cart_item_added"

    db.commit()
    db.refresh(item)

    # Recalculate bill in background and notify
    calculate_group_bill(group, db)

    item_subtotal_paise = item.unit_price_paise * item.quantity

    # Broadcast real-time update
    await manager.broadcast_to_group(group.id, {
        "event": event_type,
        "participant_id": participant.id,
        "participant_name": participant.display_name,
        "product_id": product.id,
        "product_name": product.name,
        "quantity": item.quantity,
        "subtotal_paise": item_subtotal_paise
    })

    return CartItemResponse(
        id=item.id,
        group_order_id=group.id,
        participant_id=participant.id,
        participant_name=participant.display_name,
        product_id=product.id,
        product=ProductResponse(
            id=product.id,
            category_id=product.category_id,
            name=product.name,
            description=product.description,
            price_paise=product.price_paise,
            price_inr=product.price_paise / 100.0,
            image_url=product.image_url,
            is_available=product.is_available,
            is_veg=product.is_veg,
            unit=product.unit,
            popularity_score=product.popularity_score
        ),
        quantity=item.quantity,
        unit_price_paise=item.unit_price_paise,
        unit_price_inr=item.unit_price_paise / 100.0,
        item_subtotal_paise=item_subtotal_paise,
        item_subtotal_inr=item_subtotal_paise / 100.0,
        item_notes=item.item_notes,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.patch("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    group_id: str,
    item_id: str,
    req: CartItemUpdateRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_caller_identity

    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        or_(
            GroupOrder.id == gid_clean,
            GroupOrder.id == gid_clean.lower(),
            GroupOrder.invite_code == gid_clean.upper()
        )
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.cart_status != "OPEN":
        raise HTTPException(status_code=400, detail=f"Cannot modify cart. Cart status is currently '{group.cart_status}'.")

    # Verify item exists and belongs strictly to the requested group
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.group_order_id != group.id:
        raise HTTPException(status_code=400, detail="Cart item does not belong to the specified group")

    # Authorize caller: strictly require credentials
    user, guest = resolve_caller_identity(
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )
    if not (user or guest):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Valid session token or credentials required to modify cart items"
        )

    # Caller must be item owner OR host of this exact group
    item_owner = item.participant
    is_owner = False
    is_host = False
    if user:
        is_owner = (item_owner.user_id is not None and item_owner.user_id == user.id)
        host_p = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group.id,
            GroupParticipant.user_id == user.id,
            GroupParticipant.is_host == True
        ).first()
        is_host = bool(host_p)
    elif guest:
        is_owner = (item_owner.guest_session_id is not None and item_owner.guest_session_id == guest.id)
        host_p = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group.id,
            GroupParticipant.guest_session_id == guest.id,
            GroupParticipant.is_host == True
        ).first()
        is_host = bool(host_p)

    if not is_owner and not is_host:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: You can only modify your own cart items unless you are the group host."
        )

    if req.quantity == 0:
        participant_id = item.participant_id
        db.delete(item)
        db.commit()
        calculate_group_bill(group, db)

        await manager.broadcast_to_group(group.id, {
            "event": "cart_item_removed",
            "item_id": item_id,
            "participant_id": participant_id
        })
        raise HTTPException(status_code=200, detail="Item removed")

    item.quantity = req.quantity
    if req.item_notes is not None:
        item.item_notes = req.item_notes

    db.commit()
    db.refresh(item)
    calculate_group_bill(group, db)

    item_subtotal_paise = item.unit_price_paise * item.quantity

    await manager.broadcast_to_group(group.id, {
        "event": "cart_item_updated",
        "item_id": item.id,
        "participant_id": item.participant_id,
        "quantity": item.quantity,
        "subtotal_paise": item_subtotal_paise
    })

    return CartItemResponse(
        id=item.id,
        group_order_id=group.id,
        participant_id=item.participant_id,
        participant_name=item.participant.display_name,
        product_id=item.product.id,
        product=ProductResponse(
            id=item.product.id,
            category_id=item.product.category_id,
            name=item.product.name,
            description=item.product.description,
            price_paise=item.product.price_paise,
            price_inr=item.product.price_paise / 100.0,
            image_url=item.product.image_url,
            is_available=item.product.is_available,
            is_veg=item.product.is_veg,
            unit=item.product.unit,
            popularity_score=item.product.popularity_score
        ),
        quantity=item.quantity,
        unit_price_paise=item.unit_price_paise,
        unit_price_inr=item.unit_price_paise / 100.0,
        item_subtotal_paise=item_subtotal_paise,
        item_subtotal_inr=item_subtotal_paise / 100.0,
        item_notes=item.item_notes,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.delete("/items/{item_id}")
async def delete_cart_item(
    group_id: str,
    item_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_caller_identity

    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        or_(
            GroupOrder.id == gid_clean,
            GroupOrder.id == gid_clean.lower(),
            GroupOrder.invite_code == gid_clean.upper()
        )
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.cart_status != "OPEN":
        raise HTTPException(status_code=400, detail=f"Cannot modify cart. Cart status is currently '{group.cart_status}'.")

    # Verify item exists and belongs strictly to the requested group
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.group_order_id != group.id:
        raise HTTPException(status_code=400, detail="Cart item does not belong to the specified group")

    # Authorize caller: strictly require credentials
    user, guest = resolve_caller_identity(
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )
    if not (user or guest):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Valid session token or credentials required to delete cart items"
        )

    # Caller must be item owner OR host of this exact group
    item_owner = item.participant
    is_owner = False
    is_host = False
    if user:
        is_owner = (item_owner.user_id is not None and item_owner.user_id == user.id)
        host_p = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group.id,
            GroupParticipant.user_id == user.id,
            GroupParticipant.is_host == True
        ).first()
        is_host = bool(host_p)
    elif guest:
        is_owner = (item_owner.guest_session_id is not None and item_owner.guest_session_id == guest.id)
        host_p = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group.id,
            GroupParticipant.guest_session_id == guest.id,
            GroupParticipant.is_host == True
        ).first()
        is_host = bool(host_p)

    if not is_owner and not is_host:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: You can only remove your own cart items unless you are the group host."
        )

    participant_id = item.participant_id
    db.delete(item)
    db.commit()
    calculate_group_bill(group, db)

    await manager.broadcast_to_group(group.id, {
        "event": "cart_item_removed",
        "item_id": item_id,
        "participant_id": participant_id
    })

    return {"message": "Cart item removed successfully"}


@router.get("/combined", response_model=CombinedCartResponse)
def get_combined_cart(group_id: str, db: Session = Depends(get_db)):
    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        or_(
            GroupOrder.id == gid_clean,
            GroupOrder.id == gid_clean.lower(),
            GroupOrder.invite_code == gid_clean.upper()
        )
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    participants = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == group.id).all()
    all_items = db.query(CartItem).filter(CartItem.group_order_id == group.id).all()

    total_items_count = sum(it.quantity for it in all_items)
    unique_products = set(it.product_id for it in all_items)
    total_subtotal_paise = sum(it.unit_price_paise * it.quantity for it in all_items)

    participant_carts: List[ParticipantCartResponse] = []
    for p in participants:
        p_items = [it for it in all_items if it.participant_id == p.id]
        p_subtotal = sum(it.unit_price_paise * it.quantity for it in p_items)
        
        item_responses = [
            CartItemResponse(
                id=it.id,
                group_order_id=group.id,
                participant_id=p.id,
                participant_name=p.display_name,
                product_id=it.product_id,
                product=ProductResponse(
                    id=it.product.id,
                    category_id=it.product.category_id,
                    name=it.product.name,
                    description=it.product.description,
                    price_paise=it.product.price_paise,
                    price_inr=it.product.price_paise / 100.0,
                    image_url=it.product.image_url,
                    is_available=it.product.is_available,
                    is_veg=it.product.is_veg,
                    unit=it.product.unit,
                    popularity_score=it.product.popularity_score
                ),
                quantity=it.quantity,
                unit_price_paise=it.unit_price_paise,
                unit_price_inr=it.unit_price_paise / 100.0,
                item_subtotal_paise=it.unit_price_paise * it.quantity,
                item_subtotal_inr=(it.unit_price_paise * it.quantity) / 100.0,
                item_notes=it.item_notes,
                created_at=it.created_at,
                updated_at=it.updated_at
            )
            for it in p_items
        ]

        participant_carts.append(
            ParticipantCartResponse(
                participant_id=p.id,
                participant_name=p.display_name,
                avatar_color=p.avatar_color,
                is_host=p.is_host,
                payment_status=p.payment_status,
                items=item_responses,
                items_count=sum(it.quantity for it in p_items),
                items_subtotal_paise=p_subtotal,
                items_subtotal_inr=p_subtotal / 100.0
            )
        )

    return CombinedCartResponse(
        group_id=group.id,
        group_title=group.title,
        cart_status=group.cart_status,
        total_items_count=total_items_count,
        total_unique_products_count=len(unique_products),
        items_subtotal_paise=total_subtotal_paise,
        items_subtotal_inr=total_subtotal_paise / 100.0,
        participants=participant_carts
    )
