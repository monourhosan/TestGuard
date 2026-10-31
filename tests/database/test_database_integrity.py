import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.enums import ProjectStatus, TaskStatus, UserRole
from app.models.project import Project
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import verify_test_database_safety


@pytest.mark.database
def test_db_records_persisted_after_creation(db: Session, seed_data):
    """DB-001: Direct SQL verification of entity persistence."""
    tenant = seed_data["tenant_a"]
    result = db.execute(text("SELECT name, slug FROM tenants WHERE id = :id"), {"id": tenant.id}).fetchone()
    assert result is not None
    assert result[0] == tenant.name
    assert result[1] == tenant.slug


@pytest.mark.database
def test_db_updates_reflected_in_database(db: Session, seed_data):
    """DB-002: Verify entity updates are directly written to the database."""
    project = seed_data["project_a1"]
    project.name = "Direct SQL Updated Name"
    db.commit()

    fresh_proj = db.query(Project).filter(Project.id == project.id).first()
    assert fresh_proj.name == "Direct SQL Updated Name"


@pytest.mark.database
def test_db_delete_cascades_tasks_when_project_is_deleted(db: Session, seed_data):
    """DB-003: Cascade verification - deleting a project removes its associated tasks."""
    proj = seed_data["project_a1"]
    proj_id = proj.id

    # Verify tasks exist for this project
    tasks_count_before = db.query(Task).filter(Task.project_id == proj_id).count()
    assert tasks_count_before > 0

    # Delete project
    db.delete(proj)
    db.commit()

    # Verify tasks were cascade deleted
    tasks_count_after = db.query(Task).filter(Task.project_id == proj_id).count()
    assert tasks_count_after == 0


@pytest.mark.database
def test_db_tenant_slug_unique_constraint(db: Session, seed_data):
    """DB-004: Enforce unique constraint on tenant slug at database level."""
    slug = seed_data["tenant_a"].slug
    duplicate_tenant = Tenant(name="Duplicate Slug Tenant", slug=slug)
    db.add(duplicate_tenant)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.database
def test_db_user_email_unique_constraint(db: Session, seed_data):
    """DB-005: Enforce unique constraint on user email across tenants."""
    email = seed_data["user_alpha_admin"].email
    tenant_b = seed_data["tenant_b"]
    duplicate_user = User(
        tenant_id=tenant_b.id,
        name="Collision User",
        email=email,
        password_hash="dummy_hash",
        role=UserRole.MEMBER.value,
        is_active=True,
    )
    db.add(duplicate_user)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.database
def test_db_foreign_key_rejects_nonexistent_tenant(db: Session):
    """DB-006: Foreign key rejects project creation for nonexistent tenant ID."""
    orphan_proj = Project(
        tenant_id=999999,
        name="Orphan Project",
        status=ProjectStatus.ACTIVE.value,
    )
    db.add(orphan_proj)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.database
def test_db_composite_foreign_key_blocks_cross_tenant_task(db: Session, seed_data):
    """DB-007: Composite foreign key (project_id, tenant_id) rejects task attached to another tenant's project."""
    alpha_tenant = seed_data["tenant_a"]
    beta_project = seed_data["project_b1"]

    # Attempt to create task with Tenant Alpha, but referencing Tenant Beta's project
    invalid_task = Task(
        tenant_id=alpha_tenant.id,
        project_id=beta_project.id,
        title="Cross Tenant DB Task",
        status=TaskStatus.TODO.value,
    )
    db.add(invalid_task)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.database
def test_db_passwords_stored_as_bcrypt_hashes_never_plaintext(db: Session, seed_data):
    """DB-008: Verify database stores encrypted bcrypt hashes and no plaintext passwords."""
    user = seed_data["user_alpha_admin"]
    raw_hash = db.execute(text("SELECT password_hash FROM users WHERE id = :id"), {"id": user.id}).scalar()

    assert raw_hash.startswith("$2b$") or raw_hash.startswith("$2a$")
    assert raw_hash != "PasswordAlphaAdmin123!"
    assert verify_password("PasswordAlphaAdmin123!", raw_hash) is True


@pytest.mark.database
def test_db_transaction_rollback_leaves_no_partial_state(db: Session, seed_data):
    """DB-009: Failed transaction cleanly rolls back and leaves no orphaned records."""
    tenant = seed_data["tenant_a"]
    initial_count = db.query(Project).filter(Project.tenant_id == tenant.id).count()

    # Begin a nested transaction (savepoint)
    sp = db.begin_nested()
    try:
        # Valid project added
        p1 = Project(tenant_id=tenant.id, name="Atomic Rollback Test", status="active")
        db.add(p1)
        db.flush()

        # Intentionally trigger an IntegrityError in the same nested transaction
        invalid_p = Project(tenant_id=999999, name="Failed Project", status="active")
        db.add(invalid_p)
        db.flush()
    except IntegrityError:
        sp.rollback()

    # Confirm initial count unchanged
    final_count = db.query(Project).filter(Project.tenant_id == tenant.id).count()
    assert final_count == initial_count


@pytest.mark.database
def test_db_safety_check_blocks_unsafe_database_urls():
    """DB-010: Database safety guard raises RuntimeError when run against production URL."""
    with pytest.raises(RuntimeError) as exc_info:
        verify_test_database_safety("postgresql://prod_user:secret@prod-db.example.com:5432/production_app")
    assert "SAFETY VIOLATION" in str(exc_info.value)
