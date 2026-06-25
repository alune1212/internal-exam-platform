from datetime import UTC, datetime, timedelta

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.core import auto_submit_worker
from app.models import ExamAttempt, ExamCandidateScope
from app.services import exam_service
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)


def _start_attempt(db: Session, *, ends_at: datetime) -> int:
    exam = create_exam(db, duration_minutes=30)
    candidate = create_candidate(db, name=f"worker-{ends_at.timestamp()}")
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.commit()
    create_question_with_options(db, stem=f"worker question {ends_at.timestamp()}")
    start = exam_service.start_exam(db, exam.id, candidate.id)
    attempt = db.get(ExamAttempt, start.attempt_id)
    assert attempt is not None
    attempt.ends_at = ends_at
    db.commit()
    return start.attempt_id


def test_expired_attempts_query_uses_for_update_skip_locked() -> None:
    query = auto_submit_worker._expired_attempts_query(
        datetime(2026, 1, 1, tzinfo=UTC), batch_size=25
    )

    sql = str(
        query.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "exam_attempt.ends_at <=" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql


def test_process_due_attempts_submits_only_expired_in_progress(
    db: Session,
) -> None:
    now = datetime.now(UTC)
    expired_id = _start_attempt(db, ends_at=now - timedelta(seconds=1))
    future_id = _start_attempt(db, ends_at=now + timedelta(minutes=5))

    processed = auto_submit_worker.process_due_attempts(db, now=now, batch_size=10)

    assert processed == 1
    expired_attempt = db.get(ExamAttempt, expired_id)
    future_attempt = db.get(ExamAttempt, future_id)
    assert expired_attempt is not None
    assert future_attempt is not None
    assert expired_attempt.status == "auto_submitted"
    assert future_attempt.status == "in_progress"
