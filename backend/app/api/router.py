from fastapi import APIRouter, Depends

from app.api import (
    attempts,
    auth,
    candidates,
    exams,
    imports,
    practice,
    questions,
    reports,
)
from app.core.config import settings
from app.core.dependencies import require_admin
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api")


@router.get("/health", response_model=ApiResponse[dict[str, str]], tags=["system"])
def health_check() -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok", "service": settings.app_name})


router.include_router(auth.router)
router.include_router(candidates.router)
router.include_router(practice.router)
router.include_router(exams.router)
router.include_router(attempts.router)
router.include_router(exams.admin_router, dependencies=[Depends(require_admin)])
router.include_router(questions.router, dependencies=[Depends(require_admin)])
router.include_router(reports.router, dependencies=[Depends(require_admin)])
router.include_router(imports.router, dependencies=[Depends(require_admin)])
