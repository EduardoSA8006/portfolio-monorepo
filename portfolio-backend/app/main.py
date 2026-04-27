import ipaddress
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.redis import get_redis
from app.features.auth import captcha
from app.features.auth.router import router as auth_router

configure_logging(settings.APP_ENV)

_prod = settings.APP_ENV == "production"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Process-lifetime hooks — currently only the captcha HTTP client.

    Without this, the singleton `httpx.AsyncClient` in
    `features.auth.captcha` outlives every `uvicorn --reload` cycle in
    development; each reload abandons one client and creates a new one,
    burning file descriptors. In production the worker exit reaps it
    anyway, but wiring lifespan here keeps the two environments
    symmetric and gives future shutdown tasks a place to attach.
    """
    yield
    await captcha.close_client()


app = FastAPI(
    title="Portfolio Backend",
    version="0.1.0",
    docs_url=None if _prod else "/docs",
    redoc_url=None,
    openapi_url=None if _prod else "/openapi.json",
    lifespan=lifespan,
)

# Middleware stack — last added = outermost = first to handle requests.
#
# Request path:  ProxyHeaders → TrustedHost → CORS → SecurityHeaders → routes
# Response path: routes → SecurityHeaders → CORS → TrustedHost → ProxyHeaders
#
# ProxyHeadersMiddleware (when enabled) rewrites request.client.host from
# X-Forwarded-For before TrustedHost and rate-limiting code ever run.
app.add_middleware(SecurityHeadersMiddleware, https=settings.COOKIE_SECURE)
# Innermost so a 413 still picks up SecurityHeaders on the way back out, and
# so that no other middleware buffers a 10 GB body before we get a chance
# to reject it.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.REQUEST_BODY_MAX_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    # Must mirror the verbs actually exposed by the router. Today every
    # mutating route is POST — keep the list scoped to what's used so
    # browsers don't preflight-allow methods we don't actually serve. When
    # adding PUT/PATCH/DELETE routes, extend this list AND verify
    # _ORIGIN_CHECK_METHODS in features/auth/dependencies.py covers the new
    # verb (it already does — that gate is defensive).
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", settings.CSRF_HEADER_NAME],
    expose_headers=[settings.CSRF_HEADER_NAME],
    max_age=600,
)
# CORS is browser policy; authenticated mutating requests still validate
# Origin/Referer in require_auth before touching session state.
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


def _readiness_forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def require_readiness_source(request: Request) -> None:
    if request.client is None:
        raise _readiness_forbidden()

    try:
        client_ip = ipaddress.ip_address(request.client.host)
    except ValueError as exc:
        raise _readiness_forbidden() from exc

    for allowed_cidr in settings.READINESS_ALLOWED_CIDRS:
        if client_ip in ipaddress.ip_network(allowed_cidr, strict=False):
            return

    raise _readiness_forbidden()


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — confirms the process is running."""
    return {"status": "ok"}


# Prometheus instrumentation. The /metrics endpoint is gated by the same
# CIDR allowlist as /health/ready — exposing it publicly would leak per-route
# traffic counts and timing data useful for fingerprinting and anomaly
# probing. Scrape it from inside the deploy network.
_instrumentator = Instrumentator(
    excluded_handlers=["/metrics", "/health"],
    should_group_status_codes=True,
    should_ignore_untemplated=True,
)
_instrumentator.instrument(app)
_instrumentator.expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
    tags=["observability"],
    dependencies=[Depends(require_readiness_source)],
)


@app.get(
    "/health/ready",
    tags=["health"],
    dependencies=[Depends(require_readiness_source)],
)
async def health_ready(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """Readiness probe — confirms DB and Redis are reachable."""
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ok"}
