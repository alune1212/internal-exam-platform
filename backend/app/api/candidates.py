from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_session_token
from app.schemas.auth import LoginResponse
from app.schemas.candidate import CandidateLoginRequest, CandidateRead
from app.schemas.common import ApiResponse
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/login", response_model=ApiResponse[CandidateRead])
def candidate_login(
    payload: CandidateLoginRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateRead]:
    return ApiResponse(data=candidate_service.login_candidate(db, payload))


@router.post(
    "/session", response_model=ApiResponse[LoginResponse], include_in_schema=False
)
def candidate_session(payload: CandidateLoginRequest) -> ApiResponse[LoginResponse]:
    subject = payload.employee_no or payload.name
    return ApiResponse(data=LoginResponse(token=create_session_token(subject)))
