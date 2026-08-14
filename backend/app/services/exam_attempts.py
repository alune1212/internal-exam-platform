from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.time import ensure_aware
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
    ExamCandidateScope,
    ExamRetakeGrant,
)
from app.models.attempt import SUBMITTED_STATUSES, TERMINAL_ATTEMPT_STATUSES
from app.schemas.attempt import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AttemptQuestionRead,
    AttemptRead,
    AttemptResultRead,
    AttemptSessionTakeoverResponse,
)
from app.schemas.exam import ExamRead, ExamStartResponse
from app.services.exam_configuration import (
    _assert_exam_available,
    _exam_has_question_pool,
)
from app.services.exam_errors import (
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    AttemptQuestionNotFoundError,
    AttemptResultNotReadyError,
    AttemptRevisionConflictError,
    AttemptSessionConflictError,
    CandidateNotEligibleError,
    CandidateNotFoundError,
    ExamNotActiveError,
    ExamNotFoundError,
    ExamQuestionPoolMissingError,
)
from app.services.exam_paper import (
    _optional_decimal,
    _parse_fixed_paper_rule,
    _rescale_scores,
    _select_exam_questions,
)
from app.services.exam_results import build_attempt_result
from app.services.operational_lock_service import assert_backup_write_allowed
from app.services.scoring_service import score_answer


def _build_correct_answer_snapshot(options: list) -> str:
    correct = sorted(option.label for option in options if option.is_correct)
    return ",".join(correct)


def _build_options_snapshot(options: list) -> list[dict]:
    return [
        {
            "label": option.label,
            "content": option.content,
            "sort_order": option.sort_order,
        }
        for option in sorted(options, key=lambda item: item.sort_order)
    ]


def _find_unused_retake_grant(
    db: Session,
    exam_id: int,
    candidate_id: int,
    *,
    for_update: bool = False,
) -> ExamRetakeGrant | None:
    query = (
        db.query(ExamRetakeGrant)
        .filter(
            ExamRetakeGrant.exam_id == exam_id,
            ExamRetakeGrant.candidate_id == candidate_id,
            ExamRetakeGrant.used_at.is_(None),
        )
        .order_by(ExamRetakeGrant.created_at)
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def create_retake_grant(
    db: Session, exam_id: int, candidate_id: int, *, commit: bool = True
) -> ExamRetakeGrant:
    # The public admin wrapper applies the stricter formal-attempt gate; this
    # low-level helper only needs the shared backup/writer-fence guard so its
    # existing row-level semantics remain unchanged.
    assert_backup_write_allowed(db)
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
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
    submitted = (
        db.query(ExamAttempt.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.status.in_(TERMINAL_ATTEMPT_STATUSES),
        )
        .first()
    )
    if submitted is None:
        raise AttemptNotFoundError(0)
    existing = _find_unused_retake_grant(db, exam_id, candidate_id)
    if existing is not None:
        return existing
    grant = ExamRetakeGrant(exam_id=exam_id, candidate_id=candidate_id)
    db.add(grant)
    try:
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        if _is_unused_retake_grant_unique_violation(exc):
            existing = _find_unused_retake_grant(db, exam_id, candidate_id)
            if existing is not None:
                return existing
        raise
    if commit:
        db.refresh(grant)
    return grant


def _latest_attempt_for_candidate(
    db: Session, exam_id: int, candidate_id: int
) -> ExamAttempt | None:
    return (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id, ExamAttempt.candidate_id == candidate_id
        )
        .order_by(ExamAttempt.attempt_no.desc(), ExamAttempt.id.desc())
        .first()
    )


def _has_unused_retake_grant(db: Session, exam_id: int, candidate_id: int) -> bool:
    return _find_unused_retake_grant(db, exam_id, candidate_id) is not None


def _constraint_name(exc: IntegrityError) -> str:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return str(name) if name else str(orig or exc)


