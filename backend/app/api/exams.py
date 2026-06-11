from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.exam import ExamCreate, ExamRead, ExamStartRequest, ExamStartResponse, ExamUpdate, RankingRow
from app.schemas.question import QuestionImportResult
from app.services import exam_service, import_service
from app.services.exam_service import (
    AttemptAlreadyExistsError,
    CandidateNotFoundError,
    ExamNotActiveError,
    ExamNotFoundError,
)


router = APIRouter(prefix="/exams", tags=["exams"])
admin_router = APIRouter(prefix="/admin/exams", tags=["admin-exams"])


@router.get("/active", response_model=ApiResponse[list[ExamRead]])
def list_active_exams(db: Session = Depends(get_db)) -> ApiResponse[list[ExamRead]]:
    return ApiResponse(data=exam_service.list_active_exams(db))


@router.post("/{exam_id}/start", response_model=ApiResponse[ExamStartResponse])
def start_exam(
    exam_id: int,
    payload: ExamStartRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[ExamStartResponse]:
    try:
        return ApiResponse(data=exam_service.start_exam(db, exam_id, payload.candidate_id))
    except ExamNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExamNotActiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AttemptAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{exam_id}/ranking", response_model=ApiResponse[list[RankingRow]])
def get_ranking(exam_id: int, db: Session = Depends(get_db)) -> ApiResponse[list[RankingRow]]:
    return ApiResponse(data=exam_service.get_ranking(db, exam_id))


@admin_router.post("", response_model=ApiResponse[ExamRead])
def create_exam(payload: ExamCreate, db: Session = Depends(get_db)) -> ApiResponse[ExamRead]:
    return ApiResponse(data=exam_service.create_exam(db, payload))


@admin_router.get("", response_model=ApiResponse[list[ExamRead]])
def list_admin_exams(db: Session = Depends(get_db)) -> ApiResponse[list[ExamRead]]:
    return ApiResponse(data=exam_service.list_admin_exams(db))


@admin_router.put("/{exam_id}", response_model=ApiResponse[ExamRead])
def update_exam(exam_id: int, payload: ExamUpdate, db: Session = Depends(get_db)) -> ApiResponse[ExamRead]:
    try:
        return ApiResponse(data=exam_service.update_exam(db, exam_id, payload))
    except ExamNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.post("/{exam_id}/candidates/import", response_model=ApiResponse[QuestionImportResult])
def import_exam_candidates(
    exam_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ApiResponse[QuestionImportResult]:
    result = import_service.import_candidates_from_workbook(db, file.file, file.filename or "candidates.xlsx")
    return ApiResponse(data=result)
