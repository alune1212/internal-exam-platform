from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import check_public_token_rate_limit
from app.schemas.candidate import CandidateLoginRequest, CandidateLoginResponse
from app.schemas.common import ApiResponse
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/login", response_model=ApiResponse[CandidateLoginResponse])
def candidate_login(
    payload: CandidateLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginResponse]:
    identifier = f"{payload.name}:{payload.employee_no or ''}"
    check_public_token_rate_limit(
        request, bucket="candidate-login", identifier=identifier
    )
    return ApiResponse(data=candidate_service.login_candidate(db, payload))
