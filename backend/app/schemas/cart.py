from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.product import ProductResponse


class CartItemAddRequest(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1, le=50)
    item_notes: Optional[str] = Field(None, max_length=255)


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(..., ge=0, le=50)  # 0 means remove
    item_notes: Optional[str] = Field(None, max_length=255)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_order_id: str
    participant_id: str
    participant_name: str
    product_id: str
    product: ProductResponse
    quantity: int
    unit_price_paise: int
    unit_price_inr: float
    item_subtotal_paise: int
    item_subtotal_inr: float
    item_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ParticipantCartResponse(BaseModel):
    participant_id: str
    participant_name: str
    avatar_color: str
    is_host: bool
    payment_status: str
    items: List[CartItemResponse]
    items_count: int
    items_subtotal_paise: int
    items_subtotal_inr: float


class CombinedCartResponse(BaseModel):
    group_id: str
    group_title: str
    cart_status: str
    total_items_count: int
    total_unique_products_count: int
    items_subtotal_paise: int
    items_subtotal_inr: float
    participants: List[ParticipantCartResponse]
