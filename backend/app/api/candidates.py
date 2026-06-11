from fastapi import APIRouter

from app.core.security import create_session_token
from app.schemas.auth import LoginResponse
from app.schemas.candidate import CandidateLoginRequest, CandidateRead
from app.schemas.common import ApiResponse


router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/login", response_model=ApiResponse[CandidateRead])
def candidate_login(payload: CandidateLoginRequest) -> ApiResponse[CandidateRead]:
    candidate = CandidateRead(
        id=0,
        name=payload.name,
        employee_no=payload.employee_no,
        status="active",
    )
    return ApiResponse(data=candidate)


@router.post("/session", response_model=ApiResponse[LoginResponse], include_in_schema=False)
def candidate_session(payload: CandidateLoginRequest) -> ApiResponse[LoginResponse]:
    subject = payload.employee_no or payload.name
    return ApiResponse(data=LoginResponse(token=create_session_token(subject)))
