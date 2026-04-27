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

from app.core.config import settings
from app.features.auth import (
    audit,
    captcha,
    devices,
    mfa_store,
    rate_limit,
    repository,
    token_store,
)
from app.features.auth.exceptions import (
    CaptchaInvalidError,
    CaptchaRequiredError,
    Email2FAAlreadyEnabledError,
    Email2FANotEnabledError,
    Email2FAUnavailableError,
    EmailCodeInvalidError,
    InvalidCredentialsError,
    MFAChallengeInvalidError,
    TOTPAlreadyEnabledError,
    TOTPEnrollmentMissingError,
    TOTPInvalidError,
    TOTPNotEnabledError,
)
from app.features.email import code_store as email_code_store
from app.features.email import service as email_service
from app.features.email.exceptions import EmailCodeInvalidError as EmailCodeStoreInvalid
from app.shared.security import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    hash_email,
    hash_password,
    password_needs_rehash,
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

    `new_device_token`, when present, is a freshly minted device-cookie
    token the router must Set-Cookie on the response. None means the
    incoming device cookie was reused — TTL was refreshed in Redis but
    no new cookie value needs to ride back to the browser.
    """
    session_token: str | None = None
    csrf_token: str | None = None
    mfa_challenge_token: str | None = None
    # "totp" or "email" — tells the router/frontend which verify
    # endpoint to call after an mfa_required response.
    mfa_method: str | None = None
    new_device_token: str | None = None

    @property
    def mfa_required(self) -> bool:
        return self.mfa_challenge_token is not None


@dataclass(frozen=True)
class MFAVerifyResult:
    """Return type for service.verify_mfa.

    Carries the same `new_device_token` slot as LoginResult so the
    router treats both endpoints uniformly. In practice verify_mfa
    almost never produces a new token — the device cookie was already
    written on /login. The slot is here for defense-in-depth: if the
    router ever calls verify_mfa standalone without /login having
    Set-Cookie'd, the server still mints + writes a token."""
    session_token: str
    csrf_token: str
    new_device_token: str | None = None


async def _maybe_rehash_password_hash(
    user,
    password: str,
    db: AsyncSession,
) -> None:
    if not password_needs_rehash(user.password_hash):
        return

    user.password_hash = hash_password(password)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("login.password_rehash_failed", extra={"user_id": str(user.id)})


async def _maybe_backfill_email(user, email: str, db: AsyncSession) -> None:
    """Persist the plain email on first successful login for accounts
    that predate the d5a1e3f0 migration.

    Skipped on every subsequent login. Failure is non-fatal — the
    transactional email path will fall back to the no-op branch when
    `user.email is None`, and we'll try again on the next sign-in."""
    if user.email == email:
        return
    user.email = email
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("login.email_backfill_failed", extra={"user_id": str(user.id)})


