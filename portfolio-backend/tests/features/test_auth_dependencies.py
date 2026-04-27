import pytest
from fastapi import Response
from starlette.requests import Request

from app.core.config import settings
from app.features.auth import token_store
from app.features.auth.cookies import get_cookie_key, sign_token
from app.features.auth.dependencies import require_auth
from app.features.auth.exceptions import CSRFValidationError
from app.features.auth.token_store import SessionData


@pytest.fixture(autouse=True)
def _restore_allowed_origins():
    original = list(settings.ALLOWED_ORIGINS)
    yield
    settings.ALLOWED_ORIGINS = original


def _request(headers: dict[str, str], *, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/api/v1/auth/logout",
            "headers": [
                (name.lower().encode("latin-1"), value.encode("latin-1"))
                for name, value in headers.items()
            ],
        }
    )


def _auth_headers(**extra: str) -> dict[str, str]:
    return {
        "Cookie": f"{get_cookie_key()}={sign_token('session-token')}",
        settings.CSRF_HEADER_NAME: "csrf-token",
        **extra,
    }


async def test_require_auth_accepts_post_from_allowed_origin(monkeypatch):
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]
    called = False

    async def fake_validate_and_maybe_rotate(redis, session_token):
        nonlocal called
        called = True
        assert session_token == "session-token"
        return SessionData(
            user_id="user-1",
            csrf_token="csrf-token",
            session_token=session_token,
            rotated=False,
        )

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fake_validate_and_maybe_rotate)

    session = await require_auth(
        _request(_auth_headers(Origin="https://admin.example.com")),
        Response(),
        redis=object(),
    )

    assert called is True
    assert session.user_id == "user-1"


async def test_require_auth_rejects_post_from_untrusted_origin(monkeypatch):
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    async def fail_if_called(redis, session_token):
        pytest.fail("origin validation should run before Redis session validation")

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fail_if_called)

    with pytest.raises(CSRFValidationError):
        await require_auth(
            _request(_auth_headers(Origin="https://evil.example.com")),
            Response(),
            redis=object(),
        )


async def test_require_auth_accepts_post_with_allowed_referer_when_origin_is_absent(
    monkeypatch,
):
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    async def fake_validate_and_maybe_rotate(redis, session_token):
        return SessionData(
            user_id="user-1",
            csrf_token="csrf-token",
            session_token=session_token,
            rotated=False,
        )

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fake_validate_and_maybe_rotate)

    session = await require_auth(
        _request(_auth_headers(Referer="https://admin.example.com/settings/security")),
        Response(),
        redis=object(),
    )

    assert session.user_id == "user-1"


async def test_require_auth_rejects_post_without_origin_or_referer(monkeypatch):
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    async def fail_if_called(redis, session_token):
        pytest.fail("origin validation should run before Redis session validation")

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fail_if_called)

    with pytest.raises(CSRFValidationError):
        await require_auth(_request(_auth_headers()), Response(), redis=object())


async def test_require_auth_does_not_use_referer_when_origin_is_present(monkeypatch):
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    async def fail_if_called(redis, session_token):
        pytest.fail("invalid Origin must not fall back to Referer")

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fail_if_called)

    with pytest.raises(CSRFValidationError):
        await require_auth(
            _request(
                _auth_headers(
                    Origin="https://evil.example.com",
                    Referer="https://admin.example.com/settings/security",
                )
            ),
            Response(),
            redis=object(),
        )


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
async def test_require_auth_enforces_origin_on_all_mutating_verbs(monkeypatch, method):
    """Origin gating must cover every state-changing verb. Today the router
    only exposes POST, but if a future PUT/PATCH/DELETE route gets wired
    without extending the gate, the omission must surface as a test failure
    here, not as a CSRF hole in production."""
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    async def fail_if_called(redis, session_token):
        pytest.fail("origin validation should run before Redis session validation")

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fail_if_called)

    with pytest.raises(CSRFValidationError):
        await require_auth(
            _request(
                _auth_headers(Origin="https://evil.example.com"),
                method=method,
            ),
            Response(),
            redis=object(),
        )


