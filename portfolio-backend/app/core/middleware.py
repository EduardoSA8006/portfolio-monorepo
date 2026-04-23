from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds defensive HTTP response headers to every response.

    HSTS is only sent when COOKIE_SECURE=true (i.e. production / HTTPS).
    In development (HTTP) HSTS would lock the browser out of the local server.
    """

    def __init__(self, app, *, https: bool = True) -> None:
        super().__init__(app)
        self._https = https

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if self._https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=()"
        )
        response.headers["Cache-Control"] = "no-store"
        if "server" in response.headers:
            del response.headers["server"]

        return response