async def login(
    email: str,
    password: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
    captcha_token: str | None = None,
    device_cookie_value: str | None = None,
) -> LoginResult:
    """
    Step 1 of login: validate email + password with captcha gate on repeat attempts.

    Flow:
    1. check_login_rate — raises TooManyAttemptsError if global lockout active
    2. If captcha_required and not degraded -> captcha.verify must return ok
    3. Look up user, compare password (constant-time via _DUMMY_HASH)
    4. On success: reset rate_limit; (if TOTP) return MFA challenge else session
    5. On password failure: register_login_failure (NOT on captcha failures)
    """
    email_hash = hash_email(email)

    rate_state = await rate_limit.check_login_rate(redis, client_ip, email_hash)

    if rate_state.captcha_required and not rate_state.degraded:
        verify_result = await captcha.verify(captcha_token, client_ip, redis)
        if not verify_result.ok:
            if captcha_token is None or captcha_token == "":
                await audit.record_event(
                    event_type="login_failed",
                    reason="captcha_required",
                    ip=client_ip,
                    user_agent=user_agent,
                )
                raise CaptchaRequiredError()
            if verify_result.provider_available:
                await audit.record_event(
                    event_type="login_failed",
                    reason="captcha_invalid",
                    ip=client_ip,
                    user_agent=user_agent,
                )
                raise CaptchaInvalidError()
            # Token supplied but provider became unavailable during verify —
            # degraded flag is now set; continue as if captcha passed.

    user = await repository.get_by_email_hash(email_hash, db)

    if user is None:
        verify_password(password, _DUMMY_HASH)
        failure = await rate_limit.register_login_failure(redis, client_ip, email_hash)
        logger.info(
            "login.failed",
            extra={"reason": "user_not_found", "email_hash": email_hash, "ip": client_ip},
        )
        await audit.record_event(
            event_type="login_failed",
            reason="user_not_found",
            ip=client_ip,
            user_agent=user_agent,
        )
        if failure.lockout_triggered:
            await audit.record_event(
                event_type="login_lockout_triggered",
                ip=client_ip,
                user_agent=user_agent,
            )
        raise InvalidCredentialsError(captcha_required=True)

    if not user.is_active:
        verify_password(password, _DUMMY_HASH)
        failure = await rate_limit.register_login_failure(redis, client_ip, email_hash)
        logger.info(
            "login.failed",
            extra={"reason": "account_disabled", "user_id": str(user.id), "ip": client_ip},
        )
        await audit.record_event(
            event_type="login_failed",
            user_id=str(user.id),
            reason="account_disabled",
            ip=client_ip,
            user_agent=user_agent,
        )
        if failure.lockout_triggered:
            await audit.record_event(
                event_type="login_lockout_triggered",
                user_id=str(user.id),
                ip=client_ip,
                user_agent=user_agent,
            )
        raise InvalidCredentialsError(captcha_required=True)

    if not verify_password(password, user.password_hash):
        failure = await rate_limit.register_login_failure(redis, client_ip, email_hash)
        logger.info(
            "login.failed",
            extra={"reason": "bad_password", "user_id": str(user.id), "ip": client_ip},
        )
        await audit.record_event(
            event_type="login_failed",
            user_id=str(user.id),
            reason="bad_password",
            ip=client_ip,
            user_agent=user_agent,
        )
        if failure.lockout_triggered:
            await audit.record_event(
                event_type="login_lockout_triggered",
                user_id=str(user.id),
                ip=client_ip,
                user_agent=user_agent,
            )
        raise InvalidCredentialsError(captcha_required=True)

    await _maybe_rehash_password_hash(user, password, db)
    await _maybe_backfill_email(user, email, db)
    await rate_limit.reset_login_rate(redis, client_ip, email_hash)

    # Device tracking — gate the login_notification email on first
    # sighting per (user, browser). The decision (is_new_device) flows
    # downstream: into the MFA challenge metadata if a second factor is
    # required, OR into the immediate email send on the no-MFA path.
    is_new_device, new_device_token = await devices.track_login(
        redis=redis,
        user_id=str(user.id),
        device_cookie_value=device_cookie_value,
    )

    # Method precedence: TOTP wins when both are enabled. TOTP needs no
    # SMTP round-trip at login time and has a stronger phishing-resistance
    # story (the code is bound to the device that holds the secret).
    if user.totp_enabled:
        challenge = await mfa_store.create_challenge(
            redis,
            str(user.id),
            method="totp",
            email=email,
            client_ip=client_ip,
            user_agent=user_agent,
            is_new_device=is_new_device,
        )
        logger.info("login.mfa_required", extra={"user_id": str(user.id), "ip": client_ip, "method": "totp"})
        await audit.record_event(
            event_type="login_mfa_challenge",
            user_id=str(user.id),
            reason="totp",
            ip=client_ip,
            user_agent=user_agent,
        )
        return LoginResult(
            mfa_challenge_token=challenge,
            mfa_method="totp",
            new_device_token=new_device_token,
        )

    if user.email_2fa_enabled:
        # The user opted into email 2FA; mint a code, send it, return a
        # challenge keyed to the email path. The verify endpoint
        # consumes this challenge AND the matching code before issuing
        # the session.
        challenge = await mfa_store.create_challenge(
            redis,
            str(user.id),
            method="email",
            email=email,
            client_ip=client_ip,
            user_agent=user_agent,
            is_new_device=is_new_device,
        )
        await email_service.send_two_factor_code(
            redis=redis,
            user_id=str(user.id),
            name=user.name,
            to=email,
        )
        logger.info(
            "login.mfa_required",
            extra={"user_id": str(user.id), "ip": client_ip, "method": "email"},
        )
        await audit.record_event(
            event_type="login_mfa_challenge",
            user_id=str(user.id),
            reason="email",
            ip=client_ip,
            user_agent=user_agent,
        )
        return LoginResult(
            mfa_challenge_token=challenge,
            mfa_method="email",
            new_device_token=new_device_token,
        )

    session_token, csrf_token = await token_store.create_session(redis, str(user.id))
    logger.info("login.success", extra={"user_id": str(user.id), "ip": client_ip})
    await audit.record_event(
        event_type="login_success",
        user_id=str(user.id),
        ip=client_ip,
        user_agent=user_agent,
    )
    if is_new_device:
        # Fire-and-forget — never block the login response on email.
        email_service.send_login_notification(
            name=user.name,
            to=email,
            ip=client_ip,
            user_agent=user_agent,
        )
    return LoginResult(
        session_token=session_token,
        csrf_token=csrf_token,
        new_device_token=new_device_token,
    )


