from pydantic import BaseModel, ConfigDict


class ApiResponse[T](BaseModel):
    success: bool = True
    data: T
    message: str = "ok"


class ReadinessStatus(BaseModel):
    status: str = "ready"
    database: str = "ok"
    learning_media: str = "ok"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
