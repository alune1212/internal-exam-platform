from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
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
