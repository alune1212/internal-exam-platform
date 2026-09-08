from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id
from app.core.rate_limit import check_public_token_rate_limit
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
    request: Request,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=2**31 - 1),
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[PracticeQuestionRead]]:
    candidate = practice_service.get_active_practice_candidate(db, candidate_id)
    check_public_token_rate_limit(
        request,
        bucket="practice-questions",
        identifier=f"candidate:{candidate.id}",
        include_client_ip=False,
    )
    questions = question_service.list_active_questions(db, limit=limit, offset=offset)
    return ApiResponse(
        data=[PracticeQuestionRead.model_validate(question) for question in questions]
    )


@router.post("/answers", response_model=ApiResponse[PracticeAnswerResult])
def save_practice_answer(
    payload: PracticeAnswerSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[PracticeAnswerResult]:
    return ApiResponse(
        data=practice_service.submit_practice_answer(
            db, candidate_id, payload, request=request
        )
    )


@router.get(
    "/wrong-questions", response_model=ApiResponse[list[PracticeWrongQuestionRead]]
)
def list_wrong_questions(
    request: Request,
    category_1: str | None = None,
    category_2: str | None = None,
    mastered: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=2**31 - 1),
    history_limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[PracticeWrongQuestionRead]]:
    check_public_token_rate_limit(
        request,
        bucket="practice-wrong-questions",
        identifier=f"candidate:{candidate_id}",
        include_client_ip=False,
    )
    return ApiResponse(
        data=practice_service.list_wrong_questions(
            db,
            candidate_id,
            category_1=category_1,
            category_2=category_2,
            mastered=mastered,
            limit=limit,
            offset=offset,
            history_limit=history_limit,
        )
    )
