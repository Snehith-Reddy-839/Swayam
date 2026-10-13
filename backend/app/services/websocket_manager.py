import json
import logging
from typing import Dict, List, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("munchmate.ws")


class ConnectionManager:
    """Manages group-scoped WebSocket connections for live collaborative cart and updates."""

    def __init__(self):
        # group_id -> set of active WebSockets
        self.active_groups: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_id: str):
        await websocket.accept()
        if group_id not in self.active_groups:
            self.active_groups[group_id] = set()
        self.active_groups[group_id].add(websocket)
        logger.info(f"WebSocket client connected to group {group_id}. Active: {len(self.active_groups[group_id])}")

    def disconnect(self, websocket: WebSocket, group_id: str):
        if group_id in self.active_groups:
            self.active_groups[group_id].discard(websocket)
            if not self.active_groups[group_id]:
                del self.active_groups[group_id]
        logger.info(f"WebSocket client disconnected from group {group_id}")

    async def broadcast_to_group(self, group_id: str, message: Dict[str, Any]):
        """Broadcasts a JSON message payload to all active participants in a group."""
        if group_id not in self.active_groups:
            return

        dead_connections = set()
        data_text = json.dumps(message)
        for connection in list(self.active_groups[group_id]):
            try:
                await connection.send_text(data_text)
            except Exception as e:
                logger.warning(f"Failed to send to client in group {group_id}: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead, group_id)


manager = ConnectionManager()