def _is_in_progress_attempt_unique_violation(exc: IntegrityError) -> bool:
    message = _constraint_name(exc)
    return (
        "ux_exam_attempt_one_in_progress" in message
        or "exam_attempt.exam_id, exam_attempt.candidate_id" in message
    )


def _is_unused_retake_grant_unique_violation(exc: IntegrityError) -> bool:
    message = _constraint_name(exc)
    return (
        "ux_exam_retake_grant_one_unused" in message
        or "exam_retake_grant.exam_id, exam_retake_grant.candidate_id" in message
    )


def _load_attempt_with_snapshots(
    db: Session, attempt_id: int, *, for_update: bool = False
) -> ExamAttempt:
    query = (
        db.query(ExamAttempt)
        .options(
            selectinload(ExamAttempt.questions).selectinload(
                ExamAttemptQuestion.answer
            ),
            selectinload(ExamAttempt.exam),
        )
        .filter(ExamAttempt.id == attempt_id)
    )
    if for_update:
        query = query.with_for_update().populate_existing()
    attempt = query.one_or_none()
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    return attempt


def _ensure_attempt_scope(db: Session, attempt: ExamAttempt) -> None:
    """Reject repaired/stale attempts whose formal roster scope was removed."""

    scoped = (
        db.query(ExamCandidateScope.id)
        .filter(
            ExamCandidateScope.exam_id == attempt.exam_id,
            ExamCandidateScope.candidate_id == attempt.candidate_id,
        )
        .first()
    )
    if scoped is None:
        raise CandidateNotEligibleError(attempt.candidate_id)


def _attempt_deadline(attempt: ExamAttempt) -> datetime:
    return ensure_aware(attempt.ends_at)


def _new_attempt_session_credential() -> tuple[str, str]:
    credential = token_urlsafe(32)
    return credential, sha256(credential.encode("utf-8")).hexdigest()


def verify_attempt_session(
    db: Session,
    attempt_id: int,
    candidate_id: int,
    credential: str | None,
) -> ExamAttempt:
    attempt = _load_attempt_with_snapshots(db, attempt_id, for_update=True)
    actual_hash = sha256((credential or "").encode("utf-8")).hexdigest()
    if (
        attempt.candidate_id != candidate_id
        or attempt.attempt_session_hash is None
        or not compare_digest(actual_hash, attempt.attempt_session_hash)
    ):
        raise AttemptSessionConflictError()
    _ensure_attempt_scope(db, attempt)
    return attempt


def takeover_attempt_session(
    db: Session,
    attempt_id: int,
    candidate_id: int,
) -> AttemptSessionTakeoverResponse:
    assert_backup_write_allowed(db)
    attempt = _load_attempt_with_snapshots(db, attempt_id, for_update=True)
    if attempt.candidate_id != candidate_id:
        raise AttemptNotFoundError(attempt_id)
    _ensure_attempt_scope(db, attempt)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
    credential, credential_hash = _new_attempt_session_credential()
    attempt.attempt_session_hash = credential_hash
    attempt.attempt_session_generation = max(attempt.attempt_session_generation, 0) + 1
    db.commit()
    return AttemptSessionTakeoverResponse(
        attempt_id=attempt.id,
        attempt_session_credential=credential,
        attempt_session_generation=attempt.attempt_session_generation,
        answer_revision=attempt.answer_revision,
        ends_at=ensure_aware(attempt.ends_at),
    )


def _is_attempt_expired(attempt: ExamAttempt, now: datetime | None = None) -> bool:
    return (now or datetime.now(UTC)) >= _attempt_deadline(attempt)


