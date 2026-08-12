import json
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AdminAuditEvent,
    Exam,
    ExamAttempt,
    ExamCandidateScope,
    ExamQuestionPool,
    ExamRetakeGrant,
)
from app.models.attempt import SUBMITTED_STATUSES, TERMINAL_ATTEMPT_STATUSES
from app.schemas.attempt import (
    AttemptIncidentRead,
    AttemptResultQuestion,
    AttemptResultRead,
)
from app.schemas.exam import (
    BulkRetakeApplyRead,
    BulkRetakePreviewRead,
    BulkRetakeRow,
    FormalExamEvidenceRead,
    ResultDetailsReleaseRead,
)
from app.services.exam_errors import (
    AttemptNotFoundError,
    AttemptResultNotReadyError,
    AttemptVoidError,
    BulkRetakeConflictError,
    ExamConfigError,
    ExamNotFoundError,
    ResultDetailsAlreadyReleasedError,
    ResultDetailsNotReadyError,
)
from app.services.operational_lock_service import assert_backup_write_allowed


def _details_are_released(attempt: ExamAttempt) -> bool:
    return bool(attempt.exam and attempt.exam.result_details_released_at is not None)


def build_attempt_result(attempt: ExamAttempt) -> AttemptResultRead:
    if attempt.status == "voided":
        raise AttemptResultNotReadyError(attempt.id)
    show_answer = _details_are_released(attempt)
    questions: list[AttemptResultQuestion] = []
    if show_answer:
        for question in attempt.questions:
            answer = question.answer
            questions.append(
                AttemptResultQuestion(
                    attempt_question_id=question.id,
                    stem_snapshot=question.stem_snapshot,
                    selected_answer=answer.selected_answer if answer else None,
                    correct_answer_snapshot=question.correct_answer_snapshot,
                    analysis_snapshot=question.analysis_snapshot,
                    is_correct=answer.is_correct if answer else False,
                    score_awarded=float(answer.score_awarded) if answer else 0,
                    score=float(question.score),
                )
            )

    pass_score = (
        float(attempt.pass_score_snapshot)
        if attempt.pass_score_snapshot is not None
        else None
    )
    return AttemptResultRead(
        attempt_id=attempt.id,
        score=float(attempt.score),
        total_score=float(attempt.total_score),
        pass_score=pass_score,
        is_passed=(
            float(attempt.score) >= pass_score if pass_score is not None else None
        ),
        show_answer_after_submit=show_answer,
        correct_count=attempt.correct_count,
        wrong_count=attempt.wrong_count,
        questions=questions,
    )


def release_result_details(
    db: Session,
    exam_id: int,
    *,
    operator_subject: str,
    confirmation_title: str,
) -> ResultDetailsReleaseRead:
    assert_backup_write_allowed(db)
    exam = db.query(Exam).filter(Exam.id == exam_id).with_for_update().one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if confirmation_title != exam.title:
        raise ExamConfigError("确认名称与考试名称不一致")
    if exam.result_details_released_at is not None:
        raise ResultDetailsAlreadyReleasedError(exam_id)
    in_progress = (
        db.query(ExamAttempt.id)
        .filter(ExamAttempt.exam_id == exam_id, ExamAttempt.status == "in_progress")
        .first()
    )
    if in_progress is not None:
        raise ResultDetailsNotReadyError("仍有进行中的考试记录，不能发布答案解析。")
    any_attempt = (
        db.query(ExamAttempt.id).filter(ExamAttempt.exam_id == exam_id).first()
    )
    if any_attempt is None:
        raise ResultDetailsNotReadyError("当前考试尚无答题记录，不能发布答案解析。")
    released_at = datetime.now(UTC)
    exam.result_details_released_at = released_at
    exam.result_details_released_by = operator_subject
    db.flush()
    return ResultDetailsReleaseRead(
        exam_id=exam.id,
        released_at=released_at,
        released_by=operator_subject,
    )


