import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_admin
from app.core.exceptions import ResourceNotFoundException
from app.models.project import Project
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ProjectResponse],
    summary="List projects for current tenant",
)
def list_projects(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status (active, archived)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve paginated projects strictly scoped to the authenticated user's tenant."""
    query = db.query(Project).filter(Project.tenant_id == current_user.tenant_id)

    if status:
        query = query.filter(Project.status == status)

    total = query.count()
    pages = math.ceil(total / size) if total > 0 else 0
    offset = (page - 1) * size

    projects = query.order_by(Project.created_at.desc()).offset(offset).limit(size).all()

    return PaginatedResponse(
        items=projects,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project (Admin only)",
)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new project. Enforces admin role and binds strictly to the caller's tenant."""
    # Check for duplicate project name within the same tenant
    existing = (
        db.query(Project).filter(Project.tenant_id == current_user.tenant_id, Project.name == project_in.name).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A project with name '{project_in.name}' already exists in your organization",
        )

    project = Project(
        tenant_id=current_user.tenant_id,
        name=project_in.name,
        description=project_in.description,
        status=project_in.status.value if project_in.status else "active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project by ID in current tenant")
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single project. Returns 404 if not found or if owned by another tenant."""
    if project_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id).first()
    if not project:
        raise ResourceNotFoundException("Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse, summary="Update project (Admin only)")
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update project details. Requires admin privileges and tenant ownership."""
    if project_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id).first()
    if not project:
        raise ResourceNotFoundException("Project not found")

    update_data = project_in.model_dump(exclude_unset=True)
    if not update_data:
        return project

    if "name" in update_data and update_data["name"] is not None:
        # Check duplicate name within tenant
        duplicate = (
            db.query(Project)
            .filter(
                Project.tenant_id == current_user.tenant_id,
                Project.name == update_data["name"],
                Project.id != project_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with name '{update_data['name']}' already exists",
            )
        project.name = update_data["name"]

    if "description" in update_data:
        project.description = update_data["description"]
    if "status" in update_data and update_data["status"] is not None:
        project.status = (
            update_data["status"].value if hasattr(update_data["status"], "value") else str(update_data["status"])
        )

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", response_model=MessageResponse, summary="Delete project (Admin only)")
def delete_project(
    project_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a project and its associated tasks. Requires admin privileges and tenant ownership."""
    if project_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id).first()
    if not project:
        raise ResourceNotFoundException("Project not found")

    db.delete(project)
    db.commit()
    return MessageResponse(message=f"Project {project_id} deleted successfully")
