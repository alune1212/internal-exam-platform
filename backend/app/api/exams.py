from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id
from app.schemas.common import ApiResponse
from app.schemas.exam import (
    ExamCandidateRow,
    ExamCreate,
    ExamRead,
    ExamStartResponse,
    ExamUpdate,
    RankingRow,
)
from app.schemas.question import QuestionImportResult
from app.services import exam_service

router = APIRouter(prefix="/exams", tags=["exams"])
admin_router = APIRouter(prefix="/admin/exams", tags=["admin-exams"])


@router.get("/active", response_model=ApiResponse[list[ExamRead]])
def list_active_exams(db: Session = Depends(get_db)) -> ApiResponse[list[ExamRead]]:
    return ApiResponse(data=exam_service.list_active_exams(db))


@router.post("/{exam_id}/start", response_model=ApiResponse[ExamStartResponse])
def start_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[ExamStartResponse]:
    return ApiResponse(data=exam_service.start_exam(db, exam_id, candidate_id))


@router.get("/{exam_id}/ranking", response_model=ApiResponse[list[RankingRow]])
def get_ranking(
    exam_id: int, db: Session = Depends(get_db)
) -> ApiResponse[list[RankingRow]]:
    return ApiResponse(data=exam_service.get_ranking(db, exam_id))


@admin_router.post("", response_model=ApiResponse[ExamRead])
def create_exam(
    payload: ExamCreate, db: Session = Depends(get_db)
) -> ApiResponse[ExamRead]:
    return ApiResponse(data=exam_service.create_exam(db, payload))


@admin_router.get("", response_model=ApiResponse[list[ExamRead]])
def list_admin_exams(db: Session = Depends(get_db)) -> ApiResponse[list[ExamRead]]:
    return ApiResponse(data=exam_service.list_admin_exams(db))


@admin_router.put("/{exam_id}", response_model=ApiResponse[ExamRead])
def update_exam(
    exam_id: int, payload: ExamUpdate, db: Session = Depends(get_db)
) -> ApiResponse[ExamRead]:
    return ApiResponse(data=exam_service.update_exam(db, exam_id, payload))


@admin_router.post(
    "/{exam_id}/candidates/import", response_model=ApiResponse[QuestionImportResult]
)
def import_exam_candidates(
    exam_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ApiResponse[QuestionImportResult]:
    result = exam_service.import_exam_candidates_from_workbook(
        db, exam_id, file.file, file.filename or "candidates.xlsx"
    )
    return ApiResponse(data=result)


@admin_router.get(
    "/{exam_id}/candidates", response_model=ApiResponse[list[ExamCandidateRow]]
)
def list_exam_candidates(
    exam_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ExamCandidateRow]]:
    return ApiResponse(data=exam_service.list_exam_candidates(db, exam_id))


@admin_router.delete("/{exam_id}/candidates/{candidate_id}")
def remove_exam_candidate(
    exam_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, int]]:
    return ApiResponse(
        data=exam_service.remove_exam_candidate(db, exam_id, candidate_id)
    )


@admin_router.post(
    "/{exam_id}/candidates/{candidate_id}/retake-grants",
    response_model=ApiResponse[ExamCandidateRow],
)
def create_retake_grant(
    exam_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[ExamCandidateRow]:
    return ApiResponse(
        data=exam_service.create_retake_grant_row(db, exam_id, candidate_id)
    )
