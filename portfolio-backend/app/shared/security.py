import hashlib
import hmac
import re

import bcrypt

from app.core.config import settings

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]).{8,}$"
)


def hash_email(email: str) -> str:
    """HMAC-SHA256 deterministic hash for email privacy in the database."""
    normalized = email.lower().strip()
    return hmac.new(
        settings.SECRET_KEY.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


def _pre_hash(plain: str) -> bytes:
    """SHA256 pre-hash removes bcrypt's 72-byte limit while preserving entropy."""
    return hashlib.sha256(plain.encode()).digest()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_pre_hash(plain), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_pre_hash(plain), hashed.encode())


def is_strong_password(password: str) -> bool:
    return bool(_PASSWORD_RE.match(password))
