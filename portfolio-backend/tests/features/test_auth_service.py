import uuid
from types import SimpleNamespace

import pytest

from app.features.auth import service


class _FakeDB:
    def __init__(self, order: list[str], *, commit_side_effects: list[Exception | None] | None = None) -> None:
        self.order = order
        self.commits = 0
        self.rollbacks = 0
        self._commit_side_effects = list(commit_side_effects or [])

    async def commit(self) -> None:
        self.order.append("db.commit")
        self.commits += 1
        if self._commit_side_effects:
            outcome = self._commit_side_effects.pop(0)
            if outcome is not None:
                raise outcome

    async def rollback(self) -> None:
        self.order.append("db.rollback")
        self.rollbacks += 1


class _NoCommitDB:
    async def commit(self) -> None:
        pytest.fail("business session must not be committed by audit")

    async def rollback(self) -> None:
        pytest.fail("business session must not be rolled back by audit")


class _FakeAuditDB:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.added = []

    def add(self, event) -> None:
        self.order.append("audit.add")
        self.added.append(event)

    async def commit(self) -> None:
        self.order.append("audit.commit")


class _FakeAuditSessionFactory:
    def __init__(self, audit_db: _FakeAuditDB) -> None:
        self.audit_db = audit_db

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.audit_db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def totp_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        totp_enabled=True,
        totp_secret_enc="encrypted-secret",
    )


@pytest.fixture
def login_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        is_active=True,
        password_hash="stored-hash",
        totp_enabled=False,
    )


