"""
Webhook system for notifying frontend about transcription completion.
"""

from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from loguru import logger
import json


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        message_str = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.
    Frontend connects here to receive transcription ready notifications.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for any messages from client
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await manager.send_personal_message(
                json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}),
                websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def send_transcription_ready_notification(appointment_uuid: str):
    """
    Send notification that transcription is ready.
    This is called after transcription processing is complete.
    """
    try:
        message = {
            "type": "transcription_ready",
            "appointment_uuid": appointment_uuid,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Die Transkription ist fertig und kann geprüft werden."
        }

        await manager.broadcast(message)

        logger.info(f"Sent transcription ready notification for appointment {appointment_uuid}")

    except Exception as e:
        logger.error(f"Error sending transcription ready notification: {e}")


@router.post("/test-notification/{appointment_uuid}")
async def test_notification(appointment_uuid: str):
    """
    Test endpoint to manually trigger a transcription ready notification.
    Useful for testing the notification system.
    """
    try:
        await send_transcription_ready_notification(appointment_uuid)
        return {
            "message": "Test notification sent",
            "appointment_uuid": appointment_uuid,
            "connected_clients": len(manager.active_connections)
        }
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
