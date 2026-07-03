from __future__ import annotations

"""Prometheus telemetry for the DocsMind API.

Exposes a small, dependency-light set of process and HTTP metrics that the
``LoggingMiddleware`` records for every request, plus a ``/metrics`` endpoint
(wired in ``app.main``) that a Prometheus server can scrape.

The metric *names* and *labels* are the stable contract that dashboards and
alerts depend on, so treat renames as breaking changes.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# A dedicated registry keeps DocsMind metrics isolated from any library that
# might register against the global default registry, and makes the collectors
# trivially resettable in tests.
REGISTRY = CollectorRegistry()

# Latency buckets tuned for an API that fronts LLM/RAG work: sub-second for
# CRUD, but with headroom up to 30s for streaming/agent requests.
_LATENCY_BUCKETS = (
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
)

REQUEST_COUNT = Counter(
    "docsmind_http_requests_total",
    "Total HTTP requests processed, labelled by method, route template and status.",
    ("method", "path", "status"),
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "docsmind_http_request_duration_seconds",
    "HTTP request latency in seconds, labelled by method and route template.",
    ("method", "path"),
    buckets=_LATENCY_BUCKETS,
    registry=REGISTRY,
)

REQUESTS_IN_PROGRESS = Gauge(
    "docsmind_http_requests_in_progress",
    "Number of HTTP requests currently being processed.",
    ("method",),
    registry=REGISTRY,
)


def normalize_path(request) -> str:
    """Collapse a request URL to its route *template* to avoid label explosion.

    ``/api/v1/documents/6f1c.../status`` becomes ``/api/v1/documents/{id}/status``
    by using the matched Starlette route, so high-cardinality path params never
    become distinct Prometheus label values. Falls back to the concrete path
    only when no route matched (e.g. a 404).
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return str(path)
    return request.url.path


def render_latest() -> tuple[bytes, str]:
    """Return the current metrics exposition payload and its content type."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