def start_exam(db: Session, exam_id: int, candidate_id: int) -> ExamStartResponse:
    # Keep the existing-attempt recovery branch read-only so it remains
    # available while a backup freeze or writer fence blocks writes.  New
    # attempt creation acquires the shared transaction mutex below and then
    # reloads/locks the exam before making the final active-status decision.
    exam = db.execute(select(Exam).where(Exam.id == exam_id)).scalar_one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "active":
        raise ExamNotActiveError(exam_id)

    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    if candidate.status != "active":
        raise CandidateNotEligibleError(candidate_id)
    scope = db.execute(
        select(ExamCandidateScope.id)
        .where(
            ExamCandidateScope.exam_id == exam_id,
            ExamCandidateScope.candidate_id == candidate_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if scope is None:
        raise CandidateNotEligibleError(candidate_id)

    in_progress = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.status == "in_progress",
        )
        .order_by(ExamAttempt.attempt_no.desc(), ExamAttempt.id.desc())
        .first()
    )
    if in_progress is not None:
        return _build_exam_start_response_from_attempt(in_progress)

    # A new attempt is a write and therefore must honor the backup and
    # writer-fence checks.  This also acquires the shared transaction mutex
    # used by archive/status mutations.  Reload the exam under a row lock so
    # archive-first and start-first orderings are deterministic.
    assert_backup_write_allowed(db)
    exam = (
        db.query(Exam)
        .filter(Exam.id == exam_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "active":
        raise ExamNotActiveError(exam_id)

    next_attempt_no = (
        db.query(func.coalesce(func.max(ExamAttempt.attempt_no), 0))
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
        )
        .scalar()
        or 0
    ) + 1
    has_submitted = bool(
        db.query(func.count(ExamAttempt.id))
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.status.in_(TERMINAL_ATTEMPT_STATUSES),
        )
        .scalar()
    )
    retake_grant: ExamRetakeGrant | None = None
    if has_submitted:
        retake_grant = _find_unused_retake_grant(
            db, exam_id, candidate_id, for_update=True
        )
        if retake_grant is None:
            latest_submitted = (
                db.query(ExamAttempt)
                .filter(
                    ExamAttempt.exam_id == exam_id,
                    ExamAttempt.candidate_id == candidate_id,
                    ExamAttempt.status.in_(TERMINAL_ATTEMPT_STATUSES),
                )
                .order_by(ExamAttempt.attempt_no.desc(), ExamAttempt.id.desc())
                .first()
            )
            assert latest_submitted is not None
            raise AttemptAlreadySubmittedError(latest_submitted.id)

    _assert_exam_available(exam)
    paper_seed = uuid4().hex
    if not _exam_has_question_pool(db, exam_id):
        raise ExamQuestionPoolMissingError(exam_id)
    questions = _select_exam_questions(db, exam, paper_seed)
    now = datetime.now(UTC)
    ends_at = now + timedelta(minutes=exam.duration_minutes)
    attempt_session_credential, attempt_session_hash = _new_attempt_session_credential()

    rule = _parse_fixed_paper_rule(exam.question_rule)
    if rule is not None:
        scaled_pairs = _rescale_scores(questions, rule.total_score)
        total_score = rule.total_score
        pass_score_snapshot = rule.pass_score
    else:
        scaled_pairs = [(question, question.score) for question in questions]
        total_score = sum(question.score for question in questions)
        pass_score_snapshot = _optional_decimal(
            (exam.question_rule or {}).get("pass_score"), "pass_score"
        )

    attempt = ExamAttempt(
        exam_id=exam_id,
        candidate_id=candidate_id,
        status="in_progress",
        started_at=now,
        ends_at=ends_at,
        duration_minutes_snapshot=exam.duration_minutes,
        pass_score_snapshot=pass_score_snapshot,
        show_answer_after_submit_snapshot=exam.show_answer_after_submit,
        total_score=total_score,
        attempt_no=next_attempt_no,
        attempt_kind="retake" if has_submitted else "initial",
        paper_seed=paper_seed,
        attempt_session_hash=attempt_session_hash,
        attempt_session_generation=1,
        answer_revision=0,
    )
    db.add(attempt)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if _is_in_progress_attempt_unique_violation(exc):
            existing = _latest_attempt_for_candidate(db, exam_id, candidate_id)
            if existing is not None and existing.status == "in_progress":
                return _build_exam_start_response_from_attempt(existing)
        raise
    if retake_grant is not None:
        retake_grant.used_attempt_id = attempt.id
        retake_grant.used_at = now

    snapshots: list[ExamAttemptQuestion] = []
    for index, (question, scaled_score) in enumerate(scaled_pairs):
        snapshot = ExamAttemptQuestion(
            attempt_id=attempt.id,
            original_question_id=question.id,
            question_type=question.question_type,
            stem_snapshot=question.stem,
            options_snapshot=_build_options_snapshot(question.options),
            correct_answer_snapshot=_build_correct_answer_snapshot(question.options),
            analysis_snapshot=question.analysis,
            score=scaled_score,
            sort_order=index,
        )
        db.add(snapshot)
        snapshots.append(snapshot)
    db.flush()
    question_reads = [
        AttemptQuestionRead(
            id=snapshot.id,
            question_type=snapshot.question_type,
            stem_snapshot=snapshot.stem_snapshot,
            options_snapshot=snapshot.options_snapshot,
            score=float(snapshot.score),
            sort_order=snapshot.sort_order,
            selected_answer=None,
        )
        for snapshot in snapshots
    ]
    db.commit()
    return ExamStartResponse(
        attempt_id=attempt.id,
        exam=ExamRead.model_validate(exam),
        questions=question_reads,
        started_at=now,
        ends_at=ends_at,
        attempt_session_credential=attempt_session_credential,
        attempt_session_generation=attempt.attempt_session_generation,
        answer_revision=attempt.answer_revision,
    )


