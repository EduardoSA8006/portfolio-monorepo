"""
Tests for the per-user device tracker.

Behaviors pinned here:
  * No cookie  → mint, register, return is_new=True + token to set.
  * Verified cookie + first sighting for THIS user → register, return
    is_new=True (the user gets one new-device email) + None (reuse cookie).
  * Verified cookie + already seen for this user → refresh TTL, return
    is_new=False + None (silent path — the whole point of the feature).
  * Tampered cookie → treated as no cookie (mint fresh).
  * forget_all_devices wipes every key for the user without touching
    other users' devices.
"""
import pytest
from fakeredis.aioredis import FakeRedis

from app.core.config import settings
from app.features.auth import devices
from app.features.auth.cookies import sign_token


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.mark.asyncio
async def test_no_cookie_mints_and_marks_new(redis):
    is_new, new_token = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=None
    )
    assert is_new is True
    assert new_token is not None
    assert len(new_token) == settings.DEVICE_TOKEN_BYTES * 2  # hex
    # Re-running with the just-minted (signed) cookie must hit the
    # "known" branch.
    is_new_2, new_token_2 = await devices.track_login(
        redis=redis,
        user_id="user-1",
        device_cookie_value=sign_token(new_token),
    )
    assert is_new_2 is False
    assert new_token_2 is None


@pytest.mark.asyncio
async def test_known_device_refreshes_ttl(redis, monkeypatch):
    """A known device must have its TTL refreshed on each login. We
    shrink the configured TTL so we can pin the assertion without
    waiting in the test."""
    monkeypatch.setattr(settings, "DEVICE_COOKIE_TTL_DAYS", 1)
    is_new, token = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=None
    )
    assert is_new is True
    key = f"auth:device:user-1:{token}"
    ttl_after_first = await redis.ttl(key)

    # Manually shorten the key so a refresh is observably distinct.
    await redis.expire(key, 30)
    assert await redis.ttl(key) == 30

    is_new_2, _ = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=sign_token(token)
    )
    assert is_new_2 is False
    ttl_after_refresh = await redis.ttl(key)
    assert ttl_after_refresh > 30
    assert ttl_after_refresh <= ttl_after_first


@pytest.mark.asyncio
async def test_cookie_known_for_other_user_treated_as_new(redis):
    """Same browser, two users: each user sees its own first-time
    notification; the cookie token is reused (no new Set-Cookie)."""
    is_new_a, token = await devices.track_login(
        redis=redis, user_id="user-a", device_cookie_value=None
    )
    assert is_new_a is True

    is_new_b, new_token_b = await devices.track_login(
        redis=redis, user_id="user-b", device_cookie_value=sign_token(token)
    )
    # User B has never seen this token even though the cookie verifies.
    assert is_new_b is True
    # Same cookie is reused — no fresh Set-Cookie.
    assert new_token_b is None


@pytest.mark.asyncio
async def test_tampered_cookie_treated_as_missing(redis):
    """A cookie value with a wrong signature must NOT count as known —
    the user gets a fresh token and a 'new device' email. Otherwise an
    attacker could probe the cookie format to flip the new-device gate."""
    is_new, token = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=None
    )
    assert is_new is True

    # Build a forged cookie carrying the right token but the wrong sig.
    forged = f"{token}.deadbeefdeadbeefdeadbeefdeadbeef"
    is_new_2, new_token_2 = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=forged
    )
    assert is_new_2 is True  # forced to mint fresh
    assert new_token_2 is not None
    assert new_token_2 != token


@pytest.mark.asyncio
async def test_empty_string_cookie_treated_as_missing(redis):
    is_new, token = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=""
    )
    assert is_new is True
    assert token is not None


@pytest.mark.asyncio
async def test_forget_all_devices_scoped_to_user(redis):
    # Two users, two devices each.
    for u in ("user-a", "user-b"):
        for _ in range(2):
            await devices.track_login(
                redis=redis, user_id=u, device_cookie_value=None
            )

    deleted = await devices.forget_all_devices(redis, "user-a")
    assert deleted == 2

    # User-b's devices are untouched.
    user_b_keys = [k async for k in redis.scan_iter(match="auth:device:user-b:*")]
    assert len(user_b_keys) == 2
    user_a_keys = [k async for k in redis.scan_iter(match="auth:device:user-a:*")]
    assert user_a_keys == []


@pytest.mark.asyncio
async def test_forget_device_removes_single_key(redis):
    is_new, token = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=None
    )
    assert is_new is True
    await devices.forget_device(redis, "user-1", token)
    # Next login is again "new" because the registration is gone.
    is_new_2, _ = await devices.track_login(
        redis=redis, user_id="user-1", device_cookie_value=sign_token(token)
    )
    assert is_new_2 is True
