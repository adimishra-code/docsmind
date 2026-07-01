"""Atomic Redis rate limiting middleware."""
from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import redis_client

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        max_requests: int | None = None,
        window_seconds: int | None = None,
        fail_open: bool = False,
    ):
        super().__init__(app)
        self.max_requests = max_requests or settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = window_seconds or 60
        self.fail_open = fail_open

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "127.0.0.1"
        cache_key = "rate_limit:{0}".format(client_ip)
        is_auth_endpoint = request.url.path.startswith("/api/v1/auth")

        try:
            pipe = redis_client.pipeline()
            pipe.incr(cache_key)
            pipe.expire(cache_key, self.window_seconds)
            results = await pipe.execute()
            
            current_count = results[0]
            
            if current_count > self.max_requests:
                logger.warning("Rate limit exceeded", client_ip=client_ip, count=current_count, limit=self.max_requests)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many requests", "code": "rate_limit_exceeded", "retry_after": self.window_seconds},
                )
                
        except RuntimeError as exc:
            if "Event loop is closed" in str(exc):
                logger.warning("Redis unavailable (event loop closed) — bypassing rate limiter", client_ip=client_ip)
            else:
                logger.error("Redis rate limit check failed", client_ip=client_ip, error=str(exc))
                if is_auth_endpoint or not self.fail_open:
                    return JSONResponse(
                        status_code=503,
                        content={"error": "Service temporarily unavailable", "code": "rate_limit_service_unavailable"},
                    )
        except Exception as exc:
            logger.error("Redis rate limit check failed", client_ip=client_ip, error=str(exc))
            if is_auth_endpoint or not self.fail_open:
                logger.error("Failing closed due to Redis unavailability for auth endpoint")
                return JSONResponse(
                    status_code=503,
                    content={"error": "Service temporarily unavailable", "code": "rate_limit_service_unavailable"},
                )
            logger.warning("Failing open for non-auth endpoint due to Redis error")

        return await call_next(request)