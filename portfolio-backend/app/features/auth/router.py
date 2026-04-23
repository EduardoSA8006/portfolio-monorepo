from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.features.auth import service
from app.features.auth.cookies import clear_session_cookie, set_session_cookie
from app.features.auth.dependencies import require_auth
from app.features.auth.schemas import (
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
    )
    if result.mfa_required:
        return LoginResponse(
            status="mfa_required",
            mfa_challenge_token=result.mfa_challenge_token,
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
    session_token, csrf_token = await service.verify_mfa(
        body.mfa_challenge_token,
        body.code,
        _get_client_ip(request),
        db,
        redis,
        user_agent=_get_user_agent(request),
    )
    set_session_cookie(response, session_token)
    return MFAVerifyResponse(csrf_token=csrf_token)


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
