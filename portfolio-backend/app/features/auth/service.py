"""
Auth service — business logic layer.

Coordinates repository (DB), token_store (Redis), rate_limit, and mfa_store.
Does not know about HTTP: no Request, Response, or cookies here.
"""
import logging
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth import mfa_store, rate_limit, repository, token_store
from app.features.auth.exceptions import (
    InvalidCredentialsError,
    MFAChallengeInvalidError,
    TOTPAlreadyEnabledError,
    TOTPEnrollmentMissingError,
    TOTPInvalidError,
    TOTPNotEnabledError,
)
from app.features.auth.models import AuthEvent
from app.shared.security import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    hash_email,
    hash_password,
    totp_provisioning_uri,
    verify_password,
    verify_totp_code,
)

logger = logging.getLogger(__name__)

# Precomputed at startup to prevent user-enumeration via response-timing attacks.
# An attacker probing for valid emails sees identical latency regardless of result.
_DUMMY_HASH: str = hash_password("__timing_sentinel__")


@dataclass(frozen=True)
class LoginResult:
    """
    Return type for service.login.

    Either a real session (session_token, csrf_token set) OR an MFA challenge
    (mfa_challenge_token set). Never both.
    """
    session_token: str | None = None
    csrf_token: str | None = None
    mfa_challenge_token: str | None = None

    @property
    def mfa_required(self) -> bool:
        return self.mfa_challenge_token is not None


async def _record_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: str | None = None,
    reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an audit event. Fire-and-forget — never raises."""
    try:
        event = AuthEvent(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if user_id else None,
            event_type=event_type,
            reason=reason,
            ip=ip,
            user_agent=user_agent[:500] if user_agent else None,
        )
        db.add(event)
        await db.commit()
    except Exception:
        logger.exception("audit.write_failed", extra={"event_type": event_type})


async def login(
    email: str,
    password: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
) -> LoginResult:
    """
    Step 1 of login: validate email + password.

    If the account has TOTP enabled, return an MFA challenge instead of a session.
    The caller must exchange the challenge for a session via verify_mfa().

    External response is always InvalidCredentialsError regardless of the actual
    failure reason (user-enumeration defence).
    """
    email_hash = hash_email(email)

    await rate_limit.check_login_rate(redis, client_ip, email_hash)

    user = await repository.get_by_email_hash(email_hash, db)

    if user is None:
        verify_password(password, _DUMMY_HASH)
        logger.info("login.failed", extra={"reason": "user_not_found", "email_hash": email_hash, "ip": client_ip})
        await _record_event(db, event_type="login_failed", reason="user_not_found", ip=client_ip, user_agent=user_agent)
        raise InvalidCredentialsError()

    if not user.is_active:
        verify_password(password, _DUMMY_HASH)
        logger.info("login.failed", extra={"reason": "account_disabled", "user_id": str(user.id), "ip": client_ip})
        await _record_event(db, event_type="login_failed", user_id=str(user.id), reason="account_disabled", ip=client_ip, user_agent=user_agent)
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        logger.info("login.failed", extra={"reason": "bad_password", "user_id": str(user.id), "ip": client_ip})
        await _record_event(db, event_type="login_failed", user_id=str(user.id), reason="bad_password", ip=client_ip, user_agent=user_agent)
        raise InvalidCredentialsError()

    await rate_limit.reset_login_rate(redis, client_ip, email_hash)

    if user.totp_enabled:
        challenge = await mfa_store.create_challenge(redis, str(user.id))
        logger.info("login.mfa_required", extra={"user_id": str(user.id), "ip": client_ip})
        await _record_event(db, event_type="login_mfa_challenge", user_id=str(user.id), ip=client_ip, user_agent=user_agent)
        return LoginResult(mfa_challenge_token=challenge)

    session_token, csrf_token = await token_store.create_session(redis, str(user.id))
    logger.info("login.success", extra={"user_id": str(user.id), "ip": client_ip})
    await _record_event(db, event_type="login_success", user_id=str(user.id), ip=client_ip, user_agent=user_agent)
    return LoginResult(session_token=session_token, csrf_token=csrf_token)


async def verify_mfa(
    challenge_token: str,
    code: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """
    Step 2 of login: exchange an MFA challenge + TOTP code for a real session.

    Returns (session_token, csrf_token).
    Raises MFAChallengeInvalidError or TOTPInvalidError.
    """
    try:
        user_id = await mfa_store.consume_attempt(redis, challenge_token)
    except mfa_store.ChallengeInvalidError as exc:
        logger.info("login.mfa_challenge_invalid", extra={"ip": client_ip})
        await _record_event(db, event_type="login_mfa_failed", reason="challenge_invalid", ip=client_ip, user_agent=user_agent)
        raise MFAChallengeInvalidError() from exc

    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None or not user.is_active or not user.totp_enabled or not user.totp_secret_enc:
        # Account state changed between step 1 and step 2 — fail closed.
        await mfa_store.revoke_challenge(redis, challenge_token)
        await _record_event(db, event_type="login_mfa_failed", user_id=user_id, reason="state_changed", ip=client_ip, user_agent=user_agent)
        raise MFAChallengeInvalidError()

    secret = decrypt_totp_secret(user.totp_secret_enc)
    if secret is None:
        # Decrypt failure = SECRET_KEY rotated or storage corruption. Fail closed.
        logger.error("totp.decrypt_failed", extra={"user_id": user_id})
        await mfa_store.revoke_challenge(redis, challenge_token)
        await _record_event(db, event_type="login_mfa_failed", user_id=user_id, reason="decrypt_failed", ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    if not verify_totp_code(secret, code):
        logger.info("login.mfa_bad_code", extra={"user_id": user_id, "ip": client_ip})
        await _record_event(db, event_type="login_mfa_failed", user_id=user_id, reason="bad_code", ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    # Replay guard — the same 6-digit code can't be reused within its validity window.
    if not await mfa_store.claim_code(redis, user_id, code):
        logger.info("login.mfa_replay", extra={"user_id": user_id, "ip": client_ip})
        await _record_event(db, event_type="login_mfa_failed", user_id=user_id, reason="replay", ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    await mfa_store.revoke_challenge(redis, challenge_token)
    session_token, csrf_token = await token_store.create_session(redis, user_id)
    logger.info("login.success", extra={"user_id": user_id, "ip": client_ip, "mfa": True})
    await _record_event(db, event_type="login_success", user_id=user_id, reason="mfa", ip=client_ip, user_agent=user_agent)
    return session_token, csrf_token


async def logout(
    session_token: str,
    user_id: str,
    db: AsyncSession,
    redis: Redis,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Revoke the current session."""
    await token_store.revoke_session(redis, session_token)
    await _record_event(db, event_type="logout", user_id=user_id, ip=client_ip, user_agent=user_agent)


