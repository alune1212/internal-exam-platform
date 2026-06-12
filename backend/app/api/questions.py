from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.question import (
    QuestionCreate,
    QuestionImportResult,
    QuestionRead,
    QuestionUpdate,
)
from app.services import import_service, question_service

router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])


@router.post("/import", response_model=ApiResponse[QuestionImportResult])
def import_questions(
    file: UploadFile, db: Session = Depends(get_db)
) -> ApiResponse[QuestionImportResult]:
    result = import_service.import_questions_from_workbook(
        db, file.file, file.filename or "questions.xlsx"
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[list[QuestionRead]])
def list_questions(db: Session = Depends(get_db)) -> ApiResponse[list[QuestionRead]]:
    return ApiResponse(data=question_service.list_questions(db))


@router.post("", response_model=ApiResponse[QuestionRead])
def create_question(
    payload: QuestionCreate, db: Session = Depends(get_db)
) -> ApiResponse[QuestionRead]:
    return ApiResponse(data=question_service.create_question(db, payload))


@router.put("/{question_id}", response_model=ApiResponse[QuestionRead])
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[QuestionRead]:
    return ApiResponse(data=question_service.update_question(db, question_id, payload))


@router.delete("/{question_id}", response_model=ApiResponse[dict[str, int]])
def delete_question(
    question_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict[str, int]]:
    question_service.delete_question(db, question_id)
    return ApiResponse(data={"deleted_id": question_id})
