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
