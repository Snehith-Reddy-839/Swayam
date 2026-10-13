from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class GroupCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    store_mode: str = Field("late_night_snacks", max_length=50)
    delivery_location: str = Field(..., min_length=3, max_length=255)
    cart_closing_minutes: Optional[int] = Field(30, ge=5, le=360)
    participant_limit: int = Field(15, ge=2, le=50)
    fee_policy: str = Field("EQUAL_SPLIT")  # EQUAL_SPLIT, PROPORTIONAL, HOST_COVERS, CUSTOM
    delivery_fee_paise: Optional[int] = 4000
    platform_fee_paise: Optional[int] = 1000
    packaging_fee_paise: Optional[int] = 1500
    discount_paise: Optional[int] = 0
    tax_percentage: Optional[float] = 5.0
    is_payment_required_before_finalize: bool = True
    host_approval_required: bool = False
    allow_participant_edit: bool = True
    passcode: Optional[str] = None
    # Creator info if not authenticated
    host_name: Optional[str] = None
    guest_session_token: Optional[str] = None


class GroupUpdateRequest(BaseModel):
    title: Optional[str] = None
    delivery_location: Optional[str] = None
    cart_closing_minutes: Optional[int] = None
    fee_policy: Optional[str] = None
    delivery_fee_paise: Optional[int] = None
    platform_fee_paise: Optional[int] = None
    packaging_fee_paise: Optional[int] = None
    discount_paise: Optional[int] = None
    tax_percentage: Optional[float] = None
    is_payment_required_before_finalize: Optional[bool] = None
    host_approval_required: Optional[bool] = None
    allow_participant_edit: Optional[bool] = None


class GroupJoinRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
    avatar_color: Optional[str] = "#FF5C00"
    passcode: Optional[str] = None
    guest_session_token: Optional[str] = None


class GroupParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    avatar_color: str
    is_host: bool
    payment_status: str
    amount_paid_paise: int
    amount_paid_inr: float
    joined_at: datetime


class GroupDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invite_code: str
    title: str
    host_name: str
    store_mode: str
    delivery_location: str
    cart_closing_time: Optional[datetime]
    participant_limit: int
    cart_status: str
    fee_policy: str
    delivery_fee_paise: int
    platform_fee_paise: int
    packaging_fee_paise: int
    discount_paise: int
    tax_percentage: float
    is_payment_required_before_finalize: bool
    host_approval_required: bool
    allow_participant_edit: bool
    has_passcode: bool
    created_at: datetime
    participants_count: int
    share_url: str
    host_participant_id: Optional[str] = None