def _build_exam_start_response_from_attempt(attempt: ExamAttempt) -> ExamStartResponse:
    return ExamStartResponse(
        attempt_id=attempt.id,
        exam=ExamRead.model_validate(attempt.exam),
        questions=[
            AttemptQuestionRead(
                id=snapshot.id,
                question_type=snapshot.question_type,
                stem_snapshot=snapshot.stem_snapshot,
                options_snapshot=snapshot.options_snapshot,
                score=float(snapshot.score),
                sort_order=snapshot.sort_order,
                selected_answer=(
                    snapshot.answer.selected_answer if snapshot.answer else None
                ),
            )
            for snapshot in attempt.questions
        ],
        started_at=attempt.started_at,
        ends_at=ensure_aware(attempt.ends_at),
        attempt_session_generation=attempt.attempt_session_generation,
        answer_revision=attempt.answer_revision,
    )


def get_attempt(db: Session, attempt_id: int) -> AttemptRead:
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    _ensure_attempt_scope(db, attempt)
    return AttemptRead(
        id=attempt.id,
        exam_id=attempt.exam_id,
        candidate_id=attempt.candidate_id,
        status=attempt.status,
        started_at=ensure_aware(attempt.started_at),
        duration_minutes=attempt.duration_minutes_snapshot,
        ends_at=ensure_aware(attempt.ends_at),
        server_now=datetime.now(UTC),
        submitted_at=attempt.submitted_at,
        score=float(attempt.score),
        total_score=float(attempt.total_score),
        correct_count=attempt.correct_count,
        wrong_count=attempt.wrong_count,
        attempt_session_generation=attempt.attempt_session_generation,
        answer_revision=attempt.answer_revision,
        questions=[
            AttemptQuestionRead(
                id=question.id,
                question_type=question.question_type,
                stem_snapshot=question.stem_snapshot,
                options_snapshot=question.options_snapshot,
                score=float(question.score),
                sort_order=question.sort_order,
                selected_answer=(
                    question.answer.selected_answer if question.answer else None
                ),
            )
            for question in attempt.questions
        ],
    )


