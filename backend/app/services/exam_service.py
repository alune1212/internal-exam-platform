import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.core.time import ensure_aware
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
    ExamCandidateScope,
    ExamQuestionPool,
    ExamRetakeGrant,
    ImportBatch,
    Question,
)
from app.models.attempt import SUBMITTED_STATUSES
from app.schemas.attempt import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AttemptQuestionRead,
    AttemptRead,
    AttemptResultQuestion,
    AttemptResultRead,
)
from app.schemas.exam import (
    ExamCandidateRow,
    ExamCreate,
    ExamRead,
    ExamStartResponse,
    ExamUpdate,
)
from app.schemas.question import ImportFailure, QuestionImportResult
from app.services.scoring_service import score_answer


class AdminAuthError(DomainError):
    """管理员鉴权失败。"""

    status_code = 401

    def __init__(self) -> None:
        super().__init__("管理员凭据无效，请重新登录。")


class ExamNotFoundError(DomainError):
    status_code = 404

    def __init__(self, exam_id: int) -> None:
        self.exam_id = exam_id
        super().__init__(f"考试 #{exam_id} 不存在")


class ExamNotActiveError(DomainError):
    status_code = 409

    def __init__(self, exam_id: int) -> None:
        self.exam_id = exam_id
        super().__init__(f"考试 #{exam_id} 未处于 active 状态")


class ExamNotAvailableError(DomainError):
    status_code = 409

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class CandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        self.candidate_id = candidate_id
        super().__init__(f"考生 #{candidate_id} 不存在")


class CandidateNotEligibleError(DomainError):
    status_code = 403

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考生 #{candidate_id} 当前不可参加考试")


class AttemptAlreadyExistsError(DomainError):
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考生已有进行中的考试记录 #{attempt_id}")


class AttemptNotFoundError(DomainError):
    status_code = 404

    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考试记录 #{attempt_id} 不存在")


class AttemptQuestionNotFoundError(DomainError):
    status_code = 404

    def __init__(self, attempt_question_id: int) -> None:
        self.attempt_question_id = attempt_question_id
        super().__init__(f"考试题目 #{attempt_question_id} 不存在")


class AttemptAlreadySubmittedError(DomainError):
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考试记录 #{attempt_id} 已提交")


class InsufficientQuestionsError(DomainError):
    status_code = 422

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ExamFrozenError(DomainError):
    status_code = 409

    def __init__(self, reason: str = "考试发布后结构配置已冻结") -> None:
        super().__init__(reason)


class ExamConfigError(DomainError):
    status_code = 422

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


@dataclass(frozen=True)
class FixedPaperRule:
    question_count: int
    total_score: Decimal
    type_counts: dict[str, int]


VALID_EXAM_STATUSES = {"draft", "active", "archived"}
VALID_FIXED_TYPES = {"single", "multiple", "judge"}


def _build_correct_answer_snapshot(options: list) -> str:
    """从题目选项中提取正确答案标签，逗号分隔。"""
    correct = sorted(opt.label for opt in options if opt.is_correct)
    return ",".join(correct)


def _build_options_snapshot(options: list) -> list[dict]:
    """构建选项快照 JSON 列表。"""
    return [
        {"label": opt.label, "content": opt.content, "sort_order": opt.sort_order}
        for opt in sorted(options, key=lambda o: o.sort_order)
    ]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_positive_int(value: object, field_name: str) -> int:
    if not _is_int(value) or value <= 0:
        separator = "" if field_name == "考试时长" else " "
        raise ExamConfigError(f"{field_name}{separator}必须为正整数")
    return value


def _require_non_negative_int(value: object, field_name: str) -> int:
    if not _is_int(value) or value < 0:
        raise ExamConfigError(f"{field_name} 必须为非负整数")
    return value


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        raise ExamConfigError(f"{field_name} 必须是数字")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ExamConfigError(f"{field_name} 必须是数字") from None
    if not decimal_value.is_finite():
        raise ExamConfigError(f"{field_name} 必须是数字")
    return decimal_value


