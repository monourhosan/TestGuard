import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_create_project_success(client: TestClient, alpha_admin_headers):
    """API-003: Successfully create a project with valid fields."""
    payload = {
        "name": "New Valid Project",
        "description": "A valid description",
        "status": "active",
    }
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Valid Project"
    assert data["description"] == "A valid description"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.api
def test_create_project_empty_name_rejected_422(client: TestClient, alpha_admin_headers):
    """API-004: Validation failure on empty project name."""
    payload = {"name": "", "description": "Empty name test"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_project_whitespace_name_rejected_422(client: TestClient, alpha_admin_headers):
    """API-005: Validation failure on whitespace-only project name."""
    payload = {"name": "     ", "description": "Whitespace name test"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_project_name_exceeds_max_length_rejected_422(client: TestClient, alpha_admin_headers):
    """API-006: Boundary test - project name exceeding 150 characters is rejected."""
    payload = {"name": "A" * 151, "description": "Exceeds max length"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_project_duplicate_name_within_same_tenant_fails_409(client: TestClient, alpha_admin_headers, seed_data):
    """API-007: Duplicate project name within same tenant is rejected with 409 Conflict."""
    existing_name = seed_data["project_a1"].name
    payload = {"name": existing_name, "description": "Duplicate attempt"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.api
def test_create_project_same_name_in_different_tenants_is_allowed(
    client: TestClient, alpha_admin_headers, beta_admin_headers, seed_data
):
    """API-008: Two different tenants can have projects with the same name without collision."""
    alpha_name = seed_data["project_a1"].name
    # Tenant Beta creates project with identical name as Tenant Alpha
    payload = {"name": alpha_name, "description": "Same name different tenant"}
    response = client.post("/api/v1/projects", json=payload, headers=beta_admin_headers)
    assert response.status_code == 201
    assert response.json()["name"] == alpha_name


@pytest.mark.api
def test_get_project_by_id_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-009: Retrieve a single project by valid ID."""
    project_id = seed_data["project_a1"].id
    response = client.get(f"/api/v1/projects/{project_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == project_id


@pytest.mark.api
def test_get_project_nonexistent_returns_404(client: TestClient, alpha_admin_headers):
    """API-010: Querying a nonexistent project ID returns 404."""
    response = client.get("/api/v1/projects/999999", headers=alpha_admin_headers)
    assert response.status_code == 404


@pytest.mark.api
def test_get_project_invalid_id_negative_returns_422(client: TestClient, alpha_admin_headers):
    """API-011: Negative or zero project ID returns 422 Unprocessable Entity."""
    response = client.get("/api/v1/projects/-1", headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_update_project_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-012: Successfully update project fields."""
    project_id = seed_data["project_a1"].id
    payload = {"name": "Updated Alpha Project 1", "status": "archived"}
    response = client.patch(f"/api/v1/projects/{project_id}", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Alpha Project 1"
    assert data["status"] == "archived"


@pytest.mark.api
def test_update_project_duplicate_name_fails_409(client: TestClient, alpha_admin_headers, seed_data):
    """API-013: Renaming a project to another existing project's name in same tenant returns 409."""
    proj_a1_id = seed_data["project_a1"].id
    proj_a2_name = seed_data["project_a2"].name
    payload = {"name": proj_a2_name}
    response = client.patch(f"/api/v1/projects/{proj_a1_id}", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 409


@pytest.mark.api
def test_delete_project_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-014: Successfully delete a project in own tenant."""
    project_id = seed_data["project_a2"].id
    response = client.delete(f"/api/v1/projects/{project_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify subsequent GET returns 404
    get_resp = client.get(f"/api/v1/projects/{project_id}", headers=alpha_admin_headers)
    assert get_resp.status_code == 404


@pytest.mark.api
def test_list_projects_pagination_default(client: TestClient, alpha_admin_headers):
    """API-015: Default pagination returns page 1 and size 10."""
    response = client.get("/api/v1/projects", headers=alpha_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["size"] == 10
    assert isinstance(data["items"], list)


@pytest.mark.api
def test_list_projects_pagination_invalid_page_or_size_fails_422(client: TestClient, alpha_admin_headers):
    """API-016: Invalid pagination bounds (e.g. page=0 or size=101) return 422."""
    resp1 = client.get("/api/v1/projects?page=0", headers=alpha_admin_headers)
    assert resp1.status_code == 422

    resp2 = client.get("/api/v1/projects?size=101", headers=alpha_admin_headers)
    assert resp2.status_code == 422
