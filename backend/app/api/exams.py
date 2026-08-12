from fastapi import APIRouter, BackgroundTasks, Depends, Request, UploadFile
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id, require_admin
from app.schemas.attempt import AttemptIncidentRead, AttemptVoidRequest
from app.schemas.common import ApiResponse
from app.schemas.exam import (
    BulkRetakeApplyRead,
    BulkRetakeApplyRequest,
    BulkRetakePreviewRead,
    BulkRetakePreviewRequest,
    ExamCandidateCreate,
    ExamCandidateRow,
    ExamCandidateUpdate,
    ExamCreate,
    ExamPublishRequest,
    ExamRead,
    ExamStartResponse,
    ExamUpdate,
    FormalExamEvidenceRead,
    FormalExamEvidenceRequest,
    InvitationScheduleRead,
    InvitationStatusRead,
    PublicationReadinessRead,
    ResultDetailsReleaseRead,
    ResultDetailsReleaseRequest,
)
from app.schemas.question import QuestionImportResult
from app.services import exam_service, invitation_service
from app.services.audit_service import record_admin_event

router = APIRouter(prefix="/exams", tags=["exams"])
admin_router = APIRouter(prefix="/admin/exams", tags=["admin-exams"])


@router.get("/active", response_model=ApiResponse[list[ExamRead]])
def list_active_exams(
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[ExamRead]]:
    return ApiResponse(data=exam_service.list_active_exams(db, candidate_id))


@router.post("/{exam_id}/start", response_model=ApiResponse[ExamStartResponse])
def start_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[ExamStartResponse]:
    return ApiResponse(data=exam_service.start_exam(db, exam_id, candidate_id))


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


@admin_router.get(
    "/{exam_id}/publication-readiness",
    response_model=ApiResponse[PublicationReadinessRead],
)
def get_publication_readiness(
    exam_id: int, db: Session = Depends(get_db)
) -> ApiResponse[PublicationReadinessRead]:
    return ApiResponse(data=exam_service.get_publication_readiness(db, exam_id))