async def verify_mfa(
    challenge_token: str,
    code: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
) -> MFAVerifyResult:
    """
    Step 2 of login: exchange an MFA challenge + TOTP code for a real session.

    Returns MFAVerifyResult.
    Raises MFAChallengeInvalidError or TOTPInvalidError.
    """
    try:
        user_id = await mfa_store.consume_attempt(redis, challenge_token)
    except mfa_store.ChallengeInvalidError as exc:
        logger.info("login.mfa_challenge_invalid", extra={"ip": client_ip})
        await audit.record_event(event_type="login_mfa_failed", reason="challenge_invalid", ip=client_ip, user_agent=user_agent)
        raise MFAChallengeInvalidError() from exc

    # Cross-method spend guard: an `email`-method challenge MUST NOT be
    # consumed by the TOTP verify endpoint. Same flag prevents the
    # mirror direction in verify_email_code.
    metadata_for_method = await mfa_store.get_challenge_metadata(redis, challenge_token)
    if metadata_for_method.get("method", "totp") != "totp":
        await mfa_store.revoke_challenge(redis, challenge_token)
        await audit.record_event(
            event_type="login_mfa_failed",
            user_id=user_id,
            reason="method_mismatch",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise MFAChallengeInvalidError()

    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None or not user.is_active or not user.totp_enabled or not user.totp_secret_enc:
        # Account state changed between step 1 and step 2 — fail closed.
        await mfa_store.revoke_challenge(redis, challenge_token)
        await audit.record_event(event_type="login_mfa_failed", user_id=user_id, reason="state_changed", ip=client_ip, user_agent=user_agent)
        raise MFAChallengeInvalidError()

    secret = decrypt_totp_secret(user.totp_secret_enc)
    if secret is None:
        # Decrypt failure = SECRET_KEY rotated or storage corruption. Fail closed.
        logger.error("totp.decrypt_failed", extra={"user_id": user_id})
        await mfa_store.revoke_challenge(redis, challenge_token)
        await audit.record_event(event_type="login_mfa_failed", user_id=user_id, reason="decrypt_failed", ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    if not verify_totp_code(secret, code):
        logger.info("login.mfa_bad_code", extra={"user_id": user_id, "ip": client_ip})
        await audit.record_event(event_type="login_mfa_failed", user_id=user_id, reason="bad_code", ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    # Replay guard — the same 6-digit code can't be reused within its validity window.
    if not await mfa_store.claim_code(redis, user_id, code):
        logger.info("login.mfa_replay", extra={"user_id": user_id, "ip": client_ip})
        await audit.record_event(event_type="login_mfa_failed", user_id=user_id, reason="replay", ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    # Pull the device + email metadata BEFORE revoking the challenge —
    # revoke wipes the hash. Fall back gracefully if the challenge was
    # created without metadata (e.g., older code path or test fixture).
    metadata = await mfa_store.get_challenge_metadata(redis, challenge_token)
    is_new_device = metadata.get("is_new_device") == "1"
    notify_email = metadata.get("email")
    notify_ip = metadata.get("client_ip") or client_ip
    notify_ua = metadata.get("user_agent") or user_agent

    await mfa_store.revoke_challenge(redis, challenge_token)
    session_token, csrf_token = await token_store.create_session(redis, user_id)
    logger.info("login.success", extra={"user_id": user_id, "ip": client_ip, "mfa": True})
    await audit.record_event(event_type="login_success", user_id=user_id, reason="mfa", ip=client_ip, user_agent=user_agent)

    if is_new_device and notify_email:
        # The device cookie was already Set-Cookie'd on the /login
        # response; we just need to notify. Email is fire-and-forget.
        email_service.send_login_notification(
            name=user.name,
            to=notify_email,
            ip=notify_ip,
            user_agent=notify_ua,
        )

    return MFAVerifyResult(session_token=session_token, csrf_token=csrf_token)


# -- Email-based 2FA ---------------------------------------------------------


async def verify_email_code(
    challenge_token: str,
    code: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
) -> MFAVerifyResult:
    """
    Step 2 of the email-2FA login: exchange a challenge + 6-digit code
    (the one we emailed in step 1) for a real session.

    Mirrors verify_mfa for the TOTP path:
      * Consumes the challenge atomically (attempt budget).
      * Refuses challenges issued under method != "email" (no
        cross-method spending).
      * Looks up the user, refuses if the account toggled state
        between issue and verify.
      * Validates the code via code_store. The code itself is
        one-shot — code_store deletes on success and on attempt
        budget exhaustion.
      * Fires login_notification on first sighting from this device.
    """
    try:
        user_id = await mfa_store.consume_attempt(redis, challenge_token)
    except mfa_store.ChallengeInvalidError as exc:
        logger.info("login.email_challenge_invalid", extra={"ip": client_ip})
        await audit.record_event(
            event_type="login_email_code_failed",
            reason="challenge_invalid",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise MFAChallengeInvalidError() from exc

    metadata = await mfa_store.get_challenge_metadata(redis, challenge_token)
    if metadata.get("method") != "email":
        await mfa_store.revoke_challenge(redis, challenge_token)
        await audit.record_event(
            event_type="login_email_code_failed",
            user_id=user_id,
            reason="method_mismatch",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise MFAChallengeInvalidError()

    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None or not user.is_active or not user.email_2fa_enabled:
        # Account state changed between step 1 and step 2 — fail closed.
        await mfa_store.revoke_challenge(redis, challenge_token)
        await audit.record_event(
            event_type="login_email_code_failed",
            user_id=user_id,
            reason="state_changed",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise MFAChallengeInvalidError()

    try:
        await email_code_store.verify_code(redis, user_id, code)
    except EmailCodeStoreInvalid as exc:
        logger.info(
            "login.email_code_bad",
            extra={"user_id": user_id, "ip": client_ip, "detail": str(exc)},
        )
        await audit.record_event(
            event_type="login_email_code_failed",
            user_id=user_id,
            reason="bad_code",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise EmailCodeInvalidError() from exc

    notify_email = metadata.get("email")
    notify_ip = metadata.get("client_ip") or client_ip
    notify_ua = metadata.get("user_agent") or user_agent
    is_new_device = metadata.get("is_new_device") == "1"

    await mfa_store.revoke_challenge(redis, challenge_token)
    session_token, csrf_token = await token_store.create_session(redis, user_id)
    logger.info(
        "login.success",
        extra={"user_id": user_id, "ip": client_ip, "mfa": True, "method": "email"},
    )
    await audit.record_event(
        event_type="login_success",
        user_id=user_id,
        reason="email",
        ip=client_ip,
        user_agent=user_agent,
    )

    if is_new_device and notify_email:
        email_service.send_login_notification(
            name=user.name,
            to=notify_email,
            ip=notify_ip,
            user_agent=notify_ua,
        )

    return MFAVerifyResult(session_token=session_token, csrf_token=csrf_token)


async def resend_email_code(
    challenge_token: str,
    client_ip: str,
    db: AsyncSession,
    redis: Redis,
    user_agent: str | None = None,
) -> None:
    """Re-issue + re-send the email code for a still-live challenge.

    No attempt is consumed (the user has not submitted a wrong code —
    they simply did not receive the previous one). The challenge TTL
    is unchanged. Each call DOES rotate the code (issue_code wipes the
    previous one and resets attempt counter), so an attacker who
    triggered a flood of resends gets nothing useful — every fresh
    code overwrites the last.
    """
    metadata = await mfa_store.get_challenge_metadata(redis, challenge_token)
    if not metadata or metadata.get("method") != "email":
        # Don't audit — this is the same noise as a typo'd token.
        raise MFAChallengeInvalidError()

    user_id = metadata.get("user_id")
    notify_email = metadata.get("email")
    if not user_id or not notify_email:
        raise MFAChallengeInvalidError()

    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None or not user.is_active or not user.email_2fa_enabled:
        raise MFAChallengeInvalidError()

    await email_service.send_two_factor_code(
        redis=redis,
        user_id=user_id,
        name=user.name,
        to=notify_email,
    )
    logger.info(
        "login.email_code_resent",
        extra={"user_id": user_id, "ip": client_ip},
    )


async def enable_email_2fa(
    user_id: str,
    db: AsyncSession,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Flip email_2fa_enabled to True for an authenticated user.

    Refuses when:
      * SMTP is not wired (settings.EMAIL_ENABLED=False) — the user
        would lock themselves out of subsequent logins.
      * The user has no plain `email` on file — same reason.
      * The flag is already on.

    Enabling does NOT require a re-verify ceremony: the user is
    already authenticated, and email 2FA *strengthens* auth (one more
    factor), so the threat model doesn't justify the friction.
    """
    if not settings.EMAIL_ENABLED:
        raise Email2FAUnavailableError()

    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None:
        raise InvalidCredentialsError()
    if not user.email:
        raise Email2FAUnavailableError(
            detail="Email address not on file — log in once more so it can be backfilled."
        )
    if user.email_2fa_enabled:
        raise Email2FAAlreadyEnabledError()

    user.email_2fa_enabled = True
    await db.commit()
    logger.info("auth.email_2fa_enabled", extra={"user_id": user_id})
    await audit.record_event(
        event_type="email_2fa_enabled",
        user_id=user_id,
        ip=client_ip,
        user_agent=user_agent,
    )


async def request_disable_email_2fa(
    user_id: str,
    db: AsyncSession,
    redis: Redis,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Step 1 of disabling email 2FA: send a verification code.

    The disable endpoint requires possession of a current email code,
    mirroring how `disable_totp` requires a current TOTP code. This
    prevents an attacker who has hijacked the live session from
    silently weakening the account.
    """
    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None:
        raise InvalidCredentialsError()
    if not user.email_2fa_enabled:
        raise Email2FANotEnabledError()
    if not user.email or not settings.EMAIL_ENABLED:
        raise Email2FAUnavailableError()

    await email_service.send_two_factor_code(
        redis=redis,
        user_id=user_id,
        name=user.name,
        to=user.email,
    )
    logger.info("auth.email_2fa_disable_requested", extra={"user_id": user_id})


async def disable_email_2fa(
    user_id: str,
    code: str,
    db: AsyncSession,
    redis: Redis,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Step 2 of disabling email 2FA: consume the live code.

    On success, flips the flag to False. The audit event
    `email_2fa_disabled` fans out to the admin alert path — same
    treatment as `totp_disabled`."""
    user = await repository.get_by_id(uuid.UUID(user_id), db)
    if user is None:
        raise InvalidCredentialsError()
    if not user.email_2fa_enabled:
        raise Email2FANotEnabledError()

    try:
        await email_code_store.verify_code(redis, user_id, code)
    except EmailCodeStoreInvalid as exc:
        await audit.record_event(
            event_type="email_2fa_disable_failed",
            user_id=user_id,
            reason="bad_code",
            ip=client_ip,
            user_agent=user_agent,
        )
        raise EmailCodeInvalidError() from exc

    user.email_2fa_enabled = False
    await db.commit()
    logger.info("auth.email_2fa_disabled", extra={"user_id": user_id})
    await audit.record_event(
        event_type="email_2fa_disabled",
        user_id=user_id,
        ip=client_ip,
        user_agent=user_agent,
    )


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
    await audit.record_event(event_type="logout", user_id=user_id, ip=client_ip, user_agent=user_agent)


async def clear_all_sessions(
    user_id: str,
    db: AsyncSession,
    redis: Redis,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Revoke every active session for the given user."""
    await token_store.clear_user_sessions(redis, user_id)
    await audit.record_event(event_type="sessions_cleared", user_id=user_id, ip=client_ip, user_agent=user_agent)


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
    await audit.record_event(event_type="totp_enroll_started", user_id=user_id, ip=client_ip, user_agent=user_agent)
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
        await audit.record_event(event_type="totp_confirm_failed", user_id=user_id, ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    user.totp_enabled = True
    await db.commit()
    await audit.record_event(event_type="totp_enabled", user_id=user_id, ip=client_ip, user_agent=user_agent)


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
        await audit.record_event(event_type="totp_disable_failed", user_id=user_id, ip=client_ip, user_agent=user_agent)
        raise TOTPInvalidError()

    await token_store.clear_user_sessions(redis, user_id)

    user.totp_enabled = False
    user.totp_secret_enc = None
    await db.commit()
    await audit.record_event(event_type="totp_disabled", user_id=user_id, ip=client_ip, user_agent=user_agent)
