import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.group import GroupOrder, GroupParticipant
from app.models.product import ProductCategory, Product
from app.models.cart import CartItem
from app.seed import seed_database

TEST_DATABASE_URL = "sqlite:///./test_munchmate.db"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    # Seed products into test db
    categories = [
        ProductCategory(id="noodles", name="Instant Noodles", slug="instant-noodles", icon="Soup", display_order=1),
        ProductCategory(id="drinks", name="Cold Drinks", slug="cold-drinks", icon="GlassWater", display_order=2)
    ]
    for c in categories:
        db.add(c)
    db.flush()

    products = [
        Product(
            id="p-maggi",
            category_id="noodles",
            name="Maggi Masala",
            price_paise=1400, # ₹14.00
            image_url="https://example.com/maggi.jpg",
            is_available=True,
            is_veg=True,
            unit="pack"
        ),
        Product(
            id="p-redbull",
            category_id="drinks",
            name="Red Bull Can",
            price_paise=12500, # ₹125.00
            image_url="https://example.com/redbull.jpg",
            is_available=True,
            is_veg=True,
            unit="can"
        ),
        Product(
            id="p-lays",
            category_id="noodles",
            name="Lays Chips",
            price_paise=2000, # ₹20.00
            image_url="https://example.com/lays.jpg",
            is_available=True,
            is_veg=True,
            unit="pack"
        )
    ]
    for p in products:
        db.add(p)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
