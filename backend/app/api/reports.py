from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.report import (
    AbsentCandidateRow,
    QuestionAccuracyRow,
    ScoreReportRow,
    WrongQuestionRow,
)
from app.services import report_service

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


@router.get("/scores", response_model=ApiResponse[list[ScoreReportRow]])
def get_score_report(
    db: Session = Depends(get_db),
) -> ApiResponse[list[ScoreReportRow]]:
    return ApiResponse(data=report_service.get_score_report(db))


@router.get("/question-accuracy", response_model=ApiResponse[list[QuestionAccuracyRow]])
def get_question_accuracy(
    db: Session = Depends(get_db),
) -> ApiResponse[list[QuestionAccuracyRow]]:
    return ApiResponse(data=report_service.get_question_accuracy(db))


@router.get("/wrong-questions", response_model=ApiResponse[list[WrongQuestionRow]])
def get_wrong_questions(
    db: Session = Depends(get_db),
) -> ApiResponse[list[WrongQuestionRow]]:
    return ApiResponse(data=report_service.get_wrong_questions(db))


@router.get("/absent-candidates", response_model=ApiResponse[list[AbsentCandidateRow]])
def get_absent_candidates(
    exam_id: int | None = None,
    status: str = "not_started",
    db: Session = Depends(get_db),
) -> ApiResponse[list[AbsentCandidateRow]]:
    return ApiResponse(
        data=report_service.get_absent_candidates(db, exam_id=exam_id, status=status)
    )


@router.get("/export")
def export_report(db: Session = Depends(get_db)) -> StreamingResponse:
    stream = report_service.generate_report_workbook(db)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('考试报表.xlsx')}"
        },
    )
