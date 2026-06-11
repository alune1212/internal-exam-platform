from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.attempt import AnswerSaveRequest, AnswerSaveResponse, AttemptRead, AttemptResultRead, SubmitRequest
from app.schemas.common import ApiResponse
from app.services import exam_service
from app.services.exam_service import AttemptNotFoundError, AttemptQuestionNotFoundError


router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.get("/{attempt_id}", response_model=ApiResponse[AttemptRead])
def get_attempt(attempt_id: int, db: Session = Depends(get_db)) -> ApiResponse[AttemptRead]:
    try:
        return ApiResponse(data=exam_service.get_attempt(db, attempt_id))
    except AttemptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{attempt_id}/answers/save", response_model=ApiResponse[AnswerSaveResponse])
def save_answers(
    attempt_id: int,
    payload: AnswerSaveRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[AnswerSaveResponse]:
    try:
        return ApiResponse(data=exam_service.save_answers(db, attempt_id, payload))
    except (AttemptNotFoundError, AttemptQuestionNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{attempt_id}/submit", response_model=ApiResponse[AttemptResultRead])
def submit_attempt(
    attempt_id: int,
    payload: SubmitRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[AttemptResultRead]:
    try:
        return ApiResponse(data=exam_service.submit_attempt(db, attempt_id, payload.submit_type))
    except AttemptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{attempt_id}/result", response_model=ApiResponse[AttemptResultRead])
def get_attempt_result(attempt_id: int, db: Session = Depends(get_db)) -> ApiResponse[AttemptResultRead]:
    try:
        return ApiResponse(data=exam_service.get_attempt_result(db, attempt_id))
    except AttemptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
