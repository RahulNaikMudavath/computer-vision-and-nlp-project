import json
import logging
import asyncio
from typing import Dict
from fastapi import WebSocket
from app.services.cache_service import cache_service

logger = logging.getLogger("document_ocr.websocket_manager")

class WebSocketManager:
    """
    WebSocket Connection Manager with Redis Pub/Sub listener support to facilitate
    cross-process progress notifications from Celery workers to FastAPI clients.
    """
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.listener_task = None

    async def connect(self, user_id: int, websocket: WebSocket):
        """Registers a newly connected client socket."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket client connected. User ID: {user_id} (Active connections: {len(self.active_connections)})")

    def disconnect(self, user_id: int):
        """Deregisters a disconnected client socket."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket client disconnected. User ID: {user_id} (Active connections: {len(self.active_connections)})")

    async def send_progress_local(self, user_id: int, document_id: str, status: str, progress: int, message: str):
        """Pushes a local JSON payload directly to the client socket (in-memory map)."""
        websocket = self.active_connections.get(user_id)
        if not websocket:
            return
            
        payload = {
            "document_id": document_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        
        try:
            await websocket.send_json(payload)
        except Exception as ex:
            logger.warning(f"Error transmitting local WebSocket notification to User {user_id}: {str(ex)}")
            self.disconnect(user_id)

    def publish_progress(self, user_id: int, document_id: str, status: str, progress: int, message: str):
        """
        Publishes progress milestones to the Redis Pub/Sub channel so that
        listening FastAPI server instances pick it up and push it to active clients.
        """
        payload = {
            "user_id": user_id,
            "document_id": document_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        
        # Publish to Redis channel
        if cache_service.redis_client:
            try:
                cache_service.redis_client.publish("progress_updates", json.dumps(payload))
                logger.info(f"Published progress update to Redis for User {user_id} (Status: {status})")
                return
            except Exception as ex:
                logger.error(f"Failed to publish progress to Redis: {str(ex)}")
        
        # Fallback to direct synchronous execution in single-process or testing mode
        # Run using event loop if active
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.send_progress_local(user_id, document_id, status, progress, message))
        except Exception:
            pass

    async def start_redis_listener(self):
        """
        Runs an asynchronous loop listening to the 'progress_updates' Redis Pub/Sub channel,
        routing received notifications to active local WebSocket connections.
        """
        if not cache_service.redis_client:
            logger.warning("Redis is offline. WebSocket cross-process updates subscription skipped.")
            return

        try:
            pubsub = cache_service.redis_client.pubsub()
            pubsub.subscribe("progress_updates")
            logger.info("Subscribed to Redis 'progress_updates' channel.")
            
            while True:
                # Retrieve messages asynchronously
                # Using pubsub.get_message in a non-blocking way
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if message:
                    try:
                        data = json.loads(message["data"])
                        user_id = int(data.get("user_id"))
                        document_id = data.get("document_id")
                        status = data.get("status")
                        progress = int(data.get("progress"))
                        msg = data.get("message")
                        
                        await self.send_progress_local(user_id, document_id, status, progress, msg)
                    except Exception as parse_ex:
                        logger.error(f"Error parsing Redis Pub/Sub message: {str(parse_ex)}")
                
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("Redis WebSockets Pub/Sub listener cancelled.")
        except Exception as ex:
            logger.error(f"Redis Pub/Sub listener error encountered: {str(ex)}")
            # Retry after delay
            await asyncio.sleep(2.0)
            self.listener_task = asyncio.create_task(self.start_redis_listener())

# Global connection manager singleton
websocket_manager = WebSocketManager()
