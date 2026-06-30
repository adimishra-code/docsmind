from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger
from app.db.redis import redis_client

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple IP-based rate limiting using Redis.
    Limits clients to `max_requests` per `window_seconds`.
    """
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "127.0.0.1"
        cache_key = f"rate_limit:{client_ip}"

        try:
            current = await redis_client.get(cache_key)
            if current and int(current) >= self.max_requests:
                logger.warning("Rate limit exceeded", client_ip=client_ip)
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})

            pipe = redis_client.pipeline()
            pipe.incr(cache_key)
            pipe.expire(cache_key, self.window_seconds)
            await pipe.execute()
        except Exception:
            # Fall open if Redis is unavailable
            pass

        return await call_next(request)
