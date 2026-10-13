import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.group import GroupOrder, GroupParticipant
from app.models.user import User, GuestSession
from app.models.audit import AuditLog
from app.schemas.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupJoinRequest,
    GroupParticipantResponse,
    GroupDetailResponse,
)
from app.services.websocket_manager import manager
from app.services.auth_service import decode_access_token

router = APIRouter(prefix="/groups", tags=["Group Orders"])


def generate_unique_invite_code(db: Session) -> str:
    """Generates an unguessable 6-character uppercase alphanumeric code."""
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not db.query(GroupOrder).filter(GroupOrder.invite_code == code).first():
            return code
    raise RuntimeError("Failed to generate unique invite code")


@router.post("", response_model=GroupDetailResponse)
async def create_group(
    req: GroupCreateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    # Determine host: registered user or guest host
    user: Optional[User] = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization.split(" ")[1])
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"]).first()

    host_name = user.name if user else (req.host_name or "Host")
    guest_session: Optional[GuestSession] = None
    if not user:
        if req.guest_session_token:
            guest_session = db.query(GuestSession).filter(GuestSession.session_token == req.guest_session_token).first()
        if not guest_session:
            # Create a guest session for host
            guest_session = GuestSession(
                session_token=secrets.token_urlsafe(32),
                display_name=host_name,
                avatar_color="#FF5C00",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.add(guest_session)
            db.flush()

    invite_code = generate_unique_invite_code(db)
    closing_time = datetime.now(timezone.utc) + timedelta(minutes=req.cart_closing_minutes or 30)

    group = GroupOrder(
        invite_code=invite_code,
        title=req.title,
        host_user_id=user.id if user else None,
        host_guest_session_id=guest_session.id if guest_session else None,
        host_name=host_name,
        store_mode=req.store_mode,
        delivery_location=req.delivery_location,
        cart_closing_time=closing_time,
        participant_limit=req.participant_limit,
        cart_status="OPEN",
        fee_policy=req.fee_policy,
        delivery_fee_paise=req.delivery_fee_paise or 4000,
        platform_fee_paise=req.platform_fee_paise or 1000,
        packaging_fee_paise=req.packaging_fee_paise or 1500,
        discount_paise=req.discount_paise or 0,
        tax_percentage=req.tax_percentage or 5.0,
        is_payment_required_before_finalize=req.is_payment_required_before_finalize,
        host_approval_required=req.host_approval_required,
        allow_participant_edit=req.allow_participant_edit,
        passcode=req.passcode if req.passcode else None
    )
    db.add(group)
    db.flush()

    # Automatically add the host as the first participant
    host_participant_id = str(secrets.token_hex(16))
    host_participant = GroupParticipant(
        id=host_participant_id,
        group_order_id=group.id,
        user_id=user.id if user else None,
        guest_session_id=guest_session.id if guest_session else None,
        display_name=host_name,
        avatar_color="#FF5C00",
        is_host=True,
        payment_status="PENDING"
    )
    db.add(host_participant)
    db.flush()

    # Add audit log
    audit = AuditLog(
        group_order_id=group.id,
        action="GROUP_CREATED",
        actor_type="HOST",
        actor_id=host_participant.id,
        actor_name=host_name,
        details_json=f'{{"title": "{group.title}", "invite_code": "{invite_code}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(group)

    share_url = f"{settings.FRONTEND_URL}/group/{group.invite_code}"

    return GroupDetailResponse(
        id=group.id,
        invite_code=group.invite_code,
        title=group.title,
        host_name=group.host_name,
        store_mode=group.store_mode,
        delivery_location=group.delivery_location,
        cart_closing_time=group.cart_closing_time,
        participant_limit=group.participant_limit,
        cart_status=group.cart_status,
        fee_policy=group.fee_policy,
        delivery_fee_paise=group.delivery_fee_paise,
        platform_fee_paise=group.platform_fee_paise,
        packaging_fee_paise=group.packaging_fee_paise,
        discount_paise=group.discount_paise,
        tax_percentage=group.tax_percentage,
        is_payment_required_before_finalize=group.is_payment_required_before_finalize,
        host_approval_required=group.host_approval_required,
        allow_participant_edit=group.allow_participant_edit,
        has_passcode=bool(group.passcode),
        created_at=group.created_at,
        participants_count=1,
        share_url=share_url,
        host_participant_id=host_participant.id,
        host_session_token=guest_session.session_token if guest_session else None
    )


@router.get("", response_model=List[GroupDetailResponse])
def list_recent_groups(limit: int = 10, db: Session = Depends(get_db)):
    """List recent groups for discovery, history and testing."""
    groups = db.query(GroupOrder).order_by(GroupOrder.created_at.desc()).limit(limit).all()
    results = []
    for g in groups:
        participants_count = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == g.id).count()
        results.append(
            GroupDetailResponse(
                id=g.id,
                invite_code=g.invite_code,
                title=g.title,
                host_name=g.host_name,
                store_mode=g.store_mode,
                delivery_location=g.delivery_location,
                cart_closing_time=g.cart_closing_time,
                participant_limit=g.participant_limit,
                cart_status=g.cart_status,
                fee_policy=g.fee_policy,
                delivery_fee_paise=g.delivery_fee_paise,
                platform_fee_paise=g.platform_fee_paise,
                packaging_fee_paise=g.packaging_fee_paise,
                discount_paise=g.discount_paise,
                tax_percentage=g.tax_percentage,
                is_payment_required_before_finalize=g.is_payment_required_before_finalize,
                host_approval_required=g.host_approval_required,
                allow_participant_edit=g.allow_participant_edit,
                has_passcode=bool(g.passcode),
                created_at=g.created_at,
                participants_count=participants_count,
                share_url=f"{settings.FRONTEND_URL}/group/{g.invite_code}"
            )
        )
    return results


@router.get("/{code_or_id}", response_model=GroupDetailResponse)
def get_group_details(code_or_id: str, db: Session = Depends(get_db)):
    cid_clean = code_or_id.strip()
    # Lookup by invite_code or UUID
    group = db.query(GroupOrder).filter(
        (GroupOrder.invite_code == cid_clean.upper()) |
        (GroupOrder.id == cid_clean) |
        (GroupOrder.id == cid_clean.lower())
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group order not found")

    participants_count = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == group.id).count()
    host_p = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == group.id, GroupParticipant.is_host == True).first()
    share_url = f"{settings.FRONTEND_URL}/group/{group.invite_code}"

    return GroupDetailResponse(
        id=group.id,
        invite_code=group.invite_code,
        title=group.title,
        host_name=group.host_name,
        store_mode=group.store_mode,
        delivery_location=group.delivery_location,
        cart_closing_time=group.cart_closing_time,
        participant_limit=group.participant_limit,
        cart_status=group.cart_status,
        fee_policy=group.fee_policy,
        delivery_fee_paise=group.delivery_fee_paise,
        platform_fee_paise=group.platform_fee_paise,
        packaging_fee_paise=group.packaging_fee_paise,
        discount_paise=group.discount_paise,
        tax_percentage=group.tax_percentage,
        is_payment_required_before_finalize=group.is_payment_required_before_finalize,
        host_approval_required=group.host_approval_required,
        allow_participant_edit=group.allow_participant_edit,
        has_passcode=bool(group.passcode),
        created_at=group.created_at,
        participants_count=participants_count,
        share_url=share_url,
        host_participant_id=host_p.id if host_p else None
    )


