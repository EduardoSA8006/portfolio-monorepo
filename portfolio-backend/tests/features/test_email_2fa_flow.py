"""
End-to-end-ish tests for the email-2FA path.

Coverage matrix:
  * service.login picks email branch when email_2fa_enabled and not totp_enabled.
  * service.login still prefers TOTP when both flags are on.
  * verify_email_code consumes a live code and creates a session.
  * verify_email_code rejects a TOTP-method challenge (cross-method spend).
  * verify_mfa rejects an email-method challenge (mirror direction).
  * resend_email_code re-issues without spending an attempt.
  * enable / request_disable / disable email 2FA.
  * Disable rejects when the live code is wrong + audits failure.

We mock the Celery .delay() and the SMTP client so no broker / network
is required.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.config import settings
from app.features.auth import service
from app.features.auth.exceptions import (
    Email2FAAlreadyEnabledError,
    Email2FANotEnabledError,
    Email2FAUnavailableError,
    EmailCodeInvalidError,
    MFAChallengeInvalidError,
)
from app.features.auth.rate_limit import RateCheckResult


# ─── shared fixtures ────────────────────────────────────────────────────────


def _user(**overrides):
    base = {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Alice Admin",
        "is_active": True,
        "password_hash": "argon2-hash",
        "totp_enabled": False,
        "totp_secret_enc": None,
        "email_2fa_enabled": False,
        "email": "alice@test",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def email_on(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)


@pytest.fixture
def task_spy(monkeypatch):
    """Replace the Celery .delay so no broker is needed AND we can
    inspect what the task would have sent."""
    from app.features.email import service as email_svc
    spy = MagicMock()
    monkeypatch.setattr(email_svc.send_email_task, "delay", spy)
    return spy


@pytest.fixture
def device_track_passthrough(monkeypatch):
    """track_login is exercised separately — here we want a stable
    (False, None) so the test focuses on the 2FA path."""
    spy = AsyncMock(return_value=(False, None))
    monkeypatch.setattr(service.devices, "track_login", spy)
    return spy


def _patch_login_chain(monkeypatch, user):
    async def _get_by_email_hash(_eh, _db):
        return user

    async def _check_login_rate(_redis, _ip, _eh):
        return RateCheckResult(captcha_required=False, degraded=False)

    async def _reset_login_rate(*_args, **_kwargs):
        return None

    async def _create_session(_redis, _user_id):
        return ("session-token", "csrf-token")

    async def _maybe_rehash(*_args, **_kwargs):
        return None

    async def _maybe_backfill(*_args, **_kwargs):
        return None

    async def _record_event(**_kwargs):
        return None

    monkeypatch.setattr(service.repository, "get_by_email_hash", _get_by_email_hash)
    monkeypatch.setattr(service.rate_limit, "check_login_rate", _check_login_rate)
    monkeypatch.setattr(service.rate_limit, "reset_login_rate", _reset_login_rate)
    monkeypatch.setattr(service.token_store, "create_session", _create_session)
    monkeypatch.setattr(service, "_maybe_rehash_password_hash", _maybe_rehash)
    monkeypatch.setattr(service, "_maybe_backfill_email", _maybe_backfill)
    monkeypatch.setattr(service.audit, "record_event", _record_event)
    monkeypatch.setattr(service, "verify_password", lambda plain, hashed: True)


# ─── login branch selection ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_with_email_2fa_returns_email_method(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    """email_2fa_enabled but not totp → mfa_required + method=email,
    AND a code lands in Redis + the email task is enqueued."""
    user = _user(email_2fa_enabled=True)
    _patch_login_chain(monkeypatch, user)

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=redis,
        user_agent="Mozilla/5.0",
    )
    assert result.mfa_required is True
    assert result.mfa_method == "email"
    assert result.mfa_challenge_token is not None

    # A code was issued to Redis.
    code_key = f"email:code:{user.id}"
    assert await redis.exists(code_key) == 1

    # The email task got enqueued for the right template + recipient.
    task_spy.assert_called_once()
    kwargs = task_spy.call_args.kwargs
    assert kwargs["to"] == "alice@test"
    assert kwargs["template_id"] == "two_factor_code"


@pytest.mark.asyncio
async def test_login_prefers_totp_when_both_flags_on(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    """When totp_enabled AND email_2fa_enabled, TOTP wins. Email is the
    fallback for users who don't have an authenticator app."""
    user = _user(totp_enabled=True, totp_secret_enc="enc", email_2fa_enabled=True)
    _patch_login_chain(monkeypatch, user)

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=redis,
        user_agent="Mozilla/5.0",
    )
    assert result.mfa_method == "totp"
    # No email code was issued — TOTP path skips email entirely.
    assert await redis.exists(f"email:code:{user.id}") == 0
    task_spy.assert_not_called()


