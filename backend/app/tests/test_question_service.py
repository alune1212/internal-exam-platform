import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models import Question, QuestionOption
from app.schemas.question import QuestionCreate, QuestionOptionBase, QuestionUpdate
from app.services import question_service


def _single_payload(stem: str = "哪项是正确做法？") -> QuestionCreate:
    return QuestionCreate(
        question_type="single",
        stem=stem,
        score=2,
        status="active",
        options=[
            QuestionOptionBase(
                label="A", content="保管好账号", is_correct=True, sort_order=1
            ),
            QuestionOptionBase(
                label="B", content="共享密码", is_correct=False, sort_order=2
            ),
        ],
    )


def test_create_question_persists_question_and_options(db: Session) -> None:
    created = question_service.create_question(db, _single_payload())

    stored = db.get(Question, created.id)
    options = db.scalars(
        select(QuestionOption)
        .where(QuestionOption.question_id == created.id)
        .order_by(QuestionOption.sort_order)
    ).all()

    assert stored is not None
    assert stored.stem == "哪项是正确做法？"
    assert stored.score == 2
    assert [option.label for option in options] == ["A", "B"]
    assert [option.label for option in options if option.is_correct] == ["A"]


def test_update_question_replaces_fields_and_options(db: Session) -> None:
    created = question_service.create_question(db, _single_payload())

    updated = question_service.update_question(
        db,
        created.id,
        QuestionUpdate(
            stem="更新后的题干",
            question_type="multiple",
            options=[
                QuestionOptionBase(
                    label="A", content="要求一", is_correct=True, sort_order=1
                ),
                QuestionOptionBase(
                    label="B", content="要求二", is_correct=True, sort_order=2
                ),
                QuestionOptionBase(
                    label="C", content="错误项", is_correct=False, sort_order=3
                ),
            ],
        ),
    )

    assert updated.stem == "更新后的题干"
    assert updated.question_type == "multiple"
    assert [option.label for option in updated.options] == ["A", "B", "C"]
    assert [option.label for option in updated.options if option.is_correct] == [
        "A",
        "B",
    ]


def test_create_question_rejects_invalid_answer_count(db: Session) -> None:
    payload = _single_payload()
    payload.options[1].is_correct = True

    with pytest.raises(DomainError, match="单选题只能有一个正确答案"):
        question_service.create_question(db, payload)


def test_delete_question_removes_question_and_options(db: Session) -> None:
    created = question_service.create_question(db, _single_payload())

    question_service.delete_question(db, created.id)

    assert db.get(Question, created.id) is None
    assert (
        db.scalars(
            select(QuestionOption).where(QuestionOption.question_id == created.id)
        ).all()
        == []
    )
