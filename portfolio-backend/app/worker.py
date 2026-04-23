# SECURITY: the broker and result backend should live on a Redis instance
# SEPARATE from the one that stores auth:session:* keys. Sharing the same
# instance (even on different logical DBs) means a Celery task-poisoning
# exploit could reach session data via KEYS/SCAN across DBs or a Lua escape.
#
# In production, set CELERY_BROKER_URL / CELERY_RESULT_BACKEND to a dedicated
# Redis with its own requirepass. The defaults in .env.example share the local
# dev Redis for convenience only.
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "portfolio",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
