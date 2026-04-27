from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    # RFC 5321 caps addresses at 254 characters — 200 would reject valid emails.
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8)
    captcha_token: str | None = Field(default=None, max_length=4096)


class LoginResponse(BaseModel):
    """
    Response from POST /auth/login.

    - status="ok"            → session established, csrf_token returned, cookie set.
    - status="mfa_required"  → password was correct, second factor required.
                                * mfa_method="totp" → call /auth/login/mfa
                                * mfa_method="email" → call /auth/login/email-code/verify
                                  (a code has already been emailed)
    """
    status: Literal["ok", "mfa_required"] = "ok"
    csrf_token: str | None = None
    mfa_challenge_token: str | None = None
    mfa_method: Literal["totp", "email"] | None = None
    message: str = "Login successful"


class MFAVerifyRequest(BaseModel):
    mfa_challenge_token: str = Field(..., min_length=16, max_length=128)
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be 6 digits")
        return v


class MFAVerifyResponse(BaseModel):
    csrf_token: str
    message: str = "Login successful"


class TOTPEnrollResponse(BaseModel):
    """
    Returned by POST /auth/totp/enroll.

    The secret and provisioning_uri are shown ONCE and must be entered into an
    authenticator app (or rendered as a QR from provisioning_uri). Enrollment
    is not complete until POST /auth/totp/confirm succeeds.
    """
    secret: str
    provisioning_uri: str


class TOTPConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be 6 digits")
        return v


class TOTPDisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be 6 digits")
        return v


class EmailCodeVerifyRequest(BaseModel):
    """Body for POST /auth/login/email-code/verify."""
    mfa_challenge_token: str = Field(..., min_length=16, max_length=128)
    code: str = Field(..., min_length=4, max_length=12)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be digits")
        return v


class EmailCodeVerifyResponse(BaseModel):
    csrf_token: str
    message: str = "Login successful"


class EmailCodeResendRequest(BaseModel):
    """Body for POST /auth/login/email-code/resend."""
    mfa_challenge_token: str = Field(..., min_length=16, max_length=128)


class Email2FADisableRequest(BaseModel):
    """Body for POST /auth/email-2fa/disable.

    Reuses the live email code from /email-2fa/disable/request — same
    proof-of-possession ceremony as the TOTP disable endpoint, but the
    code arrives over email instead of from an authenticator app.
    """
    code: str = Field(..., min_length=4, max_length=12)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be digits")
        return v


class AuthConfigResponse(BaseModel):
    """Public config needed by the admin login frontend."""
    hcaptcha_site_key: str
    # Whether the server has SMTP wired AT ALL — drives the
    # 'enable email 2FA' option in the admin UI. Per-user enrollment
    # state is fetched from the authenticated profile endpoint, not
    # from this public config.
    email_2fa_available: bool = False
