import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_participants.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("payment_transactions.id"), nullable=False, unique=True)
    
    # Secure token for guest receipt lookup
    access_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    # Itemized snapshot as JSON string
    items_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    items_subtotal_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_fees_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paid_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    transaction_ref: Mapped[str] = mapped_column(String(100), nullable=False)

    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    group_order = relationship("GroupOrder", back_populates="receipts")
    participant = relationship("GroupParticipant", back_populates="receipts")
    transaction = relationship("PaymentTransaction", back_populates="receipt")
