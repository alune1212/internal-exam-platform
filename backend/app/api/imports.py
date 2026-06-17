from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import template_service
from app.services.import_service import generate_failure_report

router = APIRouter(prefix="/admin/imports", tags=["admin-imports"])


@router.get("/templates/questions")
def download_question_template() -> StreamingResponse:
    stream = template_service.generate_question_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('题库导入模板.xlsx')}"
        },
    )


@router.get("/templates/candidates")
def download_candidate_template() -> StreamingResponse:
    stream = template_service.generate_candidate_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('应考人员模板.xlsx')}"
        },
    )


@router.get("/{batch_id}/failure-report")
def download_failure_report(
    batch_id: int, db: Session = Depends(get_db)
) -> StreamingResponse:
    stream = generate_failure_report(db, batch_id)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('导入失败明细.xlsx')}"
        },
    )
