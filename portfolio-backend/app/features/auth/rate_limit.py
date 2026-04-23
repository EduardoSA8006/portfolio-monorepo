"""
Login rate limiting via Redis Lua scripts.

Four-key strategy:
  auth:rl:login:{ip}:{email_hash}        — per-IP+email counter (sliding window)
  auth:rl:captcha:{ip}:{email_hash}      — flag "next attempt requires captcha"
  auth:rl:lockout_ips:{email_hash}       — set of IPs that tripped the per-IP limit
  auth:rl:lockout:{email_hash}           — global lockout flag (only set when
                                             SCARD(lockout_ips) >= LOCKOUT_DISTINCT_IPS)

The global lockout is gated by a multi-IP signal — a single abusive IP can never
trigger a DoS against the legitimate account owner.
"""
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import settings
from app.features.auth.exceptions import TooManyAttemptsError

_RL_PREFIX = "auth:rl:login:"
_CAPTCHA_PREFIX = "auth:rl:captcha:"
_LOCKOUT_IPS_PREFIX = "auth:rl:lockout_ips:"
_LOCKOUT_PREFIX = "auth:rl:lockout:"
_DEGRADED_KEY = "auth:rl:degraded"


def _rl_key(ip: str, email_hash: str) -> str:
    return f"{_RL_PREFIX}{ip}:{email_hash}"


def _captcha_key(ip: str, email_hash: str) -> str:
    return f"{_CAPTCHA_PREFIX}{ip}:{email_hash}"


def _lockout_ips_key(email_hash: str) -> str:
    return f"{_LOCKOUT_IPS_PREFIX}{email_hash}"


def _lockout_key(email_hash: str) -> str:
    return f"{_LOCKOUT_PREFIX}{email_hash}"


@dataclass(frozen=True)
class RateCheckResult:
    captcha_required: bool
    degraded: bool


# Read-only check. KEYS: lockout, captcha, degraded.
# Returns {is_locked, captcha_required, degraded}.
_CHECK_STATE = """
local is_locked = redis.call('EXISTS', KEYS[1])
local captcha_required = redis.call('EXISTS', KEYS[2])
local degraded = redis.call('EXISTS', KEYS[3])
return {is_locked, captcha_required, degraded}
"""


# Register a failure atomically.
# KEYS: rl, captcha, lockout_ips, lockout, degraded
# ARGV: max_normal, max_degraded, window_s, lockout_window_s, lockout_s,
#       distinct_ips_threshold, ip
# Returns {counter, sadd_triggered, lockout_triggered}
_REGISTER_FAILURE = """
local degraded = redis.call('EXISTS', KEYS[5])
local max_attempts = tonumber(ARGV[1])
if degraded == 1 then
    max_attempts = tonumber(ARGV[2])
end

local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[3])
end

redis.call('SETEX', KEYS[2], ARGV[3], '1')

local sadd_triggered = 0
local lockout_triggered = 0
if count > max_attempts then
    local added = redis.call('SADD', KEYS[3], ARGV[7])
    redis.call('EXPIRE', KEYS[3], ARGV[4])
    sadd_triggered = added

    local distinct = redis.call('SCARD', KEYS[3])
    if distinct >= tonumber(ARGV[6]) then
        if redis.call('EXISTS', KEYS[4]) == 0 then
            redis.call('SETEX', KEYS[4], ARGV[5], '1')
            lockout_triggered = 1
        end
    end
end

return {count, sadd_triggered, lockout_triggered}
"""


def _get_check_state_script(redis: Redis):
    """Register (lazily per-client) the read-only check script."""
    return redis.register_script(_CHECK_STATE)


def _get_register_failure_script(redis: Redis):
    """Register (lazily per-client) the failure-registration script."""
    return redis.register_script(_REGISTER_FAILURE)


async def check_login_rate(redis: Redis, ip: str, email_hash: str) -> RateCheckResult:
    """
    Read-only check. Raises TooManyAttemptsError if global lockout is active.
    Does NOT increment any counter — call register_login_failure after a real
    password failure.
    """
    script = _get_check_state_script(redis)
    result: list[int] = await script(
        keys=[
            _lockout_key(email_hash),
            _captcha_key(ip, email_hash),
            _DEGRADED_KEY,
        ],
    )
    is_locked, captcha_required, degraded = result
    if is_locked:
        raise TooManyAttemptsError()
    return RateCheckResult(
        captcha_required=bool(captcha_required),
        degraded=bool(degraded),
    )


async def register_login_failure(redis: Redis, ip: str, email_hash: str) -> None:
    """
    Called after a confirmed password failure (post-captcha).
    Increments counter, sets captcha flag, and — if threshold exceeded — adds IP
    to the lockout_ips set; if distinct IPs >= LOCKOUT_DISTINCT_IPS, sets the
    global lockout flag.
    """
    script = _get_register_failure_script(redis)
    await script(
        keys=[
            _rl_key(ip, email_hash),
            _captcha_key(ip, email_hash),
            _lockout_ips_key(email_hash),
            _lockout_key(email_hash),
            _DEGRADED_KEY,
        ],
        args=[
            str(settings.LOGIN_MAX_ATTEMPTS),
            str(settings.LOGIN_MAX_ATTEMPTS_DEGRADED),
            str(settings.LOGIN_WINDOW_SECONDS),
            str(settings.LOGIN_LOCKOUT_WINDOW_SECONDS),
            str(settings.LOGIN_LOCKOUT_SECONDS),
            str(settings.LOGIN_LOCKOUT_DISTINCT_IPS),
            ip,
        ],
    )


async def reset_login_rate(redis: Redis, ip: str, email_hash: str) -> None:
    """
    Clears counter and captcha flag for this IP+email pair after a successful
    login. The lockout_ips set and global lockout flag are intentionally NOT
    touched — one successful login does not erase evidence of a distributed
    attack that other IPs may still be running.
    """
    await redis.delete(_rl_key(ip, email_hash), _captcha_key(ip, email_hash))
