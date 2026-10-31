"""Regression Test Suite for TestGuard

Protects against high-risk regressions identified during security architecture review:
- REG-001: Cross-tenant data leakage / horizontal privilege escalation
- REG-002: Member role permission bypass on project management
- REG-003: Expired token replay attacks
- REG-004: Invalid project/task tenant disassociation
- REG-005: Input validation failure corrupting database state
- REG-006: SQL injection defense across string query parameters
- REG-007: Inactive user account access revival
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.project import Project


@pytest.mark.regression
def test_reg_001_cross_tenant_access_remains_blocked(client: TestClient, alpha_admin_headers, seed_data):
    """REG-001: Protects against Horizontal Privilege Escalation.

    Risk: Code refactoring could accidentally omit 'tenant_id' in WHERE clauses.
    Verification: Tenant A admin querying Tenant B project ID receives 404, never 200 or 403.
    """
    beta_proj_id = seed_data["project_b1"].id
    response = client.get(f"/api/v1/projects/{beta_proj_id}", headers=alpha_admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


@pytest.mark.regression
def test_reg_002_member_role_restrictions_remain_enforced(client: TestClient, alpha_member_headers):
    """REG-002: Protects against Vertical Privilege Escalation.

    Risk: Route decorator changes could expose admin-only endpoints to standard members.
    Verification: Member attempting to create a project receives HTTP 403 Forbidden.
    """
    payload = {"name": "Unauthorized Member Regression Project"}
    response = client.post("/api/v1/projects", json=payload, headers=alpha_member_headers)
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"].lower()


@pytest.mark.regression
def test_reg_003_expired_tokens_remain_rejected(client: TestClient, seed_data):
    """REG-003: Protects against Token Replay and Stale Session Attacks.

    Risk: Misconfigured JWT validation disabling expiration timestamp verification.
    Verification: An expired token must be immediately rejected with 401 Unauthorized.
    """
    user = seed_data["user_alpha_admin"]
    expired_token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        expires_delta=timedelta(seconds=-3600),  # expired 1 hour ago
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/projects", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.regression
def test_reg_004_invalid_task_project_relationships_remain_rejected(client: TestClient, alpha_admin_headers, seed_data):
    """REG-004: Protects against Orphaned or Cross-Tenant Task Linkage.

    Risk: Task creation omitting project-tenant ownership verification.
    Verification: Attempt to attach a task to another tenant's project returns 404.
    """
    foreign_proj_id = seed_data["project_b1"].id
    payload = {
        "project_id": foreign_proj_id,
        "title": "Cross Tenant Task Attachment Regression",
    }
    response = client.post("/api/v1/tasks", json=payload, headers=alpha_admin_headers)
    assert response.status_code == 404
    assert "parent project not found" in response.json()["detail"].lower()


@pytest.mark.regression
def test_reg_005_invalid_input_does_not_corrupt_database_state(
    client: TestClient, alpha_admin_headers, db: Session, seed_data
):
    """REG-005: Protects against Database Corruption from Invalid API Payloads.

    Risk: Unhandled exceptions during request validation leaving partial rows.
    Verification: Submitting invalid payload returns 422 and database record count remains unchanged.
    """
    tenant_id = seed_data["tenant_a"].id
    count_before = db.query(Project).filter(Project.tenant_id == tenant_id).count()

    # Submit invalid payload (empty project name)
    response = client.post("/api/v1/projects", json={"name": ""}, headers=alpha_admin_headers)
    assert response.status_code == 422

    count_after = db.query(Project).filter(Project.tenant_id == tenant_id).count()
    assert count_after == count_before


@pytest.mark.regression
def test_reg_006_sql_injection_defense_in_search_and_id_parameters(client: TestClient, alpha_admin_headers):
    """REG-006: Protects against SQL Injection Vulnerabilities.

    Risk: Raw SQL string concatenation in filters or ID lookups.
    Verification: Malicious SQL injection payloads in path and query parameters are safely handled.
    """
    # SQLi in path parameter
    sqli_path = "1' OR '1'='1"
    response_path = client.get(f"/api/v1/projects/{sqli_path}", headers=alpha_admin_headers)
    assert response_path.status_code in [404, 422]

    # SQLi in query parameter
    sqli_query = "active' OR '1'='1"
    response_query = client.get(f"/api/v1/projects?status={sqli_query}", headers=alpha_admin_headers)
    assert response_query.status_code == 200
    # Returns 0 records because status is literally checked as "active' OR '1'='1"
    assert response_query.json()["total"] == 0


@pytest.mark.regression
def test_reg_007_inactive_account_access_remains_blocked(client: TestClient, seed_data):
    """REG-007: Protects against Inactive Account Revocation Bypass.

    Risk: Token valid but user deactivated in database still allowed API access.
    Verification: Deactivated user token cannot access API endpoints.
    """
    inactive_user = seed_data["user_alpha_inactive"]
    token = create_access_token(
        subject=inactive_user.id,
        tenant_id=inactive_user.tenant_id,
        role=inactive_user.role,
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()
