from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services import template_service

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
