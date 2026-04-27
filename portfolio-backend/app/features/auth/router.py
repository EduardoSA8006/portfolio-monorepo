from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.features.auth import service
from app.features.auth.cookies import (
    clear_session_cookie,
    get_device_cookie_key,
    set_device_cookie,
    set_session_cookie,
)
from app.features.auth.dependencies import require_auth
from app.features.auth.schemas import (
    AuthConfigResponse,
    Email2FADisableRequest,
    EmailCodeResendRequest,
    EmailCodeVerifyRequest,
    EmailCodeVerifyResponse,
    LoginRequest,
    LoginResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    TOTPConfirmRequest,
    TOTPDisableRequest,
    TOTPEnrollResponse,
)
from app.features.auth.token_store import SessionData

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    """
    Returns request.client.host, which is the direct TCP peer address by default.
    When TRUST_PROXY_HEADERS=true, ProxyHeadersMiddleware has already rewritten
    this to the real client IP from X-Forwarded-For before this code runs.
    """
    return request.client.host if request.client else "unknown"


def _get_user_agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> LoginResponse:
    result = await service.login(
        body.email,
        body.password,
        _get_client_ip(request),
        db,
        redis,
        user_agent=_get_user_agent(request),
        captcha_token=body.captcha_token,
        device_cookie_value=request.cookies.get(get_device_cookie_key()),
    )
    # Persist the device cookie BEFORE deciding the response shape, so
    # both the MFA-required and the immediate-session paths carry it.
    if result.new_device_token:
        set_device_cookie(response, result.new_device_token)

    if result.mfa_required:
        return LoginResponse(
            status="mfa_required",
            mfa_challenge_token=result.mfa_challenge_token,
            mfa_method=result.mfa_method,
            message="MFA required",
        )
    set_session_cookie(response, result.session_token)
    return LoginResponse(status="ok", csrf_token=result.csrf_token)


@router.post("/login/mfa", response_model=MFAVerifyResponse, status_code=status.HTTP_200_OK)
async def login_mfa(
    body: MFAVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MFAVerifyResponse:
    result = await service.verify_mfa(
        body.mfa_challenge_token,
        body.code,
        _get_client_ip(request),
        db,
        redis,
        user_agent=_get_user_agent(request),
    )
    if result.new_device_token:
        set_device_cookie(response, result.new_device_token)
    set_session_cookie(response, result.session_token)
    return MFAVerifyResponse(csrf_token=result.csrf_token)


# -- Email 2FA login --------------------------------------------------------


@router.post(
    "/login/email-code/verify",
    response_model=EmailCodeVerifyResponse,
    status_code=status.HTTP_200_OK,
)
async def login_email_code_verify(
    body: EmailCodeVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EmailCodeVerifyResponse:
    """Step 2 of the email-2FA login flow — exchange a code for a session."""
    result = await service.verify_email_code(
        body.mfa_challenge_token,
        body.code,
        _get_client_ip(request),
        db,
        redis,
        user_agent=_get_user_agent(request),
    )
    if result.new_device_token:
        set_device_cookie(response, result.new_device_token)
    set_session_cookie(response, result.session_token)
    return EmailCodeVerifyResponse(csrf_token=result.csrf_token)


@router.post(
    "/login/email-code/resend",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def login_email_code_resend(
    body: EmailCodeResendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Re-send the verification code for a still-live email-2FA challenge."""
    await service.resend_email_code(
        body.mfa_challenge_token,
        _get_client_ip(request),
        db,
        redis,
        user_agent=_get_user_agent(request),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    await service.logout(
        session.session_token,
        session.user_id,
        db,
        redis,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )
    clear_session_cookie(response)


@router.post("/sessions/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_sessions(
    request: Request,
    response: Response,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    await service.clear_all_sessions(
        session.user_id,
        db,
        redis,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )
    clear_session_cookie(response)


# -- TOTP enrollment --------------------------------------------------------

@router.post("/totp/enroll", response_model=TOTPEnrollResponse, status_code=status.HTTP_200_OK)
async def totp_enroll(
    request: Request,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> TOTPEnrollResponse:
    secret, uri = await service.enroll_totp(
        session.user_id,
        db,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )
    return TOTPEnrollResponse(secret=secret, provisioning_uri=uri)


@router.post("/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def totp_confirm(
    body: TOTPConfirmRequest,
    request: Request,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.confirm_totp(
        session.user_id,
        body.code,
        db,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )


@router.post("/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def totp_disable(
    body: TOTPDisableRequest,
    request: Request,
    response: Response,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    await service.disable_totp(
        session.user_id,
        body.code,
        db,
        redis,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )
    clear_session_cookie(response)


# -- Email 2FA enrollment ---------------------------------------------------


@router.post("/email-2fa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def email_2fa_enable(
    request: Request,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Flip email 2FA on for the authenticated user.

    No code ceremony — enabling strengthens auth, so we don't gate it
    behind a re-verify the way disable does."""
    await service.enable_email_2fa(
        session.user_id,
        db,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )


@router.post("/email-2fa/disable/request", status_code=status.HTTP_204_NO_CONTENT)
async def email_2fa_disable_request(
    request: Request,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Step 1 of disabling email 2FA: send a one-shot code to the
    user's stored email. The user submits that code in step 2."""
    await service.request_disable_email_2fa(
        session.user_id,
        db,
        redis,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )


@router.post("/email-2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def email_2fa_disable(
    body: Email2FADisableRequest,
    request: Request,
    session: SessionData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Step 2 of disabling email 2FA — consume the live code, flip the flag."""
    await service.disable_email_2fa(
        session.user_id,
        body.code,
        db,
        redis,
        client_ip=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )


@router.get("/config", response_model=AuthConfigResponse, status_code=status.HTTP_200_OK)
async def auth_config() -> AuthConfigResponse:
    """
    Public config for the admin login page. No auth required — site_key is public.
    Returns empty string when hCaptcha is not configured (dev mode).
    """
    return AuthConfigResponse(
        hcaptcha_site_key=settings.HCAPTCHA_SITE_KEY,
        email_2fa_available=settings.EMAIL_ENABLED,
    )
