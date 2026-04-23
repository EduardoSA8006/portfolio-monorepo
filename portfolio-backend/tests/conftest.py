"""
Pytest configuration shared across the suite.

Sets minimally valid env vars for modules that import `settings` at load time.
Individual tests that exercise Settings validation create their own Settings
instance with explicit values.
"""
import os

os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault(
    "EMAIL_PEPPER",
    "test-email-pepper-0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://test:test@localhost:5432/test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
