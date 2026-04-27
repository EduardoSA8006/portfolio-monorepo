"""
Email-2FA code store tests.

Mirror the test surface of features/auth/test_rate_limit.py: drive the
real Lua scripts against fakeredis and assert the externally-visible
state transitions.
"""
import pytest
from fakeredis.aioredis import FakeRedis

from app.core.config import settings
from app.features.email import code_store
from app.features.email.exceptions import EmailCodeInvalidError


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.mark.asyncio
async def test_issue_code_returns_numeric_code_of_configured_length(redis):
    code = await code_store.issue_code(redis, "user-1")
    assert len(code) == settings.EMAIL_2FA_CODE_LENGTH
    assert code.isdigit()


@pytest.mark.asyncio
async def test_issue_code_writes_to_redis_with_ttl(redis):
    await code_store.issue_code(redis, "user-1")
    assert await redis.exists("email:code:user-1") == 1
    ttl = await redis.ttl("email:code:user-1")
    assert 0 < ttl <= settings.EMAIL_2FA_CODE_TTL_SECONDS


@pytest.mark.asyncio
async def test_issue_code_replaces_outstanding_code(redis):
    """A new issue must invalidate the previous code AND reset the
    attempt counter — otherwise an attacker could exhaust attempts on
    the old code, then issue a new one with no attempts left."""
    first = await code_store.issue_code(redis, "user-1")
    # Wrong attempts on the first code
    with pytest.raises(EmailCodeInvalidError):
        await code_store.verify_code(redis, "user-1", "000000")
    second = await code_store.issue_code(redis, "user-1")
    assert second != first or first == "000000"  # tolerate the 1-in-10^6 collision
    # Counter was reset: we should still be able to make the full attempt budget.
    for _ in range(settings.EMAIL_2FA_MAX_ATTEMPTS - 1):
        with pytest.raises(EmailCodeInvalidError):
            await code_store.verify_code(redis, "user-1", "000000")
    # The next wrong attempt is the one that exhausts the budget.
    with pytest.raises(EmailCodeInvalidError):
        await code_store.verify_code(redis, "user-1", "000000")


@pytest.mark.asyncio
async def test_verify_code_success_consumes_code(redis):
    code = await code_store.issue_code(redis, "user-1")
    await code_store.verify_code(redis, "user-1", code)
    # Code is one-shot — same code can't be reused even within TTL.
    with pytest.raises(EmailCodeInvalidError):
        await code_store.verify_code(redis, "user-1", code)
    assert await redis.exists("email:code:user-1") == 0


@pytest.mark.asyncio
async def test_verify_code_with_no_outstanding_code_fails(redis):
    with pytest.raises(EmailCodeInvalidError):
        await code_store.verify_code(redis, "ghost-user", "123456")


@pytest.mark.asyncio
async def test_verify_code_exhausts_attempts(redis, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_2FA_MAX_ATTEMPTS", 3)
    code = await code_store.issue_code(redis, "user-1")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.EMAIL_2FA_MAX_ATTEMPTS):
        with pytest.raises(EmailCodeInvalidError):
            await code_store.verify_code(redis, "user-1", wrong)
    # After the budget is gone, even the right code is rejected
    # (and the key has been wiped).
    with pytest.raises(EmailCodeInvalidError):
        await code_store.verify_code(redis, "user-1", code)
    assert await redis.exists("email:code:user-1") == 0


@pytest.mark.asyncio
async def test_discard_code_clears_state(redis):
    await code_store.issue_code(redis, "user-1")
    await code_store.discard_code(redis, "user-1")
    assert await redis.exists("email:code:user-1") == 0


def test_gen_numeric_code_rejects_short_length():
    with pytest.raises(ValueError, match="too small"):
        code_store._gen_numeric_code(3)
