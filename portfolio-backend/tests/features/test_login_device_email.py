"""
Integration tests for the new-device-email gate.

The promise: on the password-only login path, send_login_notification
fires iff the device is new. On the TOTP path, the email fires only
after verify_mfa succeeds — and only if the challenge metadata says
the device was new.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.features.auth import service
from app.features.auth.rate_limit import RateCheckResult


class _FakeUser:
    def __init__(
        self,
        *,
        totp_enabled: bool = False,
        email_2fa_enabled: bool = False,
        email: str | None = "alice@test",
    ):
        self.id = "00000000-0000-0000-0000-000000000001"
        self.name = "Alice Admin"
        self.is_active = True
        self.password_hash = "argon2-hash"
        self.totp_enabled = totp_enabled
        self.totp_secret_enc = "encrypted-secret" if totp_enabled else None
        self.email_2fa_enabled = email_2fa_enabled
        self.email = email


def _patch_login_happy_path(monkeypatch, *, totp_enabled: bool = False):
    """Wire up every dependency the login path touches except the parts
    the test actually wants to assert on."""
    user = _FakeUser(totp_enabled=totp_enabled)

    async def _get_by_email_hash(eh, db):
        return user

    async def _check_login_rate(redis, ip, eh):
        return RateCheckResult(captcha_required=False, degraded=False)

    async def _reset_login_rate(redis, ip, eh):
        return None

    async def _create_session(redis, user_id):
        return ("session-token", "csrf-token")

    async def _create_challenge(redis, user_id, **kwargs):
        # Stash kwargs on the function so the test can assert on them.
        _create_challenge.last_kwargs = kwargs
        return "challenge-token"

    async def _maybe_rehash(*args, **kwargs):
        return None

    async def _record_event(**kwargs):
        return None

    monkeypatch.setattr(service.repository, "get_by_email_hash", _get_by_email_hash)
    monkeypatch.setattr(service.rate_limit, "check_login_rate", _check_login_rate)
    monkeypatch.setattr(service.rate_limit, "reset_login_rate", _reset_login_rate)
    monkeypatch.setattr(service.token_store, "create_session", _create_session)
    monkeypatch.setattr(service.mfa_store, "create_challenge", _create_challenge)
    monkeypatch.setattr(service, "_maybe_rehash_password_hash", _maybe_rehash)
    monkeypatch.setattr(service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(service.audit, "record_event", _record_event)

    return user, _create_challenge


@pytest.fixture
def email_spy(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(service.email_service, "send_login_notification", spy)
    return spy


@pytest.fixture
def device_track_spy(monkeypatch):
    """Replace track_login with a controllable mock so the test can
    decide what 'is_new_device' means without standing up a Redis."""
    spy = AsyncMock()
    monkeypatch.setattr(service.devices, "track_login", spy)
    return spy


@pytest.mark.asyncio
async def test_login_no_totp_new_device_fires_email(
    monkeypatch, email_spy, device_track_spy
):
    """Password-only login + new device → one login_notification email."""
    _patch_login_happy_path(monkeypatch, totp_enabled=False)
    device_track_spy.return_value = (True, "fresh-device-token")

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=object(),
        user_agent="Mozilla/5.0",
    )
    assert result.session_token == "session-token"
    assert result.new_device_token == "fresh-device-token"

    email_spy.assert_called_once()
    kwargs = email_spy.call_args.kwargs
    assert kwargs["name"] == "Alice Admin"
    assert kwargs["to"] == "alice@test"
    assert kwargs["ip"] == "203.0.113.42"
    assert kwargs["user_agent"] == "Mozilla/5.0"


@pytest.mark.asyncio
async def test_login_no_totp_known_device_no_email(
    monkeypatch, email_spy, device_track_spy
):
    """Password-only login + known device → silent, no email at all."""
    _patch_login_happy_path(monkeypatch, totp_enabled=False)
    device_track_spy.return_value = (False, None)

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=object(),
        user_agent="Mozilla/5.0",
    )
    assert result.session_token == "session-token"
    assert result.new_device_token is None
    email_spy.assert_not_called()


@pytest.mark.asyncio
async def test_login_totp_path_does_not_fire_email_yet(
    monkeypatch, email_spy, device_track_spy
):
    """TOTP path: the email must NOT fire on /login — only after
    verify_mfa succeeds (otherwise an attacker who has the password but
    not the TOTP code would still trigger the alert, training the user
    to ignore it)."""
    user, create_challenge = _patch_login_happy_path(monkeypatch, totp_enabled=True)
    device_track_spy.return_value = (True, "fresh-device-token")

    result = await service.login(
        email="alice@test",
        password="x",
        client_ip="203.0.113.42",
        db=None,
        redis=object(),
        user_agent="Mozilla/5.0",
    )
    assert result.mfa_required is True
    assert result.mfa_challenge_token == "challenge-token"
    assert result.new_device_token == "fresh-device-token"
    email_spy.assert_not_called()

    # The challenge must carry every field verify_mfa needs to fire the
    # email later: email, ip, user-agent, is_new_device flag.
    kwargs = create_challenge.last_kwargs
    assert kwargs["email"] == "alice@test"
    assert kwargs["client_ip"] == "203.0.113.42"
    assert kwargs["user_agent"] == "Mozilla/5.0"
    assert kwargs["is_new_device"] is True


@pytest.mark.asyncio
async def test_verify_mfa_fires_email_when_challenge_says_new_device(
    monkeypatch, email_spy
):
    """Round-trip the TOTP path: verify_mfa reads the challenge's
    is_new_device flag and fires the email once on success."""
    from app.features.auth import service as svc

    async def _consume_attempt(redis, token):
        return "00000000-0000-0000-0000-000000000001"

    async def _get_by_id(uid, db):
        return _FakeUser(totp_enabled=True)

    async def _create_session(redis, user_id):
        return ("session-token", "csrf-token")

    async def _claim_code(redis, user_id, code):
        return True

    async def _revoke_challenge(redis, token):
        return None

    async def _get_challenge_metadata(redis, token):
        return {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "email": "alice@test",
            "client_ip": "203.0.113.42",
            "user_agent": "Mozilla/5.0",
            "is_new_device": "1",
        }

    async def _record_event(**kwargs):
        return None

    monkeypatch.setattr(svc.mfa_store, "consume_attempt", _consume_attempt)
    monkeypatch.setattr(svc.repository, "get_by_id", _get_by_id)
    monkeypatch.setattr(svc.token_store, "create_session", _create_session)
    monkeypatch.setattr(svc.mfa_store, "claim_code", _claim_code)
    monkeypatch.setattr(svc.mfa_store, "revoke_challenge", _revoke_challenge)
    monkeypatch.setattr(svc.mfa_store, "get_challenge_metadata", _get_challenge_metadata)
    monkeypatch.setattr(svc.audit, "record_event", _record_event)
    monkeypatch.setattr(svc, "decrypt_totp_secret", lambda value: "secret")
    monkeypatch.setattr(svc, "verify_totp_code", lambda secret, code: True)

    result = await svc.verify_mfa(
        challenge_token="challenge-token",
        code="123456",
        client_ip="now-ip",  # different from challenge — original wins
        db=None,
        redis=object(),
        user_agent="now-ua",
    )
    assert result.session_token == "session-token"
    email_spy.assert_called_once()
    kwargs = email_spy.call_args.kwargs
    assert kwargs["to"] == "alice@test"
    # Original IP (from challenge) is what the email reports — that's
    # where the new-device suspicion arose. The current ip/ua fall back
    # to the request only if the challenge omitted them.
    assert kwargs["ip"] == "203.0.113.42"
    assert kwargs["user_agent"] == "Mozilla/5.0"


@pytest.mark.asyncio
async def test_verify_mfa_no_email_when_challenge_says_known_device(
    monkeypatch, email_spy
):
    """Known device on the TOTP path → verify_mfa stays silent."""
    from app.features.auth import service as svc

    async def _consume_attempt(redis, token):
        return "00000000-0000-0000-0000-000000000001"

    async def _get_by_id(uid, db):
        return _FakeUser(totp_enabled=True)

    async def _create_session(redis, user_id):
        return ("session-token", "csrf-token")

    async def _claim_code(redis, user_id, code):
        return True

    async def _revoke_challenge(redis, token):
        return None

    async def _get_challenge_metadata(redis, token):
        return {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "is_new_device": "0",
        }

    async def _record_event(**kwargs):
        return None

    monkeypatch.setattr(svc.mfa_store, "consume_attempt", _consume_attempt)
    monkeypatch.setattr(svc.repository, "get_by_id", _get_by_id)
    monkeypatch.setattr(svc.token_store, "create_session", _create_session)
    monkeypatch.setattr(svc.mfa_store, "claim_code", _claim_code)
    monkeypatch.setattr(svc.mfa_store, "revoke_challenge", _revoke_challenge)
    monkeypatch.setattr(svc.mfa_store, "get_challenge_metadata", _get_challenge_metadata)
    monkeypatch.setattr(svc.audit, "record_event", _record_event)
    monkeypatch.setattr(svc, "decrypt_totp_secret", lambda value: "secret")
    monkeypatch.setattr(svc, "verify_totp_code", lambda secret, code: True)

    await svc.verify_mfa(
        challenge_token="challenge-token",
        code="123456",
        client_ip="ip",
        db=None,
        redis=object(),
        user_agent="ua",
    )
    email_spy.assert_not_called()
