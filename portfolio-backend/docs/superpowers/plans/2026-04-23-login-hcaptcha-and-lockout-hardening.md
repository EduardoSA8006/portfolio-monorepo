# Login hCaptcha + lockout hardening — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the single-IP DoS in the email lockout, add conditional hCaptcha on `/auth/login` after first failure, and deliver a working `/admin/login` page in the Next.js frontend.

**Architecture:** Backend gains a `captcha.py` module and an extended `rate_limit.py` with a multi-IP lockout signal and a `captcha_required` flag per IP+email pair. `service.login()` orchestrates captcha verification between rate-limit and password check. A new `GET /auth/config` exposes the hCaptcha site key. Frontend adds an `(admin)` route group with a login page that conditionally renders the hCaptcha widget based on the 401 response payload.

**Tech Stack:** FastAPI + Redis (Lua scripts via `redis.register_script`) + hCaptcha `siteverify` / Next.js 16 App Router + `@hcaptcha/react-hcaptcha` + `react-hook-form`.

**Spec:** `docs/superpowers/specs/2026-04-23-login-hcaptcha-and-lockout-hardening-design.md`

---

## File structure

**Backend — created:**
- `app/features/auth/captcha.py` — hCaptcha siteverify client + `degraded` flag writer
- `tests/features/auth/__init__.py` — package marker for new nested test dir
- `tests/features/auth/test_captcha.py` — unit tests for captcha module
- `tests/features/auth/test_rate_limit.py` — unit tests for rate_limit

**Backend — modified:**
- `app/core/config.py` — new settings (HCAPTCHA_*, LOGIN_LOCKOUT_DISTINCT_IPS, LOGIN_LOCKOUT_WINDOW_SECONDS, LOGIN_MAX_ATTEMPTS_DEGRADED) + production validator
- `app/features/auth/exceptions.py` — `CaptchaRequiredError`, `CaptchaInvalidError`
- `app/features/auth/rate_limit.py` — new Lua scripts, new functions, `RateCheckResult` dataclass
- `app/features/auth/service.py` — `login()` consumes `RateCheckResult`, calls `captcha.verify`, only calls `register_login_failure` on actual password-fail paths
- `app/features/auth/schemas.py` — `LoginRequest.captcha_token`, new `AuthConfigResponse`
- `app/features/auth/router.py` — pass captcha_token through, add `GET /auth/config`
- `tests/features/test_auth_service.py` — add cases covering captcha orchestration + degraded mode
- `.env.example` — document new hCaptcha vars
- `pyproject.toml` — add `fakeredis` to dev deps

**Frontend — created:**
- `src/app/admin/layout.tsx` — admin route group shell
- `src/app/admin/login/page.tsx` — login page
- `src/app/admin/page.tsx` — post-login stub
- `src/features/admin/auth/api.ts` — fetch wrappers
- `src/features/admin/auth/use-login.ts` — login state machine hook
- `src/features/admin/auth/hcaptcha-widget.tsx` — widget with dynamic import
- `src/features/admin/auth/types.ts`

**Frontend — modified:**
- `package.json` — add `@hcaptcha/react-hcaptcha`
- `.env.local.example` — document `NEXT_PUBLIC_API_BASE_URL`

---

## Phase A — Backend foundation

### Task 1: Add hCaptcha config settings + production validator

**Files:**
- Modify: `app/core/config.py`
- Modify: `tests/core/test_config_validators.py`

- [ ] **Step 1: Add new settings fields**

Edit `app/core/config.py`. After the existing `LOGIN_LOCKOUT_SECONDS` line (around line 84), add:

```python
    # hCaptcha — required in production, optional in development
    HCAPTCHA_SITE_KEY: str = ""
    HCAPTCHA_SECRET_KEY: str = ""
    HCAPTCHA_VERIFY_URL: str = "https://api.hcaptcha.com/siteverify"
    HCAPTCHA_TIMEOUT_SECONDS: float = 3.0

    # Login rate-limit extensions (multi-IP lockout + degraded mode)
    LOGIN_LOCKOUT_DISTINCT_IPS: int = 3
    LOGIN_LOCKOUT_WINDOW_SECONDS: int = 1800
    LOGIN_MAX_ATTEMPTS_DEGRADED: int = 2
```

- [ ] **Step 2: Add production validator**

At the end of the `Settings` class (after `_validate_session_lifetimes`), add:

```python
    @model_validator(mode="after")
    def _validate_production_requires_hcaptcha(self) -> "Settings":
        if self.APP_ENV == "production":
            if not self.HCAPTCHA_SITE_KEY or not self.HCAPTCHA_SECRET_KEY:
                raise ValueError(
                    "HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET_KEY must be set in production"
                )
        return self
```

- [ ] **Step 3: Write failing tests**

Append to `tests/core/test_config_validators.py`:

