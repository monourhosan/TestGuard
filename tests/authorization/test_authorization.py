import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token


@pytest.mark.authz
def test_admin_can_list_projects(client: TestClient, alpha_admin_headers):
    """AUTHZ-001: Admin can list projects in own tenant."""
    response = client.get("/api/v1/projects", headers=alpha_admin_headers)
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.authz
def test_admin_can_create_project(client: TestClient, alpha_admin_headers):
    """AUTHZ-002: Admin can create a new project in own tenant."""
    payload = {"name": "Admin Authz Project", "description": "Created by admin"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Admin Authz Project"


@pytest.mark.authz
def test_admin_can_update_project(client: TestClient, alpha_admin_headers, seed_data):
    """AUTHZ-003: Admin can update project in own tenant."""
    project_id = seed_data["project_a1"].id
    payload = {"description": "Updated by admin"}
    response = client.patch(f"/api/v1/projects/{project_id}", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 200
    assert response.json()["description"] == "Updated by admin"


@pytest.mark.authz
def test_admin_can_delete_project(client: TestClient, alpha_admin_headers, seed_data):
    """AUTHZ-004: Admin can delete project in own tenant."""
    project_id = seed_data["project_a2"].id
    response = client.delete(f"/api/v1/projects/{project_id}", headers=alpha_admin_headers)
    assert response.status_code == 200


@pytest.mark.authz
def test_member_can_view_projects(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-005: Member can read projects in own tenant."""
    # List projects
    list_resp = client.get("/api/v1/projects", headers=alpha_member_headers)
    assert list_resp.status_code == 200

    # Get single project
    proj_id = seed_data["project_a1"].id
    get_resp = client.get(f"/api/v1/projects/{proj_id}", headers=alpha_member_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == proj_id


@pytest.mark.authz
def test_member_cannot_create_project_returns_403(client: TestClient, alpha_member_headers):
    """AUTHZ-006: Member role is forbidden from creating projects."""
    payload = {"name": "Member Project Attempt", "description": "Should fail"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_member_headers)
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"].lower()


@pytest.mark.authz
def test_member_cannot_update_project_returns_403(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-007: Member role is forbidden from updating projects."""
    project_id = seed_data["project_a1"].id
    payload = {"name": "Unauthorized Project Rename"}
    response = client.patch(f"/api/v1/projects/{project_id}", json=payload, headers=alpha_member_headers)
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"].lower()


@pytest.mark.authz
def test_member_cannot_delete_project_returns_403(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-008: Member role is forbidden from deleting projects."""
    project_id = seed_data["project_a1"].id
    response = client.delete(f"/api/v1/projects/{project_id}", headers=alpha_member_headers)
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"].lower()


@pytest.mark.authz
def test_member_can_view_tasks(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-009: Member can read tasks in own tenant."""
    list_resp = client.get("/api/v1/tasks", headers=alpha_member_headers)
    assert list_resp.status_code == 200

    task_id = seed_data["task_a1"].id
    get_resp = client.get(f"/api/v1/tasks/{task_id}", headers=alpha_member_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id


@pytest.mark.authz
def test_member_can_create_task(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-010: Member can create tasks within own tenant."""
    proj_id = seed_data["project_a1"].id
    payload = {"project_id": proj_id, "title": "Member Created Task", "status": "todo"}
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_member_headers)
    assert response.status_code == 201
    assert response.json()["title"] == "Member Created Task"


@pytest.mark.authz
def test_member_can_update_task(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-011: Member can update tasks within own tenant."""
    task_id = seed_data["task_a1"].id
    payload = {"status": "in_progress"}
    response = client.patch(f"/api/v1/tasks/{task_id}", json=payload, headers=alpha_member_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


@pytest.mark.authz
def test_member_cannot_delete_task_returns_403(client: TestClient, alpha_member_headers, seed_data):
    """AUTHZ-012: Member role is forbidden from deleting tasks."""
    task_id = seed_data["task_a1"].id
    response = client.delete(f"/api/v1/tasks/{task_id}", headers=alpha_member_headers)
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"].lower()


@pytest.mark.authz
def test_admin_can_delete_task(client: TestClient, alpha_admin_headers, seed_data):
    """AUTHZ-013: Admin can delete tasks within own tenant."""
    task_id = seed_data["task_a2"].id
    response = client.delete(f"/api/v1/tasks/{task_id}", headers=alpha_admin_headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]


@pytest.mark.authz
def test_manipulated_role_claim_in_token_is_rejected(client: TestClient, seed_data):
    """AUTHZ-014: Forging 'role: admin' in JWT for a member account fails server verification."""
    member_user = seed_data["user_alpha_member"]
    # Token signed with correct secret, but role artificially set to 'admin'
    forged_token = create_access_token(
        subject=member_user.id,
        tenant_id=member_user.tenant_id,
        role="admin",  # Forged role!
    )
    headers = {"Authorization": f"Bearer {forged_token}"}
    payload = {"name": "Forged Admin Project"}
    response = client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 403
    assert "does not match" in response.json()["detail"].lower()
