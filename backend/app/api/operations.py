from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.schemas.common import ApiResponse
from app.schemas.operations import (
    OperationsSnapshotRead,
    RetentionArchiveRead,
    RetentionArchiveRequest,
    RetentionDeleteRead,
    RetentionDeleteRequest,
    RetentionPreviewRead,
    SessionClosureReadiness,
)
from app.services import retention_service
from app.services.operational_lock_service import inspect_writer_fence
from app.services.operations_service import get_operations_snapshot
from app.services.session_control_service import get_session_closure_readiness

router = APIRouter(prefix="/admin/operations", tags=["admin-operations"])


@router.get(
    "/session-closure-readiness",
    response_model=ApiResponse[SessionClosureReadiness],
)
def session_closure_readiness(
    db: Session = Depends(get_db),
) -> ApiResponse[SessionClosureReadiness]:
    return ApiResponse(data=get_session_closure_readiness(db))


@router.get("/snapshot", response_model=ApiResponse[OperationsSnapshotRead])
def operations_snapshot(
    db: Session = Depends(get_db),
) -> ApiResponse[OperationsSnapshotRead]:
    return ApiResponse(data=get_operations_snapshot(db))


@router.get("/writer-fence", response_model=ApiResponse[dict[str, object]])
def writer_fence_status(
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, object]]:
    """Read the shared formal writer-fence state without changing it."""

    return ApiResponse(data=inspect_writer_fence(db))


@router.get("/retention/preview", response_model=ApiResponse[RetentionPreviewRead])
def retention_preview(
    db: Session = Depends(get_db),
) -> ApiResponse[RetentionPreviewRead]:
    return ApiResponse(data=retention_service.preview_retention(db))


@router.post("/retention/archive", response_model=ApiResponse[RetentionArchiveRead])
def retention_archive(
    payload: RetentionArchiveRequest,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[RetentionArchiveRead]:
    return ApiResponse(
        data=retention_service.create_retention_archive(
            db,
            exam_ids=payload.exam_ids,
            preview_fingerprint=payload.preview_fingerprint,
            operator_subject=operator_subject,
        )
    )


@router.post("/retention/delete", response_model=ApiResponse[RetentionDeleteRead])
def retention_delete(
    payload: RetentionDeleteRequest,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[RetentionDeleteRead]:
    return ApiResponse(
        data=retention_service.delete_retained_exams(
            db,
            exam_ids=payload.exam_ids,
            preview_fingerprint=payload.preview_fingerprint,
            archive_id=payload.archive_id,
            backup_id=payload.backup_id,
            confirmation=payload.confirmation,
            operator_subject=operator_subject,
        )
    )