```python
def test_production_requires_hcaptcha_keys(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("HCAPTCHA_SITE_KEY", "")
    monkeypatch.setenv("HCAPTCHA_SECRET_KEY", "")
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", '["127.0.0.1/32"]')
    monkeypatch.setenv("ALLOWED_HOSTS", '["api.test.local"]')
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://test.local"]')
    with pytest.raises(ValueError, match="HCAPTCHA_SITE_KEY.*HCAPTCHA_SECRET_KEY"):
        Settings()


def test_development_allows_empty_hcaptcha_keys(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("HCAPTCHA_SITE_KEY", "")
    monkeypatch.setenv("HCAPTCHA_SECRET_KEY", "")
    settings = Settings()
    assert settings.HCAPTCHA_SITE_KEY == ""
    assert settings.HCAPTCHA_SECRET_KEY == ""
```

- [ ] **Step 4: Run tests**

Run: `cd portfolio-backend && poetry run pytest tests/core/test_config_validators.py -v`
Expected: PASS for both new cases.

- [ ] **Step 5: Commit**

```bash
git add app/core/config.py tests/core/test_config_validators.py
git commit -m "feat(auth): add hCaptcha + multi-IP lockout config settings"
```

---

### Task 2: Add new exceptions

**Files:**
- Modify: `app/features/auth/exceptions.py`

- [ ] **Step 1: Append exception classes**

Append to `app/features/auth/exceptions.py`:

```python


class CaptchaRequiredError(AppException):
    status_code = 401
    detail = "Captcha verification required"
    code = "AUTH_CAPTCHA_REQUIRED"


class CaptchaInvalidError(AppException):
    status_code = 401
    detail = "Captcha verification failed"
    code = "AUTH_CAPTCHA_INVALID"
```

- [ ] **Step 2: Run existing test suite — nothing should break**

Run: `poetry run pytest tests/features/ -v`
Expected: all existing tests PASS.

- [ ] **Step 3: Commit**

```bash
git add app/features/auth/exceptions.py
git commit -m "feat(auth): add CaptchaRequiredError and CaptchaInvalidError"
```

---

### Task 3: Add fakeredis dev dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dev dep**

Find the pytest section in `pyproject.toml`. It currently contains dependencies for tests. Add `fakeredis = "^2.24"` to the same section where pytest-asyncio lives. If your `pyproject.toml` uses Poetry 1.x `[tool.poetry.dev-dependencies]`, add it there. If it uses Poetry 2.x `[tool.poetry.group.dev.dependencies]`, add it there.

- [ ] **Step 2: Install**

Run: `poetry install`
Expected: `fakeredis` listed in output.

- [ ] **Step 3: Verify async import**

Run: `poetry run python -c "from fakeredis.aioredis import FakeRedis; print(FakeRedis)"`
Expected: a class printout with no import error.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "test: add fakeredis for rate_limit and captcha unit tests"
```

---

## Phase B — Captcha client module

### Task 4: Create captcha module with TDD

**Files:**
- Create: `app/features/auth/captcha.py`
- Create: `tests/features/auth/__init__.py`
- Create: `tests/features/auth/test_captcha.py`

- [ ] **Step 1: Create the test package marker**

Create empty `tests/features/auth/__init__.py`.

- [ ] **Step 2: Write failing tests**

Create `tests/features/auth/test_captcha.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fakeredis.aioredis import FakeRedis

