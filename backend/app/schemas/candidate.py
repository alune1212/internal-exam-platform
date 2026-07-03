from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel

CandidateLoginName = Annotated[str, Field(max_length=100)]
CandidateLoginEmployeeNo = Annotated[str, Field(max_length=100)]
CandidateLoginPhoneSuffix = Annotated[str, Field(max_length=20)]
CandidateLoginOtp = Annotated[str, Field(min_length=1, max_length=20)]


class CandidateLoginRequest(BaseModel):
    name: CandidateLoginName
    employee_no: CandidateLoginEmployeeNo | None = None
    email: EmailStr | None = None
    phone_suffix: CandidateLoginPhoneSuffix | None = None


class CandidateLoginChallengeResponse(BaseModel):
    challenge_id: int
    expires_at: datetime
    resend_available_at: datetime


class CandidateLoginVerifyRequest(BaseModel):
    challenge_id: int
    otp: CandidateLoginOtp


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
