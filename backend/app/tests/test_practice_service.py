from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Request
from sqlalchemy.orm import Query

from app.core.rate_limit import PublicTokenRateLimitError
from app.models import PracticeAnswer, PracticeAnswerAggregate
from app.schemas.practice import PracticeAnswerSubmitRequest
from app.services import practice_service
from app.tests.conftest import (
    create_candidate,
    create_question_with_options,
)


def test_submit_updates_immutable_detail_and_all_time_aggregate(db) -> None:
    candidate = create_candidate(db)
    question = create_question_with_options(db)

    first = practice_service.submit_practice_answer(
        db,
        candidate.id,
        PracticeAnswerSubmitRequest(question_id=question.id, selected_answer="B"),
    )
    second = practice_service.submit_practice_answer(
        db,
        candidate.id,
        PracticeAnswerSubmitRequest(question_id=question.id, selected_answer="A"),
    )

    details = (
        db.query(PracticeAnswer)
        .filter(PracticeAnswer.candidate_id == candidate.id)
        .order_by(PracticeAnswer.id)
        .all()
    )
    aggregate = (
        db.query(PracticeAnswerAggregate)
        .filter(
            PracticeAnswerAggregate.candidate_id == candidate.id,
            PracticeAnswerAggregate.question_id == question.id,
        )
        .one()
    )
    assert [detail.id for detail in details] == [
        first.practice_answer_id,
        second.practice_answer_id,
    ]
    assert aggregate.total_attempts == 2
    assert aggregate.incorrect_count == 1
    assert aggregate.latest_selected_answer == "A"
    assert aggregate.latest_is_correct is True
    assert aggregate.latest_practice_answer_id == second.practice_answer_id

    wrong = practice_service.list_wrong_questions(db, candidate.id, history_limit=1)
    assert len(wrong) == 1
    assert wrong[0].total_attempts == 2
    assert wrong[0].incorrect_count == 1
    assert wrong[0].mastered is True
    assert wrong[0].history_total == 2
    assert wrong[0].history_truncated is True
    assert [item.practice_answer_id for item in wrong[0].history] == [
        second.practice_answer_id
    ]


def test_wrong_questions_paginate_by_latest_activity_and_keep_account_scope(db) -> None:
    candidate = create_candidate(db)
    other_candidate = create_candidate(db, email="other@example.com")
    questions = [
        create_question_with_options(db, stem=f"题目{i}", category_1="分类")
        for i in range(3)
    ]
    for question in questions:
        practice_service.submit_practice_answer(
            db,
            candidate.id,
            PracticeAnswerSubmitRequest(question_id=question.id, selected_answer="B"),
        )
    other_question = create_question_with_options(db, stem="他人题目")
    practice_service.submit_practice_answer(
        db,
        other_candidate.id,
        PracticeAnswerSubmitRequest(question_id=other_question.id, selected_answer="B"),
    )

    page = practice_service.list_wrong_questions(
        db,
        candidate.id,
        category_1="分类",
        limit=1,
        offset=1,
    )
    assert len(page) == 1
    assert page[0].question_id == questions[1].id
    assert page[0].history_total == 1
    assert page[0].history_truncated is False


def test_wrong_questions_use_all_time_aggregate_after_detail_retention(db) -> None:
    candidate = create_candidate(db)
    question = create_question_with_options(db)
    practiced_at = datetime.now(UTC)
    detail = PracticeAnswer(
        candidate_id=candidate.id,
        question_id=question.id,
        selected_answer="B",
        is_correct=False,
        practiced_at=practiced_at,
    )
    db.add(detail)
    db.flush()
    db.add(
        PracticeAnswerAggregate(
            candidate_id=candidate.id,
            question_id=question.id,
            total_attempts=5,
            incorrect_count=4,
            latest_selected_answer="B",
            latest_is_correct=False,
            latest_practiced_at=practiced_at,
            latest_practice_answer_id=detail.id,
        )
    )
    db.commit()

    wrong = practice_service.list_wrong_questions(db, candidate.id)

    assert len(wrong) == 1
    assert wrong[0].total_attempts == 5
    assert wrong[0].incorrect_count == 4
    assert wrong[0].history_total == 5
    assert wrong[0].history_truncated is True
    assert len(wrong[0].history) == 1


