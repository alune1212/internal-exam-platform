from datetime import UTC, datetime

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.models import Candidate, PracticeAnswer, Question
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


def submit_practice_answer(
    db: Session, candidate_id: int, payload: PracticeAnswerSubmitRequest
) -> PracticeAnswerResult:
    assert_backup_write_allowed(db)
    candidate = get_active_practice_candidate(db, candidate_id)

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
        question.question_type,
        correct_answer,
        payload.selected_answer,
        float(question.score),
    )
    practice_answer = PracticeAnswer(
        candidate_id=candidate.id,
        question_id=question.id,
        selected_answer=payload.selected_answer,
        is_correct=scoring.is_correct,
        practiced_at=datetime.now(UTC),
    )
    db.add(practice_answer)
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
) -> list[PracticeWrongQuestionRead]:
    get_active_practice_candidate(db, candidate_id)
    query = (
        db.query(PracticeAnswer)
        .join(Question, PracticeAnswer.question_id == Question.id)
        .options(selectinload(PracticeAnswer.question).selectinload(Question.options))
        .filter(PracticeAnswer.candidate_id == candidate_id)
    )
    if category_1 is not None:
        query = query.filter(Question.category_1 == category_1)
    if category_2 is not None:
        query = query.filter(Question.category_2 == category_2)

    grouped: dict[int, list[PracticeAnswer]] = {}
    for answer in query.order_by(
        PracticeAnswer.question_id,
        PracticeAnswer.practiced_at,
        PracticeAnswer.id,
    ):
        grouped.setdefault(answer.question_id, []).append(answer)

    rows: list[PracticeWrongQuestionRead] = []
    for history in grouped.values():
        if not any(not answer.is_correct for answer in history):
            continue
        question = history[-1].question
        is_mastered = history[-1].is_correct
        if mastered is not None and is_mastered is not mastered:
            continue
        rows.append(
            PracticeWrongQuestionRead(
                question_id=question.id,
                question_type=question.question_type,
                stem=question.stem,
                category_1=question.category_1,
                category_2=question.category_2,
                status=question.status,
                correct_answer=_build_correct_answer(question),
                analysis=question.analysis,
                incorrect_count=sum(not answer.is_correct for answer in history),
                total_attempts=len(history),
                mastered=is_mastered,
                latest_practiced_at=history[-1].practiced_at,
                history=[
                    PracticeAnswerHistory(
                        practice_answer_id=answer.id,
                        selected_answer=answer.selected_answer,
                        is_correct=answer.is_correct,
                        practiced_at=answer.practiced_at,
                    )
                    for answer in history
                ],
                options=_build_option_comparison(question, history[-1].selected_answer),
            )
        )
    return sorted(rows, key=lambda row: row.latest_practiced_at, reverse=True)


def get_active_practice_candidate(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or candidate.status != "active":
        raise PracticeCandidateNotFoundError(candidate_id)
    return candidate


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