@router.post("/{invite_code}/join", response_model=GroupParticipantResponse)
async def join_group(
    invite_code: str,
    req: GroupJoinRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    code_clean = invite_code.strip()
    group = db.query(GroupOrder).filter(
        (GroupOrder.invite_code == code_clean.upper()) |
        (GroupOrder.id == code_clean) |
        (GroupOrder.id == code_clean.lower())
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group order not found")

    if group.cart_status in ["FINALIZED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot join a closed or finalized group order")

    # Passcode validation
    if group.passcode and group.passcode != req.passcode:
        raise HTTPException(status_code=403, detail="Incorrect group passcode")

    # Participant limit check
    current_count = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == group.id).count()
    if current_count >= group.participant_limit:
        raise HTTPException(status_code=400, detail=f"Group participant limit ({group.participant_limit}) reached")

    # Check user or guest session
    user: Optional[User] = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization.split(" ")[1])
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"]).first()

    guest_session: Optional[GuestSession] = None
    if not user:
        if req.guest_session_token:
            guest_session = db.query(GuestSession).filter(GuestSession.session_token == req.guest_session_token).first()
        if not guest_session:
            guest_session = GuestSession(
                session_token=secrets.token_urlsafe(32),
                display_name=req.display_name.strip(),
                avatar_color=req.avatar_color or "#10B981",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.add(guest_session)
            db.flush()

    # Check if participant already exists in group
    existing_participant: Optional[GroupParticipant] = None
    if user:
        existing_participant = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group.id,
            GroupParticipant.user_id == user.id
        ).first()
    elif guest_session:
        existing_participant = db.query(GroupParticipant).filter(
            GroupParticipant.group_order_id == group.id,
            GroupParticipant.guest_session_id == guest_session.id
        ).first()

    if existing_participant:
        return GroupParticipantResponse(
            id=existing_participant.id,
            display_name=existing_participant.display_name,
            avatar_color=existing_participant.avatar_color,
            is_host=existing_participant.is_host,
            payment_status=existing_participant.payment_status,
            amount_paid_paise=existing_participant.amount_paid_paise,
            amount_paid_inr=existing_participant.amount_paid_paise / 100.0,
            joined_at=existing_participant.joined_at,
            session_token=guest_session.session_token if guest_session else None
        )

    # Create new participant with explicit UUID
    p_id = str(uuid.uuid4())
    participant = GroupParticipant(
        id=p_id,
        group_order_id=group.id,
        user_id=user.id if user else None,
        guest_session_id=guest_session.id if guest_session else None,
        display_name=req.display_name.strip(),
        avatar_color=req.avatar_color or "#10B981",
        is_host=False,
        payment_status="PENDING"
    )
    db.add(participant)
    db.flush()

    audit = AuditLog(
        group_order_id=group.id,
        action="PARTICIPANT_JOINED",
        actor_type="PARTICIPANT",
        actor_id=p_id,
        actor_name=participant.display_name,
        details_json=f'{{"name": "{participant.display_name}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(participant)

    # Broadcast real-time event
    await manager.broadcast_to_group(group.id, {
        "event": "participant_joined",
        "participant": {
            "id": participant.id,
            "display_name": participant.display_name,
            "avatar_color": participant.avatar_color,
            "is_host": participant.is_host
        }
    })

    return GroupParticipantResponse(
        id=participant.id,
        display_name=participant.display_name,
        avatar_color=participant.avatar_color,
        is_host=participant.is_host,
        payment_status=participant.payment_status,
        amount_paid_paise=participant.amount_paid_paise,
        amount_paid_inr=participant.amount_paid_paise / 100.0,
        joined_at=participant.joined_at,
        session_token=guest_session.session_token if guest_session else None
    )


@router.get("/{group_id}/participants", response_model=List[GroupParticipantResponse])
def get_group_participants(group_id: str, db: Session = Depends(get_db)):
    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        (GroupOrder.id == gid_clean) |
        (GroupOrder.id == gid_clean.lower()) |
        (GroupOrder.invite_code == gid_clean.upper())
    ).first()
    target_id = group.id if group else gid_clean
    participants = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == target_id).all()
    return [
        GroupParticipantResponse(
            id=p.id,
            display_name=p.display_name,
            avatar_color=p.avatar_color,
            is_host=p.is_host,
            payment_status=p.payment_status,
            amount_paid_paise=p.amount_paid_paise,
            amount_paid_inr=p.amount_paid_paise / 100.0,
            joined_at=p.joined_at
        )
        for p in participants
    ]


