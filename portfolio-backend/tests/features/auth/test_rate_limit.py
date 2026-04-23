import pytest
from fakeredis.aioredis import FakeRedis

from app.core.config import settings
from app.features.auth import rate_limit
from app.features.auth.exceptions import TooManyAttemptsError


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.mark.asyncio
async def test_check_returns_not_required_before_first_failure(redis):
    state = await rate_limit.check_login_rate(redis, "1.1.1.1", "hash-a")
    assert state.captcha_required is False
    assert state.degraded is False


@pytest.mark.asyncio
async def test_register_failure_sets_captcha_flag_on_first_failure(redis):
    await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    state = await rate_limit.check_login_rate(redis, "1.1.1.1", "hash-a")
    assert state.captcha_required is True


@pytest.mark.asyncio
async def test_register_failure_does_not_trigger_sadd_below_max(redis):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    card = await redis.scard("auth:rl:lockout_ips:hash-a")
    assert card == 0


@pytest.mark.asyncio
async def test_register_failure_triggers_sadd_when_counter_exceeds_max(redis):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS + 1):
        await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    card = await redis.scard("auth:rl:lockout_ips:hash-a")
    assert card == 1


@pytest.mark.asyncio
async def test_single_ip_does_not_cause_lockout(redis):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS * 10):
        await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    # Must not raise
    state = await rate_limit.check_login_rate(redis, "9.9.9.9", "hash-a")
    assert state.captcha_required is False


@pytest.mark.asyncio
async def test_lockout_triggers_after_distinct_ips_threshold(redis):
    for ip in ["1.1.1.1", "2.2.2.2", "3.3.3.3"]:
        for _ in range(settings.LOGIN_MAX_ATTEMPTS + 1):
            await rate_limit.register_login_failure(redis, ip, "hash-a")
    with pytest.raises(TooManyAttemptsError):
        await rate_limit.check_login_rate(redis, "9.9.9.9", "hash-a")


@pytest.mark.asyncio
async def test_reset_clears_counter_and_captcha_but_preserves_lockout_set(redis):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS + 1):
        await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    assert await redis.scard("auth:rl:lockout_ips:hash-a") == 1

    await rate_limit.reset_login_rate(redis, "1.1.1.1", "hash-a")

    assert await redis.exists("auth:rl:login:1.1.1.1:hash-a") == 0
    assert await redis.exists("auth:rl:captcha:1.1.1.1:hash-a") == 0
    assert await redis.scard("auth:rl:lockout_ips:hash-a") == 1


@pytest.mark.asyncio
async def test_degraded_flag_is_surfaced(redis):
    await redis.setex("auth:rl:degraded", 60, "1")
    state = await rate_limit.check_login_rate(redis, "1.1.1.1", "hash-a")
    assert state.degraded is True


@pytest.mark.asyncio
async def test_degraded_reduces_effective_max_attempts(redis):
    await redis.setex("auth:rl:degraded", 60, "1")
    for _ in range(settings.LOGIN_MAX_ATTEMPTS_DEGRADED + 1):
        await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    assert await redis.scard("auth:rl:lockout_ips:hash-a") == 1
