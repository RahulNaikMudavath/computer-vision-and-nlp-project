import os
from celery import Celery
from app.core.config import settings

# Instantiate the Celery app
celery_app = Celery(
    "docvision_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Load configuration settings
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Import task definitions explicitly to register them
import app.tasks.worker
