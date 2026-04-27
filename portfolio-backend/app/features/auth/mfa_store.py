"""
Redis-backed MFA challenge store and TOTP replay guard.

An MFA challenge is a short-lived token issued after a successful password
check for a TOTP-enabled account. The client must exchange it for a real
session by submitting a valid TOTP code within MFA_CHALLENGE_TTL_SECONDS.

Key layout:
  auth:mfa:challenge:{challenge_token}    Hash  {user_id}, TTL = challenge_ttl
  auth:mfa:replay:{user_id}:{code}        String "1",    TTL = replay_window
"""
from __future__ import annotations

import secrets

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings

_CHALLENGE_PREFIX = "auth:mfa:challenge:"
_REPLAY_PREFIX = "auth:mfa:replay:"


class ChallengeInvalidError(Exception):
    """Challenge not found, expired, or consumed past the attempt limit."""


def _ck(token: str) -> str:
    return f"{_CHALLENGE_PREFIX}{token}"


def _rk(user_id: str, code: str) -> str:
    return f"{_REPLAY_PREFIX}{user_id}:{code}"


def _gen_challenge_token() -> str:
    # 32 bytes of entropy encoded as 64 hex chars — never shown to a human.
    return secrets.token_hex(32)


# Atomically register one verification attempt against a challenge.
# Returns user_id on success; errors when the challenge is missing or over-limit.
#
# KEYS[1]  auth:mfa:challenge:{token}
# ARGV[1]  max_attempts
_CONSUME_ATTEMPT = """
local user_id = redis.call('HGET', KEYS[1], 'user_id')
if not user_id then
    return redis.error_reply('CHALLENGE_NOT_FOUND')
end

local attempts = tonumber(redis.call('HINCRBY', KEYS[1], 'attempts', 1))
if attempts > tonumber(ARGV[1]) then
    redis.call('DEL', KEYS[1])
    return redis.error_reply('CHALLENGE_OVER_LIMIT')
end

return user_id
"""


async def create_challenge(
    redis: Redis,
    user_id: str,
    *,
    method: str = "totp",
    email: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    is_new_device: bool = False,
) -> str:
    """Issue a new MFA challenge for the given user. Returns the challenge token.

    `method` records which second-factor flow this challenge belongs to
    (`"totp"` for the authenticator-app path, `"email"` for the
    email-code path). Verify endpoints check the method before
    consuming so a TOTP code submitted to the email endpoint (or vice
    versa) hard-fails — preventing one verification path from spending
    a challenge meant for the other.

    The optional fields ride along inside the same Redis hash so the
    verify endpoint can fire a `login_notification` email after success
    without re-deriving the request context (the verify request is a
    separate HTTP call and does not see the original login form).

    All fields are stored as plain strings — Redis hash values are byte
    strings either way, and the challenge TTL is short
    (MFA_CHALLENGE_TTL_SECONDS, ~5 min), so PII exposure is bounded.
    """
    token = _gen_challenge_token()
    key = _ck(token)
    payload: dict[str, str | int] = {
        "user_id": user_id,
        "attempts": 0,
        "method": method,
    }
    if email:
        payload["email"] = email
    if client_ip:
        payload["client_ip"] = client_ip
    if user_agent:
        # Cap user-agent length so a hostile UA cannot inflate the hash
        # past a sensible bound.
        payload["user_agent"] = user_agent[:500]
    payload["is_new_device"] = "1" if is_new_device else "0"

    await redis.hset(key, mapping=payload)
    await redis.expire(key, settings.MFA_CHALLENGE_TTL_SECONDS)
    return token


async def get_challenge_metadata(redis: Redis, challenge_token: str) -> dict[str, str]:
    """Read the full challenge hash. Caller must have already passed
    consume_attempt — we use this in verify_mfa to extract the device /
    email metadata before the challenge gets revoked."""
    raw = await redis.hgetall(_ck(challenge_token))
    if not raw:
        return {}

    def _decode(value):
        return value.decode() if isinstance(value, (bytes, bytearray)) else value

    return {_decode(k): _decode(v) for k, v in raw.items()}


async def consume_attempt(redis: Redis, challenge_token: str) -> str:
    """
    Atomically register one verification attempt and return the bound user_id.

    Raises ChallengeInvalidError if the challenge is missing, expired, or
    has exceeded MFA_MAX_ATTEMPTS (in which case the challenge is deleted).
    """
    try:
        raw = await redis.eval(
            _CONSUME_ATTEMPT,
            1,
            _ck(challenge_token),
            str(settings.MFA_MAX_ATTEMPTS),
        )
    except ResponseError as exc:
        msg = str(exc)
        if "CHALLENGE_NOT_FOUND" in msg or "CHALLENGE_OVER_LIMIT" in msg:
            raise ChallengeInvalidError from exc
        raise
    # redis-py returns bytes from HGET unless decode_responses=True;
    # normalize so callers can pass into uuid.UUID without TypeError.
    return raw.decode() if isinstance(raw, (bytes, bytearray)) else raw


async def revoke_challenge(redis: Redis, challenge_token: str) -> None:
    await redis.delete(_ck(challenge_token))


async def claim_code(redis: Redis, user_id: str, code: str) -> bool:
    """
    Atomically mark a TOTP code as used for the given user.

    Returns True if the claim succeeded (code not seen before in this window),
    False if it was already used (replay attempt).
    """
    # SET NX EX atomically claims the code for the replay window.
    result = await redis.set(
        _rk(user_id, code),
        "1",
        nx=True,
        ex=settings.MFA_REPLAY_WINDOW_SECONDS,
    )
    return bool(result)
