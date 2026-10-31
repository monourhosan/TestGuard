import time

import pytest
from fastapi.testclient import TestClient


@pytest.mark.performance
def test_performance_smoke_latency_under_threshold(client: TestClient, alpha_admin_headers):
    """PERF-001: Baseline performance smoke test verifying read latency is within reasonable local limits."""
    # Measure health check latency
    start = time.perf_counter()
    resp_health = client.get("/health")
    health_duration_ms = (time.perf_counter() - start) * 1000
    assert resp_health.status_code == 200
    assert health_duration_ms < 500  # Local smoke threshold < 500ms

    # Measure project list latency
    start = time.perf_counter()
    resp_projects = client.get("/api/v1/projects", headers=alpha_admin_headers)
    projects_duration_ms = (time.perf_counter() - start) * 1000
    assert resp_projects.status_code == 200
    assert projects_duration_ms < 500


@pytest.mark.performance
def test_performance_sequential_throughput_smoke(client: TestClient, alpha_admin_headers):
    """PERF-002: Smoke test verifying 25 sequential API read requests execute cleanly without errors."""
    latencies = []
    for _ in range(25):
        t0 = time.perf_counter()
        resp = client.get("/api/v1/tasks", headers=alpha_admin_headers)
        assert resp.status_code == 200
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 250  # Average sequential latency under 250ms
