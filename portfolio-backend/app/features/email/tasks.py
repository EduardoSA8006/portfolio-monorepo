"""
Celery tasks for outbound email.

The request path enqueues these via `service.send_*` and never blocks
on SMTP. Tasks themselves are sync — they run inside the Celery worker
which is sync and lives on `celery_net` (no route to the sessions
Redis), so even a malicious template input cannot reach session keys.

Retry policy: SMTP failures are transient (transient relay outage,
greylisting, throttling). We retry with exponential backoff up to
5 attempts. Configuration / template errors (KeyError from
templates.render) are NOT retried — those are bugs that need a code
fix, not delivery resends.
"""
import logging

from app.core.config import settings
from app.features.email import client, templates
from app.features.email.exceptions import EmailDeliveryError
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="email.send",
    bind=True,
    autoretry_for=(EmailDeliveryError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
def send_email_task(self, *, to: str, template_id: str, context: dict) -> None:
    """Render a template and send it.

    Arguments are kwargs-only so the call site reads as data, not
    positional magic. `context` must be JSON-serializable — Celery
    rejects non-JSON payloads at enqueue time (configured in
    app.worker), which keeps unsafe object payloads off the broker.
    """
    if not settings.EMAIL_ENABLED:
        # Defensive: the service layer already short-circuits when
        # disabled, but a stale enqueue (config flip after enqueue,
        # before dequeue) should not blow up the worker.
        logger.info("email.send.skipped_disabled", extra={"template": template_id})
        return

    try:
        content = templates.render(template_id, context)
    except (KeyError, TypeError) as exc:
        # Render errors are programmer errors — log loudly and drop
        # the task. Retrying would loop forever on the same input.
        logger.exception(
            "email.send.template_failed",
            extra={"template": template_id, "error": type(exc).__name__},
        )
        return

    try:
        client.send_message(to=to, content=content)
    except EmailDeliveryError as exc:
        # Will be retried by autoretry_for. Log so the retry chain is
        # visible in the worker output without needing Flower.
        logger.warning(
            "email.send.retry",
            extra={
                "template": template_id,
                "attempt": self.request.retries + 1,
                "error": str(exc),
            },
        )
        raise

    logger.info("email.send.delivered", extra={"template": template_id})
