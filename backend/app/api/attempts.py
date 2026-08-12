from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id, get_fresh_candidate_id
from app.schemas.attempt import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AttemptRead,
    AttemptResultRead,
    AttemptSessionTakeoverResponse,
    SubmitRequest,
)
from app.schemas.common import ApiResponse
from app.services import exam_service
from app.services.exam_service import AttemptNotFoundError

router = APIRouter(prefix="/attempts", tags=["attempts"])


def _verify_attempt_ownership(db: Session, attempt_id: int, candidate_id: int) -> None:
    from app.models import ExamAttempt, ExamCandidateScope

    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    if attempt.candidate_id != candidate_id:
        raise AttemptNotFoundError(attempt_id)
    scoped = (
        db.query(ExamCandidateScope.id)
        .filter(
            ExamCandidateScope.exam_id == attempt.exam_id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .first()
    )
    if scoped is None:
        # Keep result ownership opaque when a stale attempt has no current
        # formal roster scope.
        raise AttemptNotFoundError(attempt_id)


@router.get("/{attempt_id}", response_model=ApiResponse[AttemptRead])
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
    attempt_session: str | None = Header(None, alias="X-Attempt-Session"),
) -> ApiResponse[AttemptRead]:
    exam_service.verify_attempt_session(db, attempt_id, candidate_id, attempt_session)
    return ApiResponse(data=exam_service.get_attempt(db, attempt_id))


@router.post(
    "/{attempt_id}/answers/save", response_model=ApiResponse[AnswerSaveResponse]
)
def save_answers(
    attempt_id: int,
    payload: AnswerSaveRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
    attempt_session: str | None = Header(None, alias="X-Attempt-Session"),
) -> ApiResponse[AnswerSaveResponse]:
    exam_service.verify_attempt_session(db, attempt_id, candidate_id, attempt_session)
    return ApiResponse(data=exam_service.save_answers(db, attempt_id, payload))


@router.post("/{attempt_id}/submit", response_model=ApiResponse[AttemptResultRead])
def submit_attempt(
    attempt_id: int,
    payload: SubmitRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
    attempt_session: str | None = Header(None, alias="X-Attempt-Session"),
) -> ApiResponse[AttemptResultRead]:
    exam_service.verify_attempt_session(db, attempt_id, candidate_id, attempt_session)
    return ApiResponse(
        data=exam_service.submit_attempt(db, attempt_id, payload.submit_type)
    )


@router.post(
    "/{attempt_id}/takeover",
    response_model=ApiResponse[AttemptSessionTakeoverResponse],
)
def takeover_attempt_session(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_fresh_candidate_id),
) -> ApiResponse[AttemptSessionTakeoverResponse]:
    return ApiResponse(
        data=exam_service.takeover_attempt_session(db, attempt_id, candidate_id)
    )


@router.get("/{attempt_id}/result", response_model=ApiResponse[AttemptResultRead])
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptResultRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.get_attempt_result(db, attempt_id))
