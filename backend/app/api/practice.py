from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.practice import PracticeAnswerResult, PracticeAnswerSubmitRequest
from app.schemas.question import QuestionRead
from app.services import practice_service, question_service

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/questions", response_model=ApiResponse[list[QuestionRead]])
def list_practice_questions(
    db: Session = Depends(get_db),
) -> ApiResponse[list[QuestionRead]]:
    return ApiResponse(data=question_service.list_active_questions(db))


@router.post("/answers", response_model=ApiResponse[PracticeAnswerResult])
def save_practice_answer(
    payload: PracticeAnswerSubmitRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[PracticeAnswerResult]:
    return ApiResponse(data=practice_service.submit_practice_answer(db, payload))
