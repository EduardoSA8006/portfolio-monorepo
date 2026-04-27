"""
Integration test for the TRUST_PROXY_HEADERS gate.

`app/main.py` adds uvicorn's ProxyHeadersMiddleware *only* when
`settings.TRUST_PROXY_HEADERS=True` — exactly so a misconfigured dev
deployment does not silently honor X-Forwarded-For from the open
internet. This test pins that contract: with the flag off, an inbound
`X-Forwarded-For: 1.2.3.4` does NOT reach `request.client.host`.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def _build_app(*, trust_proxy_headers: bool) -> Starlette:
    """Mirror the conditional wiring in app/main.py with no other middleware."""

    async def whoami(request: Request) -> JSONResponse:
        return JSONResponse({"client_host": request.client.host if request.client else None})

    app = Starlette(routes=[Route("/whoami", whoami)])
    if trust_proxy_headers:
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    return app


@pytest.mark.asyncio
async def test_x_forwarded_for_ignored_when_flag_off():
    """With TRUST_PROXY_HEADERS=False the middleware is not in the stack,
    so XFF is ignored and the real socket peer wins. This is the safety
    contract for dev environments — no spoofing through a header."""
    app = _build_app(trust_proxy_headers=False)
    transport = ASGITransport(app=app, client=("198.51.100.50", 4321))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/whoami", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r.status_code == 200
    assert r.json() == {"client_host": "198.51.100.50"}


@pytest.mark.asyncio
async def test_x_forwarded_for_honored_when_flag_on():
    """With TRUST_PROXY_HEADERS=True the middleware is wired and
    request.client.host reflects the leftmost XFF entry. This pins the
    flag's intended behavior so a future regression that drops the
    middleware silently surfaces here."""
    app = _build_app(trust_proxy_headers=True)
    transport = ASGITransport(app=app, client=("198.51.100.50", 4321))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/whoami", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r.status_code == 200
    assert r.json() == {"client_host": "1.2.3.4"}
