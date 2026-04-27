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


def _build_timeout() -> httpx.Timeout:
    """
    Per-phase timeouts. A single 3 s budget for everything bunches up the
    common-case (sub-50 ms TLS handshake) and the worst-case (slow
    response body) into the same number, so a transient handshake hiccup
    triggers a `provider_unavailable` even though the network was fine.
    Splitting the budget tracks each phase independently.
    """
    total = float(settings.HCAPTCHA_TIMEOUT_SECONDS)
    # Keep `read` as the headline number so existing settings still
    # reflect the user-visible cap on a slow siteverify response.
    return httpx.Timeout(
        connect=min(2.0, total),
        read=total,
        write=min(2.0, total),
        pool=min(2.0, total),
    )


def _get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_build_timeout())
    return _client


async def close_client() -> None:
    """
    Close and release the singleton httpx.AsyncClient.

    Wired into FastAPI's lifespan in `app.main`. In production each
    worker process tears down once at shutdown, so leaking the client
    is invisible — but in dev under `uvicorn --reload`, every reload
    creates a fresh client and abandons the old one, eventually eating
    file descriptors. Calling this on shutdown closes that loop.
    """
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None


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
