from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from sqlalchemy.orm import Session

from app.models import ExamAttempt, ImportBatch, OperationalLock, Question
from app.schemas.practice import PracticeAnswerSubmitRequest
from app.services import import_service, practice_service, question_service
from app.services.operational_lock_service import (
    BACKUP_WRITE_FREEZE,
    FormalAttemptWriteGateError,
    OperationalLockConflictError,
    WriterFenceConflictError,
    acquire_backup_write_freeze,
    acquire_lock,
    acquire_writer_fence,
    assert_backup_write_allowed,
    release_lock,
)
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)


def _add_in_progress_attempt(db: Session) -> ExamAttempt:
    exam = create_exam(db, status="active")
    candidate = create_candidate(db)
    now = datetime.now(UTC)
    attempt = ExamAttempt(
        exam_id=exam.id,
        candidate_id=candidate.id,
        status="in_progress",
        started_at=now,
        ends_at=now + timedelta(hours=1),
        duration_minutes_snapshot=60,
    )
    db.add(attempt)
    db.commit()
    return attempt


def test_operational_lock_requires_explicit_owner_release_after_ttl(
    db: Session,
) -> None:
    now = datetime.now(UTC)
    acquire_lock(
        db,
        name=BACKUP_WRITE_FREEZE,
        owner="backup-a",
        ttl_seconds=60,
        now=now,
    )
    db.commit()

    with pytest.raises(OperationalLockConflictError):
        acquire_lock(
            db,
            name=BACKUP_WRITE_FREEZE,
            owner="backup-b",
            ttl_seconds=60,
            now=now + timedelta(seconds=1),
        )
    db.rollback()
    with pytest.raises(OperationalLockConflictError):
        assert_backup_write_allowed(db, now=now + timedelta(seconds=1))
    db.rollback()

    # The diagnostic TTL is not proof that pg_dump/media archival stopped.
    # Writers and another backup remain blocked until the exact owner releases.
    with pytest.raises(OperationalLockConflictError):
        assert_backup_write_allowed(db, now=now + timedelta(hours=1))
    db.rollback()
    with pytest.raises(OperationalLockConflictError):
        acquire_lock(
            db,
            name=BACKUP_WRITE_FREEZE,
            owner="backup-b",
            ttl_seconds=10,
            now=now + timedelta(hours=1),
        )
    db.rollback()

    released = release_lock(
        db,
        name=BACKUP_WRITE_FREEZE,
        owner="backup-a",
        now=now + timedelta(hours=1),
    )
    db.commit()
    assert released.released_at is not None
    assert_backup_write_allowed(db, now=now + timedelta(hours=1, seconds=1))

    reacquired = acquire_lock(
        db,
        name=BACKUP_WRITE_FREEZE,
        owner="backup-b",
        ttl_seconds=10,
        now=now + timedelta(hours=1, seconds=2),
    )
    db.commit()
    assert reacquired.owner == "backup-b"
    with pytest.raises(OperationalLockConflictError):
        assert_backup_write_allowed(db, now=now + timedelta(hours=2))


def test_backup_lock_refuses_in_progress_formal_attempt(db: Session) -> None:
    _add_in_progress_attempt(db)

    with pytest.raises(FormalAttemptWriteGateError):
        acquire_backup_write_freeze(db, owner="daily-backup", ttl_seconds=600)

    assert db.query(OperationalLock).count() == 0


def test_writer_fence_refuses_active_backup_freeze(db: Session) -> None:
    now = datetime.now(UTC)
    acquire_backup_write_freeze(
        db,
        owner="daily-backup",
        ttl_seconds=600,
        now=now,
    )
    db.commit()

    with pytest.raises(WriterFenceConflictError, match="backup-write-freeze"):
        acquire_writer_fence(
            db,
            dataset_id="formal-dataset",
            host_id="formal-host",
            writer_generation=1,
            reason="prepare-cutover",
            now=now + timedelta(seconds=1),
        )
    db.rollback()
    assert db.get(OperationalLock, BACKUP_WRITE_FREEZE) is not None
    assert db.get(OperationalLock, "formal-writer-fence") is None


def test_writer_fence_refuses_expired_but_unreleased_backup_freeze(
    db: Session,
) -> None:
    now = datetime.now(UTC)
    acquire_backup_write_freeze(
        db,
        owner="slow-backup",
        ttl_seconds=1,
        now=now,
    )
    db.commit()

    with pytest.raises(WriterFenceConflictError, match="尚未显式释放"):
        acquire_writer_fence(
            db,
            dataset_id="formal-dataset",
            host_id="formal-host",
            writer_generation=1,
            reason="prepare-cutover-after-expiry",
            now=now + timedelta(hours=1),
        )
    db.rollback()
    assert db.get(OperationalLock, "formal-writer-fence") is None


def test_formal_attempt_blocks_import_before_batch_or_rows_are_created(
    db: Session,
) -> None:
    _add_in_progress_attempt(db)

    with pytest.raises(FormalAttemptWriteGateError):
        import_service.import_questions_from_workbook(
            db,
            BytesIO(b"not-even-parsed"),
            "blocked.xlsx",
        )

    assert db.query(ImportBatch).count() == 0
    assert db.query(Question).count() == 0


def test_backup_freeze_blocks_practice_write_but_preserves_reads(db: Session) -> None:
    candidate = create_candidate(db)
    question = create_question_with_options(db)
    acquire_backup_write_freeze(db, owner="daily-backup", ttl_seconds=600)
    db.commit()

    assert question_service.list_active_questions(db)
    with pytest.raises(OperationalLockConflictError):
        practice_service.submit_practice_answer(
            db,
            candidate.id,
            PracticeAnswerSubmitRequest(
                question_id=question.id,
                selected_answer="A",
            ),
        )
