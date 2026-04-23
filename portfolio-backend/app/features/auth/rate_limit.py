"""
Login rate limiting via Redis Lua scripts.

Two-key strategy:
  auth:rl:login:{ip}:{email_hash}  — per-IP+email attempt counter (sliding window)
  auth:rl:lockout:{email_hash}     — global lockout flag triggered after N failures

Lockout is keyed by email_hash (not by IP) to block distributed brute-force
attacks that rotate source IPs against the same target account.
"""
from redis.asyncio import Redis

from app.core.config import settings
from app.features.auth.exceptions import TooManyAttemptsError

_RL_PREFIX = "auth:rl:login:"
_LOCKOUT_PREFIX = "auth:rl:lockout:"


def _rl_key(ip: str, email_hash: str) -> str:
    return f"{_RL_PREFIX}{ip}:{email_hash}"


def _lockout_key(email_hash: str) -> str:
    return f"{_LOCKOUT_PREFIX}{email_hash}"


# Atomically check lockout, increment counter, and trigger lockout when exceeded.
#
# KEYS[1]  auth:rl:login:{ip}:{email_hash}
# KEYS[2]  auth:rl:lockout:{email_hash}
# ARGV[1]  max_attempts
# ARGV[2]  window_seconds
# ARGV[3]  lockout_seconds
#
# Returns: {count, is_locked (0|1)}
_CHECK_AND_INCREMENT = """
if redis.call('EXISTS', KEYS[2]) == 1 then
    return {-1, 1}
end

local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end

if count > tonumber(ARGV[1]) then
    redis.call('SETEX', KEYS[2], ARGV[3], '1')
    return {count, 1}
end

return {count, 0}
"""


async def check_login_rate(redis: Redis, ip: str, email_hash: str) -> None:
    """
    Increment the attempt counter and raise TooManyAttemptsError when the
    per-IP+email limit is exceeded or a global email lockout is in effect.
    """
    result: list[int] = await redis.eval(
        _CHECK_AND_INCREMENT,
        2,
        _rl_key(ip, email_hash),
        _lockout_key(email_hash),
        str(settings.LOGIN_MAX_ATTEMPTS),
        str(settings.LOGIN_WINDOW_SECONDS),
        str(settings.LOGIN_LOCKOUT_SECONDS),
    )
    _count, is_locked = result
    if is_locked:
        raise TooManyAttemptsError()


async def reset_login_rate(redis: Redis, ip: str, email_hash: str) -> None:
    """
    Delete the per-IP+email counter after a successful login.
    The global lockout key (if any) is intentionally left to expire naturally —
    a correct password does not undo a lockout triggered by other IPs.
    """
    await redis.delete(_rl_key(ip, email_hash))
