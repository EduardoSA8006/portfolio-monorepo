from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    # RFC 5321 caps addresses at 254 characters — 200 would reject valid emails.
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    """
    Response from POST /auth/login.

    - status="ok"            → session established, csrf_token returned, cookie set.
    - status="mfa_required"  → password was correct but TOTP is enabled.
                                Call /auth/login/mfa with the mfa_challenge_token.
    """
    status: Literal["ok", "mfa_required"] = "ok"
    csrf_token: str | None = None
    mfa_challenge_token: str | None = None
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
