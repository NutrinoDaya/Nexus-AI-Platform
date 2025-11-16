"""
NexusAI Platform - Celery Configuration
Task queue configuration for background processing
"""

from celery import Celery
from backend.core.config import settings

# Create Celery app
celery_app = Celery(
    "nexusai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=86400,  # 24 hours
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["backend.tasks"])
