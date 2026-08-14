"""Compatibility facade for exam services.

Routes and existing tests keep importing this module while focused modules own
configuration, paper generation, attempt lifecycle, and result construction.
"""

from sqlalchemy.orm import Session

from app.models import Candidate, Exam, ExamCandidateScope
from app.models.attempt import TERMINAL_ATTEMPT_STATUSES
from app.schemas.attempt import AnswerSaveRequest, AnswerSaveResponse, AttemptResultRead
from app.schemas.exam import (
    ExamCandidateCreate,
    ExamCandidateRow,
    ExamCandidateUpdate,
    ExamRead,
)
from app.schemas.question import QuestionImportResult
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
from app.services.exam_workspace import get_exam_workspace as get_exam_workspace
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
    if candidate is None or candidate.status != "active":
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
    db: Session, exam_id: int, scope: ExamCandidateScope
) -> ExamCandidateRow:
    candidate = scope.candidate or db.get(Candidate, scope.candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(scope.candidate_id)
    latest = _latest_attempt_for_candidate(db, exam_id, candidate.id)
    return ExamCandidateRow(
        scope_id=scope.id,
        candidate_id=candidate.id,
        roster_email=scope.roster_email,
        roster_name=scope.roster_name,
        department=scope.department,
        position=scope.position,
        exam_group=scope.exam_group,
        roster_remark=scope.roster_remark,
        account_status=candidate.status,
        invitation_status=scope.invitation_status,
        last_invitation_attempt_at=scope.last_invitation_attempt_at,
        invitation_sent_at=scope.invitation_sent_at,
        invitation_error_class=scope.invitation_error_class,
        invitation_claimed_at=scope.invitation_claimed_at,
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
    scopes = (
        db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.exam_id == exam_id)
        .order_by(ExamCandidateScope.roster_name, ExamCandidateScope.id)
        .all()
    )
    return [_build_exam_candidate_row(db, exam_id, scope) for scope in scopes]


def remove_exam_candidate(
    db: Session, exam_id: int, candidate_id: int
) -> dict[str, int]:
    assert_admin_mutation_allowed(db)
    exam = db.query(Exam).filter(Exam.id == exam_id).with_for_update().one_or_none()
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


def add_exam_candidate(
    db: Session, exam_id: int, payload: ExamCandidateCreate, *, commit: bool = True
) -> ExamCandidateRow:
    """Add one normalized email roster row to a draft exam."""

    assert_admin_mutation_allowed(db)
    exam = db.query(Exam).filter(Exam.id == exam_id).with_for_update().one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "draft":
        raise ExamFrozenError("考试发布后应考名单已冻结")
    from app.services.import_service import add_exam_roster_row

    scope = add_exam_roster_row(db, exam_id, payload.model_dump())
    if commit:
        db.commit()
        db.refresh(scope)
    return _build_exam_candidate_row(db, exam_id, scope)


def update_exam_candidate(
    db: Session,
    exam_id: int,
    candidate_id: int,
    payload: ExamCandidateUpdate,
    *,
    commit: bool = True,
) -> ExamCandidateRow:
    """Update one draft scope; account profile fields remain untouched."""

    assert_admin_mutation_allowed(db)
    exam = db.query(Exam).filter(Exam.id == exam_id).with_for_update().one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "draft":
        raise ExamFrozenError("考试发布后应考名单已冻结")
    scope = (
        db.query(ExamCandidateScope)
        .filter(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .one_or_none()
    )
    if scope is None:
        raise CandidateNotFoundError(candidate_id)
    from app.services.import_service import update_exam_roster_row

    update_exam_roster_row(db, scope, payload.model_dump(exclude_unset=True))
    if commit:
        db.commit()
        db.refresh(scope)
    return _build_exam_candidate_row(db, exam_id, scope)


def create_retake_grant_row(
    db: Session, exam_id: int, candidate_id: int
) -> ExamCandidateRow:
    assert_admin_mutation_allowed(db)
    create_retake_grant(db, exam_id, candidate_id, commit=False)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    scope = (
        db.query(ExamCandidateScope)
        .filter(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .one_or_none()
    )
    if scope is None:
        raise CandidateNotEligibleError(candidate_id)
    return _build_exam_candidate_row(db, exam_id, scope)


def import_exam_candidates_from_workbook(
    db: Session,
    exam_id: int,
    file_obj: object,
    file_name: str,
    *,
    commit: bool = True,
) -> QuestionImportResult:
    from app.services import import_service

    return import_service.import_exam_roster_from_workbook(
        db, exam_id, file_obj, file_name, commit=commit
    )
