from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
    return _pool


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(connection_pool=_get_pool())
    try:
        yield client
    finally:
        await client.aclose()
