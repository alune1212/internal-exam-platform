import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
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
from app.services.email_service import send_candidate_login_otp

router = APIRouter(prefix="/candidates", tags=["candidates"])

logger = logging.getLogger(__name__)


def _send_otp_background(
    *,
    to_email: str,
    candidate_name: str,
    otp: str,
    expires_at: str,
) -> None:
    """BackgroundTasks entry point — never raises into the request lifecycle.

    SMTP errors are logged at WARN. The challenge row is already committed
    by the service, so a delivery failure does not roll back persisted state
    and does not surface a 5xx to the caller. The candidate can request a
    new challenge via the existing resend flow.
    """
    from datetime import datetime

    try:
        send_candidate_login_otp(
            to_email=to_email,
            candidate_name=candidate_name,
            otp=otp,
            expires_at=datetime.fromisoformat(expires_at),
        )
    except Exception:  # background task must not propagate
        logger.warning(
            "candidate_login.email_delivery_failed",
            extra={
                "event": "candidate_login.email_delivery_failed",
                "to_email_sha256": f"sha256:{__import__('hashlib').sha256(to_email.encode('utf-8')).hexdigest()}",
            },
            exc_info=True,
        )


@router.post("/login", response_model=ApiResponse[CandidateLoginChallengeResponse])
def candidate_login(
    payload: CandidateLoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginChallengeResponse]:
    identifier = f"{payload.name}:{payload.email or ''}:{payload.employee_no or ''}"
    check_public_token_rate_limit(
        request, bucket="candidate-login", identifier=identifier
    )
    request_ip = request.client.host if request.client else None
    result = candidate_service.request_candidate_login_challenge(
        db, payload, request_ip=request_ip
    )
    if result.email is not None:
        background_tasks.add_task(
            _send_otp_background,
            to_email=result.email.to_email,
            candidate_name=result.email.candidate_name,
            otp=result.email.otp,
            expires_at=result.email.expires_at.isoformat(),
        )
    return ApiResponse(data=result.response)


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
