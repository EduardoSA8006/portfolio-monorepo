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


@pytest.mark.asyncio
async def test_register_failure_returns_lockout_triggered_when_threshold_crossed(redis):
    # Trip 2 IPs each over max — no lockout yet (threshold is 3 distinct IPs).
    for ip in ["1.1.1.1", "2.2.2.2"]:
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            await rate_limit.register_login_failure(redis, ip, "hash-a")
        result = await rate_limit.register_login_failure(redis, ip, "hash-a")
        assert result.lockout_triggered is False

    # 3rd IP crosses threshold → lockout fires once.
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        await rate_limit.register_login_failure(redis, "3.3.3.3", "hash-a")
    result = await rate_limit.register_login_failure(redis, "3.3.3.3", "hash-a")
    assert result.lockout_triggered is True

    # Subsequent failures don't re-trigger.
    result = await rate_limit.register_login_failure(redis, "3.3.3.3", "hash-a")
    assert result.lockout_triggered is False


# ---------------------------------------------------------------------------
# Per-IP spray defense (single IP, many emails)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ip_counter_increments_across_distinct_emails(redis):
    """The pure-IP counter aggregates failures regardless of which email
    bucket they fall into. This is precisely what the per-{IP, email}
    counter cannot detect."""
    for i in range(7):
        result = await rate_limit.register_login_failure(redis, "1.1.1.1", f"hash-{i}")
        assert result.ip_counter == i + 1
    assert int(await redis.get("auth:rl:ip:1.1.1.1")) == 7


@pytest.mark.asyncio
async def test_ip_ban_triggers_when_ip_counter_exceeds_max(redis, monkeypatch):
    """Crossing LOGIN_IP_MAX_FAILURES sets the per-IP ban flag exactly once
    and reports ip_ban_triggered=True on the call that crossed."""
    monkeypatch.setattr(settings, "LOGIN_IP_MAX_FAILURES", 5)
    # Spray 5 distinct emails, one failure each — under the limit, no ban.
    for i in range(5):
        result = await rate_limit.register_login_failure(redis, "1.1.1.1", f"hash-{i}")
        assert result.ip_ban_triggered is False
    assert await redis.exists("auth:rl:ip_banned:1.1.1.1") == 0
    # 6th failure crosses the limit → ban fires.
    result = await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-extra")
    assert result.ip_ban_triggered is True
    assert await redis.exists("auth:rl:ip_banned:1.1.1.1") == 1
    # Subsequent failures don't re-trigger (idempotent until the ban expires).
    result = await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-extra-2")
    assert result.ip_ban_triggered is False


@pytest.mark.asyncio
async def test_ip_ban_blocks_check_login_rate(redis, monkeypatch):
    """A banned IP must trip TooManyAttemptsError on check_login_rate, before
    any user lookup, even for an email it has never tried."""
    monkeypatch.setattr(settings, "LOGIN_IP_MAX_FAILURES", 3)
    for i in range(settings.LOGIN_IP_MAX_FAILURES + 1):
        await rate_limit.register_login_failure(redis, "1.1.1.1", f"hash-{i}")
    with pytest.raises(TooManyAttemptsError):
        await rate_limit.check_login_rate(redis, "1.1.1.1", "fresh-email-hash")


@pytest.mark.asyncio
async def test_ip_ban_does_not_affect_other_ips(redis, monkeypatch):
    """The ban is per-IP — a different IP still gets through cleanly,
    otherwise an attacker could DoS legitimate traffic from a CGNAT pool by
    burning their own IP."""
    monkeypatch.setattr(settings, "LOGIN_IP_MAX_FAILURES", 3)
    for i in range(settings.LOGIN_IP_MAX_FAILURES + 1):
        await rate_limit.register_login_failure(redis, "1.1.1.1", f"hash-{i}")
    state = await rate_limit.check_login_rate(redis, "9.9.9.9", "hash-a")
    assert state.captcha_required is False


@pytest.mark.asyncio
async def test_reset_does_not_clear_ip_counter_or_ban(redis, monkeypatch):
    """A successful login from the spraying IP cannot clean up the spray:
    the IP may have stumbled onto one valid {email, password} pair while
    still attacking the rest. The IP counter and ban flag must persist
    across resets — only the per-{IP, email} state is cleared."""
    monkeypatch.setattr(settings, "LOGIN_IP_MAX_FAILURES", 3)
    for i in range(settings.LOGIN_IP_MAX_FAILURES + 1):
        await rate_limit.register_login_failure(redis, "1.1.1.1", f"hash-{i}")
    assert await redis.exists("auth:rl:ip_banned:1.1.1.1") == 1

    await rate_limit.reset_login_rate(redis, "1.1.1.1", "hash-0")

    assert await redis.exists("auth:rl:ip_banned:1.1.1.1") == 1
    assert int(await redis.get("auth:rl:ip:1.1.1.1")) >= settings.LOGIN_IP_MAX_FAILURES + 1


@pytest.mark.asyncio
async def test_ip_counter_window_expires(redis, monkeypatch):
    """The IP counter is a sliding window — it must carry a TTL so a steady
    trickle of one failure per hour does not eventually accumulate to a ban."""
    monkeypatch.setattr(settings, "LOGIN_IP_WINDOW_SECONDS", 60)
    await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    ttl = await redis.ttl("auth:rl:ip:1.1.1.1")
    assert 0 < ttl <= 60
