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


@pytest.mark.parametrize("value", ["lax", "strict", "none"])
def test_cookie_samesite_accepts_valid_values(value):
    """Valid SameSite values are 'lax', 'strict', 'none'."""
    s = Settings(**_COMMON_KWARGS, COOKIE_SAMESITE=value)
    assert value == s.COOKIE_SAMESITE


@pytest.mark.parametrize("value", ["Lax", "LAX", "loose", "", "relaxed"])
def test_cookie_samesite_rejects_invalid_value(value):
    """Typos and unsupported values must be rejected at startup."""
    with pytest.raises(ValidationError, match="COOKIE_SAMESITE"):
        Settings(**_COMMON_KWARGS, COOKIE_SAMESITE=value)


def test_production_requires_cookie_secure_true():
    """APP_ENV=production + COOKIE_SECURE=False must fail — HTTPS is mandatory."""
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(
            **_COMMON_KWARGS,
            APP_ENV="production",
            COOKIE_SECURE=False,
        )


def test_production_with_cookie_secure_true_passes():
    """Happy path: production + COOKIE_SECURE=True works."""
    s = Settings(
        **_COMMON_KWARGS,
        APP_ENV="production",
        COOKIE_SECURE=True,
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS=["172.28.0.0/16"],
        ALLOWED_ORIGINS=["https://eduardoalves.online"],
        ALLOWED_HOSTS=["api.eduardoalves.online"],
    )
    assert s.COOKIE_SECURE is True


def test_allowed_origins_rejects_wildcard():
    """['*'] with credentialed cookies is a CORS foot-gun — reject at startup."""
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(**_COMMON_KWARGS, ALLOWED_ORIGINS=["*"])


def test_allowed_origins_rejects_wildcard_mixed_with_valid():
    """Wildcard mixed with valid entries is still forbidden."""
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(
            **_COMMON_KWARGS,
            ALLOWED_ORIGINS=["https://eduardoalves.online", "*"],
        )


def test_allowed_hosts_rejects_wildcard():
    """['*'] defeats TrustedHostMiddleware — reject."""
    with pytest.raises(ValidationError, match="ALLOWED_HOSTS"):
        Settings(**_COMMON_KWARGS, ALLOWED_HOSTS=["*"])


def test_session_max_age_must_cover_absolute():
    """SESSION_MAX_AGE_SECONDS < SESSION_ABSOLUTE_SECONDS leaks cookies past expiry."""
    with pytest.raises(ValidationError, match="SESSION_MAX_AGE_SECONDS"):
        Settings(
            **_COMMON_KWARGS,
            SESSION_ABSOLUTE_SECONDS=28800,
            SESSION_MAX_AGE_SECONDS=600,
        )


def test_session_idle_cannot_exceed_absolute():
    """Idle timeout larger than absolute lifetime is nonsensical — reject."""
    with pytest.raises(ValidationError, match="SESSION_IDLE_SECONDS"):
        Settings(
            **_COMMON_KWARGS,
            SESSION_ABSOLUTE_SECONDS=1800,
            SESSION_IDLE_SECONDS=3600,
        )


@pytest.mark.parametrize("value", ["development", "test", "production"])
def test_app_env_accepts_known_values(value):
    """APP_ENV must be one of the known deployment tiers."""
    # Production also needs SECURE=True per another validator; other values don't.
    extra = {
        "COOKIE_SECURE": True,
        "TRUST_PROXY_HEADERS": True,
        "TRUSTED_PROXY_CIDRS": ["172.28.0.0/16"],
        "ALLOWED_ORIGINS": ["https://eduardoalves.online"],
        "ALLOWED_HOSTS": ["api.eduardoalves.online"],
    } if value == "production" else {}
    s = Settings(**_COMMON_KWARGS, APP_ENV=value, **extra)
    assert value == s.APP_ENV


@pytest.mark.parametrize("value", ["prod", "PRODUCTION", "staging", "local", ""])
def test_app_env_rejects_unknown_value(value):
    """Typos like 'prod' must fail loudly instead of silently disabling prod gates."""
    with pytest.raises(ValidationError, match="APP_ENV"):
        Settings(**_COMMON_KWARGS, APP_ENV=value)
