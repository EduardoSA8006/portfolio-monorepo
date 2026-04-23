from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import SecurityHeadersMiddleware
from app.core.redis import get_redis
from app.features.auth.router import router as auth_router

configure_logging(settings.APP_ENV)

_prod = settings.APP_ENV == "production"

app = FastAPI(
    title="Portfolio Backend",
    version="0.1.0",
    docs_url=None if _prod else "/docs",
    redoc_url=None,
    openapi_url=None if _prod else "/openapi.json",
)

# Middleware stack — last added = outermost = first to handle requests.
#
# Request path:  ProxyHeaders → TrustedHost → CORS → SecurityHeaders → routes
# Response path: routes → SecurityHeaders → CORS → TrustedHost → ProxyHeaders
#
# ProxyHeadersMiddleware (when enabled) rewrites request.client.host from
# X-Forwarded-For before TrustedHost and rate-limiting code ever run.
app.add_middleware(SecurityHeadersMiddleware, https=settings.COOKIE_SECURE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", settings.CSRF_HEADER_NAME],
    expose_headers=[settings.CSRF_HEADER_NAME],
    max_age=600,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
if settings.TRUST_PROXY_HEADERS:
    # trusted_hosts restricts which proxy IPs to trust. uvicorn's
    # ProxyHeadersMiddleware accepts a list of IPs or CIDRs (natively since
    # 0.32). Reading from TRUSTED_PROXY_CIDRS guarantees we never deploy
    # with "*" — the validator in Settings rejects that value.
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=settings.TRUSTED_PROXY_CIDRS,
    )

register_exception_handlers(app)

app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — confirms the process is running."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """Readiness probe — confirms DB and Redis are reachable."""
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ok"}