@router.post("/{group_id}/lock")
async def lock_cart(
    group_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_host_participant

    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        (GroupOrder.id == gid_clean) |
        (GroupOrder.id == gid_clean.lower()) |
        (GroupOrder.invite_code == gid_clean.upper())
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Host Authorization
    resolve_host_participant(
        group_order_id=group.id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )

    group.cart_status = "LOCKED"
    db.commit()

    await manager.broadcast_to_group(group.id, {
        "event": "cart_locked",
        "cart_status": "LOCKED",
        "message": "The cart has been locked by the host for bill calculation and checkout."
    })
    return {"message": "Cart locked successfully", "cart_status": "LOCKED"}


@router.post("/{group_id}/reopen")
async def reopen_cart(
    group_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.services.auth_service import resolve_host_participant

    gid_clean = group_id.strip()
    group = db.query(GroupOrder).filter(
        (GroupOrder.id == gid_clean) |
        (GroupOrder.id == gid_clean.lower()) |
        (GroupOrder.invite_code == gid_clean.upper())
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Host Authorization
    resolve_host_participant(
        group_order_id=group.id,
        authorization=authorization,
        session_token=session_token,
        x_session_token=x_session_token,
        db=db
    )

    if group.cart_status in ["FINALIZED"]:
        raise HTTPException(status_code=400, detail="Cannot reopen an already finalized order")

    group.cart_status = "OPEN"
    db.commit()

    await manager.broadcast_to_group(group.id, {
        "event": "cart_reopened",
        "cart_status": "OPEN",
        "message": "The cart has been reopened by the host."
    })
    return {"message": "Cart reopened successfully", "cart_status": "OPEN"}