@admin_router.post("/{exam_id}/publish", response_model=ApiResponse[ExamRead])
def publish_exam(
    exam_id: int,
    payload: ExamPublishRequest,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[ExamRead]:
    try:
        exam = exam_service.publish_exam(
            db, exam_id, payload.confirmation_title, commit=False
        )
        readiness = exam_service.get_publication_readiness(db, exam_id)
        record_admin_event(
            db,
            operator_subject=operator_subject,
            action="exam_published",
            target_type="exam",
            target_id=exam_id,
            metadata={"exam_id": exam_id, "fingerprint": readiness.fingerprint},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return ApiResponse(data=exam)


@admin_router.post(
    "/{exam_id}/candidates/import", response_model=ApiResponse[QuestionImportResult]
)
def import_exam_candidates(
    exam_id: int,
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[QuestionImportResult]:
    try:
        result = exam_service.import_exam_candidates_from_workbook(
            db,
            exam_id,
            file.file,
            file.filename or "candidates.xlsx",
            commit=False,
        )
        record_admin_event(
            db,
            operator_subject=operator_subject,
            action="exam_roster_import",
            target_type="import_batch",
            target_id=result.batch_id,
            metadata={
                "exam_id": exam_id,
                "batch_id": result.batch_id,
                "success_count": result.success_count,
                "failed_count": result.failed_count,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return ApiResponse(data=result)


@admin_router.get(
    "/{exam_id}/candidates", response_model=ApiResponse[list[ExamCandidateRow]]
)
def list_exam_candidates(
    exam_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ExamCandidateRow]]:
    return ApiResponse(data=exam_service.list_exam_candidates(db, exam_id))


@admin_router.post(
    "/{exam_id}/candidates", response_model=ApiResponse[ExamCandidateRow]
)
def add_exam_candidate(
    exam_id: int,
    payload: ExamCandidateCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[ExamCandidateRow]:
    return ApiResponse(data=exam_service.add_exam_candidate(db, exam_id, payload))


@admin_router.patch(
    "/{exam_id}/candidates/{candidate_id}",
    response_model=ApiResponse[ExamCandidateRow],
)
@admin_router.put(
    "/{exam_id}/candidates/{candidate_id}",
    response_model=ApiResponse[ExamCandidateRow],
)
def update_exam_candidate(
    exam_id: int,
    candidate_id: int,
    payload: ExamCandidateUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[ExamCandidateRow]:
    return ApiResponse(
        data=exam_service.update_exam_candidate(db, exam_id, candidate_id, payload)
    )


@admin_router.delete("/{exam_id}/candidates/{candidate_id}")
def remove_exam_candidate(
    exam_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, int]]:
    return ApiResponse(
        data=exam_service.remove_exam_candidate(db, exam_id, candidate_id)
    )


def _schedule_read(
    schedule: invitation_service.InvitationSchedule,
) -> InvitationScheduleRead:
    return InvitationScheduleRead(
        exam_id=schedule.exam_id,
        mode=schedule.mode,
        selected_count=schedule.selected_count,
        accepted_count=schedule.accepted_count,
        rejected_count=schedule.rejected_count,
        scheduled_count=schedule.scheduled_count,
    )


@admin_router.get(
    "/{exam_id}/invitations", response_model=ApiResponse[InvitationStatusRead]
)
@admin_router.get(
    "/{exam_id}/invitations/status", response_model=ApiResponse[InvitationStatusRead]
)
def get_invitation_status(
    exam_id: int, db: Session = Depends(get_db)
) -> ApiResponse[InvitationStatusRead]:
    return ApiResponse(
        data=InvitationStatusRead.model_validate(
            invitation_service.invitation_status(db, exam_id)
        )
    )


def _schedule_invitations(
    exam_id: int,
    *,
    mode: str,
    background_tasks: BackgroundTasks,
    operator_subject: str,
    db: Session,
) -> InvitationScheduleRead:
    schedule = invitation_service.claim_invitations(
        db,
        exam_id,
        mode=mode,
        operator_subject=operator_subject,
        commit=False,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    background_tasks.add_task(
        invitation_service.deliver_claimed_invitations,
        schedule.scope_ids,
        schedule.claim_owner,
        session_factory=sessionmaker(
            bind=db.get_bind(), autoflush=False, expire_on_commit=False
        ),
        operator_subject=operator_subject,
    )
    return _schedule_read(schedule)


@admin_router.post(
    "/{exam_id}/invitations/send",
    response_model=ApiResponse[InvitationScheduleRead],
)
def send_invitations(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[InvitationScheduleRead]:
    return ApiResponse(
        data=_schedule_invitations(
            exam_id,
            mode="initial",
            background_tasks=background_tasks,
            operator_subject=operator_subject,
            db=db,
        )
    )


@admin_router.post(
    "/{exam_id}/invitations/resend",
    response_model=ApiResponse[InvitationScheduleRead],
)
def resend_invitations(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[InvitationScheduleRead]:
    return ApiResponse(
        data=_schedule_invitations(
            exam_id,
            mode="resend",
            background_tasks=background_tasks,
            operator_subject=operator_subject,
            db=db,
        )
    )


@admin_router.post(
    "/{exam_id}/candidates/{candidate_id}/retake-grants",
    response_model=ApiResponse[ExamCandidateRow],
)
def create_retake_grant(
    exam_id: int,
    candidate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[ExamCandidateRow]:
    result = exam_service.create_retake_grant_row(db, exam_id, candidate_id)
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="retake_granted",
        target_type="candidate",
        target_id=candidate_id,
        metadata={"exam_id": exam_id, "count": 1},
        request=request,
    )
    db.commit()
    return ApiResponse(data=result)


@admin_router.post(
    "/{exam_id}/result-details/release",
    response_model=ApiResponse[ResultDetailsReleaseRead],
)
def release_result_details(
    exam_id: int,
    payload: ResultDetailsReleaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[ResultDetailsReleaseRead]:
    result = exam_service.release_result_details(
        db,
        exam_id,
        operator_subject=operator_subject,
        confirmation_title=payload.confirmation_title,
    )
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="result_details_released",
        target_type="exam",
        target_id=exam_id,
        metadata={"exam_id": exam_id},
        request=request,
    )
    db.commit()
    return ApiResponse(data=result)


@admin_router.post(
    "/{exam_id}/attempts/{attempt_id}/void",
    response_model=ApiResponse[AttemptIncidentRead],
)
def void_attempt(
    exam_id: int,
    attempt_id: int,
    payload: AttemptVoidRequest,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[AttemptIncidentRead]:
    result = exam_service.void_attempt(
        db,
        attempt_id,
        operator_subject=operator_subject,
        reason=payload.reason,
    )
    if result.exam_id != exam_id:
        raise exam_service.AttemptNotFoundError(attempt_id)
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="attempt_voided",
        target_type="attempt",
        target_id=attempt_id,
        metadata={"exam_id": exam_id, "reason_code": "operator_incident"},
        request=request,
    )
    db.commit()
    return ApiResponse(data=result)


@admin_router.get(
    "/{exam_id}/incidents",
    response_model=ApiResponse[list[AttemptIncidentRead]],
)
def list_exam_incidents(
    exam_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[list[AttemptIncidentRead]]:
    return ApiResponse(data=exam_service.list_exam_incidents(db, exam_id))


@admin_router.post(
    "/{exam_id}/retakes/preview",
    response_model=ApiResponse[BulkRetakePreviewRead],
)
def preview_bulk_retake(
    exam_id: int,
    payload: BulkRetakePreviewRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[BulkRetakePreviewRead]:
    return ApiResponse(
        data=exam_service.preview_bulk_retake(
            db,
            exam_id,
            candidate_ids=payload.candidate_ids,
            void_existing=payload.void_existing,
        )
    )


@admin_router.post(
    "/{exam_id}/retakes/apply",
    response_model=ApiResponse[BulkRetakeApplyRead],
)
def apply_bulk_retake(
    exam_id: int,
    payload: BulkRetakeApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[BulkRetakeApplyRead]:
    result = exam_service.apply_bulk_retake(
        db,
        exam_id,
        candidate_ids=payload.candidate_ids,
        void_existing=payload.void_existing,
        confirmation_title=payload.confirmation_title,
        preview_fingerprint=payload.preview_fingerprint,
        reason=payload.reason,
        operator_subject=operator_subject,
    )
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="bulk_retake_granted",
        target_type="exam",
        target_id=exam_id,
        metadata={
            "exam_id": exam_id,
            "fingerprint": result.fingerprint,
            "granted_count": result.granted_count,
            "voided_count": result.voided_count,
        },
        request=request,
    )
    db.commit()
    return ApiResponse(data=result)


@admin_router.post(
    "/{exam_id}/evidence-bundle",
    response_model=ApiResponse[FormalExamEvidenceRead],
)
def build_formal_exam_evidence(
    exam_id: int,
    payload: FormalExamEvidenceRequest,
    request: Request,
    db: Session = Depends(get_db),
    operator_subject: str = Depends(require_admin),
) -> ApiResponse[FormalExamEvidenceRead]:
    result = exam_service.build_formal_exam_evidence(
        db,
        exam_id,
        operator_subject=operator_subject,
        artifact_references=payload.model_dump(),
    )
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="formal_exam_evidence_generated",
        target_type="exam",
        target_id=exam_id,
        metadata={
            "exam_id": exam_id,
            "outcome_artifact": result.checksum_sha256,
        },
        request=request,
    )
    db.commit()
    return ApiResponse(data=result)
