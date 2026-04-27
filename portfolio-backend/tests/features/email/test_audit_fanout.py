"""
Integration tests for the audit → email fan-out.

`audit.record_event` writes the auth_events row first (always), then
opportunistically calls `email.service.send_security_alert` if the
event_type is in `_SECURITY_ALERT_EVENTS`. The email side must:
  * never raise — the DB row is the source of truth, email is best-effort,
  * skip events that aren't in the alert set,
  * fire for the events the user explicitly listed (totp_disabled,
    sessions_cleared, login_lockout_triggered, cookie_signature_invalid)
    plus the rest of the curated set.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.features.auth import audit
from app.features.email import service as email_service


@pytest.fixture(autouse=True)
def _silence_db(monkeypatch):
    """The audit DB write opens an isolated AsyncSessionLocal — short
    that out so the tests can run without a live Postgres."""
    fake_session = AsyncMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()

    class _FakeFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return fake_session

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(audit, "AsyncSessionLocal", _FakeFactory())


@pytest.fixture
def alert_spy(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(email_service, "send_security_alert", spy)
    # audit imported the function name into its own namespace via
    # `from app.features.email import service as email_service`, so the
    # patch on the source module is what audit.record_event sees.
    return spy


@pytest.mark.parametrize(
    "event_type",
    [
        "cookie_signature_invalid",
        "login_lockout_triggered",
        "login_mfa_failed",
        "totp_disabled",
        "totp_disable_failed",
        "totp_confirm_failed",
        "sessions_cleared",
        "admin_recovery",
    ],
)
@pytest.mark.asyncio
async def test_security_events_fan_out_to_email(alert_spy, event_type):
    await audit.record_event(
        event_type=event_type,
        ip="203.0.113.7",
        user_agent="ua",
        reason="some-reason",
    )
    alert_spy.assert_called_once()
    kwargs = alert_spy.call_args.kwargs
    assert kwargs["event_type"] == event_type
    assert kwargs["ip"] == "203.0.113.7"
    assert kwargs["user_agent"] == "ua"
    assert kwargs["extra"] == "some-reason"


@pytest.mark.parametrize(
    "event_type",
    [
        "login_success",
        "login_failed",
        "login_mfa_challenge",
        "logout",
        "totp_enroll_started",
        "totp_enabled",
    ],
)
@pytest.mark.asyncio
async def test_routine_events_do_not_fan_out(alert_spy, event_type):
    """Routine login/logout/MFA events must not flood the admin inbox.
    They still hit auth_events for forensic search."""
    await audit.record_event(event_type=event_type, ip="1.2.3.4")
    alert_spy.assert_not_called()


@pytest.mark.asyncio
async def test_email_failure_does_not_break_audit(monkeypatch):
    """If the email layer raises, the audit call must still return None
    — the DB row already landed and an email outage cannot become an
    auth outage."""
    boom = MagicMock(side_effect=RuntimeError("email path on fire"))
    monkeypatch.setattr(email_service, "send_security_alert", boom)
    # Should not raise:
    await audit.record_event(event_type="cookie_signature_invalid", ip="1.2.3.4")
    boom.assert_called_once()