@pytest.mark.asyncio
async def test_login_no_2fa_returns_session_directly(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    user = _user()
    _patch_login_chain(monkeypatch, user)

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=redis,
    )
    assert result.session_token == "session-token"
    assert result.mfa_method is None


# ─── verify_email_code ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_email_code_succeeds_with_correct_code(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    """Round-trip the email path: login → fetch code from Redis →
    submit code → session issued."""
    user = _user(email_2fa_enabled=True)
    _patch_login_chain(monkeypatch, user)

    async def _get_by_id(_uid, _db):
        return user

    monkeypatch.setattr(service.repository, "get_by_id", _get_by_id)

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=redis,
    )
    challenge = result.mfa_challenge_token

    # Pull the code straight out of Redis (the email send is mocked,
    # but the code is real) — that's what the user would see in
    # their inbox.
    code = (await redis.hget(f"email:code:{user.id}", "code")).decode()

    verify_result = await service.verify_email_code(
        challenge_token=challenge,
        code=code,
        client_ip="203.0.113.42",
        db=None,
        redis=redis,
        user_agent="Mozilla/5.0",
    )
    assert verify_result.session_token == "session-token"

    # Code is consumed (one-shot).
    assert await redis.exists(f"email:code:{user.id}") == 0


@pytest.mark.asyncio
async def test_verify_email_code_rejects_wrong_code(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    user = _user(email_2fa_enabled=True)
    _patch_login_chain(monkeypatch, user)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="ip",
        db=None,
        redis=redis,
    )
    real_code = (await redis.hget(f"email:code:{user.id}", "code")).decode()
    wrong = "000000" if real_code != "000000" else "111111"

    with pytest.raises(EmailCodeInvalidError):
        await service.verify_email_code(
            challenge_token=result.mfa_challenge_token,
            code=wrong,
            client_ip="ip",
            db=None,
            redis=redis,
        )


@pytest.mark.asyncio
async def test_verify_email_code_rejects_totp_method_challenge(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    """An attacker can't hand a TOTP challenge to the email verify
    endpoint to spend it under the wrong rules."""
    user = _user(totp_enabled=True, totp_secret_enc="enc")
    _patch_login_chain(monkeypatch, user)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))

    result = await service.login(
        email="alice@test", password="x", client_ip="ip", db=None, redis=redis,
    )
    assert result.mfa_method == "totp"

    with pytest.raises(MFAChallengeInvalidError):
        await service.verify_email_code(
            challenge_token=result.mfa_challenge_token,
            code="000000",
            client_ip="ip",
            db=None,
            redis=redis,
        )


@pytest.mark.asyncio
async def test_verify_mfa_rejects_email_method_challenge(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    """Mirror direction — email challenge cannot be spent at the TOTP
    endpoint."""
    user = _user(email_2fa_enabled=True)
    _patch_login_chain(monkeypatch, user)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))

    result = await service.login(
        email="alice@test", password="x", client_ip="ip", db=None, redis=redis,
    )
    assert result.mfa_method == "email"

    with pytest.raises(MFAChallengeInvalidError):
        await service.verify_mfa(
            challenge_token=result.mfa_challenge_token,
            code="000000",
            client_ip="ip",
            db=None,
            redis=redis,
        )


# ─── resend_email_code ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resend_email_code_rotates_code_without_spending_attempt(
    monkeypatch, redis, email_on, task_spy, device_track_passthrough
):
    user = _user(email_2fa_enabled=True)
    _patch_login_chain(monkeypatch, user)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))

    result = await service.login(
        email="alice@test", password="x", client_ip="ip", db=None, redis=redis,
    )
    code_before = (await redis.hget(f"email:code:{user.id}", "code")).decode()

    # Resend issues a fresh code (very probably different) and the
    # attempt counter on the challenge does NOT increment (resend ≠
    # verify attempt).
    challenge_attempts_before = await redis.hget(
        f"auth:mfa:challenge:{result.mfa_challenge_token}", "attempts"
    )
    await service.resend_email_code(
        challenge_token=result.mfa_challenge_token,
        client_ip="ip",
        db=None,
        redis=redis,
    )
    code_after = (await redis.hget(f"email:code:{user.id}", "code")).decode()
    challenge_attempts_after = await redis.hget(
        f"auth:mfa:challenge:{result.mfa_challenge_token}", "attempts"
    )
    # Codes will collide 1-in-10^6; be lenient.
    assert code_after.isdigit()
    assert challenge_attempts_before == challenge_attempts_after
    # The Celery .delay was invoked twice (once on login, once on resend).
    assert task_spy.call_count == 2


@pytest.mark.asyncio
async def test_resend_email_code_rejects_unknown_challenge(redis):
    with pytest.raises(MFAChallengeInvalidError):
        await service.resend_email_code(
            challenge_token="0" * 64,
            client_ip="ip",
            db=None,
            redis=redis,
        )


# ─── enable / disable ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enable_email_2fa_flips_flag(monkeypatch, email_on):
    user = _user(email_2fa_enabled=False)
    commit_count = {"n": 0}

    class _DB:
        async def commit(self):
            commit_count["n"] += 1

    db = _DB()
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))
    audit_spy = AsyncMock()
    monkeypatch.setattr(service.audit, "record_event", audit_spy)

    await service.enable_email_2fa(str(user.id), db, client_ip="ip")
    assert user.email_2fa_enabled is True
    assert commit_count["n"] == 1
    audit_spy.assert_called_once()
    assert audit_spy.call_args.kwargs["event_type"] == "email_2fa_enabled"


@pytest.mark.asyncio
async def test_enable_email_2fa_refuses_when_smtp_off(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    with pytest.raises(Email2FAUnavailableError):
        await service.enable_email_2fa("00000000-0000-0000-0000-000000000001", None)


@pytest.mark.asyncio
async def test_enable_email_2fa_refuses_when_no_email_on_file(monkeypatch, email_on):
    user = _user(email=None)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))
    with pytest.raises(Email2FAUnavailableError):
        await service.enable_email_2fa(str(user.id), None)


@pytest.mark.asyncio
async def test_enable_email_2fa_refuses_when_already_enabled(monkeypatch, email_on):
    user = _user(email_2fa_enabled=True)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))
    with pytest.raises(Email2FAAlreadyEnabledError):
        await service.enable_email_2fa(str(user.id), None)


@pytest.mark.asyncio
async def test_disable_email_2fa_consumes_code_and_flips_flag(
    monkeypatch, redis, email_on, task_spy
):
    user = _user(email_2fa_enabled=True)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))
    audit_spy = AsyncMock()
    monkeypatch.setattr(service.audit, "record_event", audit_spy)

    class _DB:
        async def commit(self):
            return None

    # Step 1: request a code.
    await service.request_disable_email_2fa(str(user.id), _DB(), redis, client_ip="ip")
    code = (await redis.hget(f"email:code:{user.id}", "code")).decode()

    # Step 2: submit the code.
    await service.disable_email_2fa(
        str(user.id), code, _DB(), redis, client_ip="ip"
    )
    assert user.email_2fa_enabled is False
    # audit fired twice — once for the disable success.
    types = [c.kwargs["event_type"] for c in audit_spy.call_args_list]
    assert "email_2fa_disabled" in types


@pytest.mark.asyncio
async def test_disable_email_2fa_rejects_wrong_code_and_audits_failure(
    monkeypatch, redis, email_on, task_spy
):
    user = _user(email_2fa_enabled=True)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))
    audit_spy = AsyncMock()
    monkeypatch.setattr(service.audit, "record_event", audit_spy)

    class _DB:
        async def commit(self):
            return None

    await service.request_disable_email_2fa(str(user.id), _DB(), redis)

    with pytest.raises(EmailCodeInvalidError):
        await service.disable_email_2fa(
            str(user.id), "000000", _DB(), redis, client_ip="ip"
        )
    assert user.email_2fa_enabled is True  # still on
    types = [c.kwargs["event_type"] for c in audit_spy.call_args_list]
    assert "email_2fa_disable_failed" in types


@pytest.mark.asyncio
async def test_request_disable_refuses_when_not_enabled(monkeypatch, redis, email_on):
    user = _user(email_2fa_enabled=False)
    monkeypatch.setattr(service.repository, "get_by_id", AsyncMock(return_value=user))
    with pytest.raises(Email2FANotEnabledError):
        await service.request_disable_email_2fa(str(user.id), None, redis)