def _validate_question_rule(question_rule: object) -> None:
    if not isinstance(question_rule, dict):
        raise ExamConfigError("抽题规则必须是对象")
    if not question_rule:
        return

    pass_score = _optional_decimal(question_rule.get("pass_score"), "pass_score")
    if pass_score is not None and pass_score < 0:
        raise ExamConfigError("pass_score 不能为负数")
    if "question_count" not in question_rule:
        return

    question_count = _require_positive_int(
        question_rule.get("question_count"), "question_count"
    )
    total_score_value = _require_positive_int(
        question_rule.get("total_score"), "total_score"
    )
    raw_type_counts = question_rule.get("type_counts")
    if not isinstance(raw_type_counts, dict):
        raise ExamConfigError("type_counts 必须是对象")
    if set(raw_type_counts) - VALID_FIXED_TYPES:
        raise ExamConfigError("type_counts 只能包含 single、multiple、judge")
    type_counts = {
        question_type: _require_non_negative_int(
            raw_type_counts.get(question_type, 0), f"type_counts.{question_type}"
        )
        for question_type in ("single", "multiple", "judge")
    }
    if sum(type_counts.values()) != question_count:
        raise InsufficientQuestionsError("抽题规则中的题型数量合计必须等于总题数")
    if pass_score is not None and pass_score > Decimal(total_score_value):
        raise ExamConfigError("pass_score 不能大于 total_score")


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
    if status not in VALID_EXAM_STATUSES:
        raise ExamConfigError("考试状态只能是 draft、active 或 archived")
    _validate_question_rule(question_rule)
    _validate_exam_window(available_from, available_until)


def _parse_fixed_paper_rule(question_rule: dict | None) -> FixedPaperRule | None:
    if not question_rule or "question_count" not in question_rule:
        return None

    _validate_question_rule(question_rule)
    question_count = question_rule["question_count"]
    total_score = Decimal(question_rule["total_score"])
    raw_type_counts = question_rule["type_counts"]
    type_counts = {
        question_type: int(raw_type_counts.get(question_type, 0))
        for question_type in ("single", "multiple", "judge")
    }
    return FixedPaperRule(
        question_count=question_count,
        total_score=total_score,
        type_counts=type_counts,
    )


def _questions_by_type(questions: list[Question]) -> dict[str, list[Question]]:
    grouped: dict[str, list[Question]] = defaultdict(list)
    for question in questions:
        grouped[question.question_type].append(question)
    return grouped


def _category_key(question: Question) -> str:
    return question.category_1 or "(未填写)"


