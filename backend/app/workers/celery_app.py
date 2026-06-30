from __future__ import annotations

from celery import Celery
from app.core.config import settings

# Initialize Celery app
celery = Celery(
    "docsmind_workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

# Standard Celery performance and serialization setups
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Configure task execution limits
    task_time_limit=600,       # Max execution time 10 minutes
    task_soft_time_limit=540,  # Warning trigger after 9 minutes
)
