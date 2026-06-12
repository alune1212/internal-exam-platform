from datetime import UTC, datetime

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.models import Candidate, PracticeAnswer, Question
from app.schemas.practice import PracticeAnswerResult, PracticeAnswerSubmitRequest
from app.services.scoring_service import score_answer


class PracticeCandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考生 #{candidate_id} 不存在")


class PracticeQuestionNotFoundError(DomainError):
    status_code = 404

    def __init__(self, question_id: int) -> None:
        super().__init__(f"练习题目 #{question_id} 不存在")


def submit_practice_answer(
    db: Session, payload: PracticeAnswerSubmitRequest
) -> PracticeAnswerResult:
    candidate = db.get(Candidate, payload.candidate_id)
    if candidate is None or candidate.status != "active":
        raise PracticeCandidateNotFoundError(payload.candidate_id)

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
    db.add(
        PracticeAnswer(
            candidate_id=candidate.id,
            question_id=question.id,
            selected_answer=payload.selected_answer,
            is_correct=scoring.is_correct,
            practiced_at=datetime.now(UTC),
        )
    )
    db.commit()

    return PracticeAnswerResult(
        question_id=question.id,
        selected_answer=payload.selected_answer,
        correct_answer=correct_answer,
        is_correct=scoring.is_correct,
        score_awarded=scoring.score_awarded,
        score=float(question.score),
        analysis=question.analysis,
    )


def _build_correct_answer(question: Question) -> str:
    labels = sorted(option.label for option in question.options if option.is_correct)
    return ",".join(labels)
