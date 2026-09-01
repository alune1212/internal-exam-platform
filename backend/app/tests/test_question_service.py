import pytest
from sqlalchemy import select
from sqlalchemy.orm import Query, Session

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


def test_list_active_questions_paginates_stably_with_options(db: Session) -> None:
    questions = [
        question_service.create_question(db, _single_payload(f"题目 {index}"))
        for index in range(3)
    ]
    question_service.create_question(
        db,
        _single_payload("停用题目").model_copy(update={"status": "inactive"}),
    )

    page = question_service.list_active_questions(db, limit=2, offset=1)

    assert [question.id for question in page] == [questions[1].id, questions[2].id]
    assert all(
        [option.label for option in question.options] == ["A", "B"] for question in page
    )


def test_list_active_questions_rechecks_status_for_loaded_page(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = question_service.create_question(db, _single_payload("第一题"))
    second = question_service.create_question(db, _single_payload("第二题"))
    original_all = Query.all
    calls = 0

    def all_with_deactivation(query: Query) -> list[object]:
        nonlocal calls
        result = original_all(query)
        calls += 1
        if calls == 1:
            db.query(Question).filter(Question.id == first.id).update(
                {Question.status: "inactive"}, synchronize_session=False
            )
            db.flush()
        return result

    monkeypatch.setattr(Query, "all", all_with_deactivation)

    page = question_service.list_active_questions(db, limit=2)

    assert [question.id for question in page] == [second.id]
