from pydantic import BaseModel, ConfigDict


class ApiResponse[T](BaseModel):
    success: bool = True
    data: T
    message: str = "ok"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
