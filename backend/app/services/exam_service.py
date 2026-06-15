from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.core.time import ensure_aware
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
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
    ExamCreate,
    ExamRead,
    ExamStartResponse,
    ExamUpdate,
    RankingRow,
)
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
    def __init__(self, exam_id: int) -> None:
        self.exam_id = exam_id
        super().__init__(f"考试 #{exam_id} 未处于 active 状态")


class CandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        self.candidate_id = candidate_id
        super().__init__(f"考生 #{candidate_id} 不存在")


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
    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考试记录 #{attempt_id} 已提交")


class InsufficientQuestionsError(DomainError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class FixedPaperRule:
    question_count: int
    total_score: Decimal
    type_counts: dict[str, int]


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


def _parse_fixed_paper_rule(question_rule: dict | None) -> FixedPaperRule | None:
    if not question_rule or "question_count" not in question_rule:
        return None

    question_count = int(question_rule.get("question_count", 60))
    total_score = Decimal(str(question_rule.get("total_score", 100)))
    raw_type_counts = question_rule.get("type_counts") or {
        "single": 15,
        "multiple": 40,
        "judge": 5,
    }
    type_counts = {
        question_type: int(raw_type_counts.get(question_type, 0))
        for question_type in ("single", "multiple", "judge")
    }
    if sum(type_counts.values()) != question_count:
        raise InsufficientQuestionsError("抽题规则中的题型数量合计必须等于总题数")
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


def _take_from_bucket(
    selected: list[Question],
    bucket: list[Question],
    used_ids: set[int],
    count: int,
    *,
    reason: str,
) -> None:
    available = [question for question in bucket if question.id not in used_ids]
    if len(available) < count:
        raise InsufficientQuestionsError(reason)
    for question in available[:count]:
        selected.append(question)
        used_ids.add(question.id)


def _select_questions_by_type(
    questions: list[Question], rule: FixedPaperRule
) -> list[Question]:
    if len(questions) < rule.question_count:
        raise InsufficientQuestionsError("active 题目数量不足，无法生成考试试卷")

    grouped_by_type = _questions_by_type(questions)
    for question_type, count in rule.type_counts.items():
        if len(grouped_by_type[question_type]) < count:
            raise InsufficientQuestionsError(
                f"{question_type} 题目数量不足，无法生成考试试卷"
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

    for category in categories:
        multiple_bucket = by_combo.get((category, "multiple"), [])
        if multiple_bucket:
            _take_from_bucket(
                selected,
                multiple_bucket,
                used_ids,
                min(5, len(multiple_bucket)),
                reason=f"{category} 的多选题数量不足，无法生成考试试卷",
            )

    for category in categories:
        judge_bucket = by_combo.get((category, "judge"), [])
        if judge_bucket:
            _take_from_bucket(
                selected,
                judge_bucket,
                used_ids,
                1,
                reason=f"{category} 的判断题数量不足，无法生成考试试卷",
            )

    for category in categories:
        single_bucket = by_combo.get((category, "single"), [])
        if single_bucket:
            _take_from_bucket(
                selected,
                single_bucket,
                used_ids,
                1,
                reason=f"{category} 的单选题数量不足，无法生成考试试卷",
            )

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
    if sum(question.score for question in selected) != rule.total_score:
        raise InsufficientQuestionsError("抽题总分与规则不一致，无法生成考试试卷")
    return selected


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


def _select_exam_questions(db: Session, exam: Exam) -> list[Question]:
    rule = _parse_fixed_paper_rule(exam.question_rule)
    if rule is None:
        return (
            db.query(Question)
            .options(selectinload(Question.options))
            .filter(Question.status == "active")
            .order_by(Question.id)
            .all()
        )

    fixed_question_ids = exam.question_rule.get("fixed_question_ids")
    if fixed_question_ids:
        if len(fixed_question_ids) != rule.question_count:
            raise InsufficientQuestionsError("固定试卷题目数量与抽题规则不一致")
        return _load_questions_by_ids(
            db, [int(question_id) for question_id in fixed_question_ids]
        )

    active_questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.status == "active")
        .order_by(Question.id)
        .all()
    )
    selected = _select_questions_by_type(active_questions, rule)
    exam.question_rule = {
        **exam.question_rule,
        "mode": exam.question_rule.get("mode", "fixed_paper"),
        "fixed_question_ids": [question.id for question in selected],
    }
    return selected


