"""Pytest Configuration and Fixtures for TestGuard

Provides:
- Database safety checks preventing execution against non-test databases.
- Isolated test database lifecycle (tables created and dropped cleanly).
- FastAPI TestClient with overridden get_db dependency.
- Deterministic multi-tenant seed fixtures (Tenant Alpha & Beta, Admin & Member users).
- Pre-generated JWT authentication headers for testing.
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import ProjectStatus, TaskStatus, UserRole
from app.models.project import Project
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User

# --- Safety Check: Database Guard ---
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./testguard_test.db")


def verify_test_database_safety(url: str) -> None:
    """Safety guard: prevent destructive test fixtures against production databases.

    Raises RuntimeError if the database URL does not explicitly designate a test environment.
    """
    safe_identifiers = ["test", "testguard_test", ":memory:"]
    is_safe = any(identifier in url.lower() for identifier in safe_identifiers)
    if not is_safe:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Refusing to run tests against database '{url}'. "
            f"Database URL must contain one of {safe_identifiers}."
        )


verify_test_database_safety(TEST_DB_URL)

# Configure SQLAlchemy Engine for Testing
connect_args = {}
if TEST_DB_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

test_engine = create_engine(
    TEST_DB_URL,
    connect_args=connect_args,
    poolclass=StaticPool if TEST_DB_URL.startswith("sqlite") else None,
)

if TEST_DB_URL.startswith("sqlite"):

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables before test session and drop them cleanly at conclusion."""
    verify_test_database_safety(TEST_DB_URL)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Provide a transactional database session per test function with automatic rollback.

    Uses nested transactions (SAVEPOINT) so that code under test can commit or rollback
    without deassociating the outer test transaction or dropping pre-seeded test fixtures.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Establish initial SAVEPOINT
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active and connection.in_transaction():
            nested = connection.begin_nested()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient configured with the test database session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Seed Data Fixture ---
@pytest.fixture(scope="function")
def seed_data(db: Session):
    """Populate test database with two isolated tenants, multiple roles, projects, and tasks."""
    # 1. Tenants
    tenant_a = Tenant(name="Tenant Alpha Corp", slug="alpha-corp")
    tenant_b = Tenant(name="Tenant Beta Ltd", slug="beta-ltd")
    db.add_all([tenant_a, tenant_b])
    db.flush()

    # 2. Users
    user_alpha_admin = User(
        tenant_id=tenant_a.id,
        name="Alice Admin (Alpha)",
        email="admin@alpha.com",
        password_hash=hash_password("PasswordAlphaAdmin123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    user_alpha_member = User(
        tenant_id=tenant_a.id,
        name="Bob Member (Alpha)",
        email="member@alpha.com",
        password_hash=hash_password("PasswordAlphaMember123!"),
        role=UserRole.MEMBER.value,
        is_active=True,
    )
    user_alpha_inactive = User(
        tenant_id=tenant_a.id,
        name="Ian Inactive (Alpha)",
        email="inactive@alpha.com",
        password_hash=hash_password("PasswordAlphaInactive123!"),
        role=UserRole.MEMBER.value,
        is_active=False,
    )

    user_beta_admin = User(
        tenant_id=tenant_b.id,
        name="Carol Admin (Beta)",
        email="admin@beta.com",
        password_hash=hash_password("PasswordBetaAdmin123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    user_beta_member = User(
        tenant_id=tenant_b.id,
        name="Dave Member (Beta)",
        email="member@beta.com",
        password_hash=hash_password("PasswordBetaMember123!"),
        role=UserRole.MEMBER.value,
        is_active=True,
    )
    db.add_all(
        [
            user_alpha_admin,
            user_alpha_member,
            user_alpha_inactive,
            user_beta_admin,
            user_beta_member,
        ]
    )
    db.flush()

    # 3. Projects
    proj_a1 = Project(
        tenant_id=tenant_a.id,
        name="Alpha Project 1",
        description="First project belonging to Tenant Alpha",
        status=ProjectStatus.ACTIVE.value,
    )
    proj_a2 = Project(
        tenant_id=tenant_a.id,
        name="Alpha Project 2",
        description="Second project belonging to Tenant Alpha",
        status=ProjectStatus.ACTIVE.value,
    )
    proj_b1 = Project(
        tenant_id=tenant_b.id,
        name="Beta Project 1",
        description="Private project belonging to Tenant Beta",
        status=ProjectStatus.ACTIVE.value,
    )
    db.add_all([proj_a1, proj_a2, proj_b1])
    db.flush()

    # 4. Tasks
    task_a1 = Task(
        tenant_id=tenant_a.id,
        project_id=proj_a1.id,
        title="Alpha Task 1",
        description="Task in Alpha Project 1",
        status=TaskStatus.TODO.value,
    )
    task_a2 = Task(
        tenant_id=tenant_a.id,
        project_id=proj_a1.id,
        title="Alpha Task 2",
        description="Second task in Alpha Project 1",
        status=TaskStatus.DONE.value,
    )
    task_b1 = Task(
        tenant_id=tenant_b.id,
        project_id=proj_b1.id,
        title="Beta Task 1",
        description="Private task in Beta Project 1",
        status=TaskStatus.TODO.value,
    )
    db.add_all([task_a1, task_a2, task_b1])
    db.flush()

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "user_alpha_admin": user_alpha_admin,
        "user_alpha_member": user_alpha_member,
        "user_alpha_inactive": user_alpha_inactive,
        "user_beta_admin": user_beta_admin,
        "user_beta_member": user_beta_member,
        "project_a1": proj_a1,
        "project_a2": proj_a2,
        "project_b1": proj_b1,
        "task_a1": task_a1,
        "task_a2": task_a2,
        "task_b1": task_b1,
    }


# --- Auth Header Fixtures ---
@pytest.fixture
def alpha_admin_headers(seed_data) -> dict:
    user = seed_data["user_alpha_admin"]
    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def alpha_member_headers(seed_data) -> dict:
    user = seed_data["user_alpha_member"]
    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def beta_admin_headers(seed_data) -> dict:
    user = seed_data["user_beta_admin"]
    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def beta_member_headers(seed_data) -> dict:
    user = seed_data["user_beta_member"]
    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role)
    return {"Authorization": f"Bearer {token}"}
