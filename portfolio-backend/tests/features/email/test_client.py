"""
SMTP client tests.

We don't reach a real server. Instead we monkeypatch
`smtplib.SMTP` / `smtplib.SMTP_SSL` to record what the client would
have done, so the test asserts on the call sequence + the message
shape rather than a mailbox.
"""
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.features.email import client
from app.features.email.exceptions import EmailDeliveryError
from app.features.email.templates import EmailContent


@pytest.fixture
def smtp_settings(monkeypatch):
    """Set the bare minimum SMTP config so _open_smtp doesn't trip on
    empty defaults from the test environment."""
    monkeypatch.setattr(settings, "EMAIL_SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "EMAIL_SMTP_PORT", 587)
    monkeypatch.setattr(settings, "EMAIL_SMTP_USERNAME", "user@test")
    monkeypatch.setattr(settings, "EMAIL_SMTP_PASSWORD", "pw")
    monkeypatch.setattr(settings, "EMAIL_FROM_ADDRESS", "noreply@test")
    monkeypatch.setattr(settings, "EMAIL_FROM_NAME", "Tester")
    monkeypatch.setattr(settings, "EMAIL_USE_TLS", True)
    monkeypatch.setattr(settings, "EMAIL_USE_SSL", False)
    monkeypatch.setattr(settings, "EMAIL_TIMEOUT_SECONDS", 5.0)


def _capture_smtp(monkeypatch, *, raise_on_send: Exception | None = None):
    """Replace smtplib.SMTP with a MagicMock that supports `with`."""
    instance = MagicMock()
    instance.__enter__.return_value = instance
    instance.__exit__.return_value = False
    if raise_on_send is not None:
        instance.send_message.side_effect = raise_on_send
    factory = MagicMock(return_value=instance)
    monkeypatch.setattr(client.smtplib, "SMTP", factory)
    return factory, instance


def test_send_message_uses_starttls_when_use_tls(smtp_settings, monkeypatch):
    factory, smtp = _capture_smtp(monkeypatch)
    content = EmailContent(subject="Hello", text_body="hi")
    client.send_message(to="recipient@test", content=content)

    factory.assert_called_once_with(host="smtp.test", port=587, timeout=5.0)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("user@test", "pw")
    smtp.send_message.assert_called_once()


def test_send_message_uses_implicit_tls_when_use_ssl(smtp_settings, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_USE_TLS", False)
    monkeypatch.setattr(settings, "EMAIL_USE_SSL", True)

    instance = MagicMock()
    instance.__enter__.return_value = instance
    instance.__exit__.return_value = False
    factory = MagicMock(return_value=instance)
    monkeypatch.setattr(client.smtplib, "SMTP_SSL", factory)

    content = EmailContent(subject="Hello", text_body="hi")
    client.send_message(to="recipient@test", content=content)

    factory.assert_called_once()
    # SSL path skips starttls.
    instance.starttls.assert_not_called()
    instance.login.assert_called_once_with("user@test", "pw")
    instance.send_message.assert_called_once()


def test_send_message_skips_login_when_no_username(smtp_settings, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_SMTP_USERNAME", "")
    factory, smtp = _capture_smtp(monkeypatch)
    client.send_message(
        to="recipient@test",
        content=EmailContent(subject="x", text_body="y"),
    )
    smtp.login.assert_not_called()


def test_send_message_wraps_smtp_failure(smtp_settings, monkeypatch):
    """A connection/SMTP error must surface as EmailDeliveryError so
    the Celery task's retry policy fires."""
    import smtplib
    _capture_smtp(monkeypatch, raise_on_send=smtplib.SMTPServerDisconnected("x"))
    with pytest.raises(EmailDeliveryError):
        client.send_message(
            to="recipient@test",
            content=EmailContent(subject="x", text_body="y"),
        )


def test_send_message_does_not_leak_recipient_in_error(smtp_settings, monkeypatch):
    """The wrapped exception must NOT carry the recipient or the body —
    those would leak into Celery's exception logs."""
    import smtplib
    _capture_smtp(
        monkeypatch, raise_on_send=smtplib.SMTPServerDisconnected("x"),
    )
    with pytest.raises(EmailDeliveryError) as exc:
        client.send_message(
            to="leaky@test",
            content=EmailContent(subject="leaky-subject", text_body="leaky-body"),
        )
    msg = str(exc.value)
    assert "leaky@test" not in msg
    assert "leaky-subject" not in msg
    assert "leaky-body" not in msg


def test_build_message_attaches_html_alternative(smtp_settings):
    msg = client._build_message(
        to="x@test",
        content=EmailContent(
            subject="multi", text_body="plain text", html_body="<p>html</p>"
        ),
    )
    # The EmailMessage payload list contains the plain part + the
    # multipart/alternative we added with set_content + add_alternative.
    assert msg.is_multipart()
    payload_types = sorted(part.get_content_type() for part in msg.walk() if part is not msg)
    assert "text/plain" in payload_types
    assert "text/html" in payload_types


def test_build_message_text_only_when_html_absent(smtp_settings):
    msg = client._build_message(
        to="x@test",
        content=EmailContent(subject="plain", text_body="just text"),
    )
    assert not msg.is_multipart()
    assert msg.get_content_type() == "text/plain"
