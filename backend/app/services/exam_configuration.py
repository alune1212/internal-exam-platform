import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time import ensure_aware
from app.models import Candidate, Exam, ExamCandidateScope, ExamQuestionPool
from app.schemas.exam import (
    ExamCreate,
    ExamRead,
    ExamUpdate,
    PublicationReadinessIssue,
    PublicationReadinessRead,
)
from app.services.exam_errors import (
    CandidateNotEligibleError,
    ExamConfigError,
    ExamFrozenError,
    ExamNotAvailableError,
    ExamNotFoundError,
    InsufficientQuestionsError,
)
from app.services.exam_paper import (
    _load_active_question_pool,
    _require_positive_int,
    _validate_fixed_rule_capacity,
    _validate_question_rule,
)
from app.services.import_service import normalize_candidate_email
from app.services.operational_lock_service import assert_admin_mutation_allowed

VALID_EXAM_STATUSES = {"draft", "active", "archived"}
MAX_FORMAL_DURATION_MINUTES = 120
START_GRACE_MINUTES = 15


def _validate_exam_window(
    available_from: datetime | None, available_until: datetime | None
) -> None:
    if (
        available_from is not None
        and available_until is not None
        and ensure_aware(available_from) >= ensure_aware(available_until)
    ):
        raise ExamConfigError("开放开始时间必须早于结束时间")


def _validate_exam_config_values(
    *,
    duration_minutes: int,
    status: str,
    question_rule: object,
    available_from: datetime | None = None,
    available_until: datetime | None = None,
) -> None:
    _require_positive_int(duration_minutes, "考试时长")
    if duration_minutes > MAX_FORMAL_DURATION_MINUTES:
        raise ExamConfigError("正式考试时长不能超过 120 分钟")
    if status not in VALID_EXAM_STATUSES:
        raise ExamConfigError(
            "考试状态只能填写草稿（draft）、已发布（active）或已归档（archived）"
        )
    _validate_question_rule(question_rule)
    _validate_exam_window(available_from, available_until)


def _freeze_question_pool(
    db: Session, exam: Exam, *, require_questions: bool = True
) -> None:
    questions = _load_active_question_pool(db)
    if require_questions and not questions:
        raise InsufficientQuestionsError("启用题目数量不足，无法发布考试")

    db.query(ExamQuestionPool).filter(ExamQuestionPool.exam_id == exam.id).delete()
    for index, question in enumerate(questions):
        db.add(
            ExamQuestionPool(
                exam_id=exam.id,
                question_id=question.id,
                sort_order=index,
            )
        )


def _freeze_roster(db: Session, exam: Exam) -> None:
    """Validate and flush the complete roster in the publication transaction."""

    scopes = (
        db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.exam_id == exam.id)
        .with_for_update()
        .all()
    )
    if not scopes:
        raise CandidateNotEligibleError(0)
    for scope in scopes:
        candidate = db.get(Candidate, scope.candidate_id)
        reason = _validate_roster_scope(scope, candidate)
        if reason:
            raise ExamConfigError(reason)
        # Publication always starts with an explicit unsent state.  Existing
        # draft rows should already carry this default, but assigning it here
        # makes the freeze invariant explicit and prevents stale test fixtures
        # from inheriting a delivery claim.
        scope.invitation_status = "not_sent"
        scope.invitation_claimed_at = None
        scope.invitation_claim_owner = None
        scope.invitation_error_class = None
        scope.invitation_sent_at = None
    db.flush()


def _exam_has_question_pool(db: Session, exam_id: int) -> bool:
    return (
        db.query(ExamQuestionPool.id)
        .filter(ExamQuestionPool.exam_id == exam_id)
        .first()
        is not None
    )


def _assert_exam_available(exam: Exam) -> None:
    now = datetime.now(UTC)
    if exam.available_from is not None and now < ensure_aware(exam.available_from):
        raise ExamNotAvailableError("考试尚未开始")
    if exam.available_from is not None and now > ensure_aware(
        exam.available_from
    ) + timedelta(minutes=START_GRACE_MINUTES):
        raise ExamNotAvailableError("考试开始时间已截止")
    if exam.available_until is not None and now > ensure_aware(exam.available_until):
        raise ExamNotAvailableError("考试已结束")


def _candidate_exam_is_visible(exam: Exam, *, now: datetime | None = None) -> bool:
    # Published scoped exams are visible immediately.  ``_assert_exam_available``
    # remains the authoritative start-time/grace/deadline gate.
    _ = exam, now
    return True


