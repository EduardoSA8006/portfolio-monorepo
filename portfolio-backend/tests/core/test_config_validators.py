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

# Real-looking passwords that satisfy the production credential validator.
# Distinct values per service so a mistakenly-shared credential would fail
# loudly instead of silently passing tests.
_PROD_CREDENTIAL_KWARGS = {
    "POSTGRES_PASSWORD": "pg-real-prod-pw-aa",
    "REDIS_PASSWORD": "redis-real-prod-pw-bb",
    "CELERY_REDIS_PASSWORD": "celery-real-prod-pw-cc",
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


def test_readiness_allowed_cidrs_rejects_empty_list():
    """/health/ready needs at least one trusted source."""
    with pytest.raises(ValidationError, match="READINESS_ALLOWED_CIDRS"):
        Settings(**_COMMON_KWARGS, READINESS_ALLOWED_CIDRS=[])


def test_readiness_allowed_cidrs_rejects_wildcard():
    """Readiness must not be exposed to every source."""
    with pytest.raises(ValidationError, match='must not contain "\\*"'):
        Settings(**_COMMON_KWARGS, READINESS_ALLOWED_CIDRS=["*"])


def test_readiness_allowed_cidrs_rejects_invalid_entry():
    """Invalid readiness CIDRs must fail at startup."""
    with pytest.raises(ValidationError, match="not a valid IP or CIDR"):
        Settings(**_COMMON_KWARGS, READINESS_ALLOWED_CIDRS=["not-an-ip"])


def test_readiness_allowed_cidrs_accepts_valid_cidr_and_ip():
    """Readiness allowlist accepts both CIDR ranges and single IPs."""
    s = Settings(
        **_COMMON_KWARGS,
        READINESS_ALLOWED_CIDRS=["127.0.0.1/32", "::1/128", "172.28.0.0/16"],
    )
    assert s.READINESS_ALLOWED_CIDRS == ["127.0.0.1/32", "::1/128", "172.28.0.0/16"]


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
        **_PROD_CREDENTIAL_KWARGS,
        APP_ENV="production",
        COOKIE_SECURE=True,
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS=["172.28.0.0/16"],
        ALLOWED_ORIGINS=["https://eduardoalves.online"],
        ALLOWED_HOSTS=["api.eduardoalves.online"],
        HCAPTCHA_SITE_KEY="test-site-key",
        HCAPTCHA_SECRET_KEY="test-secret-key",
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


def test_session_max_age_below_absolute_rejected():
    """Cookie shorter than the server session expires the cookie mid-session,
    forcing a 401 before the user's absolute lifetime is up."""
    with pytest.raises(ValidationError, match="SESSION_MAX_AGE_SECONDS"):
        Settings(
            **_COMMON_KWARGS,
            SESSION_ABSOLUTE_SECONDS=28800,
            SESSION_MAX_AGE_SECONDS=600,
        )


def test_session_max_age_above_absolute_rejected():
    """Cookie longer than the server session leaves an orphaned cookie that
    the browser keeps sending after the server has dropped the session,
    producing the 'logged out by myself' UX bug."""
    with pytest.raises(ValidationError, match="SESSION_MAX_AGE_SECONDS"):
        Settings(
            **_COMMON_KWARGS,
            SESSION_ABSOLUTE_SECONDS=28800,
            SESSION_MAX_AGE_SECONDS=86400,
        )


def test_session_max_age_equal_to_absolute_passes():
    """Equality is the only valid configuration — cookie and server session
    expire at the same instant."""
    s = Settings(
        **_COMMON_KWARGS,
        SESSION_ABSOLUTE_SECONDS=28800,
        SESSION_MAX_AGE_SECONDS=28800,
    )
    assert s.SESSION_MAX_AGE_SECONDS == s.SESSION_ABSOLUTE_SECONDS


def test_session_idle_cannot_exceed_absolute():
    """Idle timeout larger than absolute lifetime is nonsensical — reject.
    MAX_AGE is set equal to ABSOLUTE so the equality check passes and
    the IDLE > ABSOLUTE branch is what surfaces."""
    with pytest.raises(ValidationError, match="SESSION_IDLE_SECONDS"):
        Settings(
            **_COMMON_KWARGS,
            SESSION_ABSOLUTE_SECONDS=1800,
            SESSION_MAX_AGE_SECONDS=1800,
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
        "HCAPTCHA_SITE_KEY": "test-site-key",
        "HCAPTCHA_SECRET_KEY": "test-secret-key",
        **_PROD_CREDENTIAL_KWARGS,
    } if value == "production" else {}
    s = Settings(**_COMMON_KWARGS, APP_ENV=value, **extra)
    assert value == s.APP_ENV


@pytest.mark.parametrize("value", ["prod", "PRODUCTION", "staging", "local", ""])
def test_app_env_rejects_unknown_value(value):
    """Typos like 'prod' must fail loudly instead of silently disabling prod gates."""
    with pytest.raises(ValidationError, match="APP_ENV"):
        Settings(**_COMMON_KWARGS, APP_ENV=value)


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


# ---------------------------------------------------------------------------
# Placeholder credential rejection (URLs always; bare passwords in production)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "DATABASE_URL",
        "DATABASE_URL_SYNC",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
    ],
)
@pytest.mark.parametrize("placeholder", ["REPLACE_ME", "replace_me", "CHANGE_ME", "changeme"])
def test_connection_url_rejects_placeholder_credentials(field, placeholder):
    """A connection URL embedding REPLACE_ME / CHANGE_ME must fail at startup,
    in any environment — there is no legitimate reason for the literal
    placeholder string to ship to a running instance."""
    overrides = dict(_COMMON_KWARGS)
    overrides[field] = f"redis://:{placeholder}@host:6379/0" if "REDIS" in field or "CELERY" in field else f"postgresql://u:{placeholder}@h:5432/d"
    with pytest.raises(ValidationError, match="placeholder credential"):
        Settings(**overrides)