def save_answers(
    db: Session,
    attempt_id: int,
    payload: AnswerSaveRequest,
    *,
    load_attempt: Callable[..., ExamAttempt] | None = None,
) -> AnswerSaveResponse:
    assert_backup_write_allowed(db)
    loader = load_attempt or _load_attempt_with_snapshots
    attempt = loader(db, attempt_id, for_update=True)
    _ensure_attempt_scope(db, attempt)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
    if _is_attempt_expired(attempt):
        submit_attempt(db, attempt_id, "auto")
        raise AttemptAlreadySubmittedError(attempt_id)
    if (
        attempt.attempt_session_hash is not None
        and payload.answer_revision != attempt.answer_revision
    ):
        raise AttemptRevisionConflictError(attempt.answer_revision)
    questions_by_id = {question.id: question for question in attempt.questions}
    now = datetime.now(UTC)
    for item in payload.answers:
        question = questions_by_id.get(item.attempt_question_id)
        if question is None:
            raise AttemptQuestionNotFoundError(item.attempt_question_id)
        if question.answer is None:
            question.answer = ExamAttemptAnswer(
                attempt_question_id=question.id,
                selected_answer=item.selected_answer,
                answered_at=now,
            )
        else:
            question.answer.selected_answer = item.selected_answer
            question.answer.answered_at = now
    attempt.answer_revision += 1
    db.commit()
    return AnswerSaveResponse(
        saved_count=len(payload.answers),
        saved_at=now,
        answer_revision=attempt.answer_revision,
    )


def submit_attempt(
    db: Session,
    attempt_id: int,
    submit_type: str,
    *,
    load_attempt: Callable[..., ExamAttempt] | None = None,
) -> AttemptResultRead:
    assert_backup_write_allowed(db)
    loader = load_attempt or _load_attempt_with_snapshots
    attempt = loader(db, attempt_id, for_update=True)
    _ensure_attempt_scope(db, attempt)
    result = score_and_mark_attempt_submitted(
        attempt, submit_type=submit_type, submitted_at=datetime.now(UTC)
    )
    db.commit()
    return result


def score_and_mark_attempt_submitted(
    attempt: ExamAttempt, *, submit_type: str, submitted_at: datetime
) -> AttemptResultRead:
    if attempt.status != "in_progress":
        return build_attempt_result(attempt)
    effective_submit_type = (
        "auto"
        if submit_type == "auto" or _is_attempt_expired(attempt, submitted_at)
        else submit_type
    )
    score = Decimal("0")
    correct_count = 0
    for question in attempt.questions:
        answer = question.answer
        scoring = score_answer(
            question.question_type,
            question.correct_answer_snapshot,
            answer.selected_answer if answer else None,
            float(question.score),
        )
        if answer is None:
            answer = ExamAttemptAnswer(
                attempt_question_id=question.id,
                selected_answer=None,
                answered_at=None,
            )
            question.answer = answer
        answer.is_correct = scoring.is_correct
        answer.score_awarded = Decimal(str(scoring.score_awarded))
        if scoring.is_correct:
            correct_count += 1
            score += Decimal(str(scoring.score_awarded))
    attempt.status = (
        "auto_submitted" if effective_submit_type == "auto" else "submitted"
    )
    attempt.submitted_at = submitted_at
    attempt.submit_type = effective_submit_type
    attempt.score = score
    attempt.correct_count = correct_count
    attempt.wrong_count = len(attempt.questions) - correct_count
    attempt.duration_seconds = int(
        (submitted_at - ensure_aware(attempt.started_at)).total_seconds()
    )
    return build_attempt_result(attempt)


def get_attempt_result(db: Session, attempt_id: int) -> AttemptResultRead:
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    _ensure_attempt_scope(db, attempt)
    if attempt.status not in SUBMITTED_STATUSES:
        raise AttemptResultNotReadyError(attempt_id)
    return build_attempt_result(attempt)
