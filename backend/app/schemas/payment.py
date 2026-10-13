from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class PaymentInitiateRequest(BaseModel):
    participant_id: str
    payment_mode: str = Field("UPI_QR", description="DEMO, UPI_QR, or RAZORPAY")
    idempotency_key: Optional[str] = None


class UPIQRDetailsResponse(BaseModel):
    payment_attempt_id: str
    upi_uri: str
    qr_data_url: str
    vpa: str
    payee_name: str
    amount_paise: int
    amount_inr: float
    transaction_ref: str
    instructions: List[str]


class RazorpayOrderResponse(BaseModel):
    payment_attempt_id: str
    key_id: str
    razorpay_order_id: str
    amount_paise: int
    currency: str
    prefill_name: str
    prefill_contact: Optional[str] = None


class PaymentVerifyRequest(BaseModel):
    payment_attempt_id: str
    payment_mode: str  # DEMO, UPI_QR, RAZORPAY
    
    # Razorpay verification payload
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    
    # Demo simulation parameters
    demo_outcome: Optional[str] = "SUCCESS"  # SUCCESS, FAILURE, PENDING
    
    # UPI UTR / Reference provided by user
    upi_reference: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    payment_attempt_id: str
    participant_id: str
    status: str  # PENDING, PROCESSING, PAID, FAILED, CANCELLED
    payment_mode: str
    amount_paise: int
    amount_inr: float
    receipt_id: Optional[str] = None
    receipt_token: Optional[str] = None
    failure_reason: Optional[str] = None
    verified_at: Optional[datetime] = None


class ManualUPIConfirmRequest(BaseModel):
    participant_id: str
    host_participant_id: str
    upi_reference: Optional[str] = None
    notes: Optional[str] = None
