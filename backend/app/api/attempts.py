from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id
from app.schemas.attempt import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AttemptRead,
    AttemptResultRead,
    SubmitRequest,
)
from app.schemas.common import ApiResponse
from app.services import exam_service
from app.services.exam_service import AttemptNotFoundError

router = APIRouter(prefix="/attempts", tags=["attempts"])


def _verify_attempt_ownership(db: Session, attempt_id: int, candidate_id: int) -> None:
    from app.models import ExamAttempt

    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    if attempt.candidate_id != candidate_id:
        raise AttemptNotFoundError(attempt_id)


@router.get("/{attempt_id}", response_model=ApiResponse[AttemptRead])
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.get_attempt(db, attempt_id))


@router.post(
    "/{attempt_id}/answers/save", response_model=ApiResponse[AnswerSaveResponse]
)
def save_answers(
    attempt_id: int,
    payload: AnswerSaveRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AnswerSaveResponse]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.save_answers(db, attempt_id, payload))


@router.post("/{attempt_id}/submit", response_model=ApiResponse[AttemptResultRead])
def submit_attempt(
    attempt_id: int,
    payload: SubmitRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptResultRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(
        data=exam_service.submit_attempt(db, attempt_id, payload.submit_type)
    )


@router.get("/{attempt_id}/result", response_model=ApiResponse[AttemptResultRead])
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptResultRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.get_attempt_result(db, attempt_id))
