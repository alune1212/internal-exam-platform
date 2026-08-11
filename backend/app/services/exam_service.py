"""Compatibility facade for exam services.

Routes and existing tests keep importing this module while focused modules own
configuration, paper generation, attempt lifecycle, and result construction.
"""

from sqlalchemy.orm import Session

from app.models import Candidate, Exam, ExamCandidateScope, ImportBatch
from app.models.attempt import TERMINAL_ATTEMPT_STATUSES
from app.schemas.attempt import AnswerSaveRequest, AnswerSaveResponse, AttemptResultRead
from app.schemas.exam import ExamCandidateRow, ExamRead
from app.schemas.question import ImportFailure, QuestionImportResult
from app.services.exam_attempts import (
    _has_unused_retake_grant,
    _latest_attempt_for_candidate,
    create_retake_grant,
)
from app.services.exam_attempts import (
    _is_attempt_expired as _is_attempt_expired,
)
from app.services.exam_attempts import (
    _load_attempt_with_snapshots as _load_attempt_with_snapshots,
)
from app.services.exam_attempts import (
    get_attempt as get_attempt,
)
from app.services.exam_attempts import (
    get_attempt_result as get_attempt_result,
)
from app.services.exam_attempts import (
    save_answers as _save_answers,
)
from app.services.exam_attempts import (
    score_and_mark_attempt_submitted as score_and_mark_attempt_submitted,
)
from app.services.exam_attempts import (
    start_exam as start_exam,
)
from app.services.exam_attempts import (
    submit_attempt as _submit_attempt,
)
from app.services.exam_attempts import (
    takeover_attempt_session as takeover_attempt_session,
)
from app.services.exam_attempts import (
    verify_attempt_session as verify_attempt_session,
)
from app.services.exam_configuration import (
    _build_exam_read,
    _candidate_exam_is_visible,
    _question_pool_counts_by_exam,
)
from app.services.exam_configuration import (
    create_exam as create_exam,
)
from app.services.exam_configuration import (
    get_publication_readiness as get_publication_readiness,
)
from app.services.exam_configuration import (
    publish_exam as publish_exam,
)
from app.services.exam_configuration import (
    update_exam as update_exam,
)
from app.services.exam_errors import (
    AdminAuthError as AdminAuthError,
)
from app.services.exam_errors import (
    AttemptAlreadyExistsError as AttemptAlreadyExistsError,
)
from app.services.exam_errors import (
    AttemptAlreadySubmittedError as AttemptAlreadySubmittedError,
)
from app.services.exam_errors import (
    AttemptNotFoundError as AttemptNotFoundError,
)
from app.services.exam_errors import (
    AttemptQuestionNotFoundError as AttemptQuestionNotFoundError,
)
from app.services.exam_errors import (
    AttemptResultNotReadyError as AttemptResultNotReadyError,
)
from app.services.exam_errors import (
    CandidateNotEligibleError as CandidateNotEligibleError,
)
from app.services.exam_errors import (
    CandidateNotFoundError as CandidateNotFoundError,
)
from app.services.exam_errors import (
    ExamConfigError as ExamConfigError,
)
from app.services.exam_errors import (
    ExamFrozenError as ExamFrozenError,
)
from app.services.exam_errors import (
    ExamNotActiveError as ExamNotActiveError,
)
from app.services.exam_errors import (
    ExamNotAvailableError as ExamNotAvailableError,
)
from app.services.exam_errors import (
    ExamNotFoundError as ExamNotFoundError,
)
from app.services.exam_errors import (
    ExamQuestionPoolMissingError as ExamQuestionPoolMissingError,
)
from app.services.exam_errors import (
    InsufficientQuestionsError as InsufficientQuestionsError,
)
from app.services.exam_paper import (
    FixedPaperRule as FixedPaperRule,
)
from app.services.exam_paper import (
    _rescale_scores as _rescale_scores,
)
from app.services.exam_paper import (
    _select_questions_by_type as _select_questions_by_type,
)
from app.services.exam_results import (
    apply_bulk_retake as apply_bulk_retake,
)
from app.services.exam_results import (
    build_formal_exam_evidence as build_formal_exam_evidence,
)
from app.services.exam_results import (
    list_exam_incidents as list_exam_incidents,
)
from app.services.exam_results import (
    preview_bulk_retake as preview_bulk_retake,
)
from app.services.exam_results import (
    release_result_details as release_result_details,
)
from app.services.exam_results import (
    void_attempt as void_attempt,
)
from app.services.operational_lock_service import assert_admin_mutation_allowed


