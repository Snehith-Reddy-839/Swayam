import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, GuestSession


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def create_guest_session(display_name: str, avatar_color: Optional[str], db: Session) -> GuestSession:
    """Creates a signed guest session that expires in 7 days."""
    token = secrets.token_urlsafe(32)
    colors = ["#FF5C00", "#FF8A00", "#FA5A2A", "#10B981", "#6366F1", "#EC4899", "#8B5CF6", "#06B6D4"]
    selected_color = avatar_color or secrets.choice(colors)

    session = GuestSession(
        session_token=token,
        display_name=display_name.strip(),
        avatar_color=selected_color,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_guest_session_by_token(token: str, db: Session) -> Optional[GuestSession]:
    session = db.query(GuestSession).filter(
        GuestSession.session_token == token,
        GuestSession.expires_at > datetime.now(timezone.utc)
    ).first()
    return session
