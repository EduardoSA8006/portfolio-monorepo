"""
Per-user device tracking.

Goal: send the `login_notification` email only the first time a given
browser logs into a given user account. Repeat logins from the same
browser are silent. Cookie wiped / private mode → next login looks new
(intentional — those are user-visible actions, not platform bugs).

Storage:

  Redis key  auth:device:{user_id}:{token}      Value "1", TTL = 365d.

Why one key per (user_id, token) instead of a Redis SET / HASH:
  * SET has no per-member TTL — devices a user hasn't touched in a year
    would otherwise hang around forever.
  * Per-key SETEX gives each device its own sliding-window expiry,
    refreshed on each login. A device that goes silent for >365d is
    forgotten and triggers one fresh "new device" email next time.
  * `SCAN MATCH auth:device:{user_id}:*` enumerates the user's known
    devices later, e.g. for a "trusted devices" screen.

The cookie itself rides on the existing HMAC infrastructure
(sign_token / unsign_token in cookies.py): a tampered cookie raises
CookieSignatureInvalid which we treat as "no cookie" — the user gets a
fresh token, registers as new, and sees the email. The HMAC + the
opaque random token together mean a stolen cookie alone cannot be
forged into a different user's known-device set.
"""
from __future__ import annotations

import secrets

from redis.asyncio import Redis

from app.core.config import settings
from app.features.auth.cookies import CookieSignatureInvalid, unsign_token

_DEVICE_KEY_PREFIX = "auth:device:"


def _key(user_id: str, token: str) -> str:
    return f"{_DEVICE_KEY_PREFIX}{user_id}:{token}"


def _ttl_seconds() -> int:
    return settings.DEVICE_COOKIE_TTL_DAYS * 86400


def _mint_token() -> str:
    """Fresh random device token (hex). Pure randomness — no HMAC, no
    structure; the cookie wrapper layer adds the signature."""
    return secrets.token_hex(settings.DEVICE_TOKEN_BYTES)


async def _register(redis: Redis, user_id: str, token: str) -> None:
    """SETEX (or refresh TTL on) the device key. Idempotent."""
    await redis.setex(_key(user_id, token), _ttl_seconds(), "1")


async def _is_known(redis: Redis, user_id: str, token: str) -> bool:
    return bool(await redis.exists(_key(user_id, token)))


def _extract_cookie_token(device_cookie_value: str | None) -> str | None:
    """Verify the cookie's HMAC and return the embedded raw token.

    A tampered cookie or a missing cookie collapse to None — the caller
    treats both as "no device known", which forces a fresh token mint
    on the next step.
    """
    if not device_cookie_value:
        return None
    try:
        return unsign_token(device_cookie_value)
    except CookieSignatureInvalid:
        return None


async def track_login(
    *,
    redis: Redis,
    user_id: str,
    device_cookie_value: str | None,
) -> tuple[bool, str | None]:
    """Decide if this login is from a previously-seen device.

    Returns:
        (is_new_device, new_token_to_set)

    - is_new_device: True iff we should fire a login_notification email.
    - new_token_to_set: a freshly minted token when the caller must
      Set-Cookie on the response (no valid incoming cookie). None when
      the existing cookie can be reused; the caller may skip Set-Cookie
      to keep the response slim, since the TTL was refreshed in Redis.

    The function always (re)registers the device key in Redis so the
    next login from this browser is fast-pathed as "known".
    """
    incoming = _extract_cookie_token(device_cookie_value)

    if incoming is None:
        token = _mint_token()
        await _register(redis, user_id, token)
        return True, token

    if await _is_known(redis, user_id, incoming):
        # Refresh the TTL so an active user keeps the same device alive.
        await _register(redis, user_id, incoming)
        return False, None

    # Cookie verified but unknown for this user. Three plausible causes:
    #   * the same browser was used by another admin previously,
    #   * Redis was wiped (no auth:device:* survives),
    #   * the cookie was lifted from another browser.
    # In all three the right answer is "register + fire email" — the
    # existing cookie token is reused, no Set-Cookie needed.
    await _register(redis, user_id, incoming)
    return True, None


async def forget_device(redis: Redis, user_id: str, token: str) -> None:
    """Drop a single device. Used by the recovery / sessions_cleared
    paths so a stale cookie cannot quietly re-classify the next login
    as a known device."""
    await redis.delete(_key(user_id, token))


async def forget_all_devices(redis: Redis, user_id: str) -> int:
    """Wipe every known device for a user. Returns number deleted.

    Called from the admin recovery path so post-recovery the next login
    fires a fresh `new device` email — the previous owner of the
    browser cannot silently sneak back in."""
    pattern = f"{_DEVICE_KEY_PREFIX}{user_id}:*"
    deleted = 0
    async for key in redis.scan_iter(match=pattern, count=100):
        await redis.delete(key)
        deleted += 1
    return deleted
