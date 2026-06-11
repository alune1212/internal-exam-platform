from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Candidate, Exam, ExamAttempt, ExamAttemptAnswer, ExamAttemptQuestion, Question
from app.schemas.attempt import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AttemptQuestionRead,
    AttemptRead,
    AttemptResultRead,
)
from app.schemas.exam import ExamCreate, ExamRead, ExamStartResponse, ExamUpdate, RankingRow
from app.services.scoring_service import score_answer


class DomainError(Exception):
    """业务领域异常基类，status_code 用于 API 层统一映射。"""

    status_code: int = 400


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


def _load_attempt_with_snapshots(db: Session, attempt_id: int) -> ExamAttempt:
    attempt = (
        db.query(ExamAttempt)
        .options(selectinload(ExamAttempt.questions).selectinload(ExamAttemptQuestion.answer))
        .filter(ExamAttempt.id == attempt_id)
        .one_or_none()
    )
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    return attempt


def _build_attempt_result(attempt: ExamAttempt) -> AttemptResultRead:
    questions = []
    for question in attempt.questions:
        answer = question.answer
        questions.append(
            {
                "attempt_question_id": question.id,
                "stem_snapshot": question.stem_snapshot,
                "selected_answer": answer.selected_answer if answer else None,
                "correct_answer_snapshot": question.correct_answer_snapshot,
                "analysis_snapshot": question.analysis_snapshot,
                "is_correct": answer.is_correct if answer else False,
                "score_awarded": float(answer.score_awarded) if answer else 0,
                "score": float(question.score),
            }
        )

    return AttemptResultRead(
        attempt_id=attempt.id,
        score=float(attempt.score),
        total_score=float(attempt.total_score),
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
    exam = db.get(Exam, exam_id)
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

    # 加载所有 active 题目及其选项
    questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.status == "active")
        .order_by(Question.id)
        .all()
    )

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


def save_answers(db: Session, attempt_id: int, payload: AnswerSaveRequest) -> AnswerSaveResponse:
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
    submitted_at = datetime.now(UTC)
    total_score = 0.0
    score = 0.0
    correct_count = 0

    for question in attempt.questions:
        question_score = float(question.score)
        total_score += question_score
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
        answer.score_awarded = scoring.score_awarded
        if scoring.is_correct:
            correct_count += 1
            score += scoring.score_awarded

    attempt.status = "auto_submitted" if submit_type == "auto" else "submitted"
    attempt.submitted_at = submitted_at
    attempt.submit_type = submit_type
    attempt.score = score
    attempt.total_score = total_score
    attempt.correct_count = correct_count
    attempt.wrong_count = len(attempt.questions) - correct_count
    attempt.duration_seconds = int(
        (submitted_at.replace(tzinfo=None) - attempt.started_at.replace(tzinfo=None)).total_seconds()
    )

    db.commit()
    db.refresh(attempt)
    return _build_attempt_result(attempt)


def get_attempt_result(db: Session, attempt_id: int) -> AttemptResultRead:
    return _build_attempt_result(_load_attempt_with_snapshots(db, attempt_id))


def get_ranking(db: Session, exam_id: int) -> list[RankingRow]:
    return []
