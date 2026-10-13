from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.product import ProductCategory, Product
from app.schemas.product import ProductCategoryResponse, ProductResponse, ProductListResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/categories", response_model=List[ProductCategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(ProductCategory).order_by(ProductCategory.display_order.asc()).all()
    return categories


@router.get("", response_model=ProductListResponse)
def get_products(
    category_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    is_veg: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("popularity", pattern="^(popularity|price_asc|price_desc|name)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_available == True)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_pattern),
                Product.description.ilike(search_pattern)
            )
        )

    if is_veg is not None:
        query = query.filter(Product.is_veg == is_veg)

    if sort_by == "popularity":
        query = query.order_by(Product.popularity_score.desc())
    elif sort_by == "price_asc":
        query = query.order_by(Product.price_paise.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price_paise.desc())
    elif sort_by == "name":
        query = query.order_by(Product.name.asc())

    products = query.all()
    categories = db.query(ProductCategory).order_by(ProductCategory.display_order.asc()).all()

    items = [
        ProductResponse(
            id=p.id,
            category_id=p.category_id,
            name=p.name,
            description=p.description,
            price_paise=p.price_paise,
            price_inr=p.price_paise / 100.0,
            image_url=p.image_url,
            is_available=p.is_available,
            is_veg=p.is_veg,
            unit=p.unit,
            popularity_score=p.popularity_score
        )
        for p in products
    ]

    return ProductListResponse(
        categories=categories,
        products=items,
        total=len(items)
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_details(product_id: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(
        id=p.id,
        category_id=p.category_id,
        name=p.name,
        description=p.description,
        price_paise=p.price_paise,
        price_inr=p.price_paise / 100.0,
        image_url=p.image_url,
        is_available=p.is_available,
        is_veg=p.is_veg,
        unit=p.unit,
        popularity_score=p.popularity_score
    )
