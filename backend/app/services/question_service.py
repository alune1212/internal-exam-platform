from sqlalchemy.orm import Session, selectinload

from app.models import Question
from app.schemas.question import (
    QuestionCreate,
    QuestionOptionRead,
    QuestionRead,
    QuestionUpdate,
)


def list_questions(db: Session, *, status: str | None = None) -> list[QuestionRead]:
    query = db.query(Question).options(selectinload(Question.options))
    if status is not None:
        query = query.filter(Question.status == status)
    questions = query.order_by(Question.id).all()
    return [QuestionRead.model_validate(q) for q in questions]


def list_active_questions(db: Session) -> list[QuestionRead]:
    return list_questions(db, status="active")


def create_question(db: Session, payload: QuestionCreate) -> QuestionRead:
    return QuestionRead(
        id=0,
        **payload.model_dump(exclude={"options"}),
        options=[
            QuestionOptionRead(id=index, **option.model_dump())
            for index, option in enumerate(payload.options, start=1)
        ],
    )


def update_question(
    db: Session, question_id: int, payload: QuestionUpdate
) -> QuestionRead:
    data = payload.model_dump(exclude_unset=True)
    return QuestionRead(
        id=question_id,
        question_type=data.get("question_type", "single"),
        stem=data.get("stem", "待完善题干"),
        analysis=data.get("analysis"),
        category_1=data.get("category_1"),
        category_2=data.get("category_2"),
        difficulty=data.get("difficulty"),
        score=data.get("score", 1),
        status=data.get("status", "active"),
        source=data.get("source"),
        source_no=data.get("source_no"),
        remark=data.get("remark"),
        options=[],
    )


def delete_question(db: Session, question_id: int) -> None:
    return None
