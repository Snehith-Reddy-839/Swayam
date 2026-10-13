import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, utc_now


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(30), nullable=False)  # HOST, PARTICIPANT, SYSTEM, GATEWAY
    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    group_order = relationship("GroupOrder", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("group_participants.id", ondelete="CASCADE"), nullable=True)
    
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="INFO")  # INFO, WARNING, SUCCESS, ERROR
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
