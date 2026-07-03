"""Per-endpoint throttle dependency for stricter rate limiting on sensitive routes."""
from __future__ import annotations

from fastapi import Request, Depends
from typing import Annotated

from app.api.deps import RedisDep
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


def throttle(max_requests: int, window_seconds: int, key_prefix: str = "throttle"):
    """Dependency factory: limits requests per client IP for a specific endpoint."""

    async def _throttle_dependency(request: Request, redis: RedisDep) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        cache_key = "{0}:{1}".format(key_prefix, client_ip)
        try:
            pipe = redis.pipeline()
            pipe.incr(cache_key)
            pipe.expire(cache_key, window_seconds)
            results = await pipe.execute()
        except Exception:
            # Fail open: a Redis outage should not take down the endpoint.
            logger.warning("Throttle check failed — allowing request through", client_ip=client_ip)
            return

        if results[0] > max_requests:
            raise RateLimitError("Too many requests. Please slow down.")

    return _throttle_dependency


RegisterThrottle = Annotated[None, Depends(throttle(max_requests=10, window_seconds=900, key_prefix="register"))]
