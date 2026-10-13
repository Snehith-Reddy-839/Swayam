from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ProductCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    icon: str
    display_order: int


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    name: str
    description: Optional[str] = None
    price_paise: int
    price_inr: float  # convenience formatted float
    image_url: str
    is_available: bool
    is_veg: bool
    unit: str
    popularity_score: int


class ProductListResponse(BaseModel):
    categories: List[ProductCategoryResponse]
    products: List[ProductResponse]
    total: int
