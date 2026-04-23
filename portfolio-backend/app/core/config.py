import ipaddress

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_FRAGMENTS = ("change-me", "change_me", "example", "placeholder", "secret", "dummy")
_MIN_SECRET_LENGTH = 32


def _validate_secret(name: str, value: str) -> str:
    if len(value) < _MIN_SECRET_LENGTH:
        raise ValueError(f"{name} must be at least {_MIN_SECRET_LENGTH} characters")
    lower = value.lower()
    if any(frag in lower for frag in _PLACEHOLDER_FRAGMENTS):
        raise ValueError(f"{name} appears to be a placeholder — generate a real key")
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"

    # General app secret — for future use (signing, etc.).
    # Rotating this does NOT invalidate email hashes (use EMAIL_PEPPER for that).
    SECRET_KEY: str

    # Dedicated HMAC key for email hashing.
    # Rotating EMAIL_PEPPER requires re-hashing all stored emails.
    EMAIL_PEPPER: str

    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    # Off by default — when True, SQLAlchemy logs every statement with parameters.
    # Never enable in production: email_hash and other sensitive values appear in logs.
    DB_ECHO: bool = False

    REDIS_URL: str
    REDIS_PASSWORD: str = ""

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    SESSION_TOKEN_LENGTH: int = 48
    SESSION_ROTATE_SECONDS: int = 3600
    # Absolute maximum session lifetime regardless of activity.
    SESSION_ABSOLUTE_SECONDS: int = 28800   # 8 hours
    # Idle timeout: TTL is reset to this on every authenticated request.
    # Session dies if there is no activity for this long before the absolute limit.
    SESSION_IDLE_SECONDS: int = 1800        # 30 minutes
    # Cookie max-age — browser discards the cookie after this many seconds.
    # Should be >= SESSION_ABSOLUTE_SECONDS so the cookie doesn't outlive the session.
    SESSION_MAX_AGE_SECONDS: int = 28800
    CSRF_TOKEN_LENGTH: int = 48

    COOKIE_NAME: str = "portfolio_session"
    COOKIE_SECURE: bool = True
    # "strict" is correct when frontend and API share the same registrable domain.
    # Change to "none" (with COOKIE_SECURE=True) only for cross-site topologies.
    COOKIE_SAMESITE: str = "strict"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Rate limiting — login endpoint
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 900   # 15 min sliding window per IP+email
    LOGIN_LOCKOUT_SECONDS: int = 1800  # 30 min global lockout per email

    # TOTP / MFA
    TOTP_ISSUER: str = "Portfolio Admin"
    MFA_CHALLENGE_TTL_SECONDS: int = 300  # 5 minutes between step-1 and step-2
    MFA_MAX_ATTEMPTS: int = 5             # per challenge before it's invalidated
    MFA_REPLAY_WINDOW_SECONDS: int = 90   # block reuse of the same 6-digit code

    # Set True only when the app runs behind a trusted reverse proxy
    # that injects a reliable X-Forwarded-For header.
    # When True, ProxyHeadersMiddleware is added and request.client.host
    # is automatically set to the real client IP.
    TRUST_PROXY_HEADERS: bool = False

    # CIDRs (or single IPs) that the proxy headers middleware trusts.
    # X-Forwarded-For is only honored when the direct peer falls inside one
    # of these ranges. Never use ["*"] in production — any client could then
    # spoof the header and defeat rate limiting.
    TRUSTED_PROXY_CIDRS: list[str] = ["127.0.0.1/32"]

    # CORS — list of allowed origins (JSON array in env: '["https://example.com"]')
    # Never use ["*"] with allow_credentials=True — browsers will reject it.
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # TrustedHostMiddleware — rejects requests with unknown Host headers.
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    @field_validator("SECRET_KEY")
    @classmethod
    def _validate_secret_key(cls, v: str) -> str:
        return _validate_secret("SECRET_KEY", v)

    @field_validator("EMAIL_PEPPER")
    @classmethod
    def _validate_email_pepper(cls, v: str) -> str:
        return _validate_secret("EMAIL_PEPPER", v)

    @field_validator("TRUSTED_PROXY_CIDRS")
    @classmethod
    def _validate_trusted_proxy_cidrs(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                'TRUSTED_PROXY_CIDRS must not contain "*" — '
                "specify concrete CIDRs or IPs"
            )
        for entry in v:
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as exc:
                raise ValueError(
                    f"TRUSTED_PROXY_CIDRS entry {entry!r} is not a valid IP or CIDR"
                ) from exc
        return v

    @model_validator(mode="after")
    def _validate_proxy_header_dependency(self) -> "Settings":
        if self.TRUST_PROXY_HEADERS and not self.TRUSTED_PROXY_CIDRS:
            raise ValueError(
                "TRUSTED_PROXY_CIDRS must be non-empty when TRUST_PROXY_HEADERS=True"
            )
        return self


settings = Settings()
