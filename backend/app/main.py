import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from app.seed import seed_database
from app.routers import (
    auth,
    products,
    groups,
    cart,
    billing,
    payments,
    receipts,
    orders,
    dashboard,
    ws,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("munchmate.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables are created and seed data exists
    logger.info("Initializing MunchMate database and tables...")
    Base.metadata.create_all(bind=engine)
    try:
        seed_database()
    except Exception as e:
        logger.error(f"Error during startup seeding: {e}")
    yield
    # Shutdown:
    logger.info("MunchMate backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for MunchMate — Collaborative late-night snack & grocery group ordering platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": "MunchMate API",
        "version": "1.0.0",
        "mode": settings.PAYMENT_MODE,
        "demo_mode": settings.DEMO_MODE,
        "currency": "INR (integer paise)"
    }

# Include API Routers under /api/v1
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(groups.router, prefix=settings.API_V1_PREFIX)
app.include_router(cart.router, prefix=settings.API_V1_PREFIX)
app.include_router(billing.router, prefix=settings.API_V1_PREFIX)
app.include_router(payments.router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "message": "Welcome to MunchMate API",
        "tagline": "Your group. Your cravings. One easy order.",
        "docs": "/docs",
        "health": "/health"
    }
