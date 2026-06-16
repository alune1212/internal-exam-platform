from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.scheduler import _find_expired_attempts
from app.models import ExamAttempt, ExamCandidateScope
from app.services import exam_service
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)


def _make_started_attempt(db: Session, duration_minutes: int = 60):
    """创建考试、考生、题目并开始考试，返回 (exam, candidate, start_result)。"""
    exam = create_exam(db, duration_minutes=duration_minutes)
    candidate = create_candidate(db, name="超时考生")
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.commit()
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    return exam, candidate, start_result


def test_find_expired_attempts_finds_overdue(db: Session) -> None:
    exam, candidate, start_result = _make_started_attempt(db, duration_minutes=1)

    # 手动将 started_at 改为 2 分钟前
    attempt = db.get(ExamAttempt, start_result.attempt_id)
    assert attempt is not None
    attempt.started_at = datetime.now(UTC) - timedelta(minutes=2)
    db.commit()

    expired = _find_expired_attempts(db)
    assert start_result.attempt_id in expired


def test_find_expired_attempts_skips_not_expired(db: Session) -> None:
    exam, candidate, start_result = _make_started_attempt(db, duration_minutes=60)

    expired = _find_expired_attempts(db)
    assert start_result.attempt_id not in expired


def test_find_expired_attempts_skips_submitted(db: Session) -> None:
    exam, candidate, start_result = _make_started_attempt(db, duration_minutes=1)
    exam_service.submit_attempt(db, start_result.attempt_id, "manual")

    # 即使超时，已提交的不应出现在列表中
    attempt = db.get(ExamAttempt, start_result.attempt_id)
    assert attempt is not None
    attempt.started_at = datetime.now(UTC) - timedelta(minutes=5)
    db.commit()

    expired = _find_expired_attempts(db)
    assert start_result.attempt_id not in expired
