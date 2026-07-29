import json
import logging
from typing import Any, Optional
import redis
from app.core.config import settings

logger = logging.getLogger("document_ocr.cache_service")

class CacheService:
    """
    Redis Cache Service with in-memory dict fallbacks for robust execution
    during local development, testing, and offline modes.
    """
    def __init__(self):
        self.redis_client = None
        self.mock_store = {}
        # Try initializing Redis connection pool
        self.redis_url = settings.REDIS_URL
        
        try:
            self.redis_client = redis.from_url(self.redis_url, socket_connect_timeout=2, decode_responses=True)
            self.redis_client.ping()
            logger.info("Successfully connected to Redis cache database.")
        except Exception as ex:
            self.redis_client = None
            logger.warning(f"Redis connection failed. Falling back to In-Memory mock store. Details: {str(ex)}")

    def get(self, key: str) -> Optional[str]:
        """Gets string value for a key."""
        if self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception as e:
                logger.error(f"Redis get failed: {str(e)}")
        return self.mock_store.get(key)

    def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Sets string value for a key with an optional TTL expiration in seconds."""
        if self.redis_client:
            try:
                self.redis_client.set(key, value, ex=expire)
                return True
            except Exception as e:
                logger.error(f"Redis set failed: {str(e)}")
        self.mock_store[key] = value
        return True

    def delete(self, key: str) -> bool:
        """Purges a key from the cache store."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete failed: {str(e)}")
        if key in self.mock_store:
            del self.mock_store[key]
        return True

    def get_json(self, key: str) -> Optional[Any]:
        """Retrieves and deserializes JSON payload."""
        val = self.get(key)
        if val:
            try:
                return json.loads(val)
            except Exception:
                return None
        return None

    def set_json(self, key: str, data: Any, expire: int = 3600) -> bool:
        """Serializes and caches JSON dictionary/list payload."""
        try:
            serialized = json.dumps(data)
            return self.set(key, serialized, expire=expire)
        except Exception as e:
            logger.error(f"JSON serialization for caching failed: {str(e)}")
            return False

    def clear_document_cache(self, document_id: str):
        """Helper to invalidate all OCR, metadata, and QA query caches for a document ID."""
        logger.info(f"Invalidating cache registry for document: '{document_id}'")
        self.delete(f"doc:ocr:{document_id}")
        self.delete(f"doc:meta:{document_id}")
        self.delete(f"doc:json:{document_id}")
        if self.redis_client:
            try:
                # Scan and delete QA questions cached for this document
                keys = self.redis_client.keys(f"doc:chat:{document_id}:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Failed to scan Redis for document chats keys: {str(e)}")

# Global Cache Service singleton
cache_service = CacheService()
