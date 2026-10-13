import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class MerchantOrder(Base):
    __tablename__ = "merchant_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Status: NOT_PLACED, PLACED, ACCEPTED, PREPARING, OUT_FOR_DELIVERY, DELIVERED, CANCELLED
    status: Mapped[str] = mapped_column(String(30), default="NOT_PLACED", index=True)
    
    platform_name: Mapped[str] = mapped_column(String(100), default="Blinkit / Zepto / Canteen")
    external_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    placed_by_host_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    placed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Snapshot of combined quantities
    combined_items_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_bill_paise: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    group_order = relationship("GroupOrder", back_populates="merchant_order")
