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
from app.core.config import settings
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamCandidateScope,
    ExamQuestionPool,
    OperationalLock,
    Question,
    QuestionOption,
)
from app.schemas.attempt import AnswerSaveItem, AnswerSaveRequest
from app.services import exam_service
from app.services.exam_errors import (
    AttemptResultNotReadyError,
    AttemptRevisionConflictError,
    AttemptSessionConflictError,
)
from app.services.operational_lock_service import (
    FormalAttemptWriteGateError,
    OperationalLockConflictError,
    WriterFenceActiveError,
    WriterFenceConflictError,
    acquire_backup_write_freeze,
    acquire_writer_fence,
)

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
                  candidate,
                  operational_lock,
                  admin_audit_event
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
            candidate = Candidate(
                name=f"PG 考生 {index}",
                email=f"pg-candidate-{index}@example.com",
                status="active",
            )
            db.add(candidate)
            db.flush()
            db.add(
                ExamCandidateScope(
                    exam_id=exam.id,
                    candidate_id=candidate.id,
                    roster_email=candidate.email,
                    roster_name=candidate.name or "待注册",
                )
            )
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


def test_pg_same_revision_concurrent_saves_allow_exactly_one_writer(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)
    with pg_session_factory() as db:
        start = exam_service.start_exam(db, exam_id, candidate_id)
        attempt_id = start.attempt_id
        attempt = db.get(ExamAttempt, attempt_id)
        assert attempt is not None
        question_id = attempt.questions[0].id

    barrier = threading.Barrier(2)

    def save(selected_answer: str) -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                exam_service.save_answers(
                    db,
                    attempt_id,
                    AnswerSaveRequest(
                        answer_revision=0,
                        answers=[
                            AnswerSaveItem(
                                attempt_question_id=question_id,
                                selected_answer=selected_answer,
                            )
                        ],
                    ),
                )
            except AttemptRevisionConflictError:
                db.rollback()
                return "conflict"
            return f"saved:{selected_answer}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = {
            future.result(timeout=10)
            for future in [executor.submit(save, "A"), executor.submit(save, "B")]
        }

    assert "conflict" in outcomes
    saved = outcomes - {"conflict"}
    assert saved in ({"saved:A"}, {"saved:B"})
    with pg_session_factory() as db:
        attempt = db.get(ExamAttempt, attempt_id)
        answer = (
            db.query(ExamAttemptAnswer).filter_by(attempt_question_id=question_id).one()
        )
        assert attempt is not None
        assert attempt.answer_revision == 1
        assert f"saved:{answer.selected_answer}" in saved


def test_pg_save_and_takeover_serialize_device_generation_and_revision(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)
    with pg_session_factory() as db:
        start = exam_service.start_exam(db, exam_id, candidate_id)
        attempt_id = start.attempt_id
        credential = start.attempt_session_credential
        attempt = db.get(ExamAttempt, attempt_id)
        assert attempt is not None
        question_id = attempt.questions[0].id
    assert credential is not None
    barrier = threading.Barrier(2)

    def save_from_original_device() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                exam_service.verify_attempt_session(
                    db, attempt_id, candidate_id, credential
                )
                exam_service.save_answers(
                    db,
                    attempt_id,
                    AnswerSaveRequest(
                        answer_revision=0,
                        answers=[
                            AnswerSaveItem(
                                attempt_question_id=question_id,
                                selected_answer="A",
                            )
                        ],
                    ),
                )
            except AttemptSessionConflictError:
                db.rollback()
                return "stale-device"
            return "saved"

    def takeover() -> int:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            return exam_service.takeover_attempt_session(
                db, attempt_id, candidate_id
            ).answer_revision

    with ThreadPoolExecutor(max_workers=2) as executor:
        save_future = executor.submit(save_from_original_device)
        takeover_future = executor.submit(takeover)
        save_outcome = save_future.result(timeout=10)
        takeover_revision = takeover_future.result(timeout=10)

    assert (save_outcome, takeover_revision) in {("saved", 1), ("stale-device", 0)}
    with pg_session_factory() as db:
        attempt = db.get(ExamAttempt, attempt_id)
        assert attempt is not None
        assert attempt.attempt_session_generation == 2
        assert attempt.answer_revision == takeover_revision