def _active_category_totals(questions: list[Question]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for question in questions:
        totals[_category_key(question)] += 1
    return dict(totals)


def _deduplicate_questions_by_stem(questions: list[Question]) -> list[Question]:
    seen_stems: set[str] = set()
    unique_questions: list[Question] = []
    for question in questions:
        stem_key = question.stem.strip()
        if stem_key in seen_stems:
            continue
        seen_stems.add(stem_key)
        unique_questions.append(question)
    return unique_questions


def _take_from_bucket(
    selected: list[Question],
    bucket: list[Question],
    used_ids: set[int],
    count: int,
    *,
    reason: str,
) -> None:
    if count < 0:
        raise InsufficientQuestionsError(reason)
    if count == 0:
        return
    available = [question for question in bucket if question.id not in used_ids]
    if len(available) < count:
        raise InsufficientQuestionsError(reason)
    for question in available[:count]:
        selected.append(question)
        used_ids.add(question.id)


def _select_questions_by_type(
    questions: list[Question], rule: FixedPaperRule
) -> list[Question]:
    questions = _deduplicate_questions_by_stem(questions)
    if len(questions) < rule.question_count:
        raise InsufficientQuestionsError("active 题目数量不足，无法生成考试试卷")

    grouped_by_type = _questions_by_type(questions)
    for question_type, count in rule.type_counts.items():
        if len(grouped_by_type[question_type]) < count:
            raise InsufficientQuestionsError(
                f"{question_type} 题目数量不足，无法生成考试试卷"
            )
    seen_combos = {
        (_category_key(question), question.question_type) for question in questions
    }
    for question_type, target_count in rule.type_counts.items():
        required = sum(
            1 for _category, q_type in seen_combos if q_type == question_type
        )
        if target_count < required:
            raise InsufficientQuestionsError(
                f"{question_type} 题型需要覆盖 {required} 个分类组合，"
                f"当前配置 {target_count} 题"
            )

    selected: list[Question] = []
    used_ids: set[int] = set()
    category_totals = _active_category_totals(questions)
    categories = [
        category
        for category, _total in sorted(
            category_totals.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    by_combo: dict[tuple[str, str], list[Question]] = defaultdict(list)
    for question in questions:
        by_combo[(_category_key(question), question.question_type)].append(question)

    # 按目标数量分配每种题型到各 category，确保不超过目标
    for question_type, target_count in rule.type_counts.items():
        per_category = max(1, target_count // len(categories))
        remaining = target_count
        for category in categories:
            if remaining <= 0:
                break
            bucket = by_combo.get((category, question_type), [])
            if bucket:
                count = min(per_category, remaining, len(bucket))
                _take_from_bucket(
                    selected,
                    bucket,
                    used_ids,
                    count,
                    reason=f"{category} 的{question_type}题目数量不足，无法生成考试试卷",
                )
                remaining -= count

    # 覆盖所有 category + question_type 组合
    for (category, question_type), bucket in sorted(by_combo.items()):
        if not bucket:
            continue
        if any(question.id in used_ids for question in bucket):
            continue
        _take_from_bucket(
            selected,
            bucket,
            used_ids,
            1,
            reason=f"{category} 缺少 {question_type} 题目，无法覆盖题型组合",
        )

    for question_type, target_count in rule.type_counts.items():
        current_count = sum(
            1 for question in selected if question.question_type == question_type
        )
        _take_from_bucket(
            selected,
            grouped_by_type[question_type],
            used_ids,
            target_count - current_count,
            reason=f"{question_type} 题目数量不足，无法生成考试试卷",
        )

    if len(selected) != rule.question_count:
        raise InsufficientQuestionsError("抽题数量与规则不一致，无法生成考试试卷")
    return selected


def _rescale_scores(
    questions: list[Question], target_total: Decimal
) -> list[tuple[Question, Decimal]]:
    """固定试卷按题量均分为整数分值，返回 (question, scaled_score) 列表。

    原始 Question.score 不修改；折算结果仅用于快照和 attempt.total_score。
    余数按试卷顺序分配到前若干题，确保总分精确等于 target_total。
    """
    target_points = int(target_total)
    base_points = target_points // len(questions)
    remaining_points = target_points % len(questions)
    return [
        (
            question,
            Decimal(base_points + (1 if index < remaining_points else 0)),
        )
        for index, question in enumerate(questions)
    ]


def _load_questions_by_ids(db: Session, question_ids: list[int]) -> list[Question]:
    questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id.in_(question_ids))
        .all()
    )
    by_id = {question.id: question for question in questions}
    missing_ids = [
        question_id for question_id in question_ids if question_id not in by_id
    ]
    if missing_ids:
        raise InsufficientQuestionsError("固定试卷中的题目已不存在，无法开始考试")
    return [by_id[question_id] for question_id in question_ids]


def _validate_fixed_rule_capacity(db: Session, question_rule: dict) -> None:
    rule = _parse_fixed_paper_rule(question_rule)
    if rule is None:
        active_count = (
            db.query(func.count(Question.id))
            .filter(Question.status == "active")
            .scalar()
        )
        if not active_count:
            raise InsufficientQuestionsError("active 题目数量不足，无法发布考试")
        return
    active_questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.status == "active")
        .order_by(Question.id)
        .all()
    )
    _select_questions_by_type(active_questions, rule)


def _load_active_question_pool(db: Session) -> list[Question]:
    questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.status == "active")
        .order_by(Question.id)
        .all()
    )
    return _deduplicate_questions_by_stem(questions)


