from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.models import Exam, ExamQuestionPool, Question, QuestionOption
from app.schemas.question import QuestionCreate, QuestionRead, QuestionUpdate
from app.services.operational_lock_service import assert_admin_mutation_allowed

VALID_QUESTION_TYPES = {"single", "multiple", "judge"}
VALID_STATUSES = {"active", "inactive"}


class QuestionNotFoundError(DomainError):
    status_code = 404

    def __init__(self, question_id: int) -> None:
        super().__init__(f"题目 #{question_id} 不存在")


class QuestionValidationError(DomainError):
    status_code = 422


class QuestionFrozenError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("题目已被 active 已发布考试题池引用，不能修改或删除。")


def list_questions(db: Session, *, status: str | None = None) -> list[QuestionRead]:
    query = db.query(Question).options(selectinload(Question.options))
    if status is not None:
        query = query.filter(Question.status == status)
    questions = query.order_by(Question.id).all()
    return [_read_loaded_question(question) for question in questions]


def list_active_questions(db: Session) -> list[QuestionRead]:
    return list_questions(db, status="active")


def create_question(db: Session, payload: QuestionCreate) -> QuestionRead:
    assert_admin_mutation_allowed(db)
    normalized = _normalize_payload(payload)
    _validate_question_payload(normalized)

    question = Question(**normalized.model_dump(exclude={"options"}))
    question.score = Decimal(str(normalized.score))
    question.options = [
        QuestionOption(**option.model_dump())
        for option in _sorted_options(normalized.options)
    ]
    db.add(question)
    db.commit()
    return _read_question(db, question.id)


def update_question(
    db: Session, question_id: int, payload: QuestionUpdate
) -> QuestionRead:
    assert_admin_mutation_allowed(db)
    question = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id == question_id)
        .one_or_none()
    )
    if question is None:
        raise QuestionNotFoundError(question_id)
    _ensure_question_not_in_active_exam_pool(db, question_id)

    data = payload.model_dump(exclude_unset=True)
    merged = QuestionCreate(
        question_type=data.get("question_type", question.question_type),
        stem=data.get("stem", question.stem),
        analysis=data.get("analysis", question.analysis),
        category_1=data.get("category_1", question.category_1),
        category_2=data.get("category_2", question.category_2),
        difficulty=data.get("difficulty", question.difficulty),
        score=data.get("score", float(question.score)),
        status=data.get("status", question.status),
        source=data.get("source", question.source),
        source_no=data.get("source_no", question.source_no),
        remark=data.get("remark", question.remark),
        options=data.get(
            "options",
            [
                {
                    "label": option.label,
                    "content": option.content,
                    "is_correct": option.is_correct,
                    "sort_order": option.sort_order,
                }
                for option in question.options
            ],
        ),
    )
    normalized = _normalize_payload(merged)
    _validate_question_payload(normalized)

    for field, value in normalized.model_dump(exclude={"options"}).items():
        setattr(question, field, value)
    question.score = Decimal(str(normalized.score))
    if "options" in data:
        question.options.clear()
        db.flush()
        question.options = [
            QuestionOption(**option.model_dump())
            for option in _sorted_options(normalized.options)
        ]
    db.commit()
    return _read_question(db, question_id)


def delete_question(db: Session, question_id: int) -> None:
    assert_admin_mutation_allowed(db)
    question = db.get(Question, question_id)
    if question is None:
        raise QuestionNotFoundError(question_id)
    _ensure_question_not_in_active_exam_pool(db, question_id)
    db.delete(question)
    db.commit()


def _ensure_question_not_in_active_exam_pool(db: Session, question_id: int) -> None:
    referenced = (
        db.query(ExamQuestionPool.id)
        .join(Exam, Exam.id == ExamQuestionPool.exam_id)
        .filter(
            ExamQuestionPool.question_id == question_id,
            Exam.status == "active",
        )
        .first()
    )
    if referenced is not None:
        raise QuestionFrozenError()


def _read_question(db: Session, question_id: int) -> QuestionRead:
    question = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id == question_id)
        .one()
    )
    return _read_loaded_question(question)


def _read_loaded_question(question: Question) -> QuestionRead:
    question.options.sort(key=lambda option: option.sort_order)
    return QuestionRead.model_validate(question)


def _sorted_options(options: list) -> list:
    return sorted(options, key=lambda option: option.sort_order)


def _normalize_payload(payload: QuestionCreate) -> QuestionCreate:
    data = payload.model_dump()
    data["question_type"] = data["question_type"].strip().lower()
    data["status"] = data["status"].strip().lower()
    data["stem"] = data["stem"].strip()
    for option in data["options"]:
        option["label"] = option["label"].strip().upper()
        option["content"] = option["content"].strip()
    return QuestionCreate(**data)


def _validate_question_payload(payload: QuestionCreate) -> None:
    if payload.question_type not in VALID_QUESTION_TYPES:
        raise QuestionValidationError(
            "题型只能填写单选（single）、多选（multiple）或判断（judge）"
        )
    if not payload.stem:
        raise QuestionValidationError("题干不能为空")
    if payload.score <= 0:
        raise QuestionValidationError("分值必须大于 0")
    if payload.status not in VALID_STATUSES:
        raise QuestionValidationError("状态只能填写启用（active）或停用（inactive）")

    labels = [option.label for option in payload.options]
    if len(labels) != len(set(labels)):
        raise QuestionValidationError("选项标签不能重复")
    if any(not option.label or not option.content for option in payload.options):
        raise QuestionValidationError("选项标签和内容不能为空")

    correct_count = sum(1 for option in payload.options if option.is_correct)
    if payload.question_type in {"single", "judge"} and correct_count != 1:
        raise QuestionValidationError("单选题只能有一个正确答案")
    if payload.question_type == "multiple" and correct_count < 1:
        raise QuestionValidationError("多选题至少一个正确答案")
    if payload.question_type in {"single", "multiple"} and len(payload.options) < 2:
        raise QuestionValidationError("单选题和多选题至少需要两个选项")
    if payload.question_type == "judge" and len(payload.options) != 2:
        raise QuestionValidationError("判断题必须包含两个选项")
