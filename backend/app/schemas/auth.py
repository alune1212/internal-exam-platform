from typing import Annotated

from pydantic import BaseModel, Field

LoginText = Annotated[str, Field(max_length=128)]


class AdminLoginRequest(BaseModel):
    username: LoginText
    password: LoginText


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