def _freeze_question_pool(
    db: Session, exam: Exam, *, require_questions: bool = True
) -> None:
    questions = _load_active_question_pool(db)
    if require_questions and not questions:
        raise InsufficientQuestionsError("active 题目数量不足，无法发布考试")

    db.query(ExamQuestionPool).filter(ExamQuestionPool.exam_id == exam.id).delete()
    for index, question in enumerate(questions):
        db.add(
            ExamQuestionPool(
                exam_id=exam.id,
                question_id=question.id,
                sort_order=index,
            )
        )


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
    if exam.available_until is not None and now > ensure_aware(exam.available_until):
        raise ExamNotAvailableError("考试已结束")


def _exam_availability_status(exam: Exam) -> str:
    now = datetime.now(UTC)
    if exam.available_from is not None and now < ensure_aware(exam.available_from):
        return "not_started"
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


def _build_exam_read(
    db: Session, exam: Exam, updates: dict[str, object] | None = None
) -> ExamRead:
    data = {
        "question_pool_count": _question_pool_count(db, exam.id),
        "availability_status": _exam_availability_status(exam),
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


def _select_exam_questions(
    db: Session, exam: Exam, paper_seed: str | None = None
) -> list[Question]:
    pool_rows = (
        db.query(ExamQuestionPool)
        .filter(ExamQuestionPool.exam_id == exam.id)
        .order_by(ExamQuestionPool.sort_order)
        .all()
    )
    if pool_rows:
        question_ids = [row.question_id for row in pool_rows]
        base_questions = _load_questions_by_ids(db, question_ids)
    else:
        base_questions = _load_active_question_pool(db)

    rule = _parse_fixed_paper_rule(exam.question_rule)
    if rule is None:
        return _deduplicate_questions_by_stem(base_questions)

    rng = random.Random(paper_seed)  # noqa: S311 - deterministic exam paper sampling, not a secret
    rng.shuffle(base_questions)
    selected = _select_questions_by_type(base_questions, rule)
    rng.shuffle(selected)
    return selected


def _load_attempt_with_snapshots(db: Session, attempt_id: int) -> ExamAttempt:
    attempt = (
        db.query(ExamAttempt)
        .options(
            selectinload(ExamAttempt.questions).selectinload(
                ExamAttemptQuestion.answer
            ),
            selectinload(ExamAttempt.exam),
        )
        .filter(ExamAttempt.id == attempt_id)
        .one_or_none()
    )
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    return attempt


def _build_attempt_result(attempt: ExamAttempt) -> AttemptResultRead:
    questions: list[AttemptResultQuestion] = []
    show_answer = bool(
        attempt.exam.show_answer_after_submit if attempt.exam is not None else True
    )
    for question in attempt.questions:
        answer = question.answer
        questions.append(
            AttemptResultQuestion(
                attempt_question_id=question.id,
                stem_snapshot=question.stem_snapshot,
                selected_answer=answer.selected_answer if answer else None,
                correct_answer_snapshot=question.correct_answer_snapshot
                if show_answer
                else None,
                analysis_snapshot=question.analysis_snapshot if show_answer else None,
                is_correct=answer.is_correct if answer else False,
                score_awarded=float(answer.score_awarded) if answer else 0,
                score=float(question.score),
            )
        )

    raw_pass_score = (
        attempt.exam.question_rule.get("pass_score") if attempt.exam else None
    )
    pass_score = float(raw_pass_score) if raw_pass_score is not None else None

    return AttemptResultRead(
        attempt_id=attempt.id,
        score=float(attempt.score),
        total_score=float(attempt.total_score),
        pass_score=pass_score,
        is_passed=float(attempt.score) >= pass_score
        if pass_score is not None
        else None,
        show_answer_after_submit=show_answer,
        correct_count=attempt.correct_count,
        wrong_count=attempt.wrong_count,
        questions=questions,
    )


def _list_exams(db: Session, *, status: str | None = None) -> list[ExamRead]:
    query = db.query(Exam)
    if status is not None:
        query = query.filter(Exam.status == status)
    return [_build_exam_read(db, exam) for exam in query.order_by(Exam.id).all()]


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

    latest = _latest_attempt_for_candidate(db, exam.id, candidate_id)
    has_unused_retake_grant = _has_unused_retake_grant(db, exam.id, candidate_id)
    if latest and latest.status in SUBMITTED_STATUSES and not has_unused_retake_grant:
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


def list_active_exams(db: Session, candidate_id: int | None = None) -> list[ExamRead]:
    if candidate_id is None:
        return _list_exams(db, status="active")

    exams = db.query(Exam).filter(Exam.status == "active").order_by(Exam.id).all()
    candidate_exams = [
        exam_read
        for exam in exams
        if (exam_read := _build_exam_read_for_candidate(db, exam, candidate_id))
        is not None
    ]
    return candidate_exams


def list_admin_exams(db: Session) -> list[ExamRead]:
    return _list_exams(db)


def create_exam(db: Session, payload: ExamCreate) -> ExamRead:
    data = payload.model_dump()
    _validate_exam_config_values(
        duration_minutes=data["duration_minutes"],
        status=data["status"],
        question_rule=data["question_rule"],
        available_from=data.get("available_from"),
        available_until=data.get("available_until"),
    )
    exam = Exam(**data)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _build_exam_read(db, exam)


def update_exam(db: Session, exam_id: int, payload: ExamUpdate) -> ExamRead:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)

    updates = payload.model_dump(exclude_unset=True)
    if exam.status == "active":
        frozen_fields = {"duration_minutes", "question_rule"}
        if frozen_fields.intersection(updates):
            raise ExamFrozenError()

    next_duration_minutes = updates.get("duration_minutes", exam.duration_minutes)
    next_status = updates.get("status", exam.status)
    next_question_rule = updates.get("question_rule", exam.question_rule)
    next_available_from = updates.get("available_from", exam.available_from)
    next_available_until = updates.get("available_until", exam.available_until)
    activating = updates.get("status") == "active" and exam.status != "active"
    _validate_exam_config_values(
        duration_minutes=next_duration_minutes,
        status=next_status,
        question_rule=next_question_rule,
        available_from=next_available_from,
        available_until=next_available_until,
    )

    if activating:
        _ensure_exam_has_scope(db, exam.id)
        _validate_fixed_rule_capacity(db, next_question_rule)

    for field, value in updates.items():
        setattr(exam, field, value)

    if activating:
        _freeze_question_pool(db, exam)

    db.commit()
    db.refresh(exam)
    return _build_exam_read(db, exam)


