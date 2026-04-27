from app.core.exceptions import AppException


class InvalidCredentialsError(AppException):
    status_code = 401
    detail = "Invalid email or password"
    code = "AUTH_INVALID_CREDENTIALS"

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        captcha_required: bool = False,
    ) -> None:
        super().__init__(
            detail=detail,
            code=code,
            extra={"captcha_required": captcha_required},
        )


class AccountDisabledError(AppException):
    status_code = 403
    detail = "Account is disabled"
    code = "AUTH_ACCOUNT_DISABLED"


class SessionNotFoundError(AppException):
    status_code = 401
    detail = "Session not found or expired"
    code = "AUTH_SESSION_NOT_FOUND"


class SessionExpiredError(AppException):
    status_code = 401
    detail = "Session has expired"
    code = "AUTH_SESSION_EXPIRED"


class CSRFValidationError(AppException):
    status_code = 403
    detail = "CSRF token validation failed"
    code = "AUTH_CSRF_INVALID"


class TooManyAttemptsError(AppException):
    status_code = 429
    detail = "Too many login attempts — try again later"
    code = "AUTH_TOO_MANY_ATTEMPTS"


class MFAChallengeInvalidError(AppException):
    status_code = 401
    detail = "MFA challenge is invalid or expired"
    code = "AUTH_MFA_CHALLENGE_INVALID"


class TOTPInvalidError(AppException):
    status_code = 401
    detail = "Invalid authentication code"
    code = "AUTH_TOTP_INVALID"


class TOTPAlreadyEnabledError(AppException):
    status_code = 409
    detail = "TOTP is already enabled for this account"
    code = "AUTH_TOTP_ALREADY_ENABLED"


class TOTPNotEnabledError(AppException):
    status_code = 409
    detail = "TOTP is not enabled for this account"
    code = "AUTH_TOTP_NOT_ENABLED"


class TOTPEnrollmentMissingError(AppException):
    status_code = 409
    detail = "No pending TOTP enrollment for this account"
    code = "AUTH_TOTP_ENROLLMENT_MISSING"


class CaptchaRequiredError(AppException):
    status_code = 401
    detail = "Captcha verification required"
    code = "AUTH_CAPTCHA_REQUIRED"


class CaptchaInvalidError(AppException):
    status_code = 401
    detail = "Captcha verification failed"
    code = "AUTH_CAPTCHA_INVALID"


# ── Email-based 2FA ─────────────────────────────────────────────────────────


class EmailCodeInvalidError(AppException):
    """The submitted email-2FA code did not match (or attempt budget hit).

    Same status as TOTPInvalidError so the frontend treats both MFA
    methods symmetrically — generic 'wrong code' UI."""

    status_code = 401
    detail = "Invalid verification code"
    code = "AUTH_EMAIL_CODE_INVALID"


class Email2FAUnavailableError(AppException):
    """Caller asked for a path that needs SMTP, but EMAIL_ENABLED is off
    OR the user has no email on file. Distinct status (409) so the
    frontend can show 'check your config' instead of 'try again'."""

    status_code = 409
    detail = "Email 2FA is not available — SMTP not configured or address missing"
    code = "AUTH_EMAIL_2FA_UNAVAILABLE"


class Email2FAAlreadyEnabledError(AppException):
    status_code = 409
    detail = "Email 2FA is already enabled for this account"
    code = "AUTH_EMAIL_2FA_ALREADY_ENABLED"


class Email2FANotEnabledError(AppException):
    status_code = 409
    detail = "Email 2FA is not enabled for this account"
    code = "AUTH_EMAIL_2FA_NOT_ENABLED"
