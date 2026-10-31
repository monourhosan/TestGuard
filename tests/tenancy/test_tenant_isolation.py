import pytest
from fastapi.testclient import TestClient


@pytest.mark.tenancy
def test_tenant_a_cannot_get_tenant_b_project_returns_404(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-001: Querying a project belonging to Tenant B returns 404 Not Found for Tenant A."""
    beta_proj_id = seed_data["project_b1"].id
    response = client.get(f"/api/v1/projects/{beta_proj_id}", headers=alpha_admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


@pytest.mark.tenancy
def test_tenant_a_cannot_update_tenant_b_project_returns_404(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-002: Updating a project belonging to Tenant B returns 404 Not Found for Tenant A."""
    beta_proj_id = seed_data["project_b1"].id
    payload = {"name": "Malicious Overwrite"}
    response = client.patch(f"/api/v1/projects/{beta_proj_id}", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


@pytest.mark.tenancy
def test_tenant_a_cannot_delete_tenant_b_project_returns_404(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-003: Deleting a project belonging to Tenant B returns 404 Not Found for Tenant A."""
    beta_proj_id = seed_data["project_b1"].id
    response = client.delete(f"/api/v1/projects/{beta_proj_id}", headers=alpha_admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


@pytest.mark.tenancy
def test_tenant_a_cannot_get_tenant_b_task_returns_404(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-004: Querying a task belonging to Tenant B returns 404 Not Found for Tenant A."""
    beta_task_id = seed_data["task_b1"].id
    response = client.get(f"/api/v1/tasks/{beta_task_id}", headers=alpha_admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.tenancy
def test_tenant_a_cannot_update_tenant_b_task_returns_404(client: TestClient, alpha_member_headers, seed_data):
    """TENANT-005: Updating a task belonging to Tenant B returns 404 Not Found for Tenant A."""
    beta_task_id = seed_data["task_b1"].id
    payload = {"status": "done"}
    response = client.patch(f"/api/v1/tasks/{beta_task_id}", json=payload, headers=alpha_member_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.tenancy
def test_tenant_a_cannot_delete_tenant_b_task_returns_404(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-006: Deleting a task belonging to Tenant B returns 404 Not Found for Tenant A."""
    beta_task_id = seed_data["task_b1"].id
    response = client.delete(f"/api/v1/tasks/{beta_task_id}", headers=alpha_admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.tenancy
def test_list_projects_strictly_scoped_to_current_tenant(
    client: TestClient, alpha_admin_headers, beta_admin_headers, seed_data
):
    """TENANT-007: List projects only returns records from caller's tenant; no leakage across tenants."""
    alpha_resp = client.get("/api/v1/projects", headers=alpha_admin_headers)
    assert alpha_resp.status_code == 200
    alpha_items = alpha_resp.json()["items"]
    alpha_ids = [p["id"] for p in alpha_items]

    beta_resp = client.get("/api/v1/projects", headers=beta_admin_headers)
    assert beta_resp.status_code == 200
    beta_items = beta_resp.json()["items"]
    beta_ids = [p["id"] for p in beta_items]

    # Mutual exclusivity of project IDs
    assert set(alpha_ids).isdisjoint(set(beta_ids))
    assert seed_data["project_b1"].id not in alpha_ids
    assert seed_data["project_a1"].id in alpha_ids
    assert seed_data["project_b1"].id in beta_ids


@pytest.mark.tenancy
def test_list_tasks_strictly_scoped_to_current_tenant(
    client: TestClient, alpha_admin_headers, beta_admin_headers, seed_data
):
    """TENANT-008: List tasks only returns records from caller's tenant."""
    alpha_resp = client.get("/api/v1/tasks", headers=alpha_admin_headers)
    assert alpha_resp.status_code == 200
    alpha_items = alpha_resp.json()["items"]
    alpha_ids = [t["id"] for t in alpha_items]

    beta_resp = client.get("/api/v1/tasks", headers=beta_admin_headers)
    assert beta_resp.status_code == 200
    beta_items = beta_resp.json()["items"]
    beta_ids = [t["id"] for t in beta_items]

    assert set(alpha_ids).isdisjoint(set(beta_ids))
    assert seed_data["task_b1"].id not in alpha_ids
    assert seed_data["task_b1"].id in beta_ids


@pytest.mark.tenancy
def test_cannot_create_task_with_foreign_project_id_returns_404(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-009: Creating a task with another tenant's project ID is rejected with 404."""
    beta_proj_id = seed_data["project_b1"].id
    payload = {
        "project_id": beta_proj_id,
        "title": "Cross Tenant Task Attachment Attempt",
    }
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.tenancy
def test_client_supplied_tenant_id_in_payload_does_not_override_scope(
    client: TestClient, alpha_admin_headers, seed_data
):
    """TENANT-010: Injecting an arbitrary tenant_id in request payload does not change resource assignment."""
    beta_tenant_id = seed_data["tenant_b"].id
    payload = {
        "name": "Injected Tenant Project",
        "description": "Testing injection",
        "tenant_id": beta_tenant_id,  # Malicious injection
    }
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 201
    created_project = response.json()
    # Verified: Project is assigned strictly to caller's tenant (Alpha), never injected Beta!
    assert created_project["tenant_id"] == seed_data["tenant_a"].id
    assert created_project["tenant_id"] != beta_tenant_id


@pytest.mark.tenancy
def test_pagination_totals_do_not_leak_cross_tenant_record_counts(
    client: TestClient, alpha_admin_headers, beta_admin_headers
):
    """TENANT-011: Pagination metadata reflects strictly tenant-scoped record totals."""
    alpha_resp = client.get("/api/v1/projects", headers=alpha_admin_headers)
    beta_resp = client.get("/api/v1/projects", headers=beta_admin_headers)

    alpha_total = alpha_resp.json()["total"]
    beta_total = beta_resp.json()["total"]

    # In our seed fixtures, Tenant Alpha has 2 projects, Tenant Beta has 1 project
    assert alpha_total == 2
    assert beta_total == 1


@pytest.mark.tenancy
def test_filtering_tasks_by_foreign_project_id_returns_zero_items(client: TestClient, alpha_admin_headers, seed_data):
    """TENANT-012: Filtering tasks by another tenant's project ID yields empty list, not cross-tenant tasks."""
    beta_proj_id = seed_data["project_b1"].id
    response = client.get(f"/api/v1/tasks?project_id={beta_proj_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
