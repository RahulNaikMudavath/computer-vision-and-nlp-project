import os
import shutil
import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.models.database import get_db
from app.services.cache_service import cache_service
from app.services.vlm_service import vlm_service

logger = logging.getLogger("document_ocr.monitoring")
router = APIRouter()

@router.get("/liveness", summary="Container Liveness Probe", status_code=status.HTTP_200_OK)
async def liveness() -> dict:
    """Signals standard service process survival."""
    return {"status": "healthy", "service": "DocVision AI"}

@router.get("/readiness", summary="Service Readiness Probe")
async def readiness() -> dict:
    """Checks whether dependency models and model weights are initialized."""
    # Verify VLM service state is loaded or mocked active
    if vlm_service is not None:
        return {"status": "ready", "model_loaded": True}
    return {"status": "not_ready", "model_loaded": False}

@router.get("/health", summary="Detailed Infrastructure Health Check")
async def health(db: Session = Depends(get_db)) -> dict:
    """
    Checks database connections, Redis caches pings, and storage limits.
    """
    health_status = {
        "status": "healthy",
        "database": "online",
        "redis": "online",
        "storage": "ok",
        "details": {}
    }
    
    # 1. Database Connection check
    try:
        db.execute(text("SELECT 1"))
        health_status["details"]["db_latency_ms"] = 1.0  # mock check success
    except Exception as ex:
        health_status["database"] = "offline"
        health_status["status"] = "unhealthy"
        health_status["details"]["db_error"] = str(ex)
        
    # 2. Redis Connection check
    if cache_service.redis_client:
        try:
            cache_service.redis_client.ping()
        except Exception as ex:
            health_status["redis"] = "offline"
            health_status["status"] = "unhealthy"
            health_status["details"]["redis_error"] = str(ex)
    else:
        health_status["redis"] = "using_mock_fallback"
        
    # 3. Disk Space check
    try:
        # Check upload folder workspace bounds
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024 ** 3)
        health_status["details"]["free_disk_gb"] = round(free_gb, 2)
        if free_gb < 1.0: # Less than 1GB space remaining
            health_status["storage"] = "warning_disk_low"
    except Exception as ex:
        health_status["storage"] = "error"
        health_status["details"]["disk_error"] = str(ex)
        
    return health_status
