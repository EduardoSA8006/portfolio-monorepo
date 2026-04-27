"""
Email-based 2FA code store.

Mirrors the shape of `features.auth.mfa_store` — a Redis-backed,
Lua-atomic challenge with a per-attempt budget and a TTL — except the
"challenge token" is the user_id directly (one outstanding email code
per user) and the secret being matched is the 6-digit code itself.

Key layout:
  email:code:{user_id}    Hash {code, attempts}, TTL = EMAIL_2FA_CODE_TTL_SECONDS
"""
from __future__ import annotations

import secrets

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings
from app.features.email.exceptions import EmailCodeInvalidError

_CODE_PREFIX = "email:code:"


def _ck(user_id: str) -> str:
    return f"{_CODE_PREFIX}{user_id}"


def _gen_numeric_code(length: int) -> str:
    """Numeric code with leading zeros preserved.

    `secrets.randbelow(10**length)` keeps each digit independent of the
    others (no rejection-sampling artifacts) and zero-pad guarantees a
    fixed display length the user can re-type."""
    if length < 4:
        # 4 digits = 10k codespace which is the floor where rate
        # limiting + TTL still holds. Catch a misconfig at write-time.
        raise ValueError(f"code length {length} is too small")
    return f"{secrets.randbelow(10 ** length):0{length}d}"


# Atomic verify-and-consume. Returns "OK" on match, error reply
# otherwise. We never leak whether the failure was "no code" vs
# "wrong code" via the error string — the caller turns both into
# EmailCodeInvalidError.
#
# KEYS[1]   email:code:{user_id}
# ARGV[1]   submitted code
# ARGV[2]   max_attempts
_VERIFY_AND_CONSUME = """
local stored = redis.call('HGET', KEYS[1], 'code')
if not stored then
    return redis.error_reply('CODE_NOT_FOUND')
end

local attempts = tonumber(redis.call('HINCRBY', KEYS[1], 'attempts', 1))
if attempts > tonumber(ARGV[2]) then
    redis.call('DEL', KEYS[1])
    return redis.error_reply('CODE_OVER_LIMIT')
end

if stored == ARGV[1] then
    redis.call('DEL', KEYS[1])
    return 'OK'
end

return redis.error_reply('CODE_MISMATCH')
"""


def _get_verify_script(redis: Redis):
    return redis.register_script(_VERIFY_AND_CONSUME)


async def issue_code(redis: Redis, user_id: str) -> str:
    """Generate a fresh numeric code, replace any outstanding code for
    this user, and return the plain code so the caller can hand it to
    the email render. The plain code is never logged or returned to
    HTTP clients — only the email body sees it."""
    code = _gen_numeric_code(settings.EMAIL_2FA_CODE_LENGTH)
    key = _ck(user_id)
    pipe = redis.pipeline()
    # DEL before HSET so a brand new attempt resets the attempt counter
    # along with the code value (no carryover from a previous burst).
    pipe.delete(key)
    pipe.hset(key, mapping={"code": code, "attempts": 0})
    pipe.expire(key, settings.EMAIL_2FA_CODE_TTL_SECONDS)
    await pipe.execute()
    return code


async def verify_code(redis: Redis, user_id: str, submitted: str) -> None:
    """Consume one verification attempt.

    Success → delete the code and return None.
    Failure → raise EmailCodeInvalidError; the caller MUST treat all
    failure reasons identically to avoid leaking which step failed."""
    script = _get_verify_script(redis)
    try:
        await script(keys=[_ck(user_id)], args=[submitted, settings.EMAIL_2FA_MAX_ATTEMPTS])
    except ResponseError as exc:
        raise EmailCodeInvalidError(str(exc)) from exc


async def discard_code(redis: Redis, user_id: str) -> None:
    """Drop a code without verifying — used when a session for the user
    is forcibly revoked elsewhere (logout, recovery) so a stale code
    can't be guessed against the now-defunct flow."""
    await redis.delete(_ck(user_id))
