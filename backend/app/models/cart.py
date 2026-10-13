import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_participants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Price snapshot at the time item was placed into cart (paise)
    unit_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    item_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    group_order = relationship("GroupOrder", back_populates="cart_items")
    participant = relationship("GroupParticipant", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")

    # Enforce unique product per participant per group order
    __table_args__ = (
        UniqueConstraint('group_order_id', 'participant_id', 'product_id', name='uq_cart_participant_product'),
    )
