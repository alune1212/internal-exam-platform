from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id
from app.schemas.common import ApiResponse
from app.schemas.practice import (
    PracticeAnswerResult,
    PracticeAnswerSubmitRequest,
    PracticeWrongQuestionRead,
)
from app.schemas.question import PracticeQuestionRead
from app.services import practice_service, question_service

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/questions", response_model=ApiResponse[list[PracticeQuestionRead]])
def list_practice_questions(
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[PracticeQuestionRead]]:
    practice_service.get_active_practice_candidate(db, candidate_id)
    questions = question_service.list_active_questions(db)
    return ApiResponse(
        data=[PracticeQuestionRead.model_validate(question) for question in questions]
    )


@router.post("/answers", response_model=ApiResponse[PracticeAnswerResult])
def save_practice_answer(
    payload: PracticeAnswerSubmitRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[PracticeAnswerResult]:
    return ApiResponse(
        data=practice_service.submit_practice_answer(db, candidate_id, payload)
    )


@router.get(
    "/wrong-questions", response_model=ApiResponse[list[PracticeWrongQuestionRead]]
)
def list_wrong_questions(
    category_1: str | None = None,
    category_2: str | None = None,
    mastered: bool | None = None,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[PracticeWrongQuestionRead]]:
    return ApiResponse(
        data=practice_service.list_wrong_questions(
            db,
            candidate_id,
            category_1=category_1,
            category_2=category_2,
            mastered=mastered,
        )
    )
