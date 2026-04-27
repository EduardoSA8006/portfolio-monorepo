"""
Email service — the only entry point that callers in the request path
or in `audit.record_event` should touch.

Each `send_*` function:
  1. Returns immediately if EMAIL_ENABLED is False (debug log).
  2. For codes: calls `code_store.issue_code` to mint a fresh code
     and writes it to Redis BEFORE enqueueing the email — that way
     a Celery backlog doesn't widen the window where a code exists
     in Redis but the user has no way to learn it.
  3. Enqueues the Celery task with a JSON-serializable context.
     `.delay()` is sync but cheap (single broker write); calling it
     from an async function is fine — the broker round-trip is
     dominated by network, not CPU.
"""
import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.core.config import settings
from app.features.email import code_store, templates
from app.features.email.tasks import send_email_task

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return settings.EMAIL_ENABLED


def _ttl_minutes() -> int:
    # Round up so "expires in 5 minutes" never undersells the actual
    # window the user has.
    seconds = settings.EMAIL_2FA_CODE_TTL_SECONDS
    return max(1, (seconds + 59) // 60)


async def send_two_factor_code(*, redis: Redis, user_id: str, name: str, to: str) -> None:
    """Issue a one-time code and email it. The plain code never leaves
    Redis + the rendered email body — callers do not see it."""
    if not _enabled():
        logger.debug("email.send_two_factor_code.skipped_disabled")
        return
    code = await code_store.issue_code(redis, user_id)
    send_email_task.delay(
        to=to,
        template_id="two_factor_code",
        context={
            "name": name,
            "code": code,
            "ttl_minutes": _ttl_minutes(),
        },
    )


def send_login_notification(*, name: str, to: str, ip: str, user_agent: str | None) -> None:
    """Fire-and-forget login notice. Sync because there is no Redis
    interaction to await."""
    if not _enabled():
        logger.debug("email.send_login_notification.skipped_disabled")
        return
    send_email_task.delay(
        to=to,
        template_id="login_notification",
        context={
            "name": name,
            "ip": ip,
            "user_agent": user_agent,
            "when": datetime.now(UTC).isoformat(),
        },
    )


def send_security_alert(
    *,
    event_type: str,
    ip: str | None = None,
    user_agent: str | None = None,
    extra: str | None = None,
) -> None:
    """Route a security event to EMAIL_ADMIN_RECIPIENT.

    Two layers of opt-in:
      - EMAIL_ENABLED gates the SMTP path entirely.
      - EMAIL_SECURITY_ALERTS_ENABLED keeps a noisy day from flooding
        the admin inbox while transactional 2FA email keeps working.

    Returns silently when either flag is off — security alerts are
    informative, not authoritative; the auth_events row in Postgres
    is the source of truth and is written regardless."""
    if not _enabled() or not settings.EMAIL_SECURITY_ALERTS_ENABLED:
        return
    if not settings.EMAIL_ADMIN_RECIPIENT:
        return
    # Per-event template if registered; otherwise the generic fallback
    # so a brand-new event_type still produces a useful email instead
    # of erroring out and silently dropping the alert.
    candidate = f"security/{event_type}"
    template_id = candidate if candidate in templates.TEMPLATES else "security/_generic"
    send_email_task.delay(
        to=settings.EMAIL_ADMIN_RECIPIENT,
        template_id=template_id,
        context={
            "event_type": event_type,
            "ip": ip,
            "user_agent": user_agent,
            "when": datetime.now(UTC).isoformat(),
            "extra": extra,
        },
    )


def send_admin_recovery_notice(*, name: str, to: str, ip: str | None = None) -> None:
    """Inform the recovered admin that a `--reset` just ran. Cheapest
    detection for an unauthorized recovery: the legitimate owner
    receives a notice about a reset they didn't perform."""
    if not _enabled():
        return
    send_email_task.delay(
        to=to,
        template_id="admin_recovery_notice",
        context={
            "name": name,
            "ip": ip,
            "when": datetime.now(UTC).isoformat(),
        },
    )
