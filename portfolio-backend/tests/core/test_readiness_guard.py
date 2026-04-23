import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.requests import Request

from app.core.config import settings
from app.main import app, health, require_readiness_source


@pytest.fixture(autouse=True)
def _restore_readiness_allowed_cidrs():
    original = list(settings.READINESS_ALLOWED_CIDRS)
    yield
    settings.READINESS_ALLOWED_CIDRS = original


def _request(client_host: str | None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health/ready",
        "headers": [],
    }
    if client_host is not None:
        scope["client"] = (client_host, 12345)
    return Request(scope)


def test_readiness_source_accepts_allowed_cidr():
    settings.READINESS_ALLOWED_CIDRS = ["10.0.0.0/8"]

    require_readiness_source(_request("10.20.30.40"))


def test_readiness_source_rejects_public_client():
    settings.READINESS_ALLOWED_CIDRS = ["10.0.0.0/8"]

    with pytest.raises(HTTPException) as exc_info:
        require_readiness_source(_request("203.0.113.10"))

    assert exc_info.value.status_code == 403


def test_readiness_source_rejects_missing_client():
    with pytest.raises(HTTPException) as exc_info:
        require_readiness_source(_request(None))

    assert exc_info.value.status_code == 403


async def test_health_stays_public():
    assert await health() == {"status": "ok"}


def test_readiness_route_registers_source_guard_before_resource_dependencies():
    route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/health/ready"
    )

    assert route.dependant.dependencies[0].call is require_readiness_source
