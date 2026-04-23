"""
FastAPI dependencies for auth.

require_auth:
  - Reads session token from http-only cookie
  - Reads CSRF token from request header
  - Validates Origin/Referer for authenticated POSTs
  - Validates session in Redis (atomic Lua script)
  - Performs constant-time CSRF comparison to prevent timing attacks
  - On rotation: transparently sets new cookie + new CSRF response header
"""
import hmac
from urllib.parse import urlsplit

from fastapi import Depends, Request, Response
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis
from app.features.auth import token_store
from app.features.auth.cookies import get_cookie_key, set_session_cookie, unsign_token
from app.features.auth.exceptions import (
    CSRFValidationError,
    SessionExpiredError,
    SessionNotFoundError,
)
from app.features.auth.token_store import SessionData, TokenExpiredError, TokenNotFoundError

_ORIGIN_CHECK_METHODS = frozenset({"POST"})
_TRUSTED_ORIGIN_SCHEMES = frozenset({"http", "https"})


def _origin_from_url(value: str | None, *, allow_path: bool) -> str | None:
    if value is None:
        return None

    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in _TRUSTED_ORIGIN_SCHEMES or not parsed.netloc:
        return None
    if not allow_path and (parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        return None

    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _allowed_origins() -> set[str]:
    origins: set[str] = set()
    for origin in settings.ALLOWED_ORIGINS:
        normalized = _origin_from_url(origin, allow_path=False)
        if normalized is not None:
            origins.add(normalized)
    return origins


def _has_trusted_request_origin(request: Request) -> bool:
    allowed_origins = _allowed_origins()

    origin_header = request.headers.get("Origin")
    if origin_header is not None:
        origin = _origin_from_url(origin_header, allow_path=False)
        return origin in allowed_origins

    referer_origin = _origin_from_url(request.headers.get("Referer"), allow_path=True)
    return referer_origin in allowed_origins


def _enforce_post_origin(request: Request) -> None:
    if request.method.upper() not in _ORIGIN_CHECK_METHODS:
        return
    if not _has_trusted_request_origin(request):
        raise CSRFValidationError()


async def require_auth(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
) -> SessionData:
    raw_cookie = request.cookies.get(get_cookie_key())
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)

    if not raw_cookie:
        raise SessionNotFoundError()

    # Verify the HMAC signature before any Redis I/O. A tampered or unsigned
    # cookie is indistinguishable from "no session" for the caller.
    session_token = unsign_token(raw_cookie)
    if session_token is None:
        raise SessionNotFoundError()

    if not csrf_header:
        raise CSRFValidationError()

    _enforce_post_origin(request)

    try:
        session = await token_store.validate_and_maybe_rotate(redis, session_token)
    except TokenNotFoundError as exc:
        raise SessionNotFoundError() from exc
    except TokenExpiredError as exc:
        raise SessionExpiredError() from exc

    # Constant-time comparison prevents timing-based CSRF token enumeration.
    if not hmac.compare_digest(session.csrf_token, csrf_header):
        raise CSRFValidationError()

    if session.rotated:
        set_session_cookie(response, session.session_token)
        response.headers[settings.CSRF_HEADER_NAME] = session.csrf_token

    return session
