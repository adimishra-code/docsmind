"""Redis connection with configurable pool — lazy init."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from redis.asyncio import Redis, from_url

from app.core.config import settings


class _LazyRedis:
    _client: Redis | None = None

    def _ensure(self) -> Redis:
        if self._client is None:
            self._client = from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                protocol=2,
            )
        return self._client

    def __getattr__(self, name: str):
        return getattr(self._ensure(), name)


redis_client: Redis = _LazyRedis()  # type: ignore[assignment]


async def get_redis() -> AsyncGenerator[Redis, None]:
    yield redis_client  # type: ignore[arg-type]
