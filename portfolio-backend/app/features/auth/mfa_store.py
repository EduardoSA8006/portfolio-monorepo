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


async def create_challenge(redis: Redis, user_id: str) -> str:
    """Issue a new MFA challenge for the given user. Returns the challenge token."""
    token = _gen_challenge_token()
    key = _ck(token)
    await redis.hset(key, mapping={"user_id": user_id, "attempts": 0})
    await redis.expire(key, settings.MFA_CHALLENGE_TTL_SECONDS)
    return token


async def consume_attempt(redis: Redis, challenge_token: str) -> str:
    """
    Atomically register one verification attempt and return the bound user_id.

    Raises ChallengeInvalidError if the challenge is missing, expired, or
    has exceeded MFA_MAX_ATTEMPTS (in which case the challenge is deleted).
    """
    try:
        user_id: str = await redis.eval(
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
    return user_id


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
