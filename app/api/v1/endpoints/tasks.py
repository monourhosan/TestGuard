import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_admin
from app.core.exceptions import ResourceNotFoundException
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TaskResponse], summary="List tasks for current tenant")
def list_tasks(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    project_id: Optional[int] = Query(default=None, ge=1, description="Filter by project ID"),
    status: Optional[str] = Query(default=None, description="Filter by status (todo, in_progress, done)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List paginated tasks strictly scoped to the authenticated user's tenant."""
    query = db.query(Task).filter(Task.tenant_id == current_user.tenant_id)

    if project_id is not None:
        # Also ensure the filtered project belongs to this tenant
        query = query.filter(Task.project_id == project_id)

    if status:
        query = query.filter(Task.status == status)

    total = query.count()
    pages = math.ceil(total / size) if total > 0 else 0
    offset = (page - 1) * size

    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(size).all()

    return PaginatedResponse(
        items=tasks,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task within a tenant-owned project. Both Admin and Member can create tasks."""
    # Strict Tenant Isolation Check: Verify parent project belongs to the user's tenant
    project = (
        db.query(Project).filter(Project.id == task_in.project_id, Project.tenant_id == current_user.tenant_id).first()
    )
    if not project:
        # Return 404 to avoid leaking whether the project exists in another tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent project not found in current organization",
        )

    task = Task(
        tenant_id=current_user.tenant_id,
        project_id=task_in.project_id,
        title=task_in.title,
        description=task_in.description,
        status=task_in.status.value if task_in.status else "todo",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskResponse, summary="Get task by ID in current tenant")
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single task. Returns 404 if not found or if owned by another tenant."""
    if task_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID")

    task = db.query(Task).filter(Task.id == task_id, Task.tenant_id == current_user.tenant_id).first()
    if not task:
        raise ResourceNotFoundException("Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse, summary="Update task")
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update task details. Both Admin and Member can update tasks within their own tenant."""
    if task_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID")

    task = db.query(Task).filter(Task.id == task_id, Task.tenant_id == current_user.tenant_id).first()
    if not task:
        raise ResourceNotFoundException("Task not found")

    update_data = task_in.model_dump(exclude_unset=True)
    if not update_data:
        return task

    if "title" in update_data and update_data["title"] is not None:
        task.title = update_data["title"]
    if "description" in update_data:
        task.description = update_data["description"]
    if "status" in update_data and update_data["status"] is not None:
        task.status = (
            update_data["status"].value if hasattr(update_data["status"], "value") else str(update_data["status"])
        )

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", response_model=MessageResponse, summary="Delete task (Admin only)")
def delete_task(
    task_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a task. Requires admin privileges and tenant ownership."""
    if task_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID")

    task = db.query(Task).filter(Task.id == task_id, Task.tenant_id == current_user.tenant_id).first()
    if not task:
        raise ResourceNotFoundException("Task not found")

    db.delete(task)
    db.commit()
    return MessageResponse(message=f"Task {task_id} deleted successfully")
