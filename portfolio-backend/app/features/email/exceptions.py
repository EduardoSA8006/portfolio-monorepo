"""
Email-feature exceptions.

These are NOT HTTP exceptions — sending mail is out-of-band work
(triggered from request handlers but executed inside Celery), so the
exception surfaces are about *delivery* and *configuration*, not about
HTTP responses.
"""


class EmailError(Exception):
    """Base for the email feature."""


class EmailDisabledError(EmailError):
    """Raised when a caller asks for an action that requires
    EMAIL_ENABLED=True but the feature is off."""


class EmailDeliveryError(EmailError):
    """SMTP exchange failed. The Celery task catches and retries this;
    callers in the request path never see it directly."""


class EmailCodeInvalidError(EmailError):
    """Email-based 2FA code missing, expired, mismatched, or over the
    per-challenge attempt budget. Mirrors mfa_store's
    ChallengeInvalidError so callers can treat both the same."""
