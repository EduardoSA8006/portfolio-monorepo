"""
Service-layer tests.

The service layer:
  * short-circuits to a no-op when EMAIL_ENABLED=False,
  * gates security alerts independently behind
    EMAIL_SECURITY_ALERTS_ENABLED + EMAIL_ADMIN_RECIPIENT,
  * issues a 2FA code via code_store BEFORE enqueueing the email
    so a Celery backlog doesn't open a window where the code
    exists but the user can't learn it.

We mock `send_email_task.delay` so no broker is required.
"""
from unittest.mock import MagicMock

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.config import settings
from app.features.email import service


@pytest.fixture
def task_spy(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(service.send_email_task, "delay", spy)
    return spy


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def email_on(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_SECURITY_ALERTS_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_ADMIN_RECIPIENT", "admin@test")


# ─── disabled-flag short-circuit ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_two_factor_code_noop_when_disabled(monkeypatch, redis, task_spy):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    await service.send_two_factor_code(
        redis=redis, user_id="u-1", name="Alice", to="a@test"
    )
    task_spy.assert_not_called()
    # Critically: NO code is issued either — otherwise a flag flip would
    # leave dangling codes nobody can use.
    assert await redis.exists("email:code:u-1") == 0


def test_send_login_notification_noop_when_disabled(monkeypatch, task_spy):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    service.send_login_notification(
        name="Alice", to="a@test", ip="1.2.3.4", user_agent=None
    )
    task_spy.assert_not_called()


def test_send_security_alert_noop_when_email_disabled(monkeypatch, task_spy):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    monkeypatch.setattr(settings, "EMAIL_SECURITY_ALERTS_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_ADMIN_RECIPIENT", "admin@test")
    service.send_security_alert(event_type="x")
    task_spy.assert_not_called()


def test_send_security_alert_noop_when_alerts_disabled(monkeypatch, task_spy):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_SECURITY_ALERTS_ENABLED", False)
    monkeypatch.setattr(settings, "EMAIL_ADMIN_RECIPIENT", "admin@test")
    service.send_security_alert(event_type="x")
    task_spy.assert_not_called()


def test_send_security_alert_noop_when_no_recipient(monkeypatch, task_spy):
    """Even with both flags on, no admin inbox = no alert."""
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_SECURITY_ALERTS_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_ADMIN_RECIPIENT", "")
    service.send_security_alert(event_type="x")
    task_spy.assert_not_called()


# ─── enabled path ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_two_factor_code_issues_code_and_enqueues(email_on, redis, task_spy):
    await service.send_two_factor_code(
        redis=redis, user_id="u-1", name="Alice", to="alice@test"
    )
    # Code persisted before the task is enqueued.
    assert await redis.exists("email:code:u-1") == 1

    task_spy.assert_called_once()
    kwargs = task_spy.call_args.kwargs
    assert kwargs["to"] == "alice@test"
    assert kwargs["template_id"] == "two_factor_code"
    ctx = kwargs["context"]
    assert ctx["name"] == "Alice"
    # The code in the email payload must equal the code in Redis — that
    # equality is the entire point of the flow.
    stored_code = (await redis.hget("email:code:u-1", "code")).decode()
    assert ctx["code"] == stored_code
    assert ctx["ttl_minutes"] >= 1


def test_send_login_notification_enqueues_with_context(email_on, task_spy):
    service.send_login_notification(
        name="Bob", to="bob@test", ip="203.0.113.1", user_agent="Mozilla/5"
    )
    task_spy.assert_called_once()
    ctx = task_spy.call_args.kwargs["context"]
    assert ctx["ip"] == "203.0.113.1"
    assert ctx["user_agent"] == "Mozilla/5"
    assert "when" in ctx


def test_send_security_alert_routes_to_admin_recipient(email_on, task_spy):
    service.send_security_alert(
        event_type="cookie_signature_invalid",
        ip="203.0.113.99",
        user_agent="evil",
        extra="some detail",
    )
    task_spy.assert_called_once()
    kwargs = task_spy.call_args.kwargs
    assert kwargs["to"] == "admin@test"
    # Per-event template id (replaces the old single "security_alert").
    assert kwargs["template_id"] == "security/cookie_signature_invalid"
    ctx = kwargs["context"]
    assert ctx["event_type"] == "cookie_signature_invalid"
    assert ctx["extra"] == "some detail"


def test_send_security_alert_falls_back_to_generic_for_unknown_event(
    email_on, task_spy
):
    """An event_type without a dedicated template still gets routed —
    just to the generic fallback. Otherwise audit fan-out for a
    newly-added event would silently drop the alert."""
    service.send_security_alert(event_type="brand_new_thing", ip="1.2.3.4")
    task_spy.assert_called_once()
    assert task_spy.call_args.kwargs["template_id"] == "security/_generic"


def test_send_admin_recovery_notice_enqueues(email_on, task_spy):
    service.send_admin_recovery_notice(
        name="Eve", to="eve@test", ip="10.0.0.1"
    )
    task_spy.assert_called_once()
    ctx = task_spy.call_args.kwargs["context"]
    assert ctx["name"] == "Eve"
    assert ctx["ip"] == "10.0.0.1"


def test_ttl_minutes_rounds_up(monkeypatch):
    """61 seconds must surface as 2 minutes — never undersell the
    window the user has."""
    monkeypatch.setattr(settings, "EMAIL_2FA_CODE_TTL_SECONDS", 61)
    assert service._ttl_minutes() == 2
    monkeypatch.setattr(settings, "EMAIL_2FA_CODE_TTL_SECONDS", 60)
    assert service._ttl_minutes() == 1
    monkeypatch.setattr(settings, "EMAIL_2FA_CODE_TTL_SECONDS", 1)
    assert service._ttl_minutes() == 1
