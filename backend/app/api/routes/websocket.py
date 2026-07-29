import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Query
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger("document_ocr.api.websocket")

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int = Path(..., description="User ID of the client connecting."),
    token: Optional_str = Query(None, description="Optional JWT token to perform credentials check.")
):
    """
    Real-time WebSocket endpoint that registers the client socket session.
    Keeps the connection open to receive pipeline milestones broadcasts.
    """
    await websocket_manager.connect(user_id, websocket)
    
    try:
        while True:
            # We keep the connection alive by listening for message packets
            # Standard client ping/pongs or text requests
            data = await websocket.receive_text()
            logger.debug(f"WebSocket packet received from client {user_id}: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(user_id)
    except Exception as e:
        logger.warning(f"WebSocket exception encountered for user {user_id}: {str(e)}")
        websocket_manager.disconnect(user_id)

# Helper type placeholder
from typing import Optional
Optional_str = Optional[str]
