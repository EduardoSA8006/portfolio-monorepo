import ipaddress

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_FRAGMENTS = ("change-me", "change_me", "example", "placeholder", "secret", "dummy")
# Narrower set used for connection URLs and credential fields where common
# words like "secret" can legitimately appear inside a real password. Matches
# the literal placeholders shipped in .env.example (REPLACE_ME, CHANGE_ME).
_PLACEHOLDER_CREDENTIAL_FRAGMENTS = ("replace_me", "change_me", "changeme", "replace-me")
_MIN_SECRET_LENGTH = 32
_VALID_APP_ENVS = frozenset({"development", "test", "production"})
_VALID_SAMESITE = frozenset({"lax", "strict", "none"})


def _validate_ip_networks(name: str, value: list[str], *, allow_empty: bool) -> list[str]:
    if not allow_empty and not value:
        raise ValueError(f"{name} must contain at least one CIDR or IP")
    if "*" in value:
        raise ValueError(f'{name} must not contain "*" — specify concrete CIDRs or IPs')
    for entry in value:
        try:
            ipaddress.ip_network(entry, strict=False)
        except ValueError as exc:
            raise ValueError(f"{name} entry {entry!r} is not a valid IP or CIDR") from exc
    return value


def _validate_secret(name: str, value: str) -> str:
    if len(value) < _MIN_SECRET_LENGTH:
        raise ValueError(f"{name} must be at least {_MIN_SECRET_LENGTH} characters")
    lower = value.lower()
    if any(frag in lower for frag in _PLACEHOLDER_FRAGMENTS):
        raise ValueError(f"{name} appears to be a placeholder — generate a real key")
    return value