def test_wrong_questions_rejects_oversized_offset_before_candidate_lookup(
    db, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_looked_up(*_args, **_kwargs):
        raise AssertionError("oversized offsets must fail before candidate lookup")

    monkeypatch.setattr(
        practice_service, "get_active_practice_candidate", fail_if_looked_up
    )

    with pytest.raises(practice_service.PracticeAnswerValidationError, match=r"2\^31"):
        practice_service.list_wrong_questions(db, 1, offset=2**31)


def test_submit_rebuilds_missing_aggregate_without_loading_full_history(
    db, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = create_candidate(db)
    question = create_question_with_options(db)
    practiced_at = datetime.now(UTC)
    db.add_all(
        [
            PracticeAnswer(
                candidate_id=candidate.id,
                question_id=question.id,
                selected_answer=selected_answer,
                is_correct=is_correct,
                practiced_at=practiced_at - timedelta(seconds=3 - index),
            )
            for index, (selected_answer, is_correct) in enumerate(
                [("B", False), ("A", True), ("B", False)]
            )
        ]
    )
    db.commit()

    def fail_on_full_history_load(_query: Query) -> list:
        raise AssertionError("aggregate rebuild must not load all practice details")

    monkeypatch.setattr(Query, "all", fail_on_full_history_load)

    result = practice_service.submit_practice_answer(
        db,
        candidate.id,
        PracticeAnswerSubmitRequest(question_id=question.id, selected_answer="B"),
    )

    aggregate = (
        db.query(PracticeAnswerAggregate)
        .filter(
            PracticeAnswerAggregate.candidate_id == candidate.id,
            PracticeAnswerAggregate.question_id == question.id,
        )
        .one()
    )
    assert result.is_correct is False
    assert aggregate.total_attempts == 4
    assert aggregate.incorrect_count == 3
    assert aggregate.latest_practice_answer_id == result.practice_answer_id


def test_submit_rejects_answer_longer_than_32_without_writing(db) -> None:
    candidate = create_candidate(db)
    question = create_question_with_options(db)
    payload = PracticeAnswerSubmitRequest.model_construct(
        question_id=question.id, selected_answer="x" * 33
    )

    with pytest.raises(practice_service.PracticeAnswerValidationError, match="32"):
        practice_service.submit_practice_answer(db, candidate.id, payload)

    assert db.query(PracticeAnswer).count() == 0
    assert db.query(PracticeAnswerAggregate).count() == 0


def test_submit_checks_rate_limit_before_write_locks(db, monkeypatch) -> None:
    def fail_if_locked(_db) -> None:
        raise AssertionError("rate limiting must precede the write locks")

    def reject_request(*_args, **_kwargs) -> None:
        raise PublicTokenRateLimitError()

    monkeypatch.setattr(practice_service, "assert_backup_write_allowed", fail_if_locked)
    monkeypatch.setattr(
        practice_service, "check_public_token_rate_limit", reject_request
    )

    with pytest.raises(PublicTokenRateLimitError):
        practice_service.submit_practice_answer(
            db,
            1,
            PracticeAnswerSubmitRequest(question_id=1, selected_answer="A"),
            request=Request({"type": "http", "headers": []}),
        )


def test_submit_rejects_a_hot_history_at_5000_rows(db) -> None:
    candidate = create_candidate(db)
    question = create_question_with_options(db)
    now = datetime.now(UTC)
    db.add_all(
        [
            PracticeAnswer(
                candidate_id=candidate.id,
                question_id=question.id,
                selected_answer="B",
                is_correct=False,
                practiced_at=now + timedelta(seconds=index),
            )
            for index in range(5000)
        ]
    )
    db.commit()

    with pytest.raises(practice_service.PracticeHistoryCapacityError):
        practice_service.submit_practice_answer(
            db,
            candidate.id,
            PracticeAnswerSubmitRequest(question_id=question.id, selected_answer="B"),
        )

    assert db.query(PracticeAnswer).count() == 5000
    assert db.query(PracticeAnswerAggregate).count() == 0