def create_retake_grant(
    db: Session, exam_id: int, candidate_id: int
) -> ExamRetakeGrant:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    submitted = (
        db.query(ExamAttempt.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.status.in_(SUBMITTED_STATUSES),
        )
        .first()
    )
    if submitted is None:
        raise AttemptNotFoundError(0)
    grant = ExamRetakeGrant(exam_id=exam_id, candidate_id=candidate_id)
    db.add(grant)
    db.commit()
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
    return (
        db.query(ExamRetakeGrant.id)
        .filter(
            ExamRetakeGrant.exam_id == exam_id,
            ExamRetakeGrant.candidate_id == candidate_id,
            ExamRetakeGrant.used_at.is_(None),
        )
        .first()
        is not None
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
    create_retake_grant(db, exam_id, candidate_id)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    return _build_exam_candidate_row(db, exam_id, candidate)


def import_exam_candidates_from_workbook(
    db: Session, exam_id: int, file_obj: object, file_name: str
) -> QuestionImportResult:
    from app.services import import_service

    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "draft":
        raise ExamFrozenError("考试发布后应考名单已冻结")

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
    db.commit()
    return QuestionImportResult(
        batch_id=batch.id,
        success_count=success_count,
        failed_count=len(failures),
        failures=failures,
    )


def start_exam(db: Session, exam_id: int, candidate_id: int) -> ExamStartResponse:
    """开始考试：创建 attempt 并生成题目快照。"""
    exam = db.query(Exam).filter(Exam.id == exam_id).with_for_update().one_or_none()
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "active":
        raise ExamNotActiveError(exam_id)

    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    if candidate.status != "active" or not candidate.should_attend:
        raise CandidateNotEligibleError(candidate_id)
    _ensure_candidate_in_scope(db, exam_id, candidate_id)

    existing_attempts = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
        )
        .order_by(ExamAttempt.attempt_no.desc())
        .all()
    )
    in_progress = next(
        (attempt for attempt in existing_attempts if attempt.status == "in_progress"),
        None,
    )
    if in_progress is not None:
        return _build_exam_start_response_from_attempt(in_progress)

    submitted_attempts = [
        attempt for attempt in existing_attempts if attempt.status in SUBMITTED_STATUSES
    ]
    retake_grant: ExamRetakeGrant | None = None
    if submitted_attempts:
        retake_grant = (
            db.query(ExamRetakeGrant)
            .filter(
                ExamRetakeGrant.exam_id == exam_id,
                ExamRetakeGrant.candidate_id == candidate_id,
                ExamRetakeGrant.used_at.is_(None),
            )
            .order_by(ExamRetakeGrant.created_at)
            .with_for_update()
            .first()
        )
        if retake_grant is None:
            raise AttemptAlreadySubmittedError(submitted_attempts[0].id)

    _assert_exam_available(exam)

    attempt_no = (existing_attempts[0].attempt_no if existing_attempts else 0) + 1
    attempt_kind = "retake" if submitted_attempts else "initial"
    paper_seed = uuid4().hex
    if not _exam_has_question_pool(db, exam_id):
        _freeze_question_pool(db, exam, require_questions=False)
        db.flush()
    questions = _select_exam_questions(db, exam, paper_seed)

    # 持久化 exam 行锁相关状态，释放行锁
    db.add(exam)
    db.flush()

    now = datetime.now(UTC)

    # 固定试卷按 question_rule.total_score 和题量均分；原始题目 score 不修改
    rule = _parse_fixed_paper_rule(exam.question_rule)
    if rule is not None:
        scaled_pairs = _rescale_scores(questions, rule.total_score)
        total_score = rule.total_score
    else:
        scaled_pairs = [(q, q.score) for q in questions]
        total_score = sum(q.score for q in questions)

    # 创建 attempt
    attempt = ExamAttempt(
        exam_id=exam_id,
        candidate_id=candidate_id,
        status="in_progress",
        started_at=now,
        total_score=total_score,
        attempt_no=attempt_no,
        attempt_kind=attempt_kind,
        paper_seed=paper_seed,
    )
    db.add(attempt)
    try:
        db.flush()  # 获取 attempt.id
    except IntegrityError:
        db.rollback()
        existing = _latest_attempt_for_candidate(db, exam_id, candidate_id)
        if existing is not None and existing.status == "in_progress":
            return _build_exam_start_response_from_attempt(existing)
        raise
    if retake_grant is not None:
        retake_grant.used_attempt_id = attempt.id
        retake_grant.used_at = now

    # 生成题目快照（使用本场试卷分值）
    snapshots: list[ExamAttemptQuestion] = []
    for idx, (question, scaled_score) in enumerate(scaled_pairs):
        snapshot = ExamAttemptQuestion(
            attempt_id=attempt.id,
            original_question_id=question.id,
            question_type=question.question_type,
            stem_snapshot=question.stem,
            options_snapshot=_build_options_snapshot(question.options),
            correct_answer_snapshot=_build_correct_answer_snapshot(question.options),
            analysis_snapshot=question.analysis,
            score=scaled_score,
            sort_order=idx,
        )
        db.add(snapshot)
        snapshots.append(snapshot)

    db.flush()  # 确保所有 snapshot 获得 ID

    # 在 commit 前构建响应，避免额外的 DB 查询
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
        ends_at=now + timedelta(minutes=exam.duration_minutes),
    )


