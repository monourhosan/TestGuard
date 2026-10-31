import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_create_task_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-017: Create task in tenant-owned project."""
    proj_id = seed_data["project_a1"].id
    payload = {
        "project_id": proj_id,
        "title": "API Test Task",
        "description": "Functional test description",
        "status": "todo",
    }
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "API Test Task"
    assert data["project_id"] == proj_id
    assert data["status"] == "todo"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.api
def test_create_task_empty_title_fails_422(client: TestClient, alpha_admin_headers, seed_data):
    """API-018: Empty task title is rejected with 422."""
    proj_id = seed_data["project_a1"].id
    payload = {"project_id": proj_id, "title": ""}
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_task_whitespace_title_fails_422(client: TestClient, alpha_admin_headers, seed_data):
    """API-019: Whitespace-only task title is rejected with 422."""
    proj_id = seed_data["project_a1"].id
    payload = {"project_id": proj_id, "title": "     "}
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_task_title_exceeds_max_length_fails_422(client: TestClient, alpha_admin_headers, seed_data):
    """API-020: Task title exceeding 200 characters is rejected with 422."""
    proj_id = seed_data["project_a1"].id
    payload = {"project_id": proj_id, "title": "T" * 201}
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_task_invalid_status_fails_422(client: TestClient, alpha_admin_headers, seed_data):
    """API-021: Invalid task status value is rejected with 422."""
    proj_id = seed_data["project_a1"].id
    payload = {"project_id": proj_id, "title": "Valid Title", "status": "invalid_status_xyz"}
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_create_task_nonexistent_project_fails_404(client: TestClient, alpha_admin_headers):
    """API-022: Attaching a task to a nonexistent project returns 404."""
    payload = {"project_id": 999999, "title": "Orphan Task"}
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 404


@pytest.mark.api
def test_get_task_by_id_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-023: Retrieve a task by ID."""
    task_id = seed_data["task_a1"].id
    response = client.get(f"/api/v1/tasks/{task_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == task_id


@pytest.mark.api
def test_get_task_nonexistent_returns_404(client: TestClient, alpha_admin_headers):
    """API-024: Nonexistent task ID returns 404."""
    response = client.get("/api/v1/tasks/999999", headers=alpha_admin_headers)
    assert response.status_code == 404


@pytest.mark.api
def test_get_task_invalid_id_negative_returns_422(client: TestClient, alpha_admin_headers):
    """API-025: Negative task ID returns 422."""
    response = client.get("/api/v1/tasks/-5", headers=alpha_admin_headers)
    assert response.status_code == 422


@pytest.mark.api
def test_update_task_fields_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-026: Successfully update task title and status."""
    task_id = seed_data["task_a1"].id
    payload = {"title": "Updated Task Title", "status": "in_progress"}
    response = client.patch(f"/api/v1/tasks/{task_id}", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task Title"
    assert data["status"] == "in_progress"


@pytest.mark.api
def test_delete_task_success(client: TestClient, alpha_admin_headers, seed_data):
    """API-027: Successfully delete a task."""
    task_id = seed_data["task_a1"].id
    response = client.delete(f"/api/v1/tasks/{task_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify task is gone
    get_resp = client.get(f"/api/v1/tasks/{task_id}", headers=alpha_admin_headers)
    assert get_resp.status_code == 404


@pytest.mark.api
def test_list_tasks_filter_by_project_id(client: TestClient, alpha_admin_headers, seed_data):
    """API-028: Filter tasks by project ID."""
    proj_id = seed_data["project_a1"].id
    response = client.get(f"/api/v1/tasks?project_id={proj_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    assert all(item["project_id"] == proj_id for item in items)


@pytest.mark.api
def test_list_tasks_filter_by_status(client: TestClient, alpha_admin_headers):
    """API-029: Filter tasks by status."""
    response = client.get("/api/v1/tasks?status=done", headers=alpha_admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["status"] == "done" for item in items)
