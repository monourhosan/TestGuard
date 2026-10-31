from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int = Field(ge=0, description="Total number of matching records in current tenant")
    page: int = Field(ge=1, description="Current page number")
    size: int = Field(ge=1, description="Page size limit")
    pages: int = Field(ge=0, description="Total number of available pages")


class MessageResponse(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    detail: str