async def clear_all_sessions(
    user_id: str,
    db: AsyncSession,
    redis: Redis,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Revoke every active session for the given user."""
    await token_store.clear_user_sessions(redis, user_id)
    await _record_event(db, event_type="sessions_cleared", user_id=user_id, ip=client_ip, user_agent=user_agent)


# -- TOTP enrollment --------------------------------------------------------

async def enroll_totp(
    user_id: str,
    db: AsyncSession,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """
    Begin TOTP enrollment for an authenticated user.

    Writes an encrypted secret to the DB with totp_enabled=False (pending).
    Returns (plaintext_secret, provisioning_uri) — shown to the user exactly once.
    Idempotent: if enrollment is already pending (not confirmed), returns a new
    secret and overwrites the pending one.
    """
    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None:
        raise InvalidCredentialsError()
    if user.totp_enabled:
        raise TOTPAlreadyEnabledError()

    secret = generate_totp_secret()
    user.totp_secret_enc = encrypt_totp_secret(secret)
    # Use email_hash as the account label — we don't store plaintext email.
    uri = totp_provisioning_uri(secret, account_name=f"admin:{user.email_hash[:12]}")
    await db.commit()
    await _record_event(db, event_type="totp_enroll_started", user_id=user_id, ip=client_ip, user_agent=user_agent)
    return secret, uri


async def confirm_totp(
    user_id: str,
    code: str,
    db: AsyncSession,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Confirm a pending TOTP enrollment by verifying a code generated from the
    pending secret. Only then is totp_enabled flipped to True.
    """
    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None:
        raise InvalidCredentialsError()
    if user.totp_enabled:
        raise TOTPAlreadyEnabledError()
    if not user.totp_secret_enc:
        raise TOTPEnrollmentMissingError()

    secret = decrypt_totp_secret(user.totp_secret_enc)
    if secret is None or not verify_totp_code(secret, code):
        await _record_event(db, event_type="totp_confirm_failed", user_id=user_id, ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    user.totp_enabled = True
    await db.commit()
    await _record_event(db, event_type="totp_enabled", user_id=user_id, ip=client_ip, user_agent=user_agent)


async def disable_totp(
    user_id: str,
    code: str,
    db: AsyncSession,
    redis: Redis,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Disable TOTP. Requires a valid current TOTP code as proof of possession.

    Also revokes all other sessions for the user — a disabled second factor
    means we want no stale sessions surviving the downgrade.
    """
    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None:
        raise InvalidCredentialsError()
    if not user.totp_enabled or not user.totp_secret_enc:
        raise TOTPNotEnabledError()

    secret = decrypt_totp_secret(user.totp_secret_enc)
    if secret is None or not verify_totp_code(secret, code):
        await _record_event(db, event_type="totp_disable_failed", user_id=user_id, ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    user.totp_enabled = False
    user.totp_secret_enc = None
    await db.commit()
    await token_store.clear_user_sessions(redis, user_id)
    await _record_event(db, event_type="totp_disabled", user_id=user_id, ip=client_ip, user_agent=user_agent)
