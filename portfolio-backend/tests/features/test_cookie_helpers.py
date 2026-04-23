"""
Tests for cookie helper behavior.

The `get_cookie_key` function reads settings at call time, so we can
toggle COOKIE_SECURE via monkeypatch and observe the result. The CORS
middleware is configured at import time and cannot be tested this way;
its correctness is exercised in runtime e2e checks (see runbook §9).
"""
import pytest

from app.core.config import settings
from app.features.auth.cookies import get_cookie_key


@pytest.fixture(autouse=True)
def _restore_cookie_secure():
    original = settings.COOKIE_SECURE
    yield
    settings.COOKIE_SECURE = original


def test_cookie_key_uses_host_prefix_when_secure():
    """With COOKIE_SECURE=True, cookie name must start with __Host-."""
    settings.COOKIE_SECURE = True
    assert get_cookie_key().startswith("__Host-")


def test_cookie_key_plain_when_not_secure():
    """In dev (HTTP), the __Host- prefix is dropped so the cookie is usable."""
    settings.COOKIE_SECURE = False
    assert not get_cookie_key().startswith("__Host-")
    assert get_cookie_key() == settings.COOKIE_NAME
