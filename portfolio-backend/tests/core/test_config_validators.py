"""
Tests for Settings validators in app.core.config.

We instantiate Settings with explicit values rather than relying on .env,
so we can assert the validator behavior precisely.
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

_COMMON_KWARGS = {
    "SECRET_KEY": "x" * 64,
    "EMAIL_PEPPER": "y" * 64,
    "DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/d",
    "DATABASE_URL_SYNC": "postgresql+psycopg2://u:p@h:5432/d",
    "REDIS_URL": "redis://h:6379/0",
    "CELERY_BROKER_URL": "redis://h:6379/1",
    "CELERY_RESULT_BACKEND": "redis://h:6379/2",
}


def test_trusted_proxy_cidrs_required_when_trust_proxy_headers_true():
    """TRUST_PROXY_HEADERS=True with empty TRUSTED_PROXY_CIDRS must fail."""
    with pytest.raises(ValidationError, match="TRUSTED_PROXY_CIDRS"):
        Settings(
            **_COMMON_KWARGS,
            TRUST_PROXY_HEADERS=True,
            TRUSTED_PROXY_CIDRS=[],
        )


def test_trusted_proxy_cidrs_rejects_wildcard():
    """Literal '*' must be rejected — it would defeat IP-based rate limiting."""
    with pytest.raises(ValidationError, match='must not contain "\\*"'):
        Settings(
            **_COMMON_KWARGS,
            TRUST_PROXY_HEADERS=True,
            TRUSTED_PROXY_CIDRS=["*"],
        )


def test_trusted_proxy_cidrs_rejects_invalid_entry():
    """Garbage input must fail loudly at startup, not silently."""
    with pytest.raises(ValidationError, match="not a valid IP or CIDR"):
        Settings(
            **_COMMON_KWARGS,
            TRUST_PROXY_HEADERS=True,
            TRUSTED_PROXY_CIDRS=["not-an-ip"],
        )


def test_trusted_proxy_cidrs_accepts_valid_cidr_and_ip():
    """Happy path: CIDR ranges and single IPs both work."""
    s = Settings(
        **_COMMON_KWARGS,
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS=["172.28.0.0/16", "10.0.0.1"],
    )
    assert s.TRUSTED_PROXY_CIDRS == ["172.28.0.0/16", "10.0.0.1"]


def test_trusted_proxy_headers_false_allows_empty_cidrs():
    """When proxy headers are disabled, empty CIDR list is fine."""
    s = Settings(
        **_COMMON_KWARGS,
        TRUST_PROXY_HEADERS=False,
        TRUSTED_PROXY_CIDRS=[],
    )
    assert s.TRUST_PROXY_HEADERS is False
    assert s.TRUSTED_PROXY_CIDRS == []


def test_cookie_samesite_default_is_lax():
    """
    Default is 'lax' — works for the common case where frontend and API
    share the same registrable domain. 'strict' and 'none' require
    explicit opt-in.
    """
    s = Settings(**_COMMON_KWARGS)
    assert s.COOKIE_SAMESITE == "lax"