async def test_require_auth_logs_and_audits_invalid_cookie_signature(monkeypatch, caplog):
    """A correctly-shaped cookie with a wrong HMAC signature must:
      1. raise SessionNotFoundError (external behavior unchanged), AND
      2. emit a structured `cookie_signature_invalid` log line, AND
      3. write an `auth_events` row with event_type=cookie_signature_invalid.

    Without this, an attacker probing SECRET_KEY guesses leaves no trail —
    the failure is indistinguishable from "no cookie" in observability."""
    from app.features.auth import audit
    from app.features.auth.cookies import sign_token
    from app.features.auth.dependencies import require_auth
    from app.features.auth.exceptions import SessionNotFoundError

    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    # Build a cookie that LOOKS signed (right shape) but with a wrong sig.
    real = sign_token("session-token")
    raw_token, _, _ = real.rpartition(".")
    forged = f"{raw_token}.deadbeefdeadbeefdeadbeefdeadbeef"

    audit_calls: list[dict] = []

    async def fake_record_event(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(audit, "record_event", fake_record_event)

    async def fail_if_called(redis, session_token):
        pytest.fail("forged cookie must not reach Redis")

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fail_if_called)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/logout",
            "client": ("203.0.113.7", 12345),
            "headers": [
                (b"cookie", f"{get_cookie_key()}={forged}".encode()),
                (settings.CSRF_HEADER_NAME.lower().encode(), b"csrf-token"),
                (b"origin", b"https://admin.example.com"),
                (b"user-agent", b"curl/8.0 (forgery-bot)"),
            ],
        }
    )

    import logging
    with caplog.at_level(logging.WARNING, logger="app.features.auth.dependencies"):
        with pytest.raises(SessionNotFoundError):
            await require_auth(request, Response(), redis=object())

    # Audit row was written with the right shape.
    assert len(audit_calls) == 1
    assert audit_calls[0]["event_type"] == "cookie_signature_invalid"
    assert audit_calls[0]["ip"] == "203.0.113.7"
    assert audit_calls[0]["user_agent"] == "curl/8.0 (forgery-bot)"

    # Log line is emitted with structured extras.
    matching = [r for r in caplog.records if r.message == "cookie_signature_invalid"]
    assert len(matching) == 1
    assert matching[0].ip == "203.0.113.7"
    assert matching[0].user_agent == "curl/8.0 (forgery-bot)"
    assert matching[0].csrf_header_present is True


async def test_require_auth_does_not_audit_missing_cookie(monkeypatch):
    """A missing cookie is not a forgery — no log, no audit row.
    Otherwise every unauthenticated request floods the audit table."""
    from app.features.auth import audit
    from app.features.auth.dependencies import require_auth
    from app.features.auth.exceptions import SessionNotFoundError

    audit_calls: list[dict] = []

    async def fake_record_event(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(audit, "record_event", fake_record_event)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/logout",
            "headers": [],
        }
    )
    with pytest.raises(SessionNotFoundError):
        await require_auth(request, Response(), redis=object())
    assert audit_calls == []


async def test_require_auth_does_not_audit_malformed_cookie(monkeypatch):
    """A cookie with no separator dot is malformed, not forged. Same
    bucket as missing cookie — no audit, no log."""
    from app.features.auth import audit
    from app.features.auth.dependencies import require_auth
    from app.features.auth.exceptions import SessionNotFoundError

    audit_calls: list[dict] = []

    async def fake_record_event(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(audit, "record_event", fake_record_event)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/logout",
            "headers": [
                (b"cookie", f"{get_cookie_key()}=no-dot-no-sig".encode()),
            ],
        }
    )
    with pytest.raises(SessionNotFoundError):
        await require_auth(request, Response(), redis=object())
    assert audit_calls == []


async def test_require_auth_skips_origin_check_on_get(monkeypatch):
    """Read methods must NOT trigger the Origin/Referer gate — that gate is
    a CSRF defense for state-changing requests, and GET requests can
    legitimately omit Origin (e.g., direct navigation, image fetches)."""
    settings.ALLOWED_ORIGINS = ["https://admin.example.com"]

    async def fake_validate(redis, session_token):
        return SessionData(
            user_id="user-1",
            csrf_token="csrf-token",
            session_token=session_token,
            rotated=False,
        )

    monkeypatch.setattr(token_store, "validate_and_maybe_rotate", fake_validate)

    session = await require_auth(
        _request(_auth_headers(), method="GET"),
        Response(),
        redis=object(),
    )
    assert session.user_id == "user-1"
