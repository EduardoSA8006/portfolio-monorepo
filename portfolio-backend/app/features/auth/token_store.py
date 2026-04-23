"""
Redis token store with atomic Lua scripts for the full session lifecycle.

Key layout:
  auth:session:{token}          -> Hash  {user_id, csrf_token, created_at, rotated_at, absolute_expires_at}
  auth:user:{user_id}:sessions  -> Set   of active session tokens

Session expiry model — absolute + idle:
  - absolute_expires_at: hard ceiling stored in the hash at creation time.
    A session cannot live beyond this regardless of activity.
  - Idle TTL: Redis key TTL is reset to SESSION_IDLE_SECONDS on every request.
    A session dies if there is no activity for that long before the absolute limit.
  - The effective TTL on any request is min(remaining_absolute, idle_seconds).
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings

# -- Key builders -------------------------------------------------------------

_SESSION_PREFIX = "auth:session:"
_USER_SESSIONS_PREFIX = "auth:user:"
_USER_SESSIONS_SUFFIX = ":sessions"


def _sk(token: str) -> str:
    return f"{_SESSION_PREFIX}{token}"


def _usk(user_id: str) -> str:
    return f"{_USER_SESSIONS_PREFIX}{user_id}{_USER_SESSIONS_SUFFIX}"


# -- Domain errors (low-level, not HTTP) -------------------------------------

class TokenNotFoundError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


# -- Value object ------------------------------------------------------------

@dataclass(frozen=True)
class SessionData:
    user_id: str
    csrf_token: str
    session_token: str
    rotated: bool


# -- Lua scripts -------------------------------------------------------------

# Create a brand-new session atomically.
# KEYS[1]  auth:session:{token}
# KEYS[2]  auth:user:{user_id}:sessions
# ARGV[1]  user_id
# ARGV[2]  csrf_token
# ARGV[3]  now  (unix ts)
# ARGV[4]  session_token  (value for SADD)
# ARGV[5]  idle_seconds   (initial TTL for the session key)
# ARGV[6]  absolute_expires_at  (unix ts: now + absolute_seconds)
# ARGV[7]  absolute_seconds     (TTL for the user-sessions set)
_CREATE_SESSION = """
redis.call('HSET', KEYS[1],
    'user_id',             ARGV[1],
    'csrf_token',          ARGV[2],
    'created_at',          ARGV[3],
    'rotated_at',          ARGV[3],
    'absolute_expires_at', ARGV[6]
)
redis.call('EXPIRE', KEYS[1], ARGV[5])
redis.call('SADD',   KEYS[2], ARGV[4])
redis.call('EXPIRE', KEYS[2], ARGV[7])
return 1
"""

# Validate current session, enforce absolute + idle expiry, and rotate tokens
# if the rotation window has elapsed.  Fully atomic: one Lua call for all state.
#
# KEYS[1]  auth:session:{old_token}
# ARGV[1]  old_token
# ARGV[2]  new_session_token  (pre-generated, used only when rotation occurs)
# ARGV[3]  new_csrf_token     (pre-generated, used only when rotation occurs)
# ARGV[4]  now  (unix ts)
# ARGV[5]  rotate_after_seconds
# ARGV[6]  idle_seconds  (how far to push the TTL on each valid request)
#
# Returns: {user_id, active_csrf, rotated("0"|"1"), active_token}
_VALIDATE_AND_ROTATE = """
local data = redis.call('HGETALL', KEYS[1])
if #data == 0 then
    return redis.error_reply('SESSION_NOT_FOUND')
end

local s = {}
for i = 1, #data, 2 do s[data[i]] = data[i+1] end

-- Safety net: Redis TTL ≤ 0 means key expired or has no expiry (bug).
local ttl = redis.call('TTL', KEYS[1])
if ttl <= 0 then
    return redis.error_reply('SESSION_EXPIRED')
end

local now         = tonumber(ARGV[4])
local abs_expires = tonumber(s['absolute_expires_at'])

-- Hard absolute ceiling stored in the hash — immune to TTL jitter or key resets.
if now >= abs_expires then
    return redis.error_reply('SESSION_EXPIRED')
end

-- Effective TTL = min(remaining absolute lifetime, idle window).
local remaining_abs = abs_expires - now
local idle_secs     = tonumber(ARGV[6])
local new_ttl       = math.min(remaining_abs, idle_secs)

local rotate_after = tonumber(ARGV[5])
local rotated_at   = tonumber(s['rotated_at'])

