"""
FastAPI dependencies for auth.

require_auth:
  - Reads session token from http-only cookie
  - Reads CSRF token from request header
  - Validates session in Redis (atomic Lua script)
  - Performs constant-time CSRF comparison to prevent timing attacks
  - On rotation: transparently sets new cookie + new CSRF response header
"""
import hmac

from fastapi import Depends, Request, Response
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis
from app.features.auth import token_store
from app.features.auth.exceptions import CSRFValidationError, SessionNotFoundError, SessionExpiredError
from app.features.auth.token_store import SessionData, TokenExpiredError, TokenNotFoundError
from app.features.auth.cookies import get_cookie_key, set_session_cookie, unsign_token


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

    try:
        session = await token_store.validate_and_maybe_rotate(redis, session_token)
    except TokenNotFoundError:
        raise SessionNotFoundError()
    except TokenExpiredError:
        raise SessionExpiredError()

    # Constant-time comparison prevents timing-based CSRF token enumeration.
    if not hmac.compare_digest(session.csrf_token, csrf_header):
        raise CSRFValidationError()

    if session.rotated:
        set_session_cookie(response, session.session_token)
        response.headers[settings.CSRF_HEADER_NAME] = session.csrf_token

    return session