def _load_attempt_for_incident(
    db: Session, attempt_id: int, *, for_update: bool = False
) -> ExamAttempt:
    query = (
        db.query(ExamAttempt)
        .options(selectinload(ExamAttempt.candidate))
        .filter(ExamAttempt.id == attempt_id)
    )
    if for_update:
        query = query.with_for_update().populate_existing()
    attempt = query.one_or_none()
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    return attempt


def _void_loaded_attempt(
    attempt: ExamAttempt, *, operator_subject: str, reason: str, now: datetime
) -> AttemptIncidentRead:
    if attempt.status == "voided":
        raise AttemptVoidError(f"考试记录 #{attempt.id} 已经作废。")
    if attempt.status not in ("in_progress", *SUBMITTED_STATUSES):
        raise AttemptVoidError(f"考试记录 #{attempt.id} 当前状态不能作废。")
    prior_status = attempt.status
    attempt.status = "voided"
    attempt.voided_at = now
    attempt.voided_by = operator_subject
    attempt.void_reason = reason
    attempt.attempt_session_hash = None
    return AttemptIncidentRead(
        attempt_id=attempt.id,
        exam_id=attempt.exam_id,
        candidate_id=attempt.candidate_id,
        prior_status=prior_status,
        voided_at=now,
        voided_by=operator_subject,
        reason=reason,
        attempt_no=attempt.attempt_no,
    )


def void_attempt(
    db: Session,
    attempt_id: int,
    *,
    operator_subject: str,
    reason: str,
) -> AttemptIncidentRead:
    assert_backup_write_allowed(db)
    attempt = _load_attempt_for_incident(db, attempt_id, for_update=True)
    incident = _void_loaded_attempt(
        attempt,
        operator_subject=operator_subject,
        reason=reason,
        now=datetime.now(UTC),
    )
    db.flush()
    return incident


def list_exam_incidents(db: Session, exam_id: int) -> list[AttemptIncidentRead]:
    if db.get(Exam, exam_id) is None:
        raise ExamNotFoundError(exam_id)
    attempts = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.exam_id == exam_id, ExamAttempt.status == "voided")
        .order_by(ExamAttempt.voided_at, ExamAttempt.id)
        .all()
    )
    grants = {
        candidate_id
        for (candidate_id,) in db.query(ExamRetakeGrant.candidate_id)
        .filter(
            ExamRetakeGrant.exam_id == exam_id,
            ExamRetakeGrant.used_at.is_(None),
        )
        .all()
    }
    return [
        AttemptIncidentRead(
            attempt_id=attempt.id,
            exam_id=attempt.exam_id,
            candidate_id=attempt.candidate_id,
            prior_status="unknown",
            voided_at=attempt.voided_at or attempt.updated_at,
            voided_by=attempt.voided_by or "unknown",
            reason=attempt.void_reason or "未记录原因",
            attempt_no=attempt.attempt_no,
            retake_granted=attempt.candidate_id in grants,
        )
        for attempt in attempts
    ]


