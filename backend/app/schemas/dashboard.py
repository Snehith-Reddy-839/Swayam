from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.billing import ParticipantBillShare


class ActivityLogEntry(BaseModel):
    id: str
    action: str
    actor_type: str
    actor_name: str
    details: Optional[str]
    created_at: datetime


class HostDashboardSummaryResponse(BaseModel):
    group_id: str
    group_title: str
    invite_code: str
    share_url: str
    delivery_location: str
    cart_status: str
    cart_closing_time: Optional[datetime]
    
    participants_count: int
    paid_count: int
    unpaid_count: int
    
    total_items_count: int
    grand_total_paise: int
    grand_total_inr: float
    total_collected_paise: int
    total_collected_inr: float
    outstanding_paise: int
    outstanding_inr: float
    payment_completion_pct: float
    
    is_ready_to_order: bool
    merchant_order_status: str
    
    participant_shares: List[ParticipantBillShare]
    recent_activities: List[ActivityLogEntry]
