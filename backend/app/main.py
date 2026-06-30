from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import structlog

from app.api.v1.router import api_router
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger

# 1. Configure structured logging
configure_logging()
logger = get_logger(__name__)


# 2. Lifecycle management (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DocsMind platform backend.")
    # Initialize connection pools, cache warms, etc.
    yield
    logger.info("Shutting down DocsMind platform backend.")


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)


# 3. Middleware for Request ID & Latency Tracking
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate or extract request correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Bind request context to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"
            
            logger.info(
                "Request processed successfully",
                status_code=response.status_code,
                duration=f"{process_time:.4f}s",
            )
            return response
            
        except Exception as exc:
            process_time = time.perf_counter() - start_time
            logger.exception(
                "Unhandled exception during request processing",
                duration=f"{process_time:.4f}s",
                error=str(exc),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "An unexpected error occurred on the server.",
                    "code": "internal_error",
                },
                headers={"X-Request-ID": request_id},
            )


app.add_middleware(LoggingMiddleware)


# 4. CORS configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )

# 4.1 Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)


# 5. Global Exception Handlers
@app.exception_handler(AppError)
async def domain_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Catch application layer exceptions and translate to structured HTTP responses."""
    logger.warn(
        "Application domain error",
        status_code=exc.status_code,
        error_code=exc.code,
        message=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )


@app.exception_handler(RequestValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate standard Pydantic schema errors to matching application format."""
    errors = exc.errors()
    # Format message to be client-friendly
    error_details = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err["loc"])
        error_details.append(f"{loc}: {err['msg']}")

    message = "; ".join(error_details)
    logger.warn("Request validation failed", errors=errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed: " + message,
            "code": "validation_error",
            "details": errors,
        },
    )


# 6. Include API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# 7. Core Health Checks
@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": settings.APP_NAME}
