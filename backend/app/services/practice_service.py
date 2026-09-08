from collections import defaultdict
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import case, func
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.core.rate_limit import check_public_token_rate_limit
from app.models import Candidate, PracticeAnswer, PracticeAnswerAggregate, Question
from app.schemas.practice import (
    PracticeAnswerHistory,
    PracticeAnswerResult,
    PracticeAnswerSubmitRequest,
    PracticeOptionComparison,
    PracticeWrongQuestionRead,
)
from app.services.operational_lock_service import assert_backup_write_allowed
from app.services.scoring_service import normalize_answer_set, score_answer


class PracticeCandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考试人 #{candidate_id} 不存在")


class PracticeQuestionNotFoundError(DomainError):
    status_code = 404

    def __init__(self, question_id: int) -> None:
        super().__init__(f"练习题目 #{question_id} 不存在")


class PracticeAnswerValidationError(DomainError):
    status_code = 422


class PracticeHistoryCapacityError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("练习答题记录已达到 5000 条上限，请联系管理员归档后重试。")


def submit_practice_answer(
    db: Session,
    candidate_id: int,
    payload: PracticeAnswerSubmitRequest,
    *,
    request: Request | None = None,
) -> PracticeAnswerResult:
    if len(payload.selected_answer) > 32:
        raise PracticeAnswerValidationError("所选答案长度不能超过 32 个字符")
    if request is not None:
        check_public_token_rate_limit(
            request,
            bucket="practice-answer",
            identifier=f"candidate:{candidate_id}",
            include_client_ip=False,
        )
    assert_backup_write_allowed(db)
    candidate = _lock_active_practice_candidate(db, candidate_id)

    hot_detail_count = (
        db.query(func.count(PracticeAnswer.id))
        .filter(PracticeAnswer.candidate_id == candidate.id)
        .scalar()
        or 0
    )
    if hot_detail_count >= 5000:
        raise PracticeHistoryCapacityError()

    question = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id == payload.question_id, Question.status == "active")
        .one_or_none()
    )
    if question is None:
        raise PracticeQuestionNotFoundError(payload.question_id)

    correct_answer = _build_correct_answer(question)
    scoring = score_answer(
        correct_answer,
        payload.selected_answer,
        float(question.score),
    )
    aggregate = _get_or_rebuild_aggregate(db, candidate.id, question.id)
    practice_answer = PracticeAnswer(
        candidate_id=candidate.id,
        question_id=question.id,
        selected_answer=payload.selected_answer,
        is_correct=scoring.is_correct,
        practiced_at=datetime.now(UTC),
    )
    db.add(practice_answer)
    db.flush()
    if aggregate is None:
        aggregate = PracticeAnswerAggregate(
            candidate_id=candidate.id,
            question_id=question.id,
            total_attempts=0,
            incorrect_count=0,
            latest_selected_answer=payload.selected_answer,
            latest_is_correct=scoring.is_correct,
            latest_practiced_at=practice_answer.practiced_at,
            latest_practice_answer_id=practice_answer.id,
        )
        db.add(aggregate)
    aggregate.total_attempts += 1
    if not scoring.is_correct:
        aggregate.incorrect_count += 1
    if _is_newer(
        practice_answer.practiced_at,
        practice_answer.id,
        aggregate.latest_practiced_at,
        aggregate.latest_practice_answer_id,
    ):
        aggregate.latest_selected_answer = practice_answer.selected_answer
        aggregate.latest_is_correct = practice_answer.is_correct
        aggregate.latest_practiced_at = practice_answer.practiced_at
        aggregate.latest_practice_answer_id = practice_answer.id
    db.commit()
    db.refresh(practice_answer)

    return PracticeAnswerResult(
        practice_answer_id=practice_answer.id,
        question_id=question.id,
        selected_answer=payload.selected_answer,
        score=float(question.score),
        is_correct=scoring.is_correct,
        correct_answer=correct_answer,
        analysis=question.analysis,
        option_comparison=_build_option_comparison(question, payload.selected_answer),
    )