def _exam_availability_status(exam: Exam, *, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if exam.available_from is not None and now < ensure_aware(exam.available_from):
        return "not_started"
    if exam.available_from is not None and now > ensure_aware(
        exam.available_from
    ) + timedelta(minutes=START_GRACE_MINUTES):
        return "ended"
    if exam.available_until is not None and now > ensure_aware(exam.available_until):
        return "ended"
    return "open"


def _question_pool_count(db: Session, exam_id: int) -> int:
    return (
        db.query(func.count(ExamQuestionPool.id))
        .filter(ExamQuestionPool.exam_id == exam_id)
        .scalar()
        or 0
    )


def _question_pool_counts_by_exam(db: Session, exam_ids: list[int]) -> dict[int, int]:
    if not exam_ids:
        return {}
    rows = (
        db.query(ExamQuestionPool.exam_id, func.count(ExamQuestionPool.id))
        .filter(ExamQuestionPool.exam_id.in_(exam_ids))
        .group_by(ExamQuestionPool.exam_id)
        .all()
    )
    return {exam_id: int(count) for exam_id, count in rows}


def _build_exam_read(
    db: Session,
    exam: Exam,
    updates: dict[str, object] | None = None,
    *,
    pool_counts: dict[int, int] | None = None,
    observed_at: datetime | None = None,
) -> ExamRead:
    pool_count = (
        pool_counts.get(exam.id, 0)
        if pool_counts is not None
        else _question_pool_count(db, exam.id)
    )
    data: dict[str, object] = {
        "question_pool_count": pool_count,
        "availability_status": _exam_availability_status(exam, now=observed_at),
    }
    if updates:
        data.update(updates)
    return ExamRead.model_validate(exam).model_copy(update=data)


def _ensure_exam_has_scope(db: Session, exam_id: int) -> None:
    scope_count = (
        db.query(func.count(ExamCandidateScope.id))
        .filter(ExamCandidateScope.exam_id == exam_id)
        .scalar()
    )
    if not scope_count:
        raise CandidateNotEligibleError(0)


def _validate_exam_activation_requirements(
    db: Session, exam_id: int, question_rule: dict
) -> None:
    _ensure_exam_has_scope(db, exam_id)
    _validate_fixed_rule_capacity(db, question_rule)


def _validate_roster_scope(
    scope: ExamCandidateScope, candidate: Candidate | None
) -> str | None:
    if candidate is None:
        return "应考名单关联账号不存在"
    if not normalize_candidate_email(scope.roster_email):
        return "应考名单邮箱无效"
    if normalize_candidate_email(candidate.email) != normalize_candidate_email(
        scope.roster_email
    ):
        return "应考名单邮箱与账号不一致"
    if not scope.roster_name or not scope.roster_name.strip():
        return "应考名单姓名不能为空"
    if candidate.status == "inactive":
        return "应考名单中包含已停用账号"
    return None


def get_publication_readiness(db: Session, exam_id: int) -> PublicationReadinessRead:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)

    blockers: list[PublicationReadinessIssue] = []
    warnings: list[PublicationReadinessIssue] = []
    questions = _load_active_question_pool(db)
    scopes = (
        db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.exam_id == exam_id)
        .order_by(ExamCandidateScope.id)
        .all()
    )

    if exam.status != "draft":
        blockers.append(
            PublicationReadinessIssue(
                code="exam_not_draft", message="只有草稿考试可以发布"
            )
        )
    try:
        _validate_exam_config_values(
            duration_minutes=exam.duration_minutes,
            status=exam.status,
            question_rule=exam.question_rule,
            available_from=exam.available_from,
            available_until=exam.available_until,
        )
    except (ExamConfigError, InsufficientQuestionsError) as exc:
        blockers.append(
            PublicationReadinessIssue(code="invalid_exam_config", message=str(exc))
        )

    if not scopes:
        blockers.append(
            PublicationReadinessIssue(code="empty_roster", message="应考名单不能为空")
        )
    scope_errors = [
        error
        for scope in scopes
        if (
            error := _validate_roster_scope(
                scope, db.get(Candidate, scope.candidate_id)
            )
        )
    ]
    if scope_errors:
        blockers.append(
            PublicationReadinessIssue(
                code="roster_email_not_ready",
                message=f"应考名单中有 {len(scope_errors)} 行身份或邮箱不可用",
            )
        )
    try:
        _validate_fixed_rule_capacity(db, exam.question_rule)
    except (ExamConfigError, InsufficientQuestionsError) as exc:
        blockers.append(
            PublicationReadinessIssue(code="question_pool_not_ready", message=str(exc))
        )
    if exam.available_from is None:
        warnings.append(
            PublicationReadinessIssue(
                code="missing_available_from",
                message="未设置开考时间，候选人列表将不显示开考时间提示",
            )
        )
    if exam.available_until is None:
        warnings.append(
            PublicationReadinessIssue(
                code="missing_available_until", message="未设置考试开放结束时间"
            )
        )

    fingerprint_payload = {
        "exam_id": exam.id,
        "title": exam.title,
        "duration_minutes": exam.duration_minutes,
        "question_rule": exam.question_rule,
        "available_from": (
            exam.available_from.isoformat() if exam.available_from else None
        ),
        "available_until": (
            exam.available_until.isoformat() if exam.available_until else None
        ),
        "question_ids": [question.id for question in questions],
        "roster": [
            {
                "scope_id": scope.id,
                "candidate_id": scope.candidate_id,
                "roster_email": scope.roster_email,
                "roster_name": scope.roster_name,
                "department": scope.department,
                "position": scope.position,
                "exam_group": scope.exam_group,
                "roster_remark": scope.roster_remark,
            }
            for scope in scopes
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return PublicationReadinessRead(
        exam_id=exam.id,
        ready=not blockers,
        prospective_pool_count=len(questions),
        roster_count=len(scopes),
        blockers=blockers,
        warnings=warnings,
        fingerprint=fingerprint,
    )


def _ensure_candidate_in_scope(db: Session, exam_id: int, candidate_id: int) -> None:
    scoped = (
        db.query(ExamCandidateScope.id)
        .filter(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .first()
    )
    if scoped is None:
        raise CandidateNotEligibleError(candidate_id)


def _validate_exam_status_transition(current_status: str, next_status: str) -> None:
    if next_status not in VALID_EXAM_STATUSES:
        raise ExamConfigError(
            "考试状态只能填写草稿（draft）、已发布（active）或已归档（archived）"
        )
    if current_status == next_status:
        return
    if current_status == "draft" and next_status == "active":
        return
    if current_status == "active" and next_status == "archived":
        return
    if current_status == "archived":
        raise ExamFrozenError("已归档考试不得重新激活")
    raise ExamFrozenError("考试状态流转不合法")


def create_exam(db: Session, payload: ExamCreate) -> ExamRead:
    assert_admin_mutation_allowed(db)
    data = payload.model_dump()
    _validate_exam_config_values(
        duration_minutes=data["duration_minutes"],
        status=data["status"],
        question_rule=data["question_rule"],
        available_from=data.get("available_from"),
        available_until=data.get("available_until"),
    )
    if data["status"] == "active":
        raise ExamConfigError("考试必须先创建为草稿，再通过发布流程激活")
    exam = Exam(**data)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _build_exam_read(db, exam)


def update_exam(
    db: Session, exam_id: int, payload: ExamUpdate, *, commit: bool = True
) -> ExamRead:
    assert_admin_mutation_allowed(db)
    raw_updates = payload.model_dump(exclude_unset=True)
    status_update_requested = "status" in raw_updates
    query = db.query(Exam).filter(Exam.id == exam_id)
    if status_update_requested:
        query = query.with_for_update().populate_existing()
    exam = query.one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)

    updates = dict(raw_updates)
    confirmation_title = updates.pop("confirmation_title", None)
    next_status = updates.get("status", exam.status)
    _validate_exam_status_transition(exam.status, next_status)
    if exam.status in {"active", "archived"}:
        frozen_fields = {"duration_minutes", "question_rule"}
        if frozen_fields.intersection(updates):
            raise ExamFrozenError()

    next_duration_minutes = updates.get("duration_minutes", exam.duration_minutes)
    next_question_rule = updates.get("question_rule", exam.question_rule)
    next_available_from = updates.get("available_from", exam.available_from)
    next_available_until = updates.get("available_until", exam.available_until)
    activating = updates.get("status") == "active" and exam.status != "active"
    if activating and confirmation_title != updates.get("title", exam.title):
        raise ExamConfigError("发布确认标题必须与考试标题完全一致")
    _validate_exam_config_values(
        duration_minutes=next_duration_minutes,
        status=next_status,
        question_rule=next_question_rule,
        available_from=next_available_from,
        available_until=next_available_until,
    )
    if activating:
        _validate_exam_activation_requirements(db, exam.id, next_question_rule)

    for field, value in updates.items():
        if activating and field == "status":
            continue
        setattr(exam, field, value)

    if activating:
        readiness = get_publication_readiness(db, exam.id)
        if not readiness.ready:
            messages = "；".join(issue.message for issue in readiness.blockers)
            raise ExamConfigError(f"发布预检未通过：{messages}")
        exam.status = "active"
        _freeze_question_pool(db, exam)
        _freeze_roster(db, exam)

    if commit:
        db.commit()
        db.refresh(exam)
    else:
        # Keep the mutation in the caller's transaction so route-level audit
        # writes and this business change share the same writer-fence mutex.
        db.flush()
    return _build_exam_read(db, exam)


def publish_exam(
    db: Session,
    exam_id: int,
    confirmation_title: str,
    *,
    commit: bool = True,
) -> ExamRead:
    return update_exam(
        db,
        exam_id,
        ExamUpdate(status="active", confirmation_title=confirmation_title),
        commit=commit,
    )
