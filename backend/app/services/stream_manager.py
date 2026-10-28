import asyncio
import logging
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("uvicorn.error")

class StreamManager:
    """
    Manages active WebSocket client connections and provides real-time broadcast
    of detection telemetry and annotated JPEG frames to Next.js clients.
    """
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.latest_telemetry: Optional[Dict[str, Any]] = None
        self.latest_annotated_frame_bytes: Optional[bytes] = None
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[WS] Client connected. Active clients: {len(self.active_connections)}")

        # Send latest state immediately upon connection if available
        if self.latest_telemetry:
            try:
                await websocket.send_json({
                    "type": "initial_state",
                    "telemetry": self.latest_telemetry
                })
            except Exception as e:
                logger.warning(f"[WS] Failed to send initial state to new client: {e}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WS] Client disconnected. Active clients: {len(self.active_connections)}")

    async def update_latest(self, telemetry: Dict[str, Any], frame_bytes: bytes):
        async with self._lock:
            self.latest_telemetry = telemetry
            self.latest_annotated_frame_bytes = frame_bytes

    async def broadcast(self, payload: Dict[str, Any]):
        """
        Broadcasts JSON payload to all active dashboard WebSocket subscribers.
        Automatically prunes disconnected clients.
        """
        if not self.active_connections:
            return

        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.debug(f"[WS] Error dispatching to client: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)

# Global singleton instance
stream_manager = StreamManager()
