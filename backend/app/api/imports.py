from fastapi import APIRouter

from app.schemas.common import ApiResponse


router = APIRouter(prefix="/admin/imports", tags=["admin-imports"])


@router.get("/templates", response_model=ApiResponse[list[str]])
def list_import_templates() -> ApiResponse[list[str]]:
    return ApiResponse(data=["questions", "candidates"])
