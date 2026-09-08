from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.schemas.common import ApiResponse
from app.schemas.operations import (
    MAX_RETENTION_SELECTION_IDS,
    OperationsSnapshotRead,
    RetentionArchiveRead,
    RetentionArchiveRequest,
    RetentionDeleteRead,
    RetentionDeleteRequest,
    RetentionPreviewRead,
    SessionClosureReadiness,
)
from app.schemas.practice_retention import (
    PracticeRetentionArchiveRead,
    PracticeRetentionArchiveRequest,
    PracticeRetentionDeleteRead,
    PracticeRetentionDeleteRequest,
    PracticeRetentionPreviewRead,
)
from app.services import practice_retention_service, retention_service
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


@router.get(
    "/practice-retention/preview",
    response_model=ApiResponse[PracticeRetentionPreviewRead],
)
def practice_retention_preview(
    db: Session = Depends(get_db),
    candidate_ids: list[int] | None = Query(
        default=None,
        min_length=1,
        max_length=MAX_RETENTION_SELECTION_IDS,
    ),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[PracticeRetentionPreviewRead]:
    return ApiResponse(
        data=practice_retention_service.preview_practice_retention(
            db,
            candidate_ids=candidate_ids,
            limit=limit,
            offset=offset,
        )
    )


@router.post(
    "/practice-retention/archive",
    response_model=ApiResponse[PracticeRetentionArchiveRead],
)
def practice_retention_archive(
    payload: PracticeRetentionArchiveRequest,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[PracticeRetentionArchiveRead]:
    return ApiResponse(
        data=practice_retention_service.create_practice_retention_archive(
            db,
            candidate_ids=payload.candidate_ids,
            preview_fingerprint=payload.preview_fingerprint,
            operator_subject=operator_subject,
        )
    )


@router.post(
    "/practice-retention/delete",
    response_model=ApiResponse[PracticeRetentionDeleteRead],
)
def practice_retention_delete(
    payload: PracticeRetentionDeleteRequest,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[PracticeRetentionDeleteRead]:
    return ApiResponse(
        data=practice_retention_service.delete_practice_retention(
            db,
            candidate_ids=payload.candidate_ids,
            preview_fingerprint=payload.preview_fingerprint,
            archive_id=payload.archive_id,
            backup_id=payload.backup_id,
            confirmation=payload.confirmation,
            operator_subject=operator_subject,
        )
    )
