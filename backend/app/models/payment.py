import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_participants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Idempotency token sent by client or generated
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    
    # Mode: DEMO, UPI_QR, RAZORPAY
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Gateway or UPI external identifiers
    gateway_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    upi_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # UTR number
    
    # Status: PENDING, PROCESSING, PAID, FAILED, CANCELLED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    group_order = relationship("GroupOrder", back_populates="payment_attempts")
    participant = relationship("GroupParticipant", back_populates="payment_attempts")
    transaction = relationship("PaymentTransaction", back_populates="payment_attempt", uselist=False)


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_participants.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey("payment_attempts.id"), nullable=False, unique=True)
    
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # How was this payment verified:
    # "GATEWAY_SIGNATURE", "HOST_MANUAL", "DEMO_SIMULATION"
    verified_by: Mapped[str] = mapped_column(String(50), nullable=False)
    verifier_identity: Mapped[str] = mapped_column(String(100), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    group_order = relationship("GroupOrder", back_populates="payment_transactions")
    payment_attempt = relationship("PaymentAttempt", back_populates="transaction")
    receipt = relationship("Receipt", back_populates="transaction", uselist=False)
