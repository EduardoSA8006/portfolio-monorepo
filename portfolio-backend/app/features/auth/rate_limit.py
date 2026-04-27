"""
Login rate limiting via Redis Lua scripts.

Six-key strategy:
  auth:rl:login:{ip}:{email_hash}        — per-IP+email counter (sliding window)
  auth:rl:captcha:{ip}:{email_hash}      — flag "next attempt requires captcha"
  auth:rl:lockout_ips:{email_hash}       — set of IPs that tripped the per-IP limit
  auth:rl:lockout:{email_hash}           — global lockout flag (only set when
                                             SCARD(lockout_ips) >= LOCKOUT_DISTINCT_IPS)
  auth:rl:ip:{ip}                        — pure per-IP failure counter (sliding window)
  auth:rl:ip_banned:{ip}                 — temporary IP ban flag (set when the
                                             pure-IP counter crosses
                                             LOGIN_IP_MAX_FAILURES)

The global lockout is gated by a multi-IP signal — a single abusive IP can never
trigger a DoS against the legitimate account owner.

The IP ban (auth:rl:ip:* / auth:rl:ip_banned:*) closes the symmetric gap: one
IP probing many distinct emails never trips the per-{IP,email} or per-email
gates, but it does accumulate failures on the pure-IP counter. Crossing
LOGIN_IP_MAX_FAILURES sets a ban that blocks every subsequent attempt from
that IP for LOGIN_IP_BAN_SECONDS — and the ban check happens before any user
lookup so the spray cost goes to zero on the attacker side.
"""
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import settings
from app.features.auth.exceptions import TooManyAttemptsError

_RL_PREFIX = "auth:rl:login:"
_CAPTCHA_PREFIX = "auth:rl:captcha:"
_LOCKOUT_IPS_PREFIX = "auth:rl:lockout_ips:"
_LOCKOUT_PREFIX = "auth:rl:lockout:"
_IP_COUNTER_PREFIX = "auth:rl:ip:"
_IP_BAN_PREFIX = "auth:rl:ip_banned:"
_DEGRADED_KEY = "auth:rl:degraded"


def _rl_key(ip: str, email_hash: str) -> str:
    return f"{_RL_PREFIX}{ip}:{email_hash}"


def _captcha_key(ip: str, email_hash: str) -> str:
    return f"{_CAPTCHA_PREFIX}{ip}:{email_hash}"


def _lockout_ips_key(email_hash: str) -> str:
    return f"{_LOCKOUT_IPS_PREFIX}{email_hash}"


def _lockout_key(email_hash: str) -> str:
    return f"{_LOCKOUT_PREFIX}{email_hash}"


def _ip_counter_key(ip: str) -> str:
    return f"{_IP_COUNTER_PREFIX}{ip}"


def _ip_ban_key(ip: str) -> str:
    return f"{_IP_BAN_PREFIX}{ip}"


@dataclass(frozen=True)
class RateCheckResult:
    captcha_required: bool
    degraded: bool


@dataclass(frozen=True)
class FailureRegistration:
    counter: int
    sadd_triggered: bool
    lockout_triggered: bool
    ip_counter: int
    ip_ban_triggered: bool


# Read-only check. KEYS: lockout, captcha, degraded, ip_banned.
# Returns {is_locked, captcha_required, degraded, ip_banned}.
# A set ip_banned flag short-circuits the rest of the login pipeline — see
# check_login_rate.
_CHECK_STATE = """
local is_locked = redis.call('EXISTS', KEYS[1])
local captcha_required = redis.call('EXISTS', KEYS[2])
local degraded = redis.call('EXISTS', KEYS[3])
local ip_banned = redis.call('EXISTS', KEYS[4])
return {is_locked, captcha_required, degraded, ip_banned}
"""


# Register a failure atomically.
# KEYS: rl, captcha, lockout_ips, lockout, degraded, ip_counter, ip_banned
# ARGV: max_normal, max_degraded, window_s, lockout_window_s, lockout_s,
#       distinct_ips_threshold, ip, ip_max_failures, ip_window_s, ip_ban_s
# Returns {counter, sadd_triggered, lockout_triggered, ip_counter, ip_ban_triggered}
#
# The pure-IP counter (KEYS[6]) and ban flag (KEYS[7]) are incremented on
# every failure regardless of which {IP, email} bucket it falls into — that
# is the whole point of the IP-spray defense. INCR happens inside the same
# Lua script so the per-IP counter and the per-email lockout never disagree
# about whether a failure happened (no torn-write window between them).
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

local ip_count = redis.call('INCR', KEYS[6])
if ip_count == 1 then
    redis.call('EXPIRE', KEYS[6], ARGV[9])
end

