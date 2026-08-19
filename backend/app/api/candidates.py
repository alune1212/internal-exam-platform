import logging
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id, require_admin
from app.core.rate_limit import check_public_token_rate_limit
from app.schemas.candidate import (
    AccountAdminRead,
    AccountProfileRead,
    AccountStatusUpdate,
    AuthenticatedCandidateLoginResponse,
    CandidateLoginChallengeResponse,
    CandidateLoginRequest,
    CandidateLoginVerifyRequest,
    CandidateLoginVerifyResponse,
    CandidateProfileUpdate,
    RegistrationCompleteRequest,
)
from app.schemas.common import ApiResponse
from app.services import candidate_service
from app.services.email_service import deliver_candidate_login_otp

router = APIRouter(prefix="/candidates", tags=["candidates"])
account_router = APIRouter(prefix="/account", tags=["account"])
admin_accounts_router = APIRouter(prefix="/admin/accounts", tags=["admin-accounts"])

logger = logging.getLogger(__name__)


def _send_otp_background(
    *,
    challenge_id: int,
    to_email: str,
    candidate_name: str,
    otp: str,
    expires_at: str,
) -> None:
    """Deliver a committed challenge without changing the HTTP response."""

    from datetime import datetime

    try:
        deliver_candidate_login_otp(
            challenge_id=challenge_id,
            to_email=to_email,
            candidate_name=candidate_name,
            otp=otp,
            expires_at=datetime.fromisoformat(expires_at),
        )
    except Exception as exc:  # pragma: no cover - defensive background boundary
        logger.warning(
            "candidate_login.email_delivery_failed",
            extra={
                "event": "candidate_login.email_delivery_failed",
                "challenge_id": challenge_id,
                "attempt": 0,
                "error_type": type(exc).__name__,
            },
        )


@router.post("/login", response_model=ApiResponse[CandidateLoginChallengeResponse])
def candidate_login(
    payload: CandidateLoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginChallengeResponse]:
    check_public_token_rate_limit(
        request, bucket="candidate-login", identifier=payload.email
    )
    request_ip = request.client.host if request.client else None
    result = candidate_service.request_candidate_login_challenge(
        db, payload, request_ip=request_ip
    )
    background_tasks.add_task(
        _send_otp_background,
        challenge_id=result.response.challenge_id,
        to_email=result.email.to_email,
        candidate_name=result.email.candidate_name,
        otp=result.email.otp,
        expires_at=result.email.expires_at.isoformat(),
    )
    return ApiResponse(data=result.response)


@router.post("/login/verify", response_model=ApiResponse[CandidateLoginVerifyResponse])
def verify_candidate_login(
    payload: CandidateLoginVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginVerifyResponse]:
    check_public_token_rate_limit(
        request,
        bucket="candidate-login-verify",
        identifier=f"challenge:{payload.challenge_id}",
    )
    return ApiResponse(
        data=candidate_service.verify_candidate_login_challenge(db, payload)
    )


@router.post(
    "/register/complete",
    response_model=ApiResponse[AuthenticatedCandidateLoginResponse],
)
def complete_candidate_registration(
    payload: RegistrationCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[AuthenticatedCandidateLoginResponse]:
    check_public_token_rate_limit(
        request,
        bucket="candidate-registration-complete",
        identifier=payload.registration_credential,
    )
    return ApiResponse(data=candidate_service.complete_registration(db, payload))


@account_router.get("/profile", response_model=ApiResponse[AccountProfileRead])
def get_account_profile(
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AccountProfileRead]:
    return ApiResponse(data=candidate_service.get_account_profile(db, candidate_id))


@account_router.patch("/profile", response_model=ApiResponse[AccountProfileRead])
def update_account_profile(
    payload: CandidateProfileUpdate,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AccountProfileRead]:
    return ApiResponse(
        data=candidate_service.update_account_profile(db, candidate_id, payload)
    )


@admin_accounts_router.get("", response_model=ApiResponse[list[AccountAdminRead]])
def search_accounts(
    search: str | None = Query(default=None),
    q: str | None = Query(default=None),
    status: Literal["pending", "active", "inactive"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[list[AccountAdminRead]]:
    return ApiResponse(
        data=candidate_service.list_accounts(
            db, query=search or q, status=status, limit=limit, offset=offset
        )
    )


def _set_account_status_handler(
    candidate_id: int,
    payload: AccountStatusUpdate,
    request: Request,
    db: Session,
    operator_subject: str,
) -> ApiResponse[AccountAdminRead]:
    return ApiResponse(
        data=candidate_service.set_account_status(
            db,
            candidate_id,
            payload.status,
            operator_subject=operator_subject,
            request=request,
        )
    )


@admin_accounts_router.patch(
    "/{candidate_id}/status", response_model=ApiResponse[AccountAdminRead]
)
def update_account_status(
    candidate_id: int,
    payload: AccountStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[AccountAdminRead]:
    return _set_account_status_handler(
        candidate_id, payload, request, db, operator_subject
    )


@admin_accounts_router.patch(
    "/{candidate_id}", response_model=ApiResponse[AccountAdminRead]
)
def update_account_status_compat(
    candidate_id: int,
    payload: AccountStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[AccountAdminRead]:
    """Compatibility spelling for clients that PATCH the account resource."""

    return _set_account_status_handler(
        candidate_id, payload, request, db, operator_subject
    )


@admin_accounts_router.post(
    "/{candidate_id}/activate", response_model=ApiResponse[AccountAdminRead]
)
def activate_account(
    candidate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[AccountAdminRead]:
    return ApiResponse(
        data=candidate_service.set_account_status(
            db,
            candidate_id,
            "active",
            operator_subject=operator_subject,
            request=request,
        )
    )


@admin_accounts_router.post(
    "/{candidate_id}/deactivate", response_model=ApiResponse[AccountAdminRead]
)
def deactivate_account(
    candidate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[AccountAdminRead]:
    return ApiResponse(
        data=candidate_service.set_account_status(
            db,
            candidate_id,
            "inactive",
            operator_subject=operator_subject,
            request=request,
        )
    )
