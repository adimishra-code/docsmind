from __future__ import annotations

import time
import traceback
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
from app.core import metrics
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

    # Fail fast on insecure/incomplete production configuration rather than
    # letting it surface later as a runtime 401 or an insecure credential.
    config_errors = settings.production_safety_errors()
    if config_errors:
        for problem in config_errors:
            logger.error("Production configuration error", problem=problem)
        raise RuntimeError(
            "Refusing to start in production with insecure/incomplete configuration: "
            + "; ".join(config_errors)
        )

    deps = {}

    try:
        from sqlalchemy import text
        import app.db.session as db_session
        async with db_session.AsyncSessionLocal() as conn:
            await conn.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
        logger.info("PostgreSQL connection verified")
    except Exception as exc:
        deps["postgres"] = f"unavailable: {exc}"
        logger.warning("PostgreSQL not reachable on startup", error=str(exc))

    try:
        from app.db.redis import redis_client
        await redis_client.ping()
        deps["redis"] = "ok"
        logger.info("Redis connection verified")
    except Exception as exc:
        deps["redis"] = f"unavailable: {exc}"
        logger.warning("Redis not reachable on startup", error=str(exc))

    try:
        from app.services.rag.vector_store import QdrantAdapter
        qdrant = QdrantAdapter()
        await qdrant.client.get_collections()
        deps["qdrant"] = "ok"
        logger.info("Qdrant connection verified")
    except Exception as exc:
        deps["qdrant"] = f"unavailable: {exc}"
        logger.warning("Qdrant not reachable on startup", error=str(exc))

    app.state.dependency_health = deps
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
        request.state.request_id = request_id
        
        # Bind request context to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        start_time = time.perf_counter()
        metrics.REQUESTS_IN_PROGRESS.labels(request.method).inc()

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"

            _record_metrics(request, response.status_code, process_time)
            logger.info(
                "Request processed successfully",
                status_code=response.status_code,
                duration=f"{process_time:.4f}s",
            )
            return response

        except Exception as exc:
            process_time = time.perf_counter() - start_time
            _record_metrics(request, status.HTTP_500_INTERNAL_SERVER_ERROR, process_time)
            tb = traceback.format_exc()
            logger.exception(
                "Unhandled exception during request processing",
                duration=f"{process_time:.4f}s",
                error=str(exc),
            )
            logger.error("Full traceback:\n%s", tb)
            # Full traceback is always logged server-side. It is only echoed to
            # the client outside production to avoid leaking internal details.
            content: dict[str, object] = {
                "code": "internal_error",
                "request_id": request_id,
            }
            if settings.is_production:
                content["error"] = "Internal server error"
            else:
                content["error"] = str(exc)
                content["traceback"] = tb.splitlines()[-10:]
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=content,
                headers={"X-Request-ID": request_id},
            )
        finally:
            metrics.REQUESTS_IN_PROGRESS.labels(request.method).dec()


def _record_metrics(request: Request, status_code: int, duration: float) -> None:
    """Record request count + latency against the route template (not the raw path)."""
    path = metrics.normalize_path(request)
    metrics.REQUEST_COUNT.labels(request.method, path, str(status_code)).inc()
    metrics.REQUEST_LATENCY.labels(request.method, path).observe(duration)


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
def _get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "")) or request.headers.get("X-Request-ID", "")


@app.exception_handler(AppError)
async def domain_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Catch application layer exceptions and translate to structured HTTP responses."""
    request_id = _get_request_id(request)
    logger.warn(
        "Application domain error",
        request_id=request_id,
        status_code=exc.status_code,
        error_code=exc.code,
        message=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate standard Pydantic schema errors to matching application format."""
    errors = exc.errors()
    request_id = _get_request_id(request)
    error_details = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err["loc"])
        error_details.append(f"{loc}: {err['msg']}")

    message = "; ".join(error_details)
    logger.warn("Request validation failed", request_id=request_id, errors=errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed: " + message,
            "code": "validation_error",
            "request_id": request_id,
            "details": errors,
        },
    )


# 6. Include API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# 7. OpenAPI Schema Export
@app.get("/openapi.json", tags=["system"])
async def get_openapi_schema():
    return app.openapi()

# 8. Core Health Checks
@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check(request: Request) -> dict:
    deps = getattr(request.app.state, "dependency_health", {})
    all_ok = all(v == "ok" for v in deps.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "service": settings.APP_NAME,
        "dependencies": deps,
    }


@app.get("/readyz", tags=["system"])
async def readiness_check(request: Request) -> Response:
    """Kubernetes/compose readiness probe.

    Returns 200 only when every critical dependency verified at startup is
    reachable, and 503 otherwise, so orchestrators can hold traffic off a
    backend whose datastore is down.
    """
    deps = getattr(request.app.state, "dependency_health", {})
    all_ok = bool(deps) and all(v == "ok" for v in deps.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if all_ok else "not_ready", "dependencies": deps},
    )


# 9. Prometheus metrics scrape endpoint
@app.get("/metrics", tags=["system"], include_in_schema=False)
async def prometheus_metrics() -> Response:
    payload, content_type = metrics.render_latest()
    return Response(content=payload, media_type=content_type)
