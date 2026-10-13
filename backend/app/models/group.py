import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class GroupOrder(Base):
    __tablename__ = "group_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invite_code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    
    # Host linkage (either registered user or guest host)
    host_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    host_guest_session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("guest_sessions.id"), nullable=True)
    host_name: Mapped[str] = mapped_column(String(100), nullable=False)

    store_mode: Mapped[str] = mapped_column(String(50), default="late_night_snacks")  # grocery, late_night_snacks, canteen
    delivery_location: Mapped[str] = mapped_column(String(255), nullable=False)
    cart_closing_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    participant_limit: Mapped[int] = mapped_column(Integer, default=15)

    # Status: OPEN, LOCKED, READY_FOR_CHECKOUT, FINALIZED, CANCELLED
    cart_status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)

    # Fee Allocation Policy: EQUAL_SPLIT, PROPORTIONAL, HOST_COVERS, CUSTOM
    fee_policy: Mapped[str] = mapped_column(String(30), default="EQUAL_SPLIT")
    
    # Fees in integer paise
    delivery_fee_paise: Mapped[int] = mapped_column(Integer, default=4000)
    platform_fee_paise: Mapped[int] = mapped_column(Integer, default=1000)
    packaging_fee_paise: Mapped[int] = mapped_column(Integer, default=1500)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    tax_percentage: Mapped[float] = mapped_column(Float, default=5.0)

    is_payment_required_before_finalize: Mapped[bool] = mapped_column(Boolean, default=True)
    host_approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_participant_edit: Mapped[bool] = mapped_column(Boolean, default=True)
    passcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    host_user = relationship("User", back_populates="hosted_groups", foreign_keys=[host_user_id])
    participants: Mapped[List["GroupParticipant"]] = relationship("GroupParticipant", back_populates="group_order", cascade="all, delete-orphan")
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="group_order", cascade="all, delete-orphan")
    bill_allocations: Mapped[List["BillAllocation"]] = relationship("BillAllocation", back_populates="group_order", cascade="all, delete-orphan")
    payment_attempts: Mapped[List["PaymentAttempt"]] = relationship("PaymentAttempt", back_populates="group_order", cascade="all, delete-orphan")
    payment_transactions: Mapped[List["PaymentTransaction"]] = relationship("PaymentTransaction", back_populates="group_order", cascade="all, delete-orphan")
    receipts: Mapped[List["Receipt"]] = relationship("Receipt", back_populates="group_order", cascade="all, delete-orphan")
    merchant_order = relationship("MerchantOrder", back_populates="group_order", uselist=False, cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="group_order", cascade="all, delete-orphan")


class GroupParticipant(Base):
    __tablename__ = "group_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Associated user or guest session
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    guest_session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("guest_sessions.id"), nullable=True)
    
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(20), default="#FF5C00")
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Participant Payment Status: PENDING, PROCESSING, PAID, FAILED, CANCELLED
    payment_status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    amount_paid_paise: Mapped[int] = mapped_column(Integer, default=0)

    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    group_order: Mapped["GroupOrder"] = relationship("GroupOrder", back_populates="participants")
    user = relationship("User", back_populates="group_participations")
    guest_session = relationship("GuestSession", back_populates="participations")
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="participant", cascade="all, delete-orphan")
    bill_allocation = relationship("BillAllocation", back_populates="participant", uselist=False, cascade="all, delete-orphan")
    payment_attempts: Mapped[List["PaymentAttempt"]] = relationship("PaymentAttempt", back_populates="participant")
    receipts: Mapped[List["Receipt"]] = relationship("Receipt", back_populates="participant")
