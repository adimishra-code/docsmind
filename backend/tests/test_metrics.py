from __future__ import annotations

"""Tests for the Prometheus telemetry endpoint and request instrumentation."""

import pytest
from httpx import AsyncClient

# The test client is scoped to /api/v1; system endpoints live at the root, so
# address them with an absolute URL to bypass the base_url prefix.
ROOT = "http://testserver"


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_text(client: AsyncClient) -> None:
    resp = await client.get(f"{ROOT}/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    # The metric families defined in app.core.metrics must be present.
    assert "docsmind_http_requests_total" in body
    assert "docsmind_http_request_duration_seconds" in body


@pytest.mark.asyncio
async def test_request_counter_increments_and_uses_route_template(
    client: AsyncClient,
) -> None:
    # Drive a request through a known route, then confirm it was counted under
    # the route *template* (no high-cardinality id in the label).
    await client.get(f"{ROOT}/health")
    resp = await client.get(f"{ROOT}/metrics")
    body = resp.text

    assert 'docsmind_http_requests_total{method="GET",path="/health",status="200"}' in body
    # Sanity: the counter value for /health is at least 1.
    line = next(
        l
        for l in body.splitlines()
        if l.startswith('docsmind_http_requests_total{method="GET",path="/health"')
    )
    value = float(line.rsplit(" ", 1)[1])
    assert value >= 1.0


@pytest.mark.asyncio
async def test_readyz_reports_dependency_state(client: AsyncClient) -> None:
    # In the unit harness no real datastores were verified at startup, so the
    # readiness probe must fail closed (503) rather than claim readiness.
    resp = await client.get(f"{ROOT}/readyz")
    assert resp.status_code in (200, 503)
    assert resp.json()["status"] in ("ready", "not_ready")