def list_wrong_questions(
    db: Session,
    candidate_id: int,
    *,
    category_1: str | None = None,
    category_2: str | None = None,
    mastered: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    history_limit: int = 20,
) -> list[PracticeWrongQuestionRead]:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    if offset > 2**31 - 1:
        raise PracticeAnswerValidationError("offset 不能超过 2^31-1")
    history_limit = min(max(history_limit, 1), 100)
    get_active_practice_candidate(db, candidate_id)

    filters = [
        PracticeAnswerAggregate.candidate_id == candidate_id,
        PracticeAnswerAggregate.incorrect_count > 0,
    ]
    if category_1 is not None:
        filters.append(Question.category_1 == category_1)
    if category_2 is not None:
        filters.append(Question.category_2 == category_2)
    if mastered is not None:
        filters.append(PracticeAnswerAggregate.latest_is_correct == mastered)

    aggregates = (
        db.query(PracticeAnswerAggregate, Question)
        .join(Question, PracticeAnswerAggregate.question_id == Question.id)
        .options(selectinload(Question.options))
        .filter(*filters)
        .order_by(
            PracticeAnswerAggregate.latest_practiced_at.desc(),
            PracticeAnswerAggregate.question_id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    if not aggregates:
        return []

    question_ids = [aggregate.question_id for aggregate, _question in aggregates]

    ranked_history = (
        db.query(
            PracticeAnswer.id.label("practice_answer_id"),
            PracticeAnswer.question_id.label("question_id"),
            func.row_number()
            .over(
                partition_by=PracticeAnswer.question_id,
                order_by=(
                    PracticeAnswer.practiced_at.desc(),
                    PracticeAnswer.id.desc(),
                ),
            )
            .label("history_rank"),
        )
        .filter(
            PracticeAnswer.candidate_id == candidate_id,
            PracticeAnswer.question_id.in_(question_ids),
        )
        .subquery()
    )
    history_rows = (
        db.query(PracticeAnswer)
        .join(
            ranked_history,
            ranked_history.c.practice_answer_id == PracticeAnswer.id,
        )
        .filter(ranked_history.c.history_rank <= history_limit)
        .order_by(
            PracticeAnswer.question_id,
            PracticeAnswer.practiced_at.desc(),
            PracticeAnswer.id.desc(),
        )
        .all()
    )
    history_by_question: dict[int, list[PracticeAnswer]] = defaultdict(list)
    for answer in history_rows:
        history_by_question[answer.question_id].append(answer)

    result: list[PracticeWrongQuestionRead] = []
    for aggregate, question in aggregates:
        recent_history = list(reversed(history_by_question[question.id]))
        history_total = int(aggregate.total_attempts)
        result.append(
            PracticeWrongQuestionRead(
                question_id=question.id,
                question_type=question.question_type,
                stem=question.stem,
                category_1=question.category_1,
                category_2=question.category_2,
                status=question.status,
                correct_answer=_build_correct_answer(question),
                analysis=question.analysis,
                incorrect_count=int(aggregate.incorrect_count),
                total_attempts=int(aggregate.total_attempts),
                mastered=bool(aggregate.latest_is_correct),
                latest_practiced_at=aggregate.latest_practiced_at,
                history_total=history_total,
                history_truncated=history_total > len(recent_history),
                history=[
                    PracticeAnswerHistory(
                        practice_answer_id=answer.id,
                        selected_answer=answer.selected_answer,
                        is_correct=answer.is_correct,
                        practiced_at=answer.practiced_at,
                    )
                    for answer in recent_history
                ],
                options=_build_option_comparison(
                    question, aggregate.latest_selected_answer
                ),
            )
        )
    return result


def get_active_practice_candidate(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or candidate.status != "active":
        raise PracticeCandidateNotFoundError(candidate_id)
    return candidate


def _lock_active_practice_candidate(db: Session, candidate_id: int) -> Candidate:
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .with_for_update()
        .one_or_none()
    )
    if candidate is None or candidate.status != "active":
        raise PracticeCandidateNotFoundError(candidate_id)
    return candidate


def _get_or_rebuild_aggregate(
    db: Session, candidate_id: int, question_id: int
) -> PracticeAnswerAggregate | None:
    aggregate = (
        db.query(PracticeAnswerAggregate)
        .filter(
            PracticeAnswerAggregate.candidate_id == candidate_id,
            PracticeAnswerAggregate.question_id == question_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if aggregate is not None:
        return aggregate

    incorrect_count_expression = func.coalesce(
        func.sum(case((PracticeAnswer.is_correct.is_(False), 1), else_=0)),
        0,
    )
    total_attempts, incorrect_count = (
        db.query(func.count(PracticeAnswer.id), incorrect_count_expression)
        .filter(
            PracticeAnswer.candidate_id == candidate_id,
            PracticeAnswer.question_id == question_id,
        )
        .one()
    )
    if not total_attempts:
        return None

    latest = (
        db.query(PracticeAnswer)
        .filter(
            PracticeAnswer.candidate_id == candidate_id,
            PracticeAnswer.question_id == question_id,
        )
        .order_by(PracticeAnswer.practiced_at.desc(), PracticeAnswer.id.desc())
        .first()
    )
    if latest is None:
        return None
    aggregate = PracticeAnswerAggregate(
        candidate_id=candidate_id,
        question_id=question_id,
        total_attempts=int(total_attempts),
        incorrect_count=int(incorrect_count),
        latest_selected_answer=latest.selected_answer,
        latest_is_correct=latest.is_correct,
        latest_practiced_at=latest.practiced_at,
        latest_practice_answer_id=latest.id,
    )
    db.add(aggregate)
    return aggregate


def _is_newer(
    practiced_at: datetime,
    detail_id: int,
    latest_practiced_at: datetime,
    latest_detail_id: int,
) -> bool:
    from app.core.time import to_utc

    return (to_utc(practiced_at), detail_id) > (
        to_utc(latest_practiced_at),
        latest_detail_id,
    )


def _build_correct_answer(question: Question) -> str:
    labels = sorted(option.label for option in question.options if option.is_correct)
    return ",".join(labels)


def _build_option_comparison(
    question: Question, selected_answer: str | None
) -> list[PracticeOptionComparison]:
    selected_labels = normalize_answer_set(selected_answer)
    return [
        PracticeOptionComparison(
            label=option.label,
            content=option.content,
            selected=option.label.strip().upper() in selected_labels,
            correct=option.is_correct,
        )
        for option in sorted(question.options, key=lambda item: item.sort_order)
    ]