def _load_attempt_with_snapshots(db: Session, attempt_id: int) -> ExamAttempt:
    attempt = (
        db.query(ExamAttempt)
        .options(
            selectinload(ExamAttempt.questions).selectinload(ExamAttemptQuestion.answer)
        )
        .filter(ExamAttempt.id == attempt_id)
        .one_or_none()
    )
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    return attempt


def _build_attempt_result(attempt: ExamAttempt) -> AttemptResultRead:
    questions: list[AttemptResultQuestion] = []
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
        correct_count=attempt.correct_count,
        wrong_count=attempt.wrong_count,
        questions=questions,
    )


def _list_exams(db: Session, *, status: str | None = None) -> list[ExamRead]:
    query = db.query(Exam)
    if status is not None:
        query = query.filter(Exam.status == status)
    return [ExamRead.model_validate(exam) for exam in query.order_by(Exam.id).all()]


def list_active_exams(db: Session) -> list[ExamRead]:
    return _list_exams(db, status="active")


def list_admin_exams(db: Session) -> list[ExamRead]:
    return _list_exams(db)


def create_exam(db: Session, payload: ExamCreate) -> ExamRead:
    exam = Exam(**payload.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return ExamRead.model_validate(exam)


def update_exam(db: Session, exam_id: int, payload: ExamUpdate) -> ExamRead:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exam, field, value)

    db.commit()
    return ExamRead.model_validate(exam)


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

    # 检查是否已有进行中的 attempt
    existing = db.execute(
        select(ExamAttempt).where(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.status == "in_progress",
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AttemptAlreadyExistsError(existing.id)

    questions = _select_exam_questions(db, exam)

    # 持久化 exam.question_rule（含 fixed_question_ids），释放行锁
    db.add(exam)
    db.flush()

    now = datetime.now(UTC)
    total_score = sum(q.score for q in questions)

    # 创建 attempt
    attempt = ExamAttempt(
        exam_id=exam_id,
        candidate_id=candidate_id,
        status="in_progress",
        started_at=now,
        total_score=total_score,
    )
    db.add(attempt)
    db.flush()  # 获取 attempt.id

    # 生成题目快照
    snapshots: list[ExamAttemptQuestion] = []
    for idx, question in enumerate(questions):
        snapshot = ExamAttemptQuestion(
            attempt_id=attempt.id,
            original_question_id=question.id,
            question_type=question.question_type,
            stem_snapshot=question.stem,
            options_snapshot=_build_options_snapshot(question.options),
            correct_answer_snapshot=_build_correct_answer_snapshot(question.options),
            analysis_snapshot=question.analysis,
            score=question.score,
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
        started_at=attempt.started_at,
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
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
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


def get_ranking(db: Session, exam_id: int) -> list[RankingRow]:
    """获取考试排名：按分数降序、提交时间升序。"""
    rows = (
        db.query(ExamAttempt, Candidate.name, Candidate.department)
        .join(Candidate, ExamAttempt.candidate_id == Candidate.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(SUBMITTED_STATUSES),
        )
        .order_by(ExamAttempt.score.desc(), ExamAttempt.submitted_at.asc())
        .all()
    )

    return [
        RankingRow(
            rank=idx + 1,
            candidate_name=name,
            department=department,
            score=float(attempt.score),
            total_score=float(attempt.total_score),
            submitted_at=attempt.submitted_at,
        )
        for idx, (attempt, name, department) in enumerate(rows)
    ]
