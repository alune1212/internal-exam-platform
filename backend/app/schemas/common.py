from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str = "ok"


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: str = "bad_request"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
