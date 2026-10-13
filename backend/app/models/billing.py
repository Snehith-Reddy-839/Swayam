import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class BillAllocation(Base):
    __tablename__ = "bill_allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_participants.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # All values strictly in integer paise
    items_subtotal_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shared_fees_share_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_share_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_share_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rounding_adjustment_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_payable_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_paid_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    group_order = relationship("GroupOrder", back_populates="bill_allocations")
    participant = relationship("GroupParticipant", back_populates="bill_allocation")
