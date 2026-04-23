# SECURITY: the broker and result backend live on a Redis instance that is
# SEPARATE from the one that stores auth:session:* keys. This is enforced by
# docker-compose.prod.yml — the Celery worker joins celery_net, which has no
# route to the sessions Redis on sessions_net. A compromised task therefore
# cannot KEYS/SCAN/DEL auth:session:* or escalate via Lua. Each instance has
# its own requirepass (REDIS_PASSWORD vs CELERY_REDIS_PASSWORD).
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