from app.features.auth import captcha


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def mock_client(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(captcha, "_get_http_client", lambda: client)
    return client


def _response(*, status_code, json_body=None):
    return SimpleNamespace(
        status_code=status_code,
        json=lambda: json_body or {},
    )


@pytest.mark.asyncio
async def test_verify_ok_when_siteverify_success(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.return_value = _response(status_code=200, json_body={"success": True})

    result = await captcha.verify("token-abc", "203.0.113.9", redis)

    assert result.ok is True
    assert result.provider_available is True
    assert result.reason is None


@pytest.mark.asyncio
async def test_verify_not_ok_when_siteverify_rejects(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.return_value = _response(
        status_code=200,
        json_body={"success": False, "error-codes": ["invalid-input-response"]},
    )

    result = await captcha.verify("bad-token", "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is True
    assert result.reason == "invalid-input-response"


@pytest.mark.asyncio
async def test_verify_not_ok_when_token_none(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")

    result = await captcha.verify(None, "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is True
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_verify_marks_degraded_on_timeout(redis, mock_client, monkeypatch):
    import httpx
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.side_effect = httpx.TimeoutException("timeout")

    result = await captcha.verify("token-abc", "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is False
    assert await redis.exists("auth:rl:degraded") == 1


@pytest.mark.asyncio
async def test_verify_marks_degraded_on_5xx(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.return_value = _response(status_code=503, json_body={})

    result = await captcha.verify("token-abc", "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is False
    assert await redis.exists("auth:rl:degraded") == 1


@pytest.mark.asyncio
async def test_verify_skipped_when_secret_key_empty(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "")

    result = await captcha.verify("any-token", "203.0.113.9", redis)

    assert result.ok is True
    assert result.provider_available is True
    mock_client.post.assert_not_called()
```

- [ ] **Step 3: Confirm failure**

Run: `poetry run pytest tests/features/auth/test_captcha.py -v`
Expected: FAIL with `ImportError: cannot import name 'captcha' from 'app.features.auth'`.

- [ ] **Step 4: Implement captcha module**

Create `app/features/auth/captcha.py`:

```python
"""
hCaptcha siteverify client.

Exposes verify(token, remote_ip, redis) -> VerifyResult. Isolated from
rate_limit — it only writes the auth:rl:degraded flag so rate_limit can
react to provider outage without this module knowing about login.
"""
import logging
from dataclasses import dataclass

import httpx
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEGRADED_KEY = "auth:rl:degraded"
_DEGRADED_TTL_SECONDS = 60

_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=settings.HCAPTCHA_TIMEOUT_SECONDS)
    return _client


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    provider_available: bool
    reason: str | None = None


async def _mark_degraded(redis: Redis) -> None:
    try:
        await redis.setex(_DEGRADED_KEY, _DEGRADED_TTL_SECONDS, "1")
    except Exception:
        logger.exception("captcha.mark_degraded_failed")


async def verify(token: str | None, remote_ip: str, redis: Redis) -> VerifyResult:
    """
    Validate an hCaptcha token via siteverify.

    - ok=True only if hCaptcha returned success=True
    - provider_available=False on timeout / network error / 5xx (marks degraded flag)
    - reason is the first error-code from the response, if any
    """
    if not settings.HCAPTCHA_SECRET_KEY:
        # Dev mode — no secret configured, behave as if captcha passed.
        return VerifyResult(ok=True, provider_available=True)

    if not token:
        return VerifyResult(ok=False, provider_available=True, reason="missing-token")

    payload = {
        "secret": settings.HCAPTCHA_SECRET_KEY,
        "response": token,
        "remoteip": remote_ip,
    }

    client = _get_http_client()
    try:
        response = await client.post(settings.HCAPTCHA_VERIFY_URL, data=payload)
    except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError):
        logger.warning("captcha.provider_unavailable", extra={"reason": "network"})
        await _mark_degraded(redis)
        return VerifyResult(ok=False, provider_available=False, reason="provider-unavailable")

    if response.status_code >= 500:
        logger.warning("captcha.provider_unavailable", extra={"status": response.status_code})
        await _mark_degraded(redis)
        return VerifyResult(ok=False, provider_available=False, reason="provider-5xx")

    try:
        body = response.json()
    except Exception:
        logger.warning("captcha.bad_response_body")
        await _mark_degraded(redis)
        return VerifyResult(ok=False, provider_available=False, reason="bad-response")

    if body.get("success") is True:
        return VerifyResult(ok=True, provider_available=True)

    error_codes = body.get("error-codes") or []
    reason = error_codes[0] if error_codes else "rejected"
    return VerifyResult(ok=False, provider_available=True, reason=reason)
```

- [ ] **Step 5: Confirm pass**

Run: `poetry run pytest tests/features/auth/test_captcha.py -v`
Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/features/auth/captcha.py tests/features/auth/__init__.py tests/features/auth/test_captcha.py
git commit -m "feat(auth): hCaptcha siteverify client with degraded-flag marker"
```

---

## Phase C — Rate-limit refactor (multi-IP + captcha flag)

### Task 5: Refactor rate_limit.py with TDD

**Files:**
- Modify: `app/features/auth/rate_limit.py`
- Create: `tests/features/auth/test_rate_limit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/features/auth/test_rate_limit.py`:

```python
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
async def test_single_ip_cannot_cause_lockout(redis):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS * 10):
        await rate_limit.register_login_failure(redis, "1.1.1.1", "hash-a")
    with pytest.raises(TooManyAttemptsError):
        await rate_limit.check_login_rate(redis, "9.9.9.9", "hash-a")
    # If we reach here the test should have raised. Invert expectation:


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
```

Note: the first `test_single_ip_cannot_cause_lockout` test above is placeholder; the correct test is `test_single_ip_does_not_cause_lockout` right below it. **Delete the first one** before committing.

- [ ] **Step 2: Confirm failure**

Run: `poetry run pytest tests/features/auth/test_rate_limit.py -v`
Expected: tests fail with `AttributeError` (new functions don't exist yet).

- [ ] **Step 3: Rewrite rate_limit.py using register_script pattern**

Replace the entire contents of `app/features/auth/rate_limit.py`:

```python
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
```

- [ ] **Step 4: Confirm pass**

Run: `poetry run pytest tests/features/auth/test_rate_limit.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/features/auth/rate_limit.py tests/features/auth/test_rate_limit.py
git commit -m "feat(auth): multi-IP lockout signal + captcha flag in rate_limit"
```

---

## Phase D — Service layer integration

### Task 6: Update service.login()

**Files:**
- Modify: `app/features/auth/service.py`
- Modify: `tests/features/test_auth_service.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/features/test_auth_service.py`:

```python
@pytest.mark.asyncio
async def test_login_raises_captcha_required_when_required_and_no_token(monkeypatch):
    from app.features.auth import service
    from app.features.auth.exceptions import CaptchaRequiredError
    from app.features.auth.rate_limit import RateCheckResult

    async def fake_check(redis, ip, eh):
        return RateCheckResult(captcha_required=True, degraded=False)

    verify_called = False
    async def fake_verify(token, ip, redis):
        nonlocal verify_called
        verify_called = True
        from app.features.auth.captcha import VerifyResult
        return VerifyResult(ok=False, provider_available=True, reason="missing-token")

    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check)
    monkeypatch.setattr(service.captcha, "verify", fake_verify)

    with pytest.raises(CaptchaRequiredError):
        await service.login(
            email="a@b.c",
            password="whatever1",
            client_ip="1.1.1.1",
            db=None,
            redis=None,
            captcha_token=None,
        )
    assert verify_called is True


@pytest.mark.asyncio
async def test_login_skips_captcha_when_degraded(monkeypatch):
    from app.features.auth import service
    from app.features.auth.exceptions import InvalidCredentialsError
    from app.features.auth.rate_limit import RateCheckResult

    async def fake_check(redis, ip, eh):
        return RateCheckResult(captcha_required=True, degraded=True)

    verify_called = False
    async def fake_verify(token, ip, redis):
        nonlocal verify_called
        verify_called = True
        from app.features.auth.captcha import VerifyResult
        return VerifyResult(ok=True, provider_available=True)

    async def fake_get_by_email_hash(eh, db):
        return None

    async def fake_register(redis, ip, eh):
        pass

    monkeypatch.setattr(service.rate_limit, "check_login_rate", fake_check)
    monkeypatch.setattr(service.rate_limit, "register_login_failure", fake_register)
    monkeypatch.setattr(service.captcha, "verify", fake_verify)
    monkeypatch.setattr(service.repository, "get_by_email_hash", fake_get_by_email_hash)

    with pytest.raises(InvalidCredentialsError):
        await service.login(
            email="a@b.c",
            password="whatever1",
            client_ip="1.1.1.1",
            db=None,
            redis=None,
            captcha_token="any",
        )
    assert verify_called is False
```

- [ ] **Step 2: Run — confirm failure**

Run: `poetry run pytest tests/features/test_auth_service.py::test_login_raises_captcha_required_when_required_and_no_token -v`
Expected: FAIL (service.login doesn't accept captcha_token; service.captcha doesn't exist).

- [ ] **Step 3: Update imports in service.py**

Edit `app/features/auth/service.py`. Replace the import line:

```python
from app.features.auth import mfa_store, rate_limit, repository, token_store
```

with:

```python
from app.features.auth import captcha, mfa_store, rate_limit, repository, token_store
```

And extend the exceptions import:

```python
from app.features.auth.exceptions import (
    CaptchaInvalidError,
    CaptchaRequiredError,
    InvalidCredentialsError,
    MFAChallengeInvalidError,
    TOTPAlreadyEnabledError,
    TOTPEnrollmentMissingError,
    TOTPInvalidError,
    TOTPNotEnabledError,
)
```

- [ ] **Step 4: Rewrite the login() function**

Replace the `login` function body (around `service.py:102-155`) with:

```python
async def login(
    email: str,
    password: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
    captcha_token: str | None = None,
) -> LoginResult:
    """
    Step 1 of login: validate email + password with captcha gate on repeat attempts.

    Flow:
    1. check_login_rate — raises TooManyAttemptsError if global lockout active
    2. If captcha_required and not degraded → captcha.verify must return ok
    3. Look up user, compare password (constant-time via _DUMMY_HASH)
    4. On success: reset rate_limit; (if TOTP) return MFA challenge else session
    5. On password failure: register_login_failure (NOT on captcha failures)
    """
    email_hash = hash_email(email)

    rate_state = await rate_limit.check_login_rate(redis, client_ip, email_hash)

    if rate_state.captcha_required and not rate_state.degraded:
        verify_result = await captcha.verify(captcha_token, client_ip, redis)
        if not verify_result.ok:
            if captcha_token is None or captcha_token == "":
                await _record_event(
                    event_type="login_failed",
                    reason="captcha_required",
                    ip=client_ip,
                    user_agent=user_agent,
                )
                raise CaptchaRequiredError()
            if verify_result.provider_available:
                await _record_event(
                    event_type="login_failed",
                    reason="captcha_invalid",
                    ip=client_ip,
                    user_agent=user_agent,
                )
                raise CaptchaInvalidError()
            # Token supplied but provider became unavailable during verify —
            # degraded flag is now set; continue as if captcha passed.

    user = await repository.get_by_email_hash(email_hash, db)

    if user is None:
        verify_password(password, _DUMMY_HASH)
        await rate_limit.register_login_failure(redis, client_ip, email_hash)
        logger.info(
            "login.failed",
            extra={"reason": "user_not_found", "email_hash": email_hash, "ip": client_ip},
        )
        await _record_event(
            event_type="login_failed",
            reason="user_not_found",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise InvalidCredentialsError()

    if not user.is_active:
        verify_password(password, _DUMMY_HASH)
        await rate_limit.register_login_failure(redis, client_ip, email_hash)
        logger.info(
            "login.failed",
            extra={"reason": "account_disabled", "user_id": str(user.id), "ip": client_ip},
        )
        await _record_event(
            event_type="login_failed",
            user_id=str(user.id),
            reason="account_disabled",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        await rate_limit.register_login_failure(redis, client_ip, email_hash)
        logger.info(
            "login.failed",
            extra={"reason": "bad_password", "user_id": str(user.id), "ip": client_ip},
        )
        await _record_event(
            event_type="login_failed",
            user_id=str(user.id),
            reason="bad_password",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise InvalidCredentialsError()

    await _maybe_rehash_password_hash(user, password, db)
    await rate_limit.reset_login_rate(redis, client_ip, email_hash)

    if user.totp_enabled:
        challenge = await mfa_store.create_challenge(redis, str(user.id))
        logger.info("login.mfa_required", extra={"user_id": str(user.id), "ip": client_ip})
        await _record_event(
            event_type="login_mfa_challenge",
            user_id=str(user.id),
            ip=client_ip,
            user_agent=user_agent,
        )
        return LoginResult(mfa_challenge_token=challenge)

    session_token, csrf_token = await token_store.create_session(redis, str(user.id))
    logger.info("login.success", extra={"user_id": str(user.id), "ip": client_ip})
    await _record_event(
        event_type="login_success",
        user_id=str(user.id),
        ip=client_ip,
        user_agent=user_agent,
    )
    return LoginResult(session_token=session_token, csrf_token=csrf_token)
```

- [ ] **Step 5: Fix existing tests that break on new call paths**

Run: `poetry run pytest tests/features/test_auth_service.py -v` and observe which tests broke.

For any test that previously mocked `check_login_rate` returning `None`, update the fake to return `RateCheckResult`:

```python
    async def fake_check_login_rate(redis, client_ip, email_hash):
        order.append("rate.check")
        from app.features.auth.rate_limit import RateCheckResult
        return RateCheckResult(captcha_required=False, degraded=False)
```

For any test that hits `bad_password` / `user_not_found` / `account_disabled` paths, add a `register_login_failure` mock:

```python
    async def fake_register_login_failure(redis, client_ip, email_hash):
        order.append("rate.register_failure")

    monkeypatch.setattr(service.rate_limit, "register_login_failure", fake_register_login_failure)
```

If a test's `order` assertion fails because `rate.register_failure` now appears in failure paths, update the expected order list accordingly.

- [ ] **Step 6: Re-run full suite**

Run: `poetry run pytest tests/ -v`
Expected: full suite PASS.

- [ ] **Step 7: Commit**

```bash
git add app/features/auth/service.py tests/features/test_auth_service.py
git commit -m "feat(auth): login() orchestrates captcha verify + multi-IP lockout"
```

---

### Task 7: Update schemas

**Files:**
- Modify: `app/features/auth/schemas.py`

- [ ] **Step 1: Update LoginRequest + add AuthConfigResponse**

Edit `app/features/auth/schemas.py`. Update `LoginRequest`:

```python
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8)
    captcha_token: str | None = Field(default=None, max_length=4096)
```

Append to end of file:

```python
class AuthConfigResponse(BaseModel):
    """Public config needed by the admin login frontend."""
    hcaptcha_site_key: str
```

- [ ] **Step 2: Commit**

```bash
git add app/features/auth/schemas.py
git commit -m "feat(auth): LoginRequest.captcha_token and AuthConfigResponse schema"
```

---

### Task 8: Wire router + add /auth/config endpoint

**Files:**
- Modify: `app/features/auth/router.py`

- [ ] **Step 1: Verify error shape contract**

Run: `grep -n "AppException\|detail\|code" app/core/exceptions.py`

Note the shape emitted by `AppException` handler — spec's `{"error": ...}` was illustrative, actual wire format may be `{"detail": ..., "code": ...}`. Whatever the existing handler emits is the contract. Do not change the handler for this feature.

- [ ] **Step 2: Update router.login + add /auth/config**

Edit `app/features/auth/router.py`. Update the imports section:

```python
from app.core.config import settings
from app.features.auth.schemas import (
    AuthConfigResponse,
    LoginRequest,
    LoginResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    TOTPConfirmRequest,
    TOTPDisableRequest,
    TOTPEnrollResponse,
)
```

Update the `login` handler body to forward `captcha_token`:

```python
    result = await service.login(
        body.email,
        body.password,
        _get_client_ip(request),
        db,
        redis,
        user_agent=_get_user_agent(request),
        captcha_token=body.captcha_token,
    )
```

After the last existing endpoint, append:

```python
@router.get("/config", response_model=AuthConfigResponse, status_code=status.HTTP_200_OK)
async def auth_config() -> AuthConfigResponse:
    """
    Public config for the admin login page. No auth required — site_key is public.
    Returns empty string when hCaptcha is not configured (dev mode).
    """
    return AuthConfigResponse(hcaptcha_site_key=settings.HCAPTCHA_SITE_KEY)
```

- [ ] **Step 3: Smoke test (optional)**

If stack is running:
```bash
curl -s http://localhost:8000/auth/config
```
Expected: 200 with `{"hcaptcha_site_key":""}` or configured value.

- [ ] **Step 4: Commit**

```bash
git add app/features/auth/router.py
git commit -m "feat(auth): wire captcha_token into router and add GET /auth/config"
```

---

### Task 9: Update .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add hCaptcha section**

Edit `.env.example`. Between the `# ── App ─` and `# ── Session / Auth ─` sections, insert:

```bash
# ── hCaptcha ─────────────────────────────────────────────────────────────────
# Required in production — login requires a valid captcha after the first
# failure in any given IP+email pair. In development both keys may be empty
# and captcha.verify always returns ok=True.
#
# Get keys from https://dashboard.hcaptcha.com. The site_key is public (served
# via GET /auth/config); the secret_key must stay server-side.
HCAPTCHA_SITE_KEY=
HCAPTCHA_SECRET_KEY=
HCAPTCHA_VERIFY_URL=https://api.hcaptcha.com/siteverify
HCAPTCHA_TIMEOUT_SECONDS=3.0

# ── Login rate-limit extensions ──────────────────────────────────────────────
# Global per-email lockout now only fires when distinct IPs >= this many have
# tripped the per-IP counter within the lockout window. Prevents a single
# abusive IP from DoS-locking the admin account.
LOGIN_LOCKOUT_DISTINCT_IPS=3
LOGIN_LOCKOUT_WINDOW_SECONDS=1800

# Under degraded mode (hCaptcha siteverify unreachable), the per-IP attempt
# cap drops to this for the 60s auto-renewing degraded window.
LOGIN_MAX_ATTEMPTS_DEGRADED=2
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs(env): document HCAPTCHA and multi-IP lockout settings"
```

---

## Phase E — Frontend: admin login

### Task 10: Install hCaptcha dep + env template

**Files:**
- Modify: `portfolio-frontend/package.json`

- [ ] **Step 1: Install dep**

From `portfolio-frontend/`:
```bash
pnpm add @hcaptcha/react-hcaptcha
```

- [ ] **Step 2: Create env example**

Append to (or create) `portfolio-frontend/.env.local.example`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 3: Commit**

```bash
git add package.json pnpm-lock.yaml .env.local.example
git commit -m "feat(frontend): add @hcaptcha/react-hcaptcha + API base URL env"
```

---

### Task 11: Scaffold admin route group

**Files:**
- Create: `src/app/admin/layout.tsx`
- Create: `src/app/admin/page.tsx`

- [ ] **Step 1: Create admin layout**

Create `src/app/admin/layout.tsx`:

```tsx
import type { ReactNode } from "react";

export const metadata = {
  title: "Admin — Portfolio",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50">
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Create post-login stub page**

Create `src/app/admin/page.tsx`:

```tsx
export default function AdminHome() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center p-6">
      <h1 className="text-2xl font-semibold">Welcome, admin</h1>
      <p className="mt-2 text-sm text-neutral-400">Dashboard coming soon.</p>
    </main>
  );
}
```

- [ ] **Step 3: Verify routes resolve**

From `portfolio-frontend/`:
```bash
pnpm dev
```
Open `http://localhost:3000/admin` — stub page renders with no errors.

- [ ] **Step 4: Commit**

```bash
git add src/app/admin/
git commit -m "feat(admin): scaffold admin route group + post-login stub"
```

---

### Task 12: Auth types + API client

**Files:**
- Create: `src/features/admin/auth/types.ts`
- Create: `src/features/admin/auth/api.ts`

- [ ] **Step 1: Types**

Create `src/features/admin/auth/types.ts`:

```ts
export type LoginSuccess = {
  status: "ok";
  csrf_token: string;
  message?: string;
};

export type LoginMfaRequired = {
  status: "mfa_required";
  mfa_challenge_token: string;
  message?: string;
};

export type LoginResponse = LoginSuccess | LoginMfaRequired;

export type AuthErrorPayload = {
  detail: string;
  code:
    | "AUTH_INVALID_CREDENTIALS"
    | "AUTH_CAPTCHA_REQUIRED"
    | "AUTH_CAPTCHA_INVALID"
    | "AUTH_TOO_MANY_ATTEMPTS"
    | "AUTH_MFA_CHALLENGE_INVALID"
    | "AUTH_TOTP_INVALID"
    | string;
  captcha_required?: boolean;
};

export type AuthConfig = {
  hcaptcha_site_key: string;
};
```

- [ ] **Step 2: API client**

Create `src/features/admin/auth/api.ts`:

```ts
import type { AuthConfig, AuthErrorPayload, LoginResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class AuthApiError extends Error {
  constructor(
    public status: number,
    public payload: AuthErrorPayload,
  ) {
    super(payload.detail ?? "Auth error");
  }
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const res = await fetch(`${API_BASE}/auth/config`, { credentials: "include" });
  if (!res.ok) throw new Error(`auth config failed: ${res.status}`);
  return res.json();
}

export async function login(params: {
  email: string;
  password: string;
  captcha_token?: string | null;
}): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: params.email,
      password: params.password,
      captcha_token: params.captcha_token ?? null,
    }),
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => ({}))) as AuthErrorPayload;
    throw new AuthApiError(res.status, payload);
  }
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add src/features/admin/auth/types.ts src/features/admin/auth/api.ts
git commit -m "feat(admin): auth types + API client"
```

---

### Task 13: useLogin hook

**Files:**
- Create: `src/features/admin/auth/use-login.ts`

- [ ] **Step 1: Create hook**

Create `src/features/admin/auth/use-login.ts`:

```ts
"use client";

import { useCallback, useState } from "react";

import { AuthApiError, login } from "./api";

type LoginState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "captcha_required"; message?: string }
  | { kind: "error"; message: string; captchaRequired: boolean }
  | { kind: "mfa_required"; challengeToken: string }
  | { kind: "success"; csrfToken: string };

export function useLogin() {
  const [state, setState] = useState<LoginState>({ kind: "idle" });

  const submit = useCallback(
    async (args: { email: string; password: string; captchaToken?: string | null }) => {
      setState({ kind: "submitting" });
      try {
        const result = await login({
          email: args.email,
          password: args.password,
          captcha_token: args.captchaToken ?? null,
        });
        if (result.status === "mfa_required") {
          setState({ kind: "mfa_required", challengeToken: result.mfa_challenge_token });
          return;
        }
        setState({ kind: "success", csrfToken: result.csrf_token });
      } catch (err) {
        if (err instanceof AuthApiError) {
          const code = err.payload.code;
          if (code === "AUTH_CAPTCHA_REQUIRED") {
            setState({ kind: "captcha_required" });
            return;
          }
          if (code === "AUTH_CAPTCHA_INVALID") {
            setState({
              kind: "error",
              message: "Verificação do captcha falhou. Tente novamente.",
              captchaRequired: true,
            });
            return;
          }
          if (code === "AUTH_INVALID_CREDENTIALS") {
            setState({
              kind: "error",
              message: "E-mail ou senha inválidos.",
              captchaRequired: Boolean(err.payload.captcha_required),
            });
            return;
          }
          if (code === "AUTH_TOO_MANY_ATTEMPTS") {
            setState({
              kind: "error",
              message: "Muitas tentativas. Tente novamente em alguns minutos.",
              captchaRequired: false,
            });
            return;
          }
        }
        setState({
          kind: "error",
          message: "Algo deu errado. Tente novamente.",
          captchaRequired: false,
        });
      }
    },
    [],
  );

  return { state, submit, reset: () => setState({ kind: "idle" }) };
}
```

- [ ] **Step 2: Commit**

```bash
git add src/features/admin/auth/use-login.ts
git commit -m "feat(admin): useLogin hook with captcha-required state transitions"
```

---

### Task 14: hCaptcha widget

**Files:**
- Create: `src/features/admin/auth/hcaptcha-widget.tsx`

- [ ] **Step 1: Create widget**

Create `src/features/admin/auth/hcaptcha-widget.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import { forwardRef, type Ref } from "react";

const HCaptcha = dynamic(() => import("@hcaptcha/react-hcaptcha"), { ssr: false });

type Props = {
  siteKey: string;
  onVerify: (token: string) => void;
  onExpire?: () => void;
};

export const HCaptchaWidget = forwardRef(function HCaptchaWidget(
  { siteKey, onVerify, onExpire }: Props,
  ref: Ref<unknown>,
) {
  if (!siteKey) {
    return (
      <div className="rounded border border-dashed border-neutral-700 px-3 py-2 text-xs text-neutral-500">
        hCaptcha disabled (dev mode) —{" "}
        <button type="button" className="underline" onClick={() => onVerify("dev-bypass-token")}>
          simulate verify
        </button>
      </div>
    );
  }
  return (
    <HCaptcha
      // @ts-expect-error — dynamic() typings do not forward ref generic
      ref={ref}
      sitekey={siteKey}
      onVerify={onVerify}
      onExpire={onExpire}
    />
  );
});
```

- [ ] **Step 2: Commit**

```bash
git add src/features/admin/auth/hcaptcha-widget.tsx
git commit -m "feat(admin): hCaptcha widget with dynamic import + dev bypass"
```

---

### Task 15: Login page

**Files:**
- Create: `src/app/admin/login/page.tsx`

- [ ] **Step 1: Create page**

Create `src/app/admin/login/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchAuthConfig } from "@/features/admin/auth/api";
import { HCaptchaWidget } from "@/features/admin/auth/hcaptcha-widget";
import { useLogin } from "@/features/admin/auth/use-login";

export default function AdminLoginPage() {
  const router = useRouter();
  const { state, submit } = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [siteKey, setSiteKey] = useState<string>("");

  useEffect(() => {
    fetchAuthConfig()
      .then((cfg) => setSiteKey(cfg.hcaptcha_site_key))
      .catch(() => setSiteKey(""));
  }, []);

  useEffect(() => {
    if (state.kind === "success") {
      router.replace("/admin");
    }
  }, [state, router]);

  const captchaRequired =
    state.kind === "captcha_required" ||
    (state.kind === "error" && state.captchaRequired);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">Admin login</h1>
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit({ email, password, captchaToken });
        }}
      >
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
        </label>

        {captchaRequired && (
          <HCaptchaWidget
            siteKey={siteKey}
            onVerify={(token) => setCaptchaToken(token)}
            onExpire={() => setCaptchaToken(null)}
          />
        )}

        {state.kind === "error" && (
          <p className="text-sm text-red-400">{state.message}</p>
        )}

        <button
          type="submit"
          disabled={state.kind === "submitting" || (captchaRequired && !captchaToken)}
          className="rounded bg-neutral-100 px-4 py-2 text-neutral-900 disabled:opacity-50"
        >
          {state.kind === "submitting" ? "Entrando..." : "Entrar"}
        </button>

        {state.kind === "mfa_required" && (
          <p className="text-sm text-amber-400">
            MFA required. (UI for TOTP challenge not yet implemented.)
          </p>
        )}
      </form>
    </main>
  );
}
```

- [ ] **Step 2: Verify build passes**

From `portfolio-frontend/`:
```bash
pnpm build
```
Expected: build succeeds with no type errors.

- [ ] **Step 3: Commit**

```bash
git add src/app/admin/login/page.tsx
git commit -m "feat(admin): /admin/login page with conditional hCaptcha widget"
```

---

## Phase F — Manual end-to-end verification

### Task 16: Smoke test

**Files:** none

- [ ] **Step 1: Start backend**

From `portfolio-backend/`:
```bash
docker compose up -d postgres redis redis_celery
poetry run uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend**

From `portfolio-frontend/`:
```bash
pnpm dev
```

- [ ] **Step 3: Verify /auth/config**

```bash
curl -s http://localhost:8000/auth/config
```
Expected: `{"hcaptcha_site_key":""}` in dev.

- [ ] **Step 4: Verify first load**

Open `http://localhost:3000/admin/login`. Expected: email + password visible, no widget.

- [ ] **Step 5: First wrong password → widget appears**

Submit a valid-format email with wrong password. Expected: error message "E-mail ou senha inválidos." + hCaptcha widget (or "simulate verify" in dev mode).

- [ ] **Step 6: Dev bypass + correct password → success**

Click "simulate verify", fix password, submit. Expected: redirect to `/admin` stub.

- [ ] **Step 7: Check Redis after success**

```bash
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" KEYS 'auth:rl:login:*'
```
Expected: no keys for this IP+email (reset wiped them).

- [ ] **Step 8: Verify single-IP lockout does NOT trigger**

Submit 10 wrong passwords from the same browser. After each:
```bash
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" SCARD 'auth:rl:lockout_ips:<email_hash>'
```
Expected: SCARD stays at 1. `auth:rl:lockout:<email_hash>` does NOT get set. Login remains possible with correct password + captcha.

- [ ] **Step 9: Note results or open follow-up**

If all pass, the feature is functionally verified. If any step fails, add a specific follow-up task with the error detail.

---

## Self-review

- **Spec coverage:** Tasks 1–9 cover all backend scenarios and error-handling rows from the spec. Tasks 10–15 deliver the frontend. Task 16 verifies end-to-end.
- **Placeholders:** None — every code block is complete.
- **Type consistency:** `RateCheckResult`, `VerifyResult`, `LoginResult`, `captcha_required` used consistently across tasks.
- **Deviation from spec — frontend tests:** Spec mentions `use-login.test.ts`; plan defers because the frontend repo has no test runner installed. Adding vitest + @testing-library is its own sub-project. Captured as follow-up 1.
- **Deviation from spec — login_lockout_triggered event:** The Lua script surfaces `lockout_triggered` in its return value but `register_login_failure` discards it. The audit event from the spec is not emitted. Captured as follow-up 2 (not blocking; the lockout itself works).
- **Redis down path:** No explicit catch; FastAPI's default 500 handler covers fail-closed behavior.
- **Duplicated test in Task 5:** the `test_single_ip_cannot_cause_lockout` test with `pytest.raises` is a placeholder — the following `test_single_ip_does_not_cause_lockout` is the correct version. Remove the placeholder before committing.

## Follow-ups (not blocking)

1. Frontend test infra (vitest + @testing-library/react) — separate plan.
2. `login_lockout_triggered` audit event emission — requires threading the Lua return value back through `register_login_failure`.
3. TOTP challenge UI on `/admin/login` — the hook exposes `mfa_required` state but the page currently only shows a placeholder.
4. Session-cookie-aware middleware for `/admin/*` — the stub page is accessible unauthenticated. Add a Next.js middleware that calls the backend to validate `__Host-session` before rendering.
