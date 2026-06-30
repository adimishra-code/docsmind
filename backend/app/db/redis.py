from __future__ import annotations

from collections.abc import AsyncGenerator
from redis.asyncio import Redis, from_url

from app.core.config import settings

# Create a connection pool configured for async usage
redis_client: Redis = from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=10,
)


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency yielding the shared Redis client instance."""
    yield redis_client