def _contains_placeholder_credential(value: str) -> bool:
    lower = value.lower()
    return any(frag in lower for frag in _PLACEHOLDER_CREDENTIAL_FRAGMENTS)


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

    # POSTGRES_PASSWORD and CELERY_REDIS_PASSWORD are not consumed by the app
    # directly — they parameterize the database/redis containers via Compose,
    # and the app reads the URLs above (which already embed the credential).
    # They are declared here so the production model validator can enforce
    # presence and reject placeholders fail-closed at startup.
    POSTGRES_PASSWORD: str = ""
    CELERY_REDIS_PASSWORD: str = ""

    SESSION_TOKEN_LENGTH: int = 48
    SESSION_ROTATE_SECONDS: int = 3600
    # Absolute maximum session lifetime regardless of activity.
    SESSION_ABSOLUTE_SECONDS: int = 28800   # 8 hours
    # Idle timeout: TTL is reset to this on every authenticated request.
    # Session dies if there is no activity for this long before the absolute limit.
    SESSION_IDLE_SECONDS: int = 1800        # 30 minutes
    # Cookie max-age — browser discards the cookie after this many seconds.
    # MUST equal SESSION_ABSOLUTE_SECONDS:
    #   * MAX_AGE < ABSOLUTE → cookie disappears mid-session → spurious 401.
    #   * MAX_AGE > ABSOLUTE → server kills session while cookie persists,
    #     so the next request still sends the (now-orphaned) cookie and gets
    #     a spurious 401 — exactly the "logged out by myself" UX bug.
    # The validator enforces equality.
    SESSION_MAX_AGE_SECONDS: int = 28800
    CSRF_TOKEN_LENGTH: int = 48

    COOKIE_NAME: str = "portfolio_session"
    COOKIE_SECURE: bool = True
    # 'lax' is the sweet spot for cross-origin requests between subdomains
    # of the same registrable domain (our case: eduardoalves.online ↔
    # api.eduardoalves.online). Use 'strict' only if there is no cross-origin
    # interaction; use 'none' (with Secure=True) only for truly cross-site
    # topologies with different eTLD+1.
    COOKIE_SAMESITE: str = "lax"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Rate limiting — login endpoint
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 900   # 15 min sliding window per IP+email
    LOGIN_LOCKOUT_SECONDS: int = 1800  # 30 min global lockout per email

    # hCaptcha — required in production, optional in development
    HCAPTCHA_SITE_KEY: str = ""
    HCAPTCHA_SECRET_KEY: str = ""
    HCAPTCHA_VERIFY_URL: str = "https://api.hcaptcha.com/siteverify"
    HCAPTCHA_TIMEOUT_SECONDS: float = 3.0

    # Login rate-limit extensions (multi-IP lockout + degraded mode)
    LOGIN_LOCKOUT_DISTINCT_IPS: int = 3
    LOGIN_LOCKOUT_WINDOW_SECONDS: int = 1800
    LOGIN_MAX_ATTEMPTS_DEGRADED: int = 2

    # Per-IP spray defense (single IP, many emails). The {IP, email_hash}
    # counter alone lets a lone IP try LOGIN_MAX_ATTEMPTS against every
    # distinct email indefinitely without ever tripping a global gate.
    # This pure-IP counter caps total failures per IP across all emails:
    # crossing LOGIN_IP_MAX_FAILURES inside LOGIN_IP_WINDOW_SECONDS sets a
    # ban flag for LOGIN_IP_BAN_SECONDS — every subsequent login attempt
    # from that IP raises TooManyAttempts before any user lookup.
    LOGIN_IP_MAX_FAILURES: int = 100
    LOGIN_IP_WINDOW_SECONDS: int = 900
    LOGIN_IP_BAN_SECONDS: int = 1800

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

    # /health/ready is intentionally not public. Only callers in these CIDRs
    # may query dependency state (DB/Redis). Add proxy/LB/internal ranges in
    # deployment config as needed.
    READINESS_ALLOWED_CIDRS: list[str] = ["127.0.0.1/32", "::1/128"]

    # CORS — list of allowed origins (JSON array in env: '["https://example.com"]')
    # Never use ["*"] with allow_credentials=True — browsers will reject it.
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # TrustedHostMiddleware — rejects requests with unknown Host headers.
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # Maximum accepted request body, in bytes. The API only consumes small
    # JSON payloads (login credentials, MFA codes, etc.); 64 KiB is two
    # orders of magnitude above the largest legitimate request and three
    # orders below where a malicious upload would consume meaningful
    # memory. Traefik enforces the same limit upstream — this is the
    # in-process safety net.
    REQUEST_BODY_MAX_BYTES: int = 65536

    # ── SMTP / Email ─────────────────────────────────────────────────────
    # Master switch. With EMAIL_ENABLED=False every send_* call in
    # features.email.service is a no-op (logs at DEBUG and returns). This
    # keeps dev environments free of SMTP creds while production wires
    # them in via .env.
    EMAIL_ENABLED: bool = False
    EMAIL_SMTP_HOST: str = ""
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USERNAME: str = ""
    EMAIL_SMTP_PASSWORD: str = ""
    # STARTTLS on a plain submission port (587). Mutually exclusive with
    # EMAIL_USE_SSL — set only one.
    EMAIL_USE_TLS: bool = True
    # Implicit TLS on port 465. Some providers require this.
    EMAIL_USE_SSL: bool = False
    EMAIL_FROM_ADDRESS: str = ""
    EMAIL_FROM_NAME: str = "Portfolio Admin"
    # Per-connection timeout (seconds). The Celery task wraps each send
    # and retries on TimeoutError, so a slow MTA doesn't pin a worker.
    EMAIL_TIMEOUT_SECONDS: float = 10.0
    # Single inbox that receives security alerts (lockouts, signature
    # forgery, recovery events). Leave empty to disable alert routing
    # even when EMAIL_ENABLED=True.
    EMAIL_ADMIN_RECIPIENT: str = ""
    # When True, the audit pipeline also fires emails for security
    # events. Independent flag from EMAIL_ENABLED so we can wire SMTP
    # for transactional mail (verification codes) without spamming the
    # admin inbox during a noisy day.
    EMAIL_SECURITY_ALERTS_ENABLED: bool = False
    # Email-based 2FA code parameters. Code length is in DIGITS (Redis
    # stores the literal numeric string). TTL covers the full
    # request/respond round-trip including user typing.
    EMAIL_2FA_CODE_LENGTH: int = 6
    EMAIL_2FA_CODE_TTL_SECONDS: int = 300
    EMAIL_2FA_MAX_ATTEMPTS: int = 5

    # ── Device tracking (new-device email gate) ──────────────────────────
    # On every successful login the server checks whether a stable cookie
    # `__Host-portfolio_device` (signed by SECRET_KEY) carries a token it
    # has previously seen for this user. First sighting → fire one
    # `login_notification` email; subsequent logins from the same browser
    # are silent. Cookie is wiped → next login looks new (acceptable —
    # private mode and "clear cookies" are user-visible actions).
    DEVICE_COOKIE_NAME: str = "portfolio_device"
    DEVICE_COOKIE_TTL_DAYS: int = 365
    # Number of bytes of randomness in the device token. 16 bytes = 32
    # hex chars = 128 bits — way past brute-force territory and short
    # enough not to bloat the cookie.
    DEVICE_TOKEN_BYTES: int = 16

    @field_validator("SECRET_KEY")
    @classmethod
    def _validate_secret_key(cls, v: str) -> str:
        return _validate_secret("SECRET_KEY", v)

    @field_validator("EMAIL_PEPPER")
    @classmethod
    def _validate_email_pepper(cls, v: str) -> str:
        return _validate_secret("EMAIL_PEPPER", v)

    @field_validator("SESSION_TOKEN_LENGTH", "CSRF_TOKEN_LENGTH")
    @classmethod
    def _validate_token_length_even(cls, v: int) -> int:
        # _gen_token in token_store calls secrets.token_hex(length // 2),
        # which returns 2 hex chars per byte. An odd `length` silently
        # produces `length - 1` chars and halves entropy on the rounded-down
        # byte. Reject odd values at startup so the lengths in the rest of
        # the system match what the cookie actually carries.
        if v % 2 != 0:
            raise ValueError(
                "must be even — _gen_token uses secrets.token_hex(length // 2) "
                "and emits 2 hex chars per byte; an odd value rounds down "
                "and silently shortens the token"
            )
        if v < 16:
            raise ValueError("must be >= 16 for adequate entropy (8 bytes)")
        return v

    @field_validator(
        "DATABASE_URL",
        "DATABASE_URL_SYNC",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
    )
    @classmethod
    def _reject_placeholder_credentials_in_url(cls, v: str) -> str:
        # A URL like redis://:REPLACE_ME@redis:6379/0 means the operator copied
        # .env.example without filling in the real password. Refuse to boot in
        # any environment — there is no legitimate reason to ship the literal
        # placeholder string into a connection URL.
        if _contains_placeholder_credential(v):
            raise ValueError(
                "placeholder credential detected in connection URL — "
                "replace REPLACE_ME / CHANGE_ME with the real password"
            )
        return v

    @field_validator("TRUSTED_PROXY_CIDRS")
    @classmethod
    def _validate_trusted_proxy_cidrs(cls, v: list[str]) -> list[str]:
        return _validate_ip_networks("TRUSTED_PROXY_CIDRS", v, allow_empty=True)

    @field_validator("READINESS_ALLOWED_CIDRS")
    @classmethod
    def _validate_readiness_allowed_cidrs(cls, v: list[str]) -> list[str]:
        return _validate_ip_networks("READINESS_ALLOWED_CIDRS", v, allow_empty=False)

    @field_validator("APP_ENV")
    @classmethod
    def _validate_app_env(cls, v: str) -> str:
        if v not in _VALID_APP_ENVS:
            raise ValueError(
                f"APP_ENV must be one of {sorted(_VALID_APP_ENVS)}, got {v!r}"
            )
        return v

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def _validate_cookie_samesite(cls, v: str) -> str:
        if v not in _VALID_SAMESITE:
            raise ValueError(
                f"COOKIE_SAMESITE must be one of {sorted(_VALID_SAMESITE)} "
                f"(lowercase), got {v!r}"
            )
        return v

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def _validate_allowed_origins(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                'ALLOWED_ORIGINS must not contain "*" — wildcard is incompatible '
                "with allow_credentials=True and defeats CSRF defense via Origin"
            )
        return v

    @field_validator("ALLOWED_HOSTS")
    @classmethod
    def _validate_allowed_hosts(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                'ALLOWED_HOSTS must not contain "*" — wildcard disables the '
                "TrustedHostMiddleware defense against Host header poisoning"
            )
        return v

    @model_validator(mode="after")
    def _validate_proxy_header_dependency(self) -> "Settings":
        if self.TRUST_PROXY_HEADERS and not self.TRUSTED_PROXY_CIDRS:
            raise ValueError(
                "TRUSTED_PROXY_CIDRS must be non-empty when TRUST_PROXY_HEADERS=True"
            )
        return self

    @model_validator(mode="after")
    def _validate_production_requires_cookie_secure(self) -> "Settings":
        if self.APP_ENV == "production" and not self.COOKIE_SECURE:
            raise ValueError(
                "COOKIE_SECURE must be True in production — "
                "HTTP cookies cannot be sent over the same-site boundary securely"
            )
        return self

    @model_validator(mode="after")
    def _validate_session_lifetimes(self) -> "Settings":
        if self.SESSION_MAX_AGE_SECONDS != self.SESSION_ABSOLUTE_SECONDS:
            raise ValueError(
                "SESSION_MAX_AGE_SECONDS must equal SESSION_ABSOLUTE_SECONDS "
                f"(got {self.SESSION_MAX_AGE_SECONDS} vs {self.SESSION_ABSOLUTE_SECONDS}) — "
                "any divergence produces spurious 401s: a smaller cookie max-age "
                "expires the cookie before the server session, a larger one leaves "
                "an orphaned cookie that the browser keeps sending after the "
                "server session is gone"
            )
        if self.SESSION_IDLE_SECONDS > self.SESSION_ABSOLUTE_SECONDS:
            raise ValueError(
                "SESSION_IDLE_SECONDS must be <= SESSION_ABSOLUTE_SECONDS — "
                "idle timeout cannot outlive absolute lifetime"
            )
        return self

    @model_validator(mode="after")
    def _validate_production_requires_hcaptcha(self) -> "Settings":
        if self.APP_ENV == "production":
            if not self.HCAPTCHA_SITE_KEY or not self.HCAPTCHA_SECRET_KEY:
                raise ValueError(
                    "HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET_KEY must be set in production"
                )
        return self

    @model_validator(mode="after")
    def _validate_email_consistency(self) -> "Settings":
        """When email is on, the wiring must be complete enough to send.

        We don't peek at the network here — that's the SMTP client's job.
        We just refuse to start with a half-configured setup that would
        only fail at the first send (which might be hours after boot
        for a low-traffic alert path)."""
        if not self.EMAIL_ENABLED:
            return self
        missing: list[str] = []
        if not self.EMAIL_SMTP_HOST:
            missing.append("EMAIL_SMTP_HOST")
        if not self.EMAIL_FROM_ADDRESS:
            missing.append("EMAIL_FROM_ADDRESS")
        if self.EMAIL_USE_TLS and self.EMAIL_USE_SSL:
            raise ValueError(
                "EMAIL_USE_TLS and EMAIL_USE_SSL are mutually exclusive — "
                "STARTTLS (587) vs implicit TLS (465). Pick one."
            )
        if self.APP_ENV == "production":
            # Authenticated submission only in prod — refuse to ship
            # mail anonymously through a relay that we did not lock down.
            if not self.EMAIL_SMTP_USERNAME:
                missing.append("EMAIL_SMTP_USERNAME")
            if not self.EMAIL_SMTP_PASSWORD:
                missing.append("EMAIL_SMTP_PASSWORD")
            if self.EMAIL_SECURITY_ALERTS_ENABLED and not self.EMAIL_ADMIN_RECIPIENT:
                missing.append("EMAIL_ADMIN_RECIPIENT")
        if missing:
            raise ValueError(
                "EMAIL_ENABLED=True but the following are missing: "
                + ", ".join(missing)
            )
        return self

    @model_validator(mode="after")
    def _validate_production_credential_passwords(self) -> "Settings":
        # Production must reject empty or placeholder values for the three
        # service passwords. The URL-level validator already covers the case
        # where the placeholder is embedded in DATABASE_URL/REDIS_URL/etc.;
        # this catches the bare-password fields that don't appear in URLs
        # but still parameterize the containers (POSTGRES_PASSWORD,
        # CELERY_REDIS_PASSWORD) and reasserts REDIS_PASSWORD for symmetry.
        if self.APP_ENV != "production":
            return self
        failures: list[str] = []
        for name, value in (
            ("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD),
            ("REDIS_PASSWORD", self.REDIS_PASSWORD),
            ("CELERY_REDIS_PASSWORD", self.CELERY_REDIS_PASSWORD),
        ):
            if not value:
                failures.append(f"{name} must be set in production")
            elif _contains_placeholder_credential(value):
                failures.append(
                    f"{name} appears to be a placeholder — replace REPLACE_ME / "
                    "CHANGE_ME with the real password"
                )
        if failures:
            raise ValueError("; ".join(failures))
        return self


settings = Settings()
