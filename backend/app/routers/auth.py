from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, GuestSession
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    GuestSessionCreate,
    GuestSessionResponse,
)
from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    create_guest_session,
    get_guest_session_by_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    user = User(
        name=req.name,
        email=req.email.lower(),
        phone=req.phone,
        hashed_password=get_password_hash(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id, "email": user.email, "name": user.name})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email
    )


@router.post("/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = create_access_token(data={"sub": user.id, "email": user.email, "name": user.name})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email
    )


@router.post("/guest-session", response_model=GuestSessionResponse)
def create_guest(req: GuestSessionCreate, db: Session = Depends(get_db)):
    """Creates a friction-free guest session with an avatar color."""
    session = create_guest_session(req.display_name, req.avatar_color, db)
    return GuestSessionResponse(
        id=session.id,
        session_token=session.session_token,
        display_name=session.display_name,
        avatar_color=session.avatar_color,
        expires_at=session.expires_at
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
