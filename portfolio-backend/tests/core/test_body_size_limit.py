"""
Tests for BodySizeLimitMiddleware.

We exercise the middleware end-to-end through Starlette/HTTPX so the
behavior matches what FastAPI handlers actually see — both the cheap
Content-Length path and the streaming counter path.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.core.middleware import BodySizeLimitMiddleware


def _build_app(*, max_bytes: int) -> Starlette:
    async def echo(request: Request) -> JSONResponse:
        body = await request.body()
        return JSONResponse({"received_bytes": len(body)})

    app = Starlette(routes=[Route("/echo", echo, methods=["POST"])])
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes)
    return app


@pytest.fixture
def client():
    app = _build_app(max_bytes=64)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_under_limit_passes(client):
    """A request well under the limit reaches the handler unchanged."""
    async with client as ac:
        r = await ac.post("/echo", content=b"x" * 32)
    assert r.status_code == 200
    assert r.json() == {"received_bytes": 32}


@pytest.mark.asyncio
async def test_at_limit_passes(client):
    """Exactly the limit must succeed — boundary is inclusive."""
    async with client as ac:
        r = await ac.post("/echo", content=b"x" * 64)
    assert r.status_code == 200
    assert r.json() == {"received_bytes": 64}


@pytest.mark.asyncio
async def test_content_length_over_limit_short_circuits(client):
    """A declared Content-Length over the limit must 413 without ever
    invoking the handler — that's the cheap path the attacker pays for."""
    handler_called = False

    async def echo(request: Request) -> JSONResponse:
        nonlocal handler_called
        handler_called = True
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/echo", echo, methods=["POST"])])
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=64)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/echo", content=b"x" * 1024)
    assert r.status_code == 413
    assert r.json()["error"] == "PAYLOAD_TOO_LARGE"
    assert handler_called is False


@pytest.mark.asyncio
async def test_chunked_upload_over_limit_returns_413():
    """Chunked uploads with no truthful Content-Length still get policed
    by the streaming byte counter."""

    async def chunks():
        # Total = 200 bytes, well over the 64-byte limit.
        for _ in range(10):
            yield b"x" * 20

    app = _build_app(max_bytes=64)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/echo", content=chunks())
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_non_http_scope_passes_through():
    """Lifespan / websocket scopes must not be intercepted."""
    received = []

    async def app(scope, receive, send):
        received.append(scope["type"])

    wrapped = BodySizeLimitMiddleware(app, max_bytes=64)
    await wrapped({"type": "lifespan"}, lambda: None, lambda m: None)
    assert received == ["lifespan"]


def test_init_rejects_non_positive_max_bytes():
    async def app(scope, receive, send):
        return None

    with pytest.raises(ValueError):
        BodySizeLimitMiddleware(app, max_bytes=0)
    with pytest.raises(ValueError):
        BodySizeLimitMiddleware(app, max_bytes=-1)
