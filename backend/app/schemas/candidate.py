from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class CandidateLoginRequest(BaseModel):
    name: str
    employee_no: str | None = None
    phone_suffix: str | None = None


class CandidateBase(BaseModel):
    name: str
    employee_no: str | None = None
    department: str | None = None
    position: str | None = None
    phone_suffix: str | None = None
    email: EmailStr | None = None
    exam_group: str | None = None
    should_attend: bool = True
    status: str = "active"
    remark: str | None = None


class CandidateRead(CandidateBase, ORMModel):
    id: int


class CandidateLoginResponse(CandidateRead):
    token: str


class CandidateImportRow(CandidateBase):
    pass
