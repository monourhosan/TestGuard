import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_health_check_returns_200_and_expected_payload(client: TestClient):
    """API-001: Health check endpoint returns HTTP 200 with service metadata."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "TestGuard"
    assert "version" in data
    assert "environment" in data


@pytest.mark.api
def test_openapi_documentation_accessible(client: TestClient):
    """API-002: OpenAPI schema and documentation endpoints are available."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
