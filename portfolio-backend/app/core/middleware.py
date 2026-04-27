from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """
    Reject requests whose body exceeds a fixed byte limit.

    Two layers:
      1. Cheap path — if Content-Length is present and already over the
         limit, return 413 without reading a single body byte.
      2. Streaming path — for chunked uploads (no Content-Length, or a
         lying one), count bytes as they arrive in the ASGI receive
         stream. The chunk that pushes the running total past the limit
         truncates the body and the first response message is swapped for
         a 413.

    Implemented as a raw ASGI middleware (not BaseHTTPMiddleware) so the
    receive interception happens before any handler buffers the body.
    Traefik should also enforce a body limit upstream — this is the
    in-process safety net for paths that bypass Traefik (dev, internal
    calls, misconfiguration).
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = -1
                if declared > self.max_bytes:
                    await _send_413(scope, send)
                    return
                break

        received = 0
        rejected = False
        sent_413 = False

        async def limited_receive() -> Message:
            nonlocal received, rejected
            message = await receive()
            if rejected or message["type"] != "http.request":
                return message
            body: bytes = message.get("body", b"") or b""
            received += len(body)
            if received > self.max_bytes:
                rejected = True
                # Truncate: hand the downstream app a clean, empty,
                # terminal body so it can finish synchronously. The send
                # filter below replaces whatever response it produces.
                return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def filtered_send(message: Message) -> None:
            nonlocal sent_413
            if rejected:
                if message["type"] == "http.response.start" and not sent_413:
                    sent_413 = True
                    await _send_413(scope, send)
                # Swallow body messages — 413 already covered the wire.
                return
            await send(message)

        await self.app(scope, limited_receive, filtered_send)


async def _empty_receive() -> Message:
    return {"type": "http.disconnect"}


async def _send_413(scope: Scope, send: Send) -> None:
    response = JSONResponse(
        status_code=413,
        content={"error": "PAYLOAD_TOO_LARGE", "detail": "request body exceeds limit"},
    )
    await response(scope, _empty_receive, send)


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
        # API only ever returns JSON. Lock the document down so a stray
        # text/html response (e.g. an error page leaking through) cannot
        # load scripts/styles, be framed for clickjacking, or have its
        # base URI rewritten. frame-ancestors 'none' is the modern
        # equivalent of X-Frame-Options=DENY (kept above for legacy UAs).
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        if "server" in response.headers:
            del response.headers["server"]

        return response
