from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import ProjectStatus

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class ProjectBase(BaseModel):
    name: NonEmptyString
    description: Optional[str] = Field(default=None, max_length=1000)
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectCreate(BaseModel):
    name: NonEmptyString
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[ProjectStatus] = ProjectStatus.ACTIVE


class ProjectUpdate(BaseModel):
    name: Optional[NonEmptyString] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
