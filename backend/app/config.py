from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "MunchMate — Group Ordering Made Effortless"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "munchmate-super-secret-production-grade-key-2026-secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str = "sqlite:///./munchmate.db"
    
    # Frontend URL for link generation & CORS
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    # Payment Configuration
    # Modes: "demo", "razorpay"
    PAYMENT_MODE: str = "demo"
    DEMO_MODE: bool = True
    
    # Direct UPI Configuration
    UPI_VPA: str = "munchmate@upi"
    UPI_PAYEE_NAME: str = "MunchMate Group Pool"

    # Razorpay Gateway Configuration (Optional/Live)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Group Defaults
    DEFAULT_DELIVERY_FEE_PAISE: int = 4000  # ₹40.00 in paise
    DEFAULT_PLATFORM_FEE_PAISE: int = 1000  # ₹10.00 in paise
    DEFAULT_PACKAGING_FEE_PAISE: int = 1500 # ₹15.00 in paise
    DEFAULT_TAX_PERCENTAGE: float = 5.0      # 5% GST on food

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


settings = Settings()
