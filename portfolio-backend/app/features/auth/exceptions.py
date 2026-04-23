from app.core.exceptions import AppException


class InvalidCredentialsError(AppException):
    status_code = 401
    detail = "Invalid email or password"
    code = "AUTH_INVALID_CREDENTIALS"


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
