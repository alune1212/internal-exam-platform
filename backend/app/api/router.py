from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import (
    attempts,
    auth,
    candidates,
    exams,
    imports,
    learning,
    operations,
    practice,
    questions,
    reports,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.schemas.common import ApiResponse, ReadinessStatus
from app.services import readiness_service

router = APIRouter(prefix="/api")


@router.get("/health", response_model=ApiResponse[dict[str, str]], tags=["system"])
def health_check() -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok", "service": settings.app_name})


@router.get("/ready", response_model=ApiResponse[ReadinessStatus], tags=["system"])
def readiness_check(db: Session = Depends(get_db)) -> ApiResponse[ReadinessStatus]:
    return ApiResponse(data=readiness_service.check_readiness(db))


router.include_router(auth.router)
router.include_router(candidates.router)
router.include_router(learning.router)
router.include_router(practice.router)
router.include_router(exams.router)
router.include_router(attempts.router)
router.include_router(learning.admin_router, dependencies=[Depends(require_admin)])
router.include_router(exams.admin_router, dependencies=[Depends(require_admin)])
router.include_router(questions.router, dependencies=[Depends(require_admin)])
router.include_router(reports.router, dependencies=[Depends(require_admin)])
router.include_router(imports.router, dependencies=[Depends(require_admin)])
router.include_router(operations.router, dependencies=[Depends(require_admin)])