async def test_login_rehashes_password_hash_after_successful_verify(monkeypatch, login_user):
    order: list[str] = []
    db = _FakeDB(order)

    async def fake_get_by_email_hash(email_hash, db_arg):
        assert db_arg is db
        return login_user

    async def fake_check_login_rate(redis, client_ip, email_hash):
        order.append("rate.check")
        from app.features.auth.rate_limit import RateCheckResult
        return RateCheckResult(captcha_required=False, degraded=False)

    async def fake_reset_login_rate(redis, client_ip, email_hash):
        order.append("rate.reset")

    async def fake_create_session(redis, user_id):
        order.append("session.create")
        return "session-token", "csrf-token"

    async def fake_record_event(*args, **kwargs):
        order.append("audit")

    monkeypatch.setattr(service.repository, "get_by_email_hash", fake_get_by_email_hash)
    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check_login_rate)
    monkeypatch.setattr(service.rate_limit, "reset_login_rate", fake_reset_login_rate)
    monkeypatch.setattr(service.token_store, "create_session", fake_create_session)
    monkeypatch.setattr(service, "_record_event", fake_record_event)
    monkeypatch.setattr(service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(service, "password_needs_rehash", lambda hashed: True)
    monkeypatch.setattr(service, "hash_password", lambda plain: "upgraded-hash")

    result = await service.login("admin@example.com", "correct-password", "127.0.0.1", db, redis=object())

    assert result.session_token == "session-token"
    assert result.csrf_token == "csrf-token"
    assert login_user.password_hash == "upgraded-hash"
    assert db.commits == 1
    assert db.rollbacks == 0
    assert order == ["rate.check", "db.commit", "rate.reset", "session.create", "audit"]


async def test_login_continues_when_password_rehash_commit_fails(monkeypatch, login_user):
    order: list[str] = []
    db = _FakeDB(order, commit_side_effects=[RuntimeError("db unavailable")])

    async def fake_get_by_email_hash(email_hash, db_arg):
        return login_user

    async def fake_check_login_rate(redis, client_ip, email_hash):
        order.append("rate.check")
        from app.features.auth.rate_limit import RateCheckResult
        return RateCheckResult(captcha_required=False, degraded=False)

    async def fake_reset_login_rate(redis, client_ip, email_hash):
        order.append("rate.reset")

    async def fake_create_session(redis, user_id):
        order.append("session.create")
        return "session-token", "csrf-token"

    async def fake_record_event(*args, **kwargs):
        order.append("audit")

    monkeypatch.setattr(service.repository, "get_by_email_hash", fake_get_by_email_hash)
    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check_login_rate)
    monkeypatch.setattr(service.rate_limit, "reset_login_rate", fake_reset_login_rate)
    monkeypatch.setattr(service.token_store, "create_session", fake_create_session)
    monkeypatch.setattr(service, "_record_event", fake_record_event)
    monkeypatch.setattr(service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(service, "password_needs_rehash", lambda hashed: True)
    monkeypatch.setattr(service, "hash_password", lambda plain: "upgraded-hash")

    result = await service.login("admin@example.com", "correct-password", "127.0.0.1", db, redis=object())

    assert result.session_token == "session-token"
    assert result.csrf_token == "csrf-token"
    assert db.commits == 1
    assert db.rollbacks == 1
    assert order == ["rate.check", "db.commit", "db.rollback", "rate.reset", "session.create", "audit"]


async def test_login_audit_does_not_commit_business_session(monkeypatch, login_user):
    order: list[str] = []
    audit_db = _FakeAuditDB(order)

    async def fake_get_by_email_hash(email_hash, db_arg):
        assert isinstance(db_arg, _NoCommitDB)
        return login_user

    async def fake_check_login_rate(redis, client_ip, email_hash):
        order.append("rate.check")
        from app.features.auth.rate_limit import RateCheckResult
        return RateCheckResult(captcha_required=False, degraded=False)

    async def fake_reset_login_rate(redis, client_ip, email_hash):
        order.append("rate.reset")

    async def fake_create_session(redis, user_id):
        order.append("session.create")
        return "session-token", "csrf-token"

    async def fake_maybe_rehash_password_hash(*args, **kwargs):
        return None

    monkeypatch.setattr(service.repository, "get_by_email_hash", fake_get_by_email_hash)
    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check_login_rate)
    monkeypatch.setattr(service.rate_limit, "reset_login_rate", fake_reset_login_rate)
    monkeypatch.setattr(service.token_store, "create_session", fake_create_session)
    monkeypatch.setattr(service, "_maybe_rehash_password_hash", fake_maybe_rehash_password_hash)
    monkeypatch.setattr(service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(service, "AsyncSessionLocal", _FakeAuditSessionFactory(audit_db))

    result = await service.login(
        "admin@example.com",
        "correct-password",
        "127.0.0.1",
        _NoCommitDB(),
        redis=object(),
    )

    assert result.session_token == "session-token"
    assert result.csrf_token == "csrf-token"
    assert len(audit_db.added) == 1
    assert audit_db.added[0].event_type == "login_success"
    assert order == ["rate.check", "rate.reset", "session.create", "audit.add", "audit.commit"]


async def test_disable_totp_revokes_sessions_before_db_downgrade(monkeypatch, totp_user):
    order: list[str] = []
    db = _FakeDB(order)

    async def fake_get_by_id(user_id, db_arg):
        assert user_id == totp_user.id
        assert db_arg is db
        return totp_user

    async def fake_clear_user_sessions(redis, user_id):
        assert user_id == str(totp_user.id)
        assert totp_user.totp_enabled is True
        assert totp_user.totp_secret_enc == "encrypted-secret"
        order.append("redis.clear_sessions")
        return 2

    async def fake_record_event(*args, **kwargs):
        order.append("audit")

    monkeypatch.setattr(service.repository, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(service, "decrypt_totp_secret", lambda value: "secret")
    monkeypatch.setattr(service, "verify_totp_code", lambda secret, code: True)
    monkeypatch.setattr(service.token_store, "clear_user_sessions", fake_clear_user_sessions)
    monkeypatch.setattr(service, "_record_event", fake_record_event)

    await service.disable_totp(str(totp_user.id), "123456", db, redis=object())

    assert order == ["redis.clear_sessions", "db.commit", "audit"]
    assert db.commits == 1
    assert totp_user.totp_enabled is False
    assert totp_user.totp_secret_enc is None


async def test_disable_totp_keeps_mfa_enabled_when_session_revocation_fails(
    monkeypatch,
    totp_user,
):
    order: list[str] = []
    db = _FakeDB(order)

    async def fake_get_by_id(user_id, db_arg):
        return totp_user

    async def fake_clear_user_sessions(redis, user_id):
        order.append("redis.clear_sessions")
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(service.repository, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(service, "decrypt_totp_secret", lambda value: "secret")
    monkeypatch.setattr(service, "verify_totp_code", lambda secret, code: True)
    monkeypatch.setattr(service.token_store, "clear_user_sessions", fake_clear_user_sessions)

    with pytest.raises(RuntimeError, match="redis unavailable"):
        await service.disable_totp(str(totp_user.id), "123456", db, redis=object())

    assert order == ["redis.clear_sessions"]
    assert db.commits == 0
    assert totp_user.totp_enabled is True
    assert totp_user.totp_secret_enc == "encrypted-secret"


@pytest.mark.asyncio
async def test_login_raises_captcha_required_when_required_and_no_token(monkeypatch):
    from app.features.auth import service
    from app.features.auth.exceptions import CaptchaRequiredError
    from app.features.auth.rate_limit import RateCheckResult

    async def fake_check(redis, ip, eh):
        return RateCheckResult(captcha_required=True, degraded=False)

    verify_called = False
    async def fake_verify(token, ip, redis):
        nonlocal verify_called
        verify_called = True
        from app.features.auth.captcha import VerifyResult
        return VerifyResult(ok=False, provider_available=True, reason="missing-token")

    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check)
    monkeypatch.setattr(service.captcha, "verify", fake_verify)

    with pytest.raises(CaptchaRequiredError):
        await service.login(
            email="a@b.c",
            password="whatever1",
            client_ip="1.1.1.1",
            db=None,
            redis=None,
            captcha_token=None,
        )
    assert verify_called is True


@pytest.mark.asyncio
async def test_login_skips_captcha_when_degraded(monkeypatch):
    from app.features.auth import service
    from app.features.auth.exceptions import InvalidCredentialsError
    from app.features.auth.rate_limit import RateCheckResult

    async def fake_check(redis, ip, eh):
        return RateCheckResult(captcha_required=True, degraded=True)

    verify_called = False
    async def fake_verify(token, ip, redis):
        nonlocal verify_called
        verify_called = True
        from app.features.auth.captcha import VerifyResult
        return VerifyResult(ok=True, provider_available=True)

    async def fake_get_by_email_hash(eh, db):
        return None

    async def fake_register(redis, ip, eh):
        pass

    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check)
    monkeypatch.setattr(service.rate_limit, "register_login_failure", fake_register)
    monkeypatch.setattr(service.captcha, "verify", fake_verify)
    monkeypatch.setattr(service.repository, "get_by_email_hash", fake_get_by_email_hash)

    with pytest.raises(InvalidCredentialsError):
        await service.login(
            email="a@b.c",
            password="whatever1",
            client_ip="1.1.1.1",
            db=None,
            redis=None,
            captcha_token="any",
        )
    assert verify_called is False


@pytest.mark.asyncio
async def test_login_invalid_credentials_carries_captcha_required_flag(monkeypatch):
    from app.features.auth import service
    from app.features.auth.exceptions import InvalidCredentialsError
    from app.features.auth.rate_limit import RateCheckResult

    async def fake_check(redis, ip, eh):
        return RateCheckResult(captcha_required=False, degraded=False)

    async def fake_register(redis, ip, eh):
        pass

    async def fake_get_by_email_hash(eh, db):
        return None

    async def fake_record_event(*args, **kwargs):
        return None

    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check)
    monkeypatch.setattr(service.rate_limit, "register_login_failure", fake_register)
    monkeypatch.setattr(service.repository, "get_by_email_hash", fake_get_by_email_hash)
    monkeypatch.setattr(service, "_record_event", fake_record_event)

    with pytest.raises(InvalidCredentialsError) as exc_info:
        await service.login(
            email="a@b.c",
            password="whatever1",
            client_ip="1.1.1.1",
            db=None,
            redis=None,
            captcha_token=None,
        )
    assert exc_info.value.extra == {"captcha_required": True}
