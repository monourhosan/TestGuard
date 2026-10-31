from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token


@pytest.mark.auth
def test_login_success_with_valid_credentials(client: TestClient, seed_data):
    """AUTH-001: Authenticate successfully with valid email and password."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@alpha.com", "password": "PasswordAlphaAdmin123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.auth
def test_login_fails_with_incorrect_password(client: TestClient, seed_data):
    """AUTH-002: Rejection of valid user with wrong password."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@alpha.com", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


@pytest.mark.auth
def test_login_fails_with_unknown_email(client: TestClient, seed_data):
    """AUTH-003: Rejection of unknown email address."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@unknown.com", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


@pytest.mark.auth
def test_login_fails_with_inactive_user(client: TestClient, seed_data):
    """AUTH-004: Rejection of inactive user account."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@alpha.com", "password": "PasswordAlphaInactive123!"},
    )
    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.auth
def test_login_fails_with_missing_fields(client: TestClient):
    """AUTH-005: Rejection of request with missing required fields."""
    # Missing password
    resp1 = client.post("/api/v1/auth/login", json={"email": "admin@alpha.com"})
    assert resp1.status_code == 422

    # Missing email
    resp2 = client.post("/api/v1/auth/login", json={"password": "Password123!"})
    assert resp2.status_code == 422


@pytest.mark.auth
def test_login_fails_with_invalid_email_format(client: TestClient):
    """AUTH-006: Rejection of malformed email address."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "Password123!"},
    )
    assert response.status_code == 422


@pytest.mark.auth
def test_login_fails_with_malformed_json_body(client: TestClient):
    """AUTH-007: Rejection of non-JSON or malformed payload."""
    response = client.post(
        "/api/v1/auth/login",
        content="this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.auth
def test_protected_route_without_token_rejected(client: TestClient):
    """AUTH-008: Protected endpoint rejects request without Authorization header."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "credentials" in response.json()["detail"].lower()


@pytest.mark.auth
def test_protected_route_with_malformed_token_rejected(client: TestClient):
    """AUTH-009: Protected endpoint rejects malformed token strings."""
    headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "malformed" in response.json()["detail"].lower()


@pytest.mark.auth
def test_protected_route_with_expired_token_rejected(client: TestClient, seed_data):
    """AUTH-010: Protected endpoint rejects expired JWT tokens."""
    user = seed_data["user_alpha_admin"]
    expired_token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.auth
def test_protected_route_with_tampered_token_rejected(client: TestClient, seed_data):
    """AUTH-011: Protected endpoint rejects JWT with invalid cryptographic signature."""
    user = seed_data["user_alpha_admin"]
    # Sign with an unauthorized external secret (32 bytes to satisfy RFC 7518)
    tampered_token = jwt.encode(
        {"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role, "exp": 9999999999},
        "wrong-unauthorized-secret-key-32b",
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "malformed or tampered" in response.json()["detail"].lower()


@pytest.mark.auth
def test_valid_token_identifies_correct_user_and_tenant(client: TestClient, alpha_admin_headers, seed_data):
    """AUTH-012: Valid token yields current authenticated user with proper tenant isolation."""
    response = client.get("/api/v1/auth/me", headers=alpha_admin_headers)
    assert response.status_code == 200
    data = response.json()
    expected_user = seed_data["user_alpha_admin"]
    assert data["id"] == expected_user.id
    assert data["email"] == expected_user.email
    assert data["tenant_id"] == expected_user.tenant_id
    assert data["role"] == "admin"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data
