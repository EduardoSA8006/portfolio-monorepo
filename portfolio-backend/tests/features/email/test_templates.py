"""
Template tests — pure rendering, no I/O.

We assert that each template:
  * produces a non-empty subject and body,
  * inlines every required context variable,
  * surfaces obvious markers (the 6-digit code, the IP, etc.) so a
    regression that swaps two fields would fail loudly.
"""
from datetime import UTC, datetime

import pytest

from app.features.email import templates


def test_two_factor_code_carries_code_and_ttl():
    out = templates.two_factor_code(name="Alice", code="123456", ttl_minutes=5)
    assert "Alice" in out.text_body
    assert "123456" in out.text_body
    assert "5 minute" in out.text_body
    assert out.subject.startswith("[Portfolio]")
    assert "123456" in out.subject  # the code is in the subject too — handy for inbox preview
    # HTML body now ships alongside text — multipart/alternative path.
    assert out.html_body is not None
    assert "123456" in out.html_body
    assert "Alice" in out.html_body


def test_two_factor_code_singular_minute():
    """Edge: 1 min should not render '1 minutes'."""
    out = templates.two_factor_code(name="Alice", code="000001", ttl_minutes=1)
    assert "1 minute." in out.text_body
    assert "1 minutes" not in out.text_body


def test_login_notification_inlines_ip_and_when():
    when = datetime(2026, 4, 27, 12, 30, 0, tzinfo=UTC)
    out = templates.login_notification(
        name="Bob",
        ip="203.0.113.10",
        user_agent="curl/8.0",
        when=when,
    )
    assert "Bob" in out.text_body
    assert "203.0.113.10" in out.text_body
    assert "curl/8.0" in out.text_body
    assert "2026-04-27 12:30:00 UTC" in out.text_body


def test_login_notification_handles_missing_user_agent():
    out = templates.login_notification(
        name="Bob", ip="1.2.3.4", user_agent=None
    )
    assert "(no user-agent header)" in out.text_body


def test_security_alert_renders_per_event_template():
    """The per-event template carries the event-specific narrative
    (the cookie_signature_invalid template mentions HMAC + SECRET_KEY)
    AND the structured fields (IP, agent, reason)."""
    when = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
    out = templates.security_alert(
        event_type="cookie_signature_invalid",
        ip="203.0.113.99",
        user_agent="evil-bot/1.0",
        when=when,
        extra="forged signature",
    )
    assert "[SECURITY]" in out.subject
    assert "cookie_signature_invalid" in out.subject
    body = out.text_body
    assert "203.0.113.99" in body
    assert "evil-bot/1.0" in body
    assert "forged signature" in body
    # Per-event template cue — proves we picked the dedicated file,
    # not the generic fallback.
    assert "HMAC" in body or "SECRET_KEY" in body


def test_security_alert_with_unknown_ip_uses_placeholder():
    out = templates.security_alert(
        event_type="login_lockout_triggered", ip=None, user_agent=None
    )
    body = out.text_body
    assert "(unknown)" in body
    assert "(none)" in body


def test_security_alert_unknown_event_falls_back_to_generic():
    """An event_type with no dedicated template still renders via the
    `_generic` fallback so audit fan-out never errors out."""
    out = templates.security_event(
        event_type="brand_new_event_type",
        ip="1.2.3.4",
        user_agent="ua",
        extra="something",
    )
    body = out.text_body
    assert "brand_new_event_type" in body
    assert "1.2.3.4" in body
    # Generic template carries this giveaway phrase (line-broken in the
    # rendered text; we look at the prefix that survives the wrap).
    assert "no dedicated" in body


def test_security_event_html_escapes_user_agent():
    """A malicious user-agent must never render as live markup in the
    HTML alert. Jinja's autoescape on the html env handles this."""
    out = templates.security_event(
        event_type="cookie_signature_invalid",
        ip="1.2.3.4",
        user_agent="<script>alert(1)</script>",
    )
    assert "<script>alert(1)</script>" not in out.html_body
    assert "&lt;script&gt;" in out.html_body


def test_admin_recovery_notice_inline():
    out = templates.admin_recovery_notice(
        name="Eve", ip="10.0.0.1", when=datetime(2026, 4, 27, tzinfo=UTC)
    )
    assert "Eve" in out.text_body
    assert "10.0.0.1" in out.text_body
    assert "2026-04-27" in out.text_body


def test_render_dispatches_by_id():
    """The Celery task uses templates.render(id, context). Make sure each
    registered id resolves to the function shape it advertises."""
    out = templates.render(
        "two_factor_code",
        {"name": "Alice", "code": "999999", "ttl_minutes": 5},
    )
    assert "999999" in out.text_body


def test_render_unknown_template_raises_keyerror():
    with pytest.raises(KeyError, match="unknown email template"):
        templates.render("not_a_real_template", {})
