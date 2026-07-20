import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import auto_submit_worker
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamCandidateScope,
    ExamQuestionPool,
    Question,
    QuestionOption,
)
from app.services import exam_service

POSTGRES_TEST_DATABASE_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")


@pytest.fixture
def pg_session_factory() -> Iterator[sessionmaker[Session]]:
    if POSTGRES_TEST_DATABASE_URL is None:
        pytest.skip(
            "POSTGRES_TEST_DATABASE_URL is required for PostgreSQL concurrency tests"
        )
    engine = create_engine(POSTGRES_TEST_DATABASE_URL, pool_pre_ping=True)
    _clean_postgres(engine)
    try:
        yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    finally:
        _clean_postgres(engine)
        engine.dispose()


def _clean_postgres(engine: Engine) -> None:
    _assert_isolated_test_database(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE
                  exam_attempt_answer,
                  exam_attempt_question,
                  exam_attempt,
                  exam_retake_grant,
                  exam_candidate_scope,
                  exam_question_pool,
                  practice_answer,
                  question_option,
                  question,
                  exam,
                  candidate
                RESTART IDENTITY CASCADE
                """
            )
        )


def _assert_isolated_test_database(engine: Engine) -> None:
    database_name = engine.url.database or ""
    if not engine.url.drivername.startswith("postgresql") or not database_name.endswith(
        "_test"
    ):
        raise RuntimeError(
            "PostgreSQL concurrency tests require an isolated database ending in _test"
        )


def test_pg_database_guard_rejects_non_test_database() -> None:
    unsafe_engine = create_engine("postgresql+psycopg://exam@127.0.0.1/internal_exam")
    try:
        with pytest.raises(RuntimeError, match="isolated database ending in _test"):
            _assert_isolated_test_database(unsafe_engine)
    finally:
        unsafe_engine.dispose()


def _seed_exam(
    session_factory: sessionmaker[Session], *, candidate_count: int
) -> tuple[int, list[int]]:
    with session_factory() as db:
        exam = Exam(
            title="PG 并发考试",
            duration_minutes=30,
            status="active",
            question_rule={
                "question_count": 2,
                "total_score": 100,
                "type_counts": {"single": 2, "multiple": 0, "judge": 0},
            },
        )
        db.add(exam)
        db.flush()

        questions: list[Question] = []
        for index in range(2):
            question = Question(
                question_type="single",
                stem=f"PG 并发题 {index}",
                score=1,
                status="active",
            )
            db.add(question)
            db.flush()
            db.add_all(
                [
                    QuestionOption(
                        question_id=question.id,
                        label="A",
                        content="正确",
                        is_correct=True,
                        sort_order=0,
                    ),
                    QuestionOption(
                        question_id=question.id,
                        label="B",
                        content="错误",
                        is_correct=False,
                        sort_order=1,
                    ),
                ]
            )
            db.add(
                ExamQuestionPool(
                    exam_id=exam.id, question_id=question.id, sort_order=index
                )
            )
            questions.append(question)

        candidate_ids: list[int] = []
        for index in range(candidate_count):
            candidate = Candidate(name=f"PG 考生 {index}", status="active")
            db.add(candidate)
            db.flush()
            db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
            candidate_ids.append(candidate.id)

        db.commit()
        return exam.id, candidate_ids


def _start_concurrently(
    session_factory: sessionmaker[Session], exam_id: int, candidate_ids: list[int]
) -> list[int]:
    barrier = threading.Barrier(len(candidate_ids))

    def start(candidate_id: int) -> int:
        with session_factory() as db:
            barrier.wait(timeout=10)
            return exam_service.start_exam(db, exam_id, candidate_id).attempt_id

    with ThreadPoolExecutor(max_workers=len(candidate_ids)) as executor:
        futures = [
            executor.submit(start, candidate_id) for candidate_id in candidate_ids
        ]
        return [future.result(timeout=10) for future in futures]


def test_pg_same_candidate_concurrent_start_returns_one_attempt(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)

    attempt_ids = _start_concurrently(
        pg_session_factory, exam_id, [candidate_id, candidate_id]
    )

    assert len(set(attempt_ids)) == 1
    with pg_session_factory() as db:
        count = (
            db.query(ExamAttempt)
            .filter(
                ExamAttempt.exam_id == exam_id,
                ExamAttempt.candidate_id == candidate_id,
                ExamAttempt.status == "in_progress",
            )
            .count()
        )
    assert count == 1


def test_pg_different_candidates_start_same_exam_concurrently(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, candidate_ids = _seed_exam(pg_session_factory, candidate_count=2)

    attempt_ids = _start_concurrently(pg_session_factory, exam_id, candidate_ids)

    assert len(set(attempt_ids)) == 2
    with pg_session_factory() as db:
        count = (
            db.query(ExamAttempt)
            .filter(ExamAttempt.exam_id == exam_id, ExamAttempt.status == "in_progress")
            .count()
        )
    assert count == 2


def test_pg_auto_submit_skips_locked_attempt_being_saved(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)
    with pg_session_factory() as db:
        attempt_id = exam_service.start_exam(db, exam_id, candidate_id).attempt_id
        attempt = db.get(ExamAttempt, attempt_id)
        assert attempt is not None
        attempt.ends_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

    lock_session = pg_session_factory()
    try:
        lock_session.begin()
        locked_attempt = lock_session.execute(
            select(ExamAttempt).where(ExamAttempt.id == attempt_id).with_for_update()
        ).scalar_one()
        assert locked_attempt.id == attempt_id

        with pg_session_factory() as worker_db:
            processed = auto_submit_worker.process_due_attempts(
                worker_db, now=datetime.now(UTC), batch_size=10
            )
        assert processed == 0
    finally:
        lock_session.rollback()
        lock_session.close()

    with pg_session_factory() as worker_db:
        processed = auto_submit_worker.process_due_attempts(
            worker_db, now=datetime.now(UTC), batch_size=10
        )
    assert processed == 1


def test_pg_duplicate_manual_submit_is_idempotent(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)
    with pg_session_factory() as db:
        attempt_id = exam_service.start_exam(db, exam_id, candidate_id).attempt_id

    barrier = threading.Barrier(2)

    def submit() -> int:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            return exam_service.submit_attempt(db, attempt_id, "manual").attempt_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        submitted_attempt_ids = [
            future.result(timeout=10)
            for future in [executor.submit(submit), executor.submit(submit)]
        ]

    assert submitted_attempt_ids == [attempt_id, attempt_id]
    with pg_session_factory() as db:
        attempt = db.get(ExamAttempt, attempt_id)
        assert attempt is not None
        assert attempt.status == "submitted"
        assert (
            db.query(ExamAttempt)
            .filter(ExamAttempt.id == attempt_id, ExamAttempt.status == "submitted")
            .count()
            == 1
        )
