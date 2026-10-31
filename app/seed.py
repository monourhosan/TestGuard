"""TestGuard Deterministic Database Seeder

Seeds the database with two isolated tenants (Tenant Alpha and Tenant Beta),
admin and member user accounts, sample projects, and sample tasks.
Idempotent: safe to run multiple times without duplicating records.
"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import ProjectStatus, TaskStatus, UserRole
from app.models.project import Project
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User


def seed_database(db: Session) -> None:
    print("[INFO] Starting TestGuard database seeding...")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # 1. Seed Tenants
    tenants_data = [
        {"name": "Tenant Alpha (Acme Corp)", "slug": "acme"},
        {"name": "Tenant Beta (Globex)", "slug": "globex"},
    ]

    tenants = {}
    for t_data in tenants_data:
        tenant = db.query(Tenant).filter(Tenant.slug == t_data["slug"]).first()
        if not tenant:
            tenant = Tenant(name=t_data["name"], slug=t_data["slug"])
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"[CREATED] Tenant: {tenant.name} (id={tenant.id}, slug={tenant.slug})")
        else:
            print(f"[EXISTS] Tenant: {tenant.name} (id={tenant.id})")
        tenants[t_data["slug"]] = tenant

    alpha = tenants["acme"]
    beta = tenants["globex"]

    # 2. Seed Users
    users_data = [
        # Tenant Alpha Users
        {
            "tenant_id": alpha.id,
            "name": "Alice Admin (Alpha)",
            "email": "admin@alpha.com",
            "password": "AdminPassword123!",
            "role": UserRole.ADMIN.value,
            "is_active": True,
        },
        {
            "tenant_id": alpha.id,
            "name": "Bob Member (Alpha)",
            "email": "member@alpha.com",
            "password": "MemberPassword123!",
            "role": UserRole.MEMBER.value,
            "is_active": True,
        },
        {
            "tenant_id": alpha.id,
            "name": "Inactive User (Alpha)",
            "email": "inactive@alpha.com",
            "password": "InactivePassword123!",
            "role": UserRole.MEMBER.value,
            "is_active": False,
        },
        # Tenant Beta Users
        {
            "tenant_id": beta.id,
            "name": "Carol Admin (Beta)",
            "email": "admin@beta.com",
            "password": "AdminPassword123!",
            "role": UserRole.ADMIN.value,
            "is_active": True,
        },
        {
            "tenant_id": beta.id,
            "name": "Dave Member (Beta)",
            "email": "member@beta.com",
            "password": "MemberPassword123!",
            "role": UserRole.MEMBER.value,
            "is_active": True,
        },
    ]

    for u_data in users_data:
        user = db.query(User).filter(User.email == u_data["email"]).first()
        if not user:
            user = User(
                tenant_id=u_data["tenant_id"],
                name=u_data["name"],
                email=u_data["email"],
                password_hash=hash_password(u_data["password"]),
                role=u_data["role"],
                is_active=u_data["is_active"],
            )
            db.add(user)
            db.commit()
            print(f"[CREATED] User: {user.email} (Tenant={user.tenant_id}, Role={user.role})")
        else:
            print(f"[EXISTS] User: {user.email}")

    # 3. Seed Projects
    projects_data = [
        {
            "tenant_id": alpha.id,
            "name": "Alpha Platform Modernization",
            "description": "Core backend service refactoring for Tenant Alpha",
            "status": ProjectStatus.ACTIVE.value,
        },
        {
            "tenant_id": alpha.id,
            "name": "Alpha Mobile Client",
            "description": "Mobile application development",
            "status": ProjectStatus.ACTIVE.value,
        },
        {
            "tenant_id": beta.id,
            "name": "Beta Supply Chain Analytics",
            "description": "Data pipelines and predictive models for Tenant Beta",
            "status": ProjectStatus.ACTIVE.value,
        },
    ]

    projects = {}
    for p_data in projects_data:
        project = (
            db.query(Project).filter(Project.tenant_id == p_data["tenant_id"], Project.name == p_data["name"]).first()
        )
        if not project:
            project = Project(
                tenant_id=p_data["tenant_id"],
                name=p_data["name"],
                description=p_data["description"],
                status=p_data["status"],
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            print(f"[CREATED] Project: '{project.name}' (id={project.id}, Tenant={project.tenant_id})")
        else:
            print(f"[EXISTS] Project: '{project.name}' (id={project.id})")
        projects[p_data["name"]] = project

    alpha_proj = projects["Alpha Platform Modernization"]
    beta_proj = projects["Beta Supply Chain Analytics"]

    # 4. Seed Tasks
    tasks_data = [
        {
            "tenant_id": alpha.id,
            "project_id": alpha_proj.id,
            "title": "Design REST API Endpoints",
            "description": "Draft OpenAPI 3.0 specification for v1 endpoints",
            "status": TaskStatus.DONE.value,
        },
        {
            "tenant_id": alpha.id,
            "project_id": alpha_proj.id,
            "title": "Implement JWT Security Middleware",
            "description": "Configure token issuance, expiration, and tenant scoping",
            "status": TaskStatus.IN_PROGRESS.value,
        },
        {
            "tenant_id": beta.id,
            "project_id": beta_proj.id,
            "title": "Data Warehouse ETL Ingestion",
            "description": "Build automated nightly ingestion DAGs",
            "status": TaskStatus.TODO.value,
        },
    ]

    for t_data in tasks_data:
        task = (
            db.query(Task)
            .filter(
                Task.tenant_id == t_data["tenant_id"],
                Task.project_id == t_data["project_id"],
                Task.title == t_data["title"],
            )
            .first()
        )
        if not task:
            task = Task(
                tenant_id=t_data["tenant_id"],
                project_id=t_data["project_id"],
                title=t_data["title"],
                description=t_data["description"],
                status=t_data["status"],
            )
            db.add(task)
            db.commit()
            print(f"[CREATED] Task: '{task.title}' (id={task.id}, Tenant={task.tenant_id})")
        else:
            print(f"[EXISTS] Task: '{task.title}' (id={task.id})")

    print("[SUCCESS] TestGuard database seeding completed successfully.")


if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        seed_database(db_session)
    finally:
        db_session.close()