local ip_ban_triggered = 0
if ip_count > tonumber(ARGV[8]) then
    if redis.call('EXISTS', KEYS[7]) == 0 then
        redis.call('SETEX', KEYS[7], ARGV[10], '1')
        ip_ban_triggered = 1
    end
end

return {count, sadd_triggered, lockout_triggered, ip_count, ip_ban_triggered}
"""


def _get_check_state_script(redis: Redis):
    """Register (lazily per-client) the read-only check script."""
    return redis.register_script(_CHECK_STATE)


def _get_register_failure_script(redis: Redis):
    """Register (lazily per-client) the failure-registration script."""
    return redis.register_script(_REGISTER_FAILURE)


async def check_login_rate(redis: Redis, ip: str, email_hash: str) -> RateCheckResult:
    """
    Read-only check. Raises TooManyAttemptsError when EITHER the per-email
    global lockout flag (multi-IP attack) OR the per-IP ban flag (single-IP
    spray) is set. Does NOT increment any counter — call register_login_failure
    after a real password failure.
    """
    script = _get_check_state_script(redis)
    result: list[int] = await script(
        keys=[
            _lockout_key(email_hash),
            _captcha_key(ip, email_hash),
            _DEGRADED_KEY,
            _ip_ban_key(ip),
        ],
    )
    is_locked, captcha_required, degraded, ip_banned = result
    if is_locked or ip_banned:
        raise TooManyAttemptsError()
    return RateCheckResult(
        captcha_required=bool(captcha_required),
        degraded=bool(degraded),
    )


async def register_login_failure(
    redis: Redis, ip: str, email_hash: str
) -> FailureRegistration:
    """
    Called after a confirmed password failure (post-captcha).

    Atomically (single Lua script):
      1. INCR per-{IP, email} counter, set captcha flag.
      2. If counter exceeds the per-{IP, email} limit, add IP to the email's
         lockout_ips set; if distinct IPs >= LOGIN_LOCKOUT_DISTINCT_IPS, set
         the per-email global lockout flag.
      3. INCR pure per-IP counter; if it exceeds LOGIN_IP_MAX_FAILURES inside
         LOGIN_IP_WINDOW_SECONDS, set the per-IP ban flag.

    The per-email lockout side and the per-IP ban side both progress in the
    same script — there is no torn-write window where one observer could see
    the IP counter incremented but a stale ban state.

    Returns FailureRegistration:
      - counter:           per-{IP, email} failure count (sliding window)
      - sadd_triggered:    this call added the IP to the email's lockout set
      - lockout_triggered: this call activated the per-email global lockout
                           (true at most once per lockout window)
      - ip_counter:        pure per-IP failure count (sliding window)
      - ip_ban_triggered:  this call activated the per-IP ban (true at most
                           once per ban window)
    """
    script = _get_register_failure_script(redis)
    result: list[int] = await script(
        keys=[
            _rl_key(ip, email_hash),
            _captcha_key(ip, email_hash),
            _lockout_ips_key(email_hash),
            _lockout_key(email_hash),
            _DEGRADED_KEY,
            _ip_counter_key(ip),
            _ip_ban_key(ip),
        ],
        args=[
            str(settings.LOGIN_MAX_ATTEMPTS),
            str(settings.LOGIN_MAX_ATTEMPTS_DEGRADED),
            str(settings.LOGIN_WINDOW_SECONDS),
            str(settings.LOGIN_LOCKOUT_WINDOW_SECONDS),
            str(settings.LOGIN_LOCKOUT_SECONDS),
            str(settings.LOGIN_LOCKOUT_DISTINCT_IPS),
            ip,
            str(settings.LOGIN_IP_MAX_FAILURES),
            str(settings.LOGIN_IP_WINDOW_SECONDS),
            str(settings.LOGIN_IP_BAN_SECONDS),
        ],
    )
    counter, sadd_triggered, lockout_triggered, ip_counter, ip_ban_triggered = result
    return FailureRegistration(
        counter=int(counter),
        sadd_triggered=bool(sadd_triggered),
        lockout_triggered=bool(lockout_triggered),
        ip_counter=int(ip_counter),
        ip_ban_triggered=bool(ip_ban_triggered),
    )


async def reset_login_rate(redis: Redis, ip: str, email_hash: str) -> None:
    """
    Clears counter and captcha flag for this IP+email pair after a successful
    login. The lockout_ips set, global lockout flag, pure-IP counter, and IP
    ban flag are intentionally NOT touched — one successful login does not
    erase evidence of a distributed attack still in progress on other IPs,
    nor of an in-progress spray attack from this same IP that just happened
    to find a valid {email, password} pair.
    """
    await redis.delete(_rl_key(ip, email_hash), _captcha_key(ip, email_hash))
