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


class TooManySessionsError(AppException):
    status_code = 429
    detail = "Too many active sessions"
    code = "AUTH_TOO_MANY_SESSIONS"
