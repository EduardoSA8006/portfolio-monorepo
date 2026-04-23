import base64
import hashlib
import hmac
import re

import pyotp
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

_ARGON2_TIME_COST = 3
_ARGON2_MEMORY_COST_KIB = 65536
_ARGON2_PARALLELISM = 4
_ARGON2_HASH_LEN = 32
_ARGON2_SALT_LEN = 16

_ph = PasswordHasher(
    time_cost=_ARGON2_TIME_COST,
    memory_cost=_ARGON2_MEMORY_COST_KIB,
    parallelism=_ARGON2_PARALLELISM,
    hash_len=_ARGON2_HASH_LEN,
    salt_len=_ARGON2_SALT_LEN,
    type=Type.ID,
)

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]).{8,}$"
)


def hash_email(email: str) -> str:
    """HMAC-SHA256 deterministic hash for email privacy in the database.

    Uses EMAIL_PEPPER (not SECRET_KEY) so the two can be rotated independently.
    Rotating EMAIL_PEPPER invalidates all stored email hashes and requires a migration.
    """
    normalized = email.lower().strip()
    return hmac.new(
        settings.EMAIL_PEPPER.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    try:
        return _ph.check_needs_rehash(hashed)
    except InvalidHashError:
        return False


def is_strong_password(password: str) -> bool:
    return bool(_PASSWORD_RE.match(password))


# -- TOTP / MFA --------------------------------------------------------------

# HKDF-derived Fernet key. Deterministic from SECRET_KEY, so restarts don't
# lose the ability to decrypt stored secrets. Rotating SECRET_KEY requires
# re-encrypting every stored totp_secret_enc.
def _totp_fernet() -> Fernet:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"portfolio-totp-v1",
        info=b"totp-secret-encryption",
    )
    raw = hkdf.derive(settings.SECRET_KEY.encode())
    return Fernet(base64.urlsafe_b64encode(raw))


def generate_totp_secret() -> str:
    """Generate a fresh base32 TOTP secret (RFC 6238)."""
    return pyotp.random_base32()


def encrypt_totp_secret(plaintext: str) -> str:
    """Encrypt a base32 TOTP secret for storage at rest."""
    return _totp_fernet().encrypt(plaintext.encode()).decode()


def decrypt_totp_secret(ciphertext: str) -> str | None:
    """Decrypt a stored TOTP secret. Returns None on tamper/invalid token."""
    try:
        return _totp_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code with ±1 window tolerance (clock skew).

    Replay protection (blocking reuse of the same code) is caller responsibility.
    """
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def totp_provisioning_uri(secret: str, account_name: str) -> str:
    """Build the otpauth:// URI for QR-code enrollment."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=account_name,
        issuer_name=settings.TOTP_ISSUER,
    )
