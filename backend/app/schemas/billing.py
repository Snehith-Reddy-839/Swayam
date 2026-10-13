from typing import List, Optional
from pydantic import BaseModel


class ParticipantBillShare(BaseModel):
    participant_id: str
    participant_name: str
    avatar_color: str
    is_host: bool
    payment_status: str
    items_count: int
    items_subtotal_paise: int
    items_subtotal_inr: float
    delivery_share_paise: int
    platform_share_paise: int
    packaging_share_paise: int
    shared_fees_total_paise: int
    shared_fees_total_inr: float
    tax_share_paise: int
    tax_share_inr: float
    discount_share_paise: int
    discount_share_inr: float
    rounding_adjustment_paise: int
    total_payable_paise: int
    total_payable_inr: float
    amount_paid_paise: int
    amount_paid_inr: float
    outstanding_paise: int
    outstanding_inr: float


class BillCalculationResponse(BaseModel):
    group_id: str
    fee_policy: str
    participants_count: int
    
    # Bill Components in Paise and INR
    total_items_subtotal_paise: int
    total_items_subtotal_inr: float
    
    delivery_fee_paise: int
    delivery_fee_inr: float
    
    platform_fee_paise: int
    platform_fee_inr: float
    
    packaging_fee_paise: int
    packaging_fee_inr: float
    
    total_shared_fees_paise: int
    total_shared_fees_inr: float
    
    tax_percentage: float
    total_tax_paise: int
    total_tax_inr: float
    
    total_discount_paise: int
    total_discount_inr: float
    
    grand_total_paise: int
    grand_total_inr: float
    
    total_paid_paise: int
    total_paid_inr: float
    
    total_outstanding_paise: int
    total_outstanding_inr: float
    
    is_fully_paid: bool
    
    # Mathematical proof check
    sum_of_participant_shares_paise: int
    is_deterministic_exact_match: bool
    
    participant_shares: List[ParticipantBillShare]


class UpdateFeePolicyRequest(BaseModel):
    fee_policy: str  # EQUAL_SPLIT, PROPORTIONAL, HOST_COVERS
    delivery_fee_paise: Optional[int] = None
    platform_fee_paise: Optional[int] = None
    packaging_fee_paise: Optional[int] = None
    discount_paise: Optional[int] = None