def _build_exam_start_response_from_attempt(attempt: ExamAttempt) -> ExamStartResponse:
    questions = [
        AttemptQuestionRead(
            id=snapshot.id,
            question_type=snapshot.question_type,
            stem_snapshot=snapshot.stem_snapshot,
            options_snapshot=snapshot.options_snapshot,
            score=float(snapshot.score),
            sort_order=snapshot.sort_order,
            selected_answer=snapshot.answer.selected_answer
            if snapshot.answer is not None
            else None,
        )
        for snapshot in attempt.questions
    ]
    return ExamStartResponse(
        attempt_id=attempt.id,
        exam=ExamRead.model_validate(attempt.exam),
        questions=questions,
        started_at=attempt.started_at,
        ends_at=ensure_aware(attempt.started_at)
        + timedelta(minutes=attempt.exam.duration_minutes),
    )


def get_attempt(db: Session, attempt_id: int) -> AttemptRead:
    """获取考试记录及其题目快照。"""
    attempt = _load_attempt_with_snapshots(db, attempt_id)

    question_reads = [
        AttemptQuestionRead(
            id=q.id,
            question_type=q.question_type,
            stem_snapshot=q.stem_snapshot,
            options_snapshot=q.options_snapshot,
            score=float(q.score),
            sort_order=q.sort_order,
            selected_answer=q.answer.selected_answer if q.answer else None,
        )
        for q in attempt.questions
    ]

    return AttemptRead(
        id=attempt.id,
        exam_id=attempt.exam_id,
        candidate_id=attempt.candidate_id,
        status=attempt.status,
        started_at=ensure_aware(attempt.started_at),
        duration_minutes=attempt.exam.duration_minutes,
        ends_at=ensure_aware(attempt.started_at)
        + timedelta(minutes=attempt.exam.duration_minutes),
        server_now=datetime.now(UTC),
        submitted_at=attempt.submitted_at,
        score=float(attempt.score),
        total_score=float(attempt.total_score),
        correct_count=attempt.correct_count,
        wrong_count=attempt.wrong_count,
        questions=question_reads,
    )


