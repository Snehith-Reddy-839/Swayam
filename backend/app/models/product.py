import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="Package")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id: Mapped[str] = mapped_column(String(50), ForeignKey("product_categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Price stored in integer paise (e.g. ₹55.00 -> 5500 paise)
    price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_veg: Mapped[bool] = mapped_column(Boolean, default=True)
    unit: Mapped[str] = mapped_column(String(30), default="pack")
    popularity_score: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped["ProductCategory"] = relationship("ProductCategory", back_populates="products")
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="product")