def test_connection_url_placeholder_rejected_even_outside_production():
    """The URL placeholder check is unconditional — APP_ENV does not gate it."""
    overrides = dict(_COMMON_KWARGS)
    overrides["REDIS_URL"] = "redis://:REPLACE_ME@redis:6379/0"
    with pytest.raises(ValidationError, match="placeholder credential"):
        Settings(**overrides, APP_ENV="development")


def _prod_kwargs(**overrides):
    """Helper: build a kwargs dict that satisfies every prod gate by default,
    so each test can override exactly the field it's exercising."""
    base = {
        **_COMMON_KWARGS,
        **_PROD_CREDENTIAL_KWARGS,
        "APP_ENV": "production",
        "COOKIE_SECURE": True,
        "TRUST_PROXY_HEADERS": True,
        "TRUSTED_PROXY_CIDRS": ["172.28.0.0/16"],
        "ALLOWED_ORIGINS": ["https://eduardoalves.online"],
        "ALLOWED_HOSTS": ["api.eduardoalves.online"],
        "HCAPTCHA_SITE_KEY": "test-site-key",
        "HCAPTCHA_SECRET_KEY": "test-secret-key",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "field", ["POSTGRES_PASSWORD", "REDIS_PASSWORD", "CELERY_REDIS_PASSWORD"]
)
def test_production_rejects_empty_credential(field):
    """Each of the three service passwords must be non-empty in production."""
    with pytest.raises(ValidationError, match=f"{field}.*must be set"):
        Settings(**_prod_kwargs(**{field: ""}))


@pytest.mark.parametrize(
    "field", ["POSTGRES_PASSWORD", "REDIS_PASSWORD", "CELERY_REDIS_PASSWORD"]
)
@pytest.mark.parametrize("placeholder", ["REPLACE_ME", "replace_me", "CHANGE_ME", "changeme"])
def test_production_rejects_placeholder_credential(field, placeholder):
    """REPLACE_ME / CHANGE_ME in any of the three service passwords must fail
    in production. Catches the case where .env was copied from .env.example
    but a password was forgotten."""
    with pytest.raises(ValidationError, match=f"{field}.*placeholder"):
        Settings(**_prod_kwargs(**{field: placeholder}))


def test_production_aggregates_multiple_credential_failures():
    """When several fields are misconfigured, the error message lists them all
    so the operator fixes the .env in one round-trip rather than re-running
    boot for each missing field."""
    with pytest.raises(ValidationError) as exc:
        Settings(**_prod_kwargs(POSTGRES_PASSWORD="", REDIS_PASSWORD="REPLACE_ME"))
    msg = str(exc.value)
    assert "POSTGRES_PASSWORD" in msg
    assert "REDIS_PASSWORD" in msg


@pytest.mark.parametrize("field", ["SESSION_TOKEN_LENGTH", "CSRF_TOKEN_LENGTH"])
@pytest.mark.parametrize("bad_value", [47, 31, 1])
def test_token_length_rejects_odd_values(field, bad_value):
    """secrets.token_hex(length // 2) silently rounds odd lengths down,
    halving entropy on the rounded byte. Reject at startup."""
    with pytest.raises(ValidationError, match="must be even"):
        Settings(**_COMMON_KWARGS, **{field: bad_value})


@pytest.mark.parametrize("field", ["SESSION_TOKEN_LENGTH", "CSRF_TOKEN_LENGTH"])
def test_token_length_rejects_too_short(field):
    """Even but short — under 16 hex chars (8 bytes) is too little entropy
    for a session/CSRF token regardless of evenness."""
    with pytest.raises(ValidationError, match=">= 16"):
        Settings(**_COMMON_KWARGS, **{field: 8})


def test_development_allows_empty_credentials():
    """The credential model validator only fires in production. Dev/test
    suites must not need to wire real-looking passwords through fixtures."""
    s = Settings(
        **_COMMON_KWARGS,
        APP_ENV="development",
        POSTGRES_PASSWORD="",
        REDIS_PASSWORD="",
        CELERY_REDIS_PASSWORD="",
    )
    assert s.APP_ENV == "development"
