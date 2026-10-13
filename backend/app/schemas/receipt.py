from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ReceiptItemLine(BaseModel):
    product_name: str
    quantity: int
    unit_price_paise: int
    unit_price_inr: float
    total_price_paise: int
    total_price_inr: float
    item_notes: Optional[str] = None


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    receipt_number: str
    group_order_id: str
    group_title: str
    delivery_location: str
    participant_id: str
    participant_name: str
    access_token: str
    
    items: List[ReceiptItemLine]
    
    items_subtotal_paise: int
    items_subtotal_inr: float
    shared_fees_paise: int
    shared_fees_inr: float
    tax_paise: int
    tax_inr: float
    discount_paise: int
    discount_inr: float
    total_paid_paise: int
    total_paid_inr: float
    
    payment_method: str
    transaction_ref: str
    issued_at: datetime
    merchant_order_status: str


class FinalCombinedProductGroup(BaseModel):
    product_id: str
    product_name: str
    category_name: str
    unit: str
    total_quantity: int
    unit_price_paise: int
    unit_price_inr: float
    total_price_paise: int
    total_price_inr: float
    ordered_by: List[str]  # participant names


class FinalCombinedOrderSummaryResponse(BaseModel):
    group_id: str
    group_title: str
    invite_code: str
    delivery_location: str
    cart_status: str
    merchant_order_status: str
    platform_name: Optional[str]
    external_order_id: Optional[str]
    
    total_participants: int
    paid_participants_count: int
    
    total_items_count: int
    grouped_products: List[FinalCombinedProductGroup]
    
    items_subtotal_paise: int
    items_subtotal_inr: float
    shared_fees_paise: int
    shared_fees_inr: float
    tax_paise: int
    tax_inr: float
    grand_total_paise: int
    grand_total_inr: float
    
    total_paid_paise: int
    total_paid_inr: float
    remaining_unpaid_paise: int
    remaining_unpaid_inr: float
    
    is_fully_paid: bool
