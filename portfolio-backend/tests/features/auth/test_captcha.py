from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fakeredis.aioredis import FakeRedis

from app.features.auth import captcha


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def mock_client(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(captcha, "_get_http_client", lambda: client)
    return client


def _response(*, status_code, json_body=None):
    return SimpleNamespace(
        status_code=status_code,
        json=lambda: json_body or {},
    )


@pytest.mark.asyncio
async def test_verify_ok_when_siteverify_success(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.return_value = _response(status_code=200, json_body={"success": True})

    result = await captcha.verify("token-abc", "203.0.113.9", redis)

    assert result.ok is True
    assert result.provider_available is True
    assert result.reason is None


@pytest.mark.asyncio
async def test_verify_not_ok_when_siteverify_rejects(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.return_value = _response(
        status_code=200,
        json_body={"success": False, "error-codes": ["invalid-input-response"]},
    )

    result = await captcha.verify("bad-token", "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is True
    assert result.reason == "invalid-input-response"


@pytest.mark.asyncio
async def test_verify_not_ok_when_token_none(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")

    result = await captcha.verify(None, "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is True
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_verify_marks_degraded_on_timeout(redis, mock_client, monkeypatch):
    import httpx

    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.side_effect = httpx.TimeoutException("timeout")

    result = await captcha.verify("token-abc", "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is False
    assert await redis.exists("auth:rl:degraded") == 1


@pytest.mark.asyncio
async def test_verify_marks_degraded_on_5xx(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "test-secret")
    mock_client.post.return_value = _response(status_code=503, json_body={})

    result = await captcha.verify("token-abc", "203.0.113.9", redis)

    assert result.ok is False
    assert result.provider_available is False
    assert await redis.exists("auth:rl:degraded") == 1


@pytest.mark.asyncio
async def test_verify_skipped_when_secret_key_empty(redis, mock_client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "HCAPTCHA_SECRET_KEY", "")

    result = await captcha.verify("any-token", "203.0.113.9", redis)

    assert result.ok is True
    assert result.provider_available is True
    mock_client.post.assert_not_called()