if (now - rotated_at) >= rotate_after then
    local new_sk = 'auth:session:' .. ARGV[2]
    local usk    = 'auth:user:' .. s['user_id'] .. ':sessions'

    redis.call('HSET', new_sk,
        'user_id',             s['user_id'],
        'csrf_token',          ARGV[3],
        'created_at',          s['created_at'],
        'rotated_at',          tostring(now),
        'absolute_expires_at', s['absolute_expires_at']
    )
    redis.call('EXPIRE', new_sk, new_ttl)
    redis.call('SREM', usk, ARGV[1])
    redis.call('SADD', usk, ARGV[2])
    redis.call('DEL', KEYS[1])

    return {s['user_id'], ARGV[3], '1', ARGV[2]}
else
    -- No rotation: slide the idle window forward.
    redis.call('EXPIRE', KEYS[1], new_ttl)
    return {s['user_id'], s['csrf_token'], '0', ARGV[1]}
end
"""

# Revoke a single session.
# KEYS[1]  auth:session:{token}
# ARGV[1]  token
_REVOKE_SESSION = """
local user_id = redis.call('HGET', KEYS[1], 'user_id')
if not user_id then return 0 end

local usk = 'auth:user:' .. user_id .. ':sessions'
redis.call('DEL',  KEYS[1])
redis.call('SREM', usk, ARGV[1])
return 1
"""

# Revoke all sessions for a user.
# KEYS[1]  auth:user:{user_id}:sessions
_CLEAR_USER_SESSIONS = """
local tokens = redis.call('SMEMBERS', KEYS[1])
for _, token in ipairs(tokens) do
    redis.call('DEL', 'auth:session:' .. token)
end
redis.call('DEL', KEYS[1])
return #tokens
"""


# -- Public API --------------------------------------------------------------

def _gen_token(length: int) -> str:
    return secrets.token_hex(length // 2)


async def create_session(redis: Redis, user_id: str) -> tuple[str, str]:
    """Create a new session. Returns (session_token, csrf_token)."""
    session_token = _gen_token(settings.SESSION_TOKEN_LENGTH)
    csrf_token    = _gen_token(settings.CSRF_TOKEN_LENGTH)
    now           = int(time.time())
    absolute_expires_at = now + settings.SESSION_ABSOLUTE_SECONDS

    await redis.eval(
        _CREATE_SESSION,
        2,
        _sk(session_token),
        _usk(user_id),
        user_id,
        csrf_token,
        str(now),
        session_token,
        str(settings.SESSION_IDLE_SECONDS),
        str(absolute_expires_at),
        str(settings.SESSION_ABSOLUTE_SECONDS),
    )
    return session_token, csrf_token


async def validate_and_maybe_rotate(redis: Redis, session_token: str) -> SessionData:
    """
    Atomically validate the session, enforce absolute+idle expiry, and rotate
    tokens if the rotation window elapsed.

    On rotation the old token is deleted and a new one is created in a single Lua call.
    Callers must check SessionData.rotated and propagate new tokens to the client.

    Raises TokenNotFoundError or TokenExpiredError on failure.
    """
    new_token = _gen_token(settings.SESSION_TOKEN_LENGTH)
    new_csrf  = _gen_token(settings.CSRF_TOKEN_LENGTH)
    now       = str(int(time.time()))

    try:
        result: list[str] = await redis.eval(
            _VALIDATE_AND_ROTATE,
            1,
            _sk(session_token),
            session_token,
            new_token,
            new_csrf,
            now,
            str(settings.SESSION_ROTATE_SECONDS),
            str(settings.SESSION_IDLE_SECONDS),
        )
    except ResponseError as exc:
        msg = str(exc)
        if "SESSION_NOT_FOUND" in msg:
            raise TokenNotFoundError from exc
        if "SESSION_EXPIRED" in msg:
            raise TokenExpiredError from exc
        raise

    user_id, active_csrf, rotated_flag, active_token = result
    return SessionData(
        user_id=user_id,
        csrf_token=active_csrf,
        session_token=active_token,
        rotated=rotated_flag == "1",
    )


async def revoke_session(redis: Redis, session_token: str) -> None:
    """Revoke a single session atomically."""
    await redis.eval(_REVOKE_SESSION, 1, _sk(session_token), session_token)


async def clear_user_sessions(redis: Redis, user_id: str) -> int:
    """Revoke all active sessions for the given user. Returns the count revoked."""
    return await redis.eval(_CLEAR_USER_SESSIONS, 1, _usk(user_id))