def save_answers(
    db: Session, attempt_id: int, payload: AnswerSaveRequest
) -> AnswerSaveResponse:
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
    if attempt.exam and attempt.exam.status != "active":
        raise ExamNotActiveError(attempt.exam_id)
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

    db.commit()
    return AnswerSaveResponse(saved_count=len(payload.answers), saved_at=now)


def submit_attempt(db: Session, attempt_id: int, submit_type: str) -> AttemptResultRead:
    # 轻量快速检查：避免不必要的 FOR UPDATE
    quick = db.get(ExamAttempt, attempt_id)
    if quick is None:
        raise AttemptNotFoundError(attempt_id)
    if quick.status != "in_progress":
        return _build_attempt_result(_load_attempt_with_snapshots(db, attempt_id))

    # 加行锁后重新加载完整 attempt + snapshots + exam
    attempt = (
        db.query(ExamAttempt)
        .options(
            selectinload(ExamAttempt.questions).selectinload(
                ExamAttemptQuestion.answer
            ),
            selectinload(ExamAttempt.exam),
        )
        .filter(ExamAttempt.id == attempt_id)
        .with_for_update()
        .one_or_none()
    )
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    if attempt.status != "in_progress":
        return _build_attempt_result(attempt)

    submitted_at = datetime.now(UTC)
    score = Decimal("0")
    correct_count = 0

    for question in attempt.questions:
        question_score = float(question.score)
        answer = question.answer
        selected_answer = answer.selected_answer if answer else None
        scoring = score_answer(
            question.question_type,
            question.correct_answer_snapshot,
            selected_answer,
            question_score,
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

    attempt.status = "auto_submitted" if submit_type == "auto" else "submitted"
    attempt.submitted_at = submitted_at
    attempt.submit_type = submit_type
    attempt.score = score
    attempt.correct_count = correct_count
    attempt.wrong_count = len(attempt.questions) - correct_count
    attempt.duration_seconds = int(
        (submitted_at - ensure_aware(attempt.started_at)).total_seconds()
    )

    result = _build_attempt_result(attempt)
    db.commit()
    return result


def get_attempt_result(db: Session, attempt_id: int) -> AttemptResultRead:
    return _build_attempt_result(_load_attempt_with_snapshots(db, attempt_id))
