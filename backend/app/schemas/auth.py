from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=6)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime


class GuestSessionCreate(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
    avatar_color: Optional[str] = "#FF5C00"


class GuestSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_token: str
    display_name: str
    avatar_color: str
    expires_at: datetime