def test_pg_manual_submit_and_void_serialize_to_one_terminal_incident(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)
    with pg_session_factory() as db:
        attempt_id = exam_service.start_exam(db, exam_id, candidate_id).attempt_id
    barrier = threading.Barrier(2)

    def submit() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                exam_service.submit_attempt(db, attempt_id, "manual")
            except AttemptResultNotReadyError:
                db.rollback()
                return "observed-void"
            return "submitted"

    def void() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            exam_service.void_attempt(
                db,
                attempt_id,
                operator_subject="pg-operator",
                reason="PG 并发事故验证",
            )
            db.commit()
            return "voided"

    with ThreadPoolExecutor(max_workers=2) as executor:
        submit_future = executor.submit(submit)
        void_future = executor.submit(void)
        outcomes = (submit_future.result(timeout=10), void_future.result(timeout=10))

    assert outcomes in {("submitted", "voided"), ("observed-void", "voided")}
    with pg_session_factory() as db:
        attempt = db.get(ExamAttempt, attempt_id)
        assert attempt is not None
        assert attempt.status == "voided"
        assert attempt.voided_by == "pg-operator"
        assert attempt.attempt_session_hash is None


def test_pg_start_and_backup_freeze_serialize_without_unsafe_overlap(
    pg_session_factory: sessionmaker[Session],
) -> None:
    exam_id, (candidate_id,) = _seed_exam(pg_session_factory, candidate_count=1)
    barrier = threading.Barrier(2)

    def start_attempt() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                exam_service.start_exam(db, exam_id, candidate_id)
            except OperationalLockConflictError:
                db.rollback()
                return "blocked"
            return "started"

    def acquire_backup() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                acquire_backup_write_freeze(
                    db,
                    owner="pg-concurrency-backup",
                    ttl_seconds=60,
                )
                db.commit()
            except FormalAttemptWriteGateError:
                db.rollback()
                return "skipped"
            return "locked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        start_future = executor.submit(start_attempt)
        backup_future = executor.submit(acquire_backup)
        outcome = (start_future.result(timeout=10), backup_future.result(timeout=10))

    assert outcome in {("started", "skipped"), ("blocked", "locked")}
    with pg_session_factory() as db:
        in_progress = db.query(ExamAttempt).filter_by(status="in_progress").count()
        active_locks = db.query(OperationalLock).filter_by(released_at=None).count()
    assert (in_progress, active_locks) in {(1, 0), (0, 1)}


def test_pg_writer_fence_and_backup_freeze_serialize_without_overlap(
    pg_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "internal")
    barrier = threading.Barrier(2)

    def acquire_backup() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                acquire_backup_write_freeze(
                    db,
                    owner="pg-concurrency-backup",
                    ttl_seconds=60,
                )
                db.commit()
            except (
                FormalAttemptWriteGateError,
                OperationalLockConflictError,
                WriterFenceActiveError,
            ):
                db.rollback()
                return "blocked"
            return "backup-locked"

    def acquire_fence() -> str:
        with pg_session_factory() as db:
            barrier.wait(timeout=10)
            try:
                acquire_writer_fence(
                    db,
                    dataset_id="pg-concurrency-dataset",
                    host_id="pg-concurrency-host",
                    writer_generation=1,
                    reason="concurrency-test",
                )
                db.commit()
            except WriterFenceConflictError:
                db.rollback()
                return "blocked"
            return "fence-locked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        backup_future = executor.submit(acquire_backup)
        fence_future = executor.submit(acquire_fence)
        outcome = (backup_future.result(timeout=10), fence_future.result(timeout=10))

    assert outcome in {
        ("backup-locked", "blocked"),
        ("blocked", "fence-locked"),
    }
    with pg_session_factory() as db:
        active_locks = db.query(OperationalLock).filter_by(released_at=None).all()
    assert len(active_locks) == 1