def _latest_attempt(
    db: Session, exam_id: int, candidate_id: int, *, for_update: bool = False
) -> ExamAttempt | None:
    query = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
        )
        .order_by(ExamAttempt.attempt_no.desc(), ExamAttempt.id.desc())
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def _retake_preview_rows(
    db: Session,
    exam_id: int,
    candidate_ids: list[int],
    *,
    void_existing: bool,
) -> list[BulkRetakeRow]:
    scoped_ids = {
        candidate_id
        for (candidate_id,) in db.query(ExamCandidateScope.candidate_id)
        .filter(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id.in_(candidate_ids),
        )
        .all()
    }
    scopes = {
        scope.candidate_id: scope
        for scope in db.query(ExamCandidateScope)
        .filter(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id.in_(candidate_ids),
        )
        .all()
    }
    unused_grants = {
        candidate_id
        for (candidate_id,) in db.query(ExamRetakeGrant.candidate_id)
        .filter(
            ExamRetakeGrant.exam_id == exam_id,
            ExamRetakeGrant.candidate_id.in_(candidate_ids),
            ExamRetakeGrant.used_at.is_(None),
        )
        .all()
    }
    rows: list[BulkRetakeRow] = []
    for candidate_id in sorted(set(candidate_ids)):
        scope = scopes.get(candidate_id)
        attempt = _latest_attempt(db, exam_id, candidate_id)
        base = {
            "candidate_id": candidate_id,
            # Formal identity is always the frozen scope snapshot.  The
            # compatibility ``candidate_name`` field is retained in this
            # response for old clients but receives the same frozen value.
            "candidate_name": scope.roster_name if scope else None,
            "roster_email": scope.roster_email if scope else None,
            "roster_name": scope.roster_name if scope else None,
            "attempt_id": attempt.id if attempt else None,
            "prior_status": attempt.status if attempt else None,
        }
        if candidate_id not in scoped_ids:
            rows.append(
                BulkRetakeRow(**base, outcome="skipped", reason="不在本场应考名单")
            )
        elif candidate_id in unused_grants:
            rows.append(
                BulkRetakeRow(**base, outcome="skipped", reason="已有未使用补考授权")
            )
        elif attempt is None:
            rows.append(BulkRetakeRow(**base, outcome="skipped", reason="尚无答题记录"))
        elif attempt.status == "in_progress" and not void_existing:
            rows.append(
                BulkRetakeRow(
                    **base,
                    outcome="skipped",
                    reason="考试仍在进行；需选择同时作废",
                )
            )
        elif attempt.status in TERMINAL_ATTEMPT_STATUSES or (
            attempt.status == "in_progress" and void_existing
        ):
            rows.append(BulkRetakeRow(**base, outcome="eligible", reason="可授予补考"))
        else:
            rows.append(
                BulkRetakeRow(**base, outcome="skipped", reason="状态不符合补考条件")
            )
    return rows


def _retake_fingerprint(
    *, exam_id: int, void_existing: bool, rows: list[BulkRetakeRow]
) -> str:
    payload = {
        "exam_id": exam_id,
        "void_existing": void_existing,
        "rows": [row.model_dump(mode="json") for row in rows],
    }
    return sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()


def preview_bulk_retake(
    db: Session,
    exam_id: int,
    *,
    candidate_ids: list[int],
    void_existing: bool,
) -> BulkRetakePreviewRead:
    if db.get(Exam, exam_id) is None:
        raise ExamNotFoundError(exam_id)
    rows = _retake_preview_rows(db, exam_id, candidate_ids, void_existing=void_existing)
    eligible_count = sum(row.outcome == "eligible" for row in rows)
    return BulkRetakePreviewRead(
        exam_id=exam_id,
        void_existing=void_existing,
        eligible_count=eligible_count,
        skipped_count=len(rows) - eligible_count,
        rows=rows,
        fingerprint=_retake_fingerprint(
            exam_id=exam_id, void_existing=void_existing, rows=rows
        ),
    )


