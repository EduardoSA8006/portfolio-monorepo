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
