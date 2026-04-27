"""
SMTP client wrapper.

Synchronous on purpose: it runs inside the Celery worker, which is
sync, and stdlib `smtplib` is robust enough for the volume this app
sends (transactional only — verification codes, security alerts,
notifications). Keeping the dependency footprint to stdlib avoids
adding a runtime library for what is effectively a few hundred bytes
of plain-text per send.

The high-level service layer never imports this module — it only
enqueues a Celery task. That keeps the request path off the SMTP
socket entirely.
"""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import settings
from app.features.email.exceptions import EmailDeliveryError
from app.features.email.templates import EmailContent


def _from_header() -> str:
    return formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM_ADDRESS))


def _build_message(*, to: str, content: EmailContent) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = _from_header()
    msg["To"] = to
    msg["Subject"] = content.subject
    # Stable Message-ID so retries (Celery) don't multiply messages on
    # the recipient side if their MTA dedupes by ID.
    msg["Message-ID"] = make_msgid(domain=settings.EMAIL_FROM_ADDRESS.split("@")[-1] or "localhost")
    msg.set_content(content.text_body)
    if content.html_body:
        msg.add_alternative(content.html_body, subtype="html")
    return msg


def _open_smtp() -> smtplib.SMTP | smtplib.SMTP_SSL:
    """Return an authenticated SMTP connection.

    Three modes:
      - implicit TLS (SSL) on 465 → SMTP_SSL
      - STARTTLS on 587 → SMTP + starttls()
      - plain (no TLS) → SMTP, only allowed when both flags are False
        and we are NOT in production (the config validator already
        forbids EMAIL_ENABLED in prod without explicit transport flags).
    """
    timeout = settings.EMAIL_TIMEOUT_SECONDS
    host = settings.EMAIL_SMTP_HOST
    port = settings.EMAIL_SMTP_PORT
    if settings.EMAIL_USE_SSL:
        ctx = ssl.create_default_context()
        client: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
            host=host, port=port, timeout=timeout, context=ctx
        )
    else:
        client = smtplib.SMTP(host=host, port=port, timeout=timeout)
        if settings.EMAIL_USE_TLS:
            client.starttls(context=ssl.create_default_context())
    if settings.EMAIL_SMTP_USERNAME:
        client.login(settings.EMAIL_SMTP_USERNAME, settings.EMAIL_SMTP_PASSWORD)
    return client


def send_message(*, to: str, content: EmailContent) -> None:
    """Send a single message and close the connection.

    Raises EmailDeliveryError on any underlying SMTP/network failure;
    the Celery task wraps this and applies the retry policy.
    """
    msg = _build_message(to=to, content=content)
    try:
        with _open_smtp() as client:
            client.send_message(msg)
    except (
        smtplib.SMTPException,
        ConnectionError,
        TimeoutError,
        OSError,
    ) as exc:
        # Don't include the message body in the wrapped error — Celery
        # will log the exception, and verification codes / addresses
        # would otherwise leak into logs.
        raise EmailDeliveryError(
            f"failed to send to <redacted>: {type(exc).__name__}"
        ) from exc