def apply_bulk_retake(
    db: Session,
    exam_id: int,
    *,
    candidate_ids: list[int],
    void_existing: bool,
    confirmation_title: str,
    preview_fingerprint: str,
    reason: str,
    operator_subject: str,
) -> BulkRetakeApplyRead:
    assert_backup_write_allowed(db)
    exam = db.query(Exam).filter(Exam.id == exam_id).with_for_update().one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if confirmation_title != exam.title:
        raise ExamConfigError("确认名称与考试名称不一致")
    (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id.in_(candidate_ids),
        )
        .with_for_update()
        .all()
    )
    preview = preview_bulk_retake(
        db,
        exam_id,
        candidate_ids=candidate_ids,
        void_existing=void_existing,
    )
    if preview.fingerprint != preview_fingerprint:
        raise BulkRetakeConflictError("补考预览已经变化，请刷新预览后重新确认。")

    now = datetime.now(UTC)
    result_rows: list[BulkRetakeRow] = []
    voided_count = 0
    granted_count = 0
    for row in preview.rows:
        if row.outcome != "eligible":
            result_rows.append(row)
            continue
        attempt = _latest_attempt(db, exam_id, row.candidate_id, for_update=True)
        if attempt is None:
            raise BulkRetakeConflictError("答题记录已经变化，请重新预览。")
        if void_existing and attempt.status != "voided":
            _void_loaded_attempt(
                attempt,
                operator_subject=operator_subject,
                reason=reason,
                now=now,
            )
            voided_count += 1
        db.add(ExamRetakeGrant(exam_id=exam_id, candidate_id=row.candidate_id))
        granted_count += 1
        result_rows.append(
            row.model_copy(update={"outcome": "granted", "reason": "补考授权已创建"})
        )
    db.flush()
    return BulkRetakeApplyRead(
        exam_id=exam_id,
        void_existing=void_existing,
        eligible_count=preview.eligible_count,
        skipped_count=preview.skipped_count,
        rows=result_rows,
        fingerprint=preview.fingerprint,
        granted_count=granted_count,
        voided_count=voided_count,
        applied_at=now,
    )


_SENSITIVE_REFERENCE_MARKERS = ("password", "secret", "token", "otp")


def _safe_artifact_references(references: dict[str, str | None]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in references.items():
        if value is None:
            continue
        normalized = value.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if any(marker in lowered for marker in _SENSITIVE_REFERENCE_MARKERS):
            continue
        safe[key] = normalized
    return safe


def build_formal_exam_evidence(
    db: Session,
    exam_id: int,
    *,
    operator_subject: str,
    artifact_references: dict[str, str | None],
) -> FormalExamEvidenceRead:
    # The endpoint also appends an audit event, so keep evidence generation in
    # the same guarded mutation contract even though the manifest itself is
    # returned in memory.
    assert_backup_write_allowed(db)
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    generated_at = datetime.now(UTC)
    status_counts: dict[str, int] = {}
    status_count_rows = (
        db.query(ExamAttempt.status, func.count(ExamAttempt.id))
        .filter(ExamAttempt.exam_id == exam_id)
        .group_by(ExamAttempt.status)
        .all()
    )
    for status, count in status_count_rows:
        status_counts[str(status)] = int(count)
    audit_events = [
        event
        for event in db.query(AdminAuditEvent).order_by(AdminAuditEvent.id).all()
        if event.metadata_json.get("exam_id") == exam_id
        or (event.target_type == "exam" and event.target_id == str(exam_id))
    ]
    manifest: dict[str, object] = {
        "schema_version": 1,
        "exam": {
            "id": exam.id,
            "title": exam.title,
            "status": exam.status,
            "available_from": exam.available_from.isoformat()
            if exam.available_from
            else None,
            "available_until": exam.available_until.isoformat()
            if exam.available_until
            else None,
            "duration_minutes": exam.duration_minutes,
            "result_details_released_at": exam.result_details_released_at.isoformat()
            if exam.result_details_released_at
            else None,
            "result_details_released_by": exam.result_details_released_by,
        },
        "roster_count": db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.exam_id == exam_id)
        .count(),
        "frozen_pool_count": db.query(ExamQuestionPool)
        .filter(ExamQuestionPool.exam_id == exam_id)
        .count(),
        "attempt_status_counts": status_counts,
        "audit_event_ids": [event.id for event in audit_events],
        "audit_actions": sorted({event.action for event in audit_events}),
        "artifact_references": _safe_artifact_references(artifact_references),
        "generated_at": generated_at.isoformat(),
        "generated_by": operator_subject,
    }
    serialized = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return FormalExamEvidenceRead(
        exam_id=exam_id,
        generated_at=generated_at,
        manifest=manifest,
        checksum_sha256=sha256(serialized).hexdigest(),
    )
