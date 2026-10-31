from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import TaskStatus

NonEmptyTaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class TaskCreate(BaseModel):
    project_id: int = Field(gt=0, description="Parent project ID belonging to current tenant")
    title: NonEmptyTaskTitle
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[TaskStatus] = TaskStatus.TODO


class TaskUpdate(BaseModel):
    title: Optional[NonEmptyTaskTitle] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[TaskStatus] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    project_id: int
    title: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
