"""
Session cookie serialization + HMAC signature (defense in depth).

The value written to the cookie is  "{raw_token}.{sig}"  where
    sig = HMAC-SHA256(SECRET_KEY, raw_token)  (hex, first 32 chars = 128 bits)

The Redis key remains  auth:session:{raw_token}  — the signature never touches
Redis. Consequence: an attacker who gains Redis-write-only access cannot forge
a working session because they cannot produce a valid signature without
SECRET_KEY. Rotating SECRET_KEY invalidates every outstanding cookie, which is
the desired behavior during an incident.
"""
import hashlib
import hmac

from fastapi import Response

from app.core.config import settings

# 128 bits of signature entropy — plenty for a short-lived session cookie
# without making the cookie value unreasonably long.
_SIG_HEX_LEN = 32


def get_cookie_key() -> str:
    """
    Returns the cookie name with __Host- prefix when COOKIE_SECURE=True.

    The __Host- prefix enforces three browser invariants automatically:
      - Secure flag must be set (HTTPS only)
      - Path must be "/"
      - Domain attribute must be absent (host-only binding)

    This prevents subdomain cookie injection attacks. Only applicable when
    the frontend and API are on the same host (same-domain topology).
    """
    if settings.COOKIE_SECURE:
        return f"__Host-{settings.COOKIE_NAME}"
    return settings.COOKIE_NAME


def _sign(raw_token: str) -> str:
    mac = hmac.new(
        settings.SECRET_KEY.encode(),
        raw_token.encode(),
        hashlib.sha256,
    ).hexdigest()
    return mac[:_SIG_HEX_LEN]


def sign_token(raw_token: str) -> str:
    """Produce the cookie-encoded form of a session token."""
    return f"{raw_token}.{_sign(raw_token)}"


class CookieSignatureInvalid(Exception):
    """
    Cookie has the right shape (`token.sig`) but the HMAC does not verify.

    This is raised — instead of returning None — so the caller can
    distinguish an attempted forgery from a legitimately-absent or
    malformed cookie. The dependency layer turns this into a structured
    log line plus an `auth_events` audit row, so an attacker probing
    SECRET_KEY guesses leaves a paper trail rather than vanishing into
    the same bucket as "no cookie".
    """


def unsign_token(cookie_value: str) -> str | None:
    """
    Verify an incoming cookie value and return the raw session token.

    Returns None when there is nothing to verify — empty cookie or
    malformed shape (no separator, empty halves). Those cases are
    indistinguishable from "no cookie" and don't warrant alerting.

    Raises CookieSignatureInvalid when the cookie has the correct shape
    but the HMAC does not match — that case is suspicious (forgery
    attempt or stale cookie after SECRET_KEY rotation) and the caller is
    expected to log + audit before falling back to the no-session path.
    """
    if not cookie_value or "." not in cookie_value:
        return None
    raw_token, _, sig = cookie_value.rpartition(".")
    if not raw_token or not sig:
        return None
    expected = _sign(raw_token)
    # Constant-time compare to avoid leaking the signature byte-by-byte.
    if not hmac.compare_digest(sig, expected):
        raise CookieSignatureInvalid()
    return raw_token


def _cookie_kwargs() -> dict:
    return {
        "key": get_cookie_key(),
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
        # Domain must be omitted when using __Host- prefix — the browser enforces this.
        # Explicitly set to None so FastAPI does not emit a Domain attribute.
        "domain": None,
    }


def set_session_cookie(response: Response, token: str) -> None:
    """Sign the token and write it into the session cookie."""
    response.set_cookie(
        value=sign_token(token),
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        **_cookie_kwargs(),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(**_cookie_kwargs())


# ── Device cookie ────────────────────────────────────────────────────────
# Long-lived browser identifier used to recognise a returning device and
# avoid spamming login_notification emails on every session. Same HMAC
# signing as the session cookie (sign_token / unsign_token) so a tampered
# value surfaces as CookieSignatureInvalid the same way.


def get_device_cookie_key() -> str:
    """Mirror of get_cookie_key() for the device cookie."""
    if settings.COOKIE_SECURE:
        return f"__Host-{settings.DEVICE_COOKIE_NAME}"
    return settings.DEVICE_COOKIE_NAME


def _device_cookie_kwargs() -> dict:
    return {
        "key": get_device_cookie_key(),
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
        "domain": None,
    }


def set_device_cookie(response: Response, token: str) -> None:
    """Persist a fresh / refreshed device token into the browser."""
    response.set_cookie(
        value=sign_token(token),
        max_age=settings.DEVICE_COOKIE_TTL_DAYS * 86400,
        **_device_cookie_kwargs(),
    )


def clear_device_cookie(response: Response) -> None:
    response.delete_cookie(**_device_cookie_kwargs())
