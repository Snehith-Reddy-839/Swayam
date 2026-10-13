import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import or_
from app.services.websocket_manager import manager
from app.database import SessionLocal
from app.models.group import GroupOrder

logger = logging.getLogger("munchmate.ws")

router = APIRouter(tags=["Real-time Collaboration"])


@router.websocket("/ws/{group_id}")
async def websocket_group_endpoint(websocket: WebSocket, group_id: str):
    gid_clean = group_id.strip()
    db = SessionLocal()
    try:
        group = db.query(GroupOrder).filter(
            or_(
                GroupOrder.id == gid_clean,
                GroupOrder.id == gid_clean.lower(),
                GroupOrder.invite_code == gid_clean.upper()
            )
        ).first()
        target_id = group.id if group else gid_clean
    finally:
        db.close()

    await manager.connect(websocket, target_id)
    try:
        # Send initial connected acknowledgement
        await websocket.send_text(json.dumps({
            "event": "connected",
            "group_id": target_id,
            "message": "Connected to MunchMate live group channel"
        }))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Handle client ping
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, target_id)
    except Exception as e:
        logger.error(f"WebSocket error in group {target_id}: {e}")
        manager.disconnect(websocket, target_id)
