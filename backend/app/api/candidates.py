from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import check_public_token_rate_limit
from app.schemas.candidate import (
    CandidateLoginChallengeResponse,
    CandidateLoginRequest,
    CandidateLoginResponse,
    CandidateLoginVerifyRequest,
)
from app.schemas.common import ApiResponse
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/login", response_model=ApiResponse[CandidateLoginChallengeResponse])
def candidate_login(
    payload: CandidateLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginChallengeResponse]:
    identifier = f"{payload.name}:{payload.email or ''}:{payload.employee_no or ''}"
    check_public_token_rate_limit(
        request, bucket="candidate-login", identifier=identifier
    )
    request_ip = request.client.host if request.client else None
    return ApiResponse(
        data=candidate_service.request_candidate_login_challenge(
            db, payload, request_ip=request_ip
        )
    )


@router.post("/login/verify", response_model=ApiResponse[CandidateLoginResponse])
def verify_candidate_login(
    payload: CandidateLoginVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginResponse]:
    check_public_token_rate_limit(
        request,
        bucket="candidate-login-verify",
        identifier=f"challenge:{payload.challenge_id}",
    )
    return ApiResponse(
        data=candidate_service.verify_candidate_login_challenge(db, payload)
    )
