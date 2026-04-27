"""
Auth audit-event sink.

Single shared helper that writes an `auth_events` row in an isolated DB
session and never raises. Both the auth service (login/logout/MFA flows)
and the auth dependency layer (cookie-signature forgery attempts) write
through this — so security-relevant events arrive at the same table with
the same shape regardless of which call path produced them.

Some event types also fan out to email via
`features.email.service.send_security_alert`. The email side is a
fire-and-forget Celery enqueue and is double-gated (EMAIL_ENABLED +
EMAIL_SECURITY_ALERTS_ENABLED) — a missing/failed email never affects
the DB write. The DB row is the source of truth; the email is just a
heads-up.
"""
import logging
import uuid

from app.core.database import AsyncSessionLocal
from app.features.auth.models import AuthEvent
from app.features.email import service as email_service

logger = logging.getLogger(__name__)

# Subset of event_types that warrant an immediate admin email when
# EMAIL_SECURITY_ALERTS_ENABLED is on. Anything not in this set still
# lands in auth_events but doesn't ping the inbox.
#
# Inclusion criterion: the event represents either a security-changing
# action (TOTP turned off, sessions wiped, recovery executed) or a
# signal of attack-in-progress (lockout fired, forged cookie). Routine
# events (login_success/login_failed/logout) are deliberately excluded
# — those flow through the auth_events table and would drown the inbox
# in transactional noise.
_SECURITY_ALERT_EVENTS = frozenset(
    {
        # Forgery / attack-in-progress
        "cookie_signature_invalid",
        "login_lockout_triggered",
        "login_mfa_failed",          # repeated MFA failures = ongoing attempt
        "login_email_code_failed",   # repeated email-2FA failures = same
        # Security-changing admin actions (each one weakens or rotates
        # the auth surface — admin must see them out-of-band so a
        # malicious operator with DB access cannot quietly disable MFA)
        "totp_disabled",
        "totp_disable_failed",
        "totp_confirm_failed",
        "email_2fa_disabled",
        "email_2fa_disable_failed",
        "sessions_cleared",
        "admin_recovery",
    }
)


async def record_event(
    *,
    event_type: str,
    user_id: str | None = None,
    reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an audit event in an independent DB session. Never raises.

    The session is intentionally separate from any caller's session so an
    audit failure cannot rollback business logic, and a business-logic
    rollback cannot wipe the audit trail.
    """
    try:
        async with AsyncSessionLocal() as audit_db:
            event = AuthEvent(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id) if user_id else None,
                event_type=event_type,
                reason=reason,
                ip=ip,
                user_agent=user_agent[:500] if user_agent else None,
            )
            audit_db.add(event)
            await audit_db.commit()
    except Exception:
        logger.exception("audit.write_failed", extra={"event_type": event_type})

    if event_type in _SECURITY_ALERT_EVENTS:
        try:
            email_service.send_security_alert(
                event_type=event_type,
                ip=ip,
                user_agent=user_agent,
                extra=reason,
            )
        except Exception:
            # Email failures must NEVER bubble up from the audit path —
            # the DB row is what matters, the email is best-effort.
            logger.exception(
                "audit.email_alert_failed", extra={"event_type": event_type}
            )
