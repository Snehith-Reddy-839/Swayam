from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class MerchantOrderCreateRequest(BaseModel):
    platform_name: str = Field("Blinkit", description="Blinkit, Zepto, Swiggy Instamart, Canteen, etc.")
    external_order_id: Optional[str] = Field(None, description="Order ID from the delivery app")
    estimated_delivery_minutes: Optional[int] = Field(25, ge=5, le=180)
    notes: Optional[str] = None


class MerchantOrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="NOT_PLACED, PLACED, ACCEPTED, PREPARING, OUT_FOR_DELIVERY, DELIVERED, CANCELLED")
    notes: Optional[str] = None
    external_order_id: Optional[str] = None


class MerchantOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_order_id: str
    status: str
    platform_name: str
    external_order_id: Optional[str]
    placed_by_host_name: str
    placed_at: Optional[datetime]
    estimated_delivery: Optional[datetime]
    notes: Optional[str]
    total_bill_paise: int
    total_bill_inr: float
    updated_at: datetime