def _list_exams(db: Session, *, status: str | None = None) -> list[ExamRead]:
    query = db.query(Exam)
    if status is not None:
        query = query.filter(Exam.status == status)
    exams = query.order_by(Exam.id).all()
    pool_counts = _question_pool_counts_by_exam(db, [exam.id for exam in exams])
    return [_build_exam_read(db, exam, pool_counts=pool_counts) for exam in exams]


def _build_exam_read_for_candidate(
    db: Session, exam: Exam, candidate_id: int
) -> ExamRead | None:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or candidate.status != "active" or not candidate.should_attend:
        return None
    scope = (
        db.query(ExamCandidateScope.id)
        .filter(
            ExamCandidateScope.exam_id == exam.id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .first()
    )
    if scope is None:
        return None
    if not _candidate_exam_is_visible(exam):
        return None

    latest = _latest_attempt_for_candidate(db, exam.id, candidate_id)
    has_unused_retake_grant = _has_unused_retake_grant(db, exam.id, candidate_id)
    if (
        latest
        and latest.status in TERMINAL_ATTEMPT_STATUSES
        and not has_unused_retake_grant
    ):
        return None
    return _build_exam_read(
        db,
        exam,
        {
            "latest_attempt_id": latest.id if latest else None,
            "latest_attempt_status": latest.status if latest else None,
            "has_unused_retake_grant": has_unused_retake_grant,
        },
    )


def list_active_exams(db: Session, candidate_id: int) -> list[ExamRead]:
    exams = db.query(Exam).filter(Exam.status == "active").order_by(Exam.id).all()
    return [
        exam_read
        for exam in exams
        if (exam_read := _build_exam_read_for_candidate(db, exam, candidate_id))
        is not None
    ]


def list_admin_exams(db: Session) -> list[ExamRead]:
    return _list_exams(db)


def save_answers(
    db: Session, attempt_id: int, payload: AnswerSaveRequest
) -> AnswerSaveResponse:
    return _save_answers(
        db,
        attempt_id,
        payload,
        load_attempt=_load_attempt_with_snapshots,
    )


def submit_attempt(db: Session, attempt_id: int, submit_type: str) -> AttemptResultRead:
    return _submit_attempt(
        db,
        attempt_id,
        submit_type,
        load_attempt=_load_attempt_with_snapshots,
    )


def _build_exam_candidate_row(
    db: Session, exam_id: int, candidate: Candidate
) -> ExamCandidateRow:
    latest = _latest_attempt_for_candidate(db, exam_id, candidate.id)
    return ExamCandidateRow(
        candidate_id=candidate.id,
        candidate_name=candidate.name,
        employee_no=candidate.employee_no,
        department=candidate.department,
        exam_group=candidate.exam_group,
        should_attend=candidate.should_attend,
        candidate_status=candidate.status,
        latest_attempt_id=latest.id if latest else None,
        latest_attempt_status=latest.status if latest else None,
        latest_score=float(latest.score) if latest else None,
        latest_total_score=float(latest.total_score) if latest else None,
        latest_submitted_at=latest.submitted_at if latest else None,
        attempt_no=latest.attempt_no if latest else None,
        attempt_kind=latest.attempt_kind if latest else None,
        has_unused_retake_grant=_has_unused_retake_grant(db, exam_id, candidate.id),
    )


def list_exam_candidates(db: Session, exam_id: int) -> list[ExamCandidateRow]:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    candidates = (
        db.query(Candidate)
        .join(ExamCandidateScope, ExamCandidateScope.candidate_id == Candidate.id)
        .filter(ExamCandidateScope.exam_id == exam_id)
        .order_by(Candidate.name, Candidate.id)
        .all()
    )
    return [
        _build_exam_candidate_row(db, exam_id, candidate) for candidate in candidates
    ]


def remove_exam_candidate(
    db: Session, exam_id: int, candidate_id: int
) -> dict[str, int]:
    assert_admin_mutation_allowed(db)
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "draft":
        raise ExamFrozenError("考试发布后应考名单已冻结")
    deleted = (
        db.query(ExamCandidateScope)
        .filter(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .delete()
    )
    db.commit()
    return {"removed_count": deleted}


def create_retake_grant_row(
    db: Session, exam_id: int, candidate_id: int
) -> ExamCandidateRow:
    assert_admin_mutation_allowed(db)
    create_retake_grant(db, exam_id, candidate_id, commit=False)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    return _build_exam_candidate_row(db, exam_id, candidate)


def import_exam_candidates_from_workbook(
    db: Session,
    exam_id: int,
    file_obj: object,
    file_name: str,
    *,
    commit: bool = True,
) -> QuestionImportResult:
    assert_admin_mutation_allowed(db)
    from app.services import import_service

    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "draft":
        raise ExamFrozenError("考试发布后应考名单已冻结")

    import_service.validate_upload_file_size(file_obj)
    parsed = import_service.parse_workbook(file_obj)
    failures: list[ImportFailure] = []
    success_count = 0
    for row_number, row in enumerate(parsed.rows, start=2):
        employee_no = import_service._optional_text(row.get("employee_no"))
        candidate = None
        if employee_no:
            candidate = (
                db.query(Candidate).filter(Candidate.employee_no == employee_no).first()
            )
        else:
            name = import_service._optional_text(row.get("name"))
            if name:
                candidate = (
                    db.query(Candidate)
                    .filter(Candidate.employee_no.is_(None), Candidate.name == name)
                    .first()
                )
        if candidate is None:
            reason = import_service._validate_candidate_import_row(
                row=row,
                existing_employee_numbers={
                    item[0]
                    for item in db.query(Candidate.employee_no)
                    .filter(Candidate.employee_no.isnot(None))
                    .all()
                },
                existing_names_without_no={
                    item[0]
                    for item in db.query(Candidate.name)
                    .filter(Candidate.employee_no.is_(None))
                    .all()
                },
            )
            if reason:
                failures.append(ImportFailure(row_number=row_number, reason=reason))
                continue
            candidate = import_service._build_candidate(row)
            db.add(candidate)
            db.flush()
        else:
            row_email = import_service.normalize_candidate_email(row.get("email"))
            email_reason = import_service.validate_candidate_email(row)
            existing_email = import_service.normalize_candidate_email(candidate.email)
            if email_reason == "邮箱格式不正确":
                failures.append(
                    ImportFailure(row_number=row_number, reason=email_reason)
                )
                continue
            if existing_email is None:
                if row_email is None:
                    failures.append(
                        ImportFailure(row_number=row_number, reason="邮箱不能为空")
                    )
                    continue
                candidate.email = row_email
            elif row_email is not None and row_email != existing_email:
                failures.append(
                    ImportFailure(
                        row_number=row_number,
                        reason="邮箱与已有考试人员不一致",
                    )
                )
                continue
            elif candidate.email != existing_email:
                candidate.email = existing_email

        exists = (
            db.query(ExamCandidateScope.id)
            .filter(
                ExamCandidateScope.exam_id == exam_id,
                ExamCandidateScope.candidate_id == candidate.id,
            )
            .first()
        )
        if exists is None:
            db.add(ExamCandidateScope(exam_id=exam_id, candidate_id=candidate.id))
        success_count += 1

    batch = ImportBatch(
        import_type="exam_candidates",
        file_name=file_name,
        total_count=parsed.total_count,
        success_count=success_count,
        failed_count=len(failures),
        status="completed",
        error_report=[failure.model_dump() for failure in failures],
    )
    db.add(batch)
    db.flush()
    if commit:
        db.commit()
    return QuestionImportResult(
        batch_id=batch.id,
        success_count=success_count,
        failed_count=len(failures),
        failures=failures,
    )
