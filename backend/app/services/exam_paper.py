import random
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, ExamQuestionPool, Question
from app.services.exam_errors import ExamConfigError, InsufficientQuestionsError


@dataclass(frozen=True)
class FixedPaperRule:
    question_count: int
    total_score: Decimal
    type_counts: dict[str, int]
    pass_score: Decimal | None


VALID_FIXED_TYPES = {"single", "multiple", "judge"}


def _require_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        separator = "" if field_name == "考试时长" else " "
        raise ExamConfigError(f"{field_name}{separator}必须为正整数")
    return value


def _require_non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
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
        raise ExamConfigError("question_count 必须为正整数")

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


def _questions_by_type(questions: list[Question]) -> dict[str, list[Question]]:
    grouped: dict[str, list[Question]] = defaultdict(list)
    for question in questions:
        grouped[question.question_type].append(question)
    return grouped


def _parse_fixed_paper_rule(question_rule: dict | None) -> FixedPaperRule | None:
    """Convert a stored question_rule into a typed FixedPaperRule.

    Re-validates the shape on read so a persisted exam whose rule dict was
    inserted outside the update pipeline (legacy fixtures, ops imports, etc.)
    still raises a domain error rather than KeyError at attempt-start time.
    """
    if not question_rule:
        return None

    _validate_question_rule(question_rule)
    question_count = question_rule["question_count"]
    total_score = Decimal(question_rule["total_score"])
    raw_type_counts = question_rule["type_counts"]
    type_counts = {
        question_type: int(raw_type_counts.get(question_type, 0))
        for question_type in ("single", "multiple", "judge")
    }
    pass_score = _optional_decimal(question_rule.get("pass_score"), "pass_score")
    return FixedPaperRule(
        question_count=question_count,
        total_score=total_score,
        type_counts=type_counts,
        pass_score=pass_score,
    )


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
        raise InsufficientQuestionsError("启用题目数量不足，无法生成考试试卷")

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

    for (category, question_type), bucket in sorted(by_combo.items()):
        if not bucket or any(question.id in used_ids for question in bucket):
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
    target_points = int(target_total)
    base_points = target_points // len(questions)
    remaining_points = target_points % len(questions)
    return [
        (question, Decimal(base_points + (1 if index < remaining_points else 0)))
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
            raise InsufficientQuestionsError("启用题目数量不足，无法发布考试")
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


def _select_exam_questions(
    db: Session, exam: Exam, paper_seed: str | None = None
) -> list[Question]:
    pool_rows = (
        db.query(ExamQuestionPool)
        .filter(ExamQuestionPool.exam_id == exam.id)
        .order_by(ExamQuestionPool.sort_order)
        .all()
    )
    base_questions = (
        _load_questions_by_ids(db, [row.question_id for row in pool_rows])
        if pool_rows
        else _load_active_question_pool(db)
    )
    rule = _parse_fixed_paper_rule(exam.question_rule)
    if rule is None:
        return _deduplicate_questions_by_stem(base_questions)

    rng = random.Random(paper_seed)  # noqa: S311 - deterministic sampling only
    rng.shuffle(base_questions)
    selected = _select_questions_by_type(base_questions, rule)
    rng.shuffle(selected)
    return selected
