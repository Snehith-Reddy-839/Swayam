import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
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


def resolve_caller_identity(
    authorization: Optional[str] = None,
    session_token: Optional[str] = None,
    x_session_token: Optional[str] = None,
    db: Session = None
) -> Tuple[Optional[User], Optional[GuestSession]]:
    """
    Validates server-issued credentials provided via:
    1. Authorization header ('Bearer <jwt>' or 'Guest <session_token>')
    2. Explicit session_token param/body
    3. X-Session-Token header
    Returns (user, guest_session). Raises HTTPException if an explicit credential is malformed or invalid.
    """
    token = session_token or x_session_token
    auth_header = authorization.strip() if authorization else None

    # Check Authorization header format
    if auth_header:
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header.split(" ", 1)[1].strip()
            payload = decode_access_token(jwt_token)
            if not payload or "sub" not in payload:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Invalid or expired access token")
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if not user:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="User account not found")
            return (user, None)
        elif auth_header.startswith("Guest "):
            token = auth_header.split(" ", 1)[1].strip()

    if token:
        token = token.strip()
        guest = get_guest_session_by_token(token, db)
        if not guest:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid or expired guest session token")
        return (None, guest)

    return (None, None)


def resolve_caller_participant(
    group_order_id: str,
    authorization: Optional[str] = None,
    session_token: Optional[str] = None,
    x_session_token: Optional[str] = None,
    participant_id_hint: Optional[str] = None,
    db: Session = None
):
    """
    Strictly authenticates the caller and verifies membership in the specified group_order_id.
    Derives participant identity from server-side validated credentials.
    Rejects missing or invalid credentials with 401, and foreign group access or mismatch with 403.
    """
    from fastapi import HTTPException
    from app.models.group import GroupParticipant

    user, guest = resolve_caller_identity(
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )

    if not user and not guest:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid session token or bearer token."
        )

    # Find the participant record in the group matching this credential
    participant: Optional[GroupParticipant] = None
    if user:
        participant = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group_order_id,
            GroupParticipant.user_id == user.id
        ).first()
    elif guest:
        participant = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group_order_id,
            GroupParticipant.guest_session_id == guest.id
        ).first()

    if not participant:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Caller is not a participant in this group order."
        )

    if participant_id_hint and participant_id_hint != participant.id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Caller identity does not match the requested participant ID."
        )

    return participant


def resolve_host_participant(
    group_order_id: str,
    authorization: Optional[str] = None,
    session_token: Optional[str] = None,
    x_session_token: Optional[str] = None,
    host_participant_id_hint: Optional[str] = None,
    db: Session = None
):
    """
    Strictly authenticates the caller and verifies that they are the genuine HOST of the specific group.
    Rejects unauthenticated callers with 401, non-hosts or hosts from another group with 403.
    """
    from fastapi import HTTPException

    participant = resolve_caller_participant(
        group_order_id=group_order_id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        participant_id_hint=host_participant_id_hint,
        db=db
    )

    if not participant.is_host:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only the group host is authorized to perform this operation."
        )

    return participant
