"""Standalone auto-submit worker.

Run with:
    python -m app.core.auto_submit_worker
"""

import logging
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import ExamAttempt, ExamAttemptQuestion
from app.services.exam_service import (
    _is_attempt_expired,
    score_and_mark_attempt_submitted,
)
from app.services.operational_lock_service import (
    OperationalLockConflictError,
    WriterFenceActiveError,
    assert_backup_write_allowed,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = settings.auto_submit_check_interval_seconds
DEFAULT_BATCH_SIZE = settings.auto_submit_batch_size


def _expired_attempts_query(
    now: datetime, batch_size: int
) -> Select[tuple[ExamAttempt]]:
    # Eager-load questions + per-question answers so score_and_mark_attempt_submitted
    # doesn't trigger N+1 lazy loads while iterating the batch.
    return (
        select(ExamAttempt)
        .options(
            selectinload(ExamAttempt.questions).selectinload(ExamAttemptQuestion.answer)
        )
        .where(
            ExamAttempt.status == "in_progress",
            ExamAttempt.ends_at <= now,
        )
        .order_by(ExamAttempt.ends_at, ExamAttempt.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )


def process_due_attempts(
    db: Session, *, now: datetime | None = None, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    due_at = now or datetime.now(UTC)
    # Keep auto-submit inside the same transaction mutex as API writers.  A
    # cutover fence (or an explicit backup freeze) therefore causes a safe,
    # silent no-op rather than mutating formal rows mid-cutover.
    try:
        assert_backup_write_allowed(db, now=due_at)
    except (OperationalLockConflictError, WriterFenceActiveError):
        db.rollback()
        return 0
    attempts = db.execute(_expired_attempts_query(due_at, batch_size)).scalars().all()
    processed = 0
    for attempt in attempts:
        # Re-check the deadline inside the loop: another worker may have
        # already submitted (or the row may have been touched between
        # the query and the lock). Reuse the service-layer predicate so
        # "what counts as expired" stays in one place.
        if not _is_attempt_expired(attempt, due_at):
            continue
        score_and_mark_attempt_submitted(
            attempt, submit_type="auto", submitted_at=due_at
        )
        processed += 1
    db.commit()
    return processed


def write_heartbeat(path: str | Path, *, now: datetime | None = None) -> None:
    heartbeat_path = Path(path)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_at = now or datetime.now(UTC)
    temporary_path = heartbeat_path.with_name(f".{heartbeat_path.name}.tmp")
    temporary_path.write_text(str(heartbeat_at.timestamp()), encoding="utf-8")
    temporary_path.replace(heartbeat_path)


def is_heartbeat_fresh(
    path: str | Path,
    *,
    max_age_seconds: int,
    now: datetime | None = None,
) -> bool:
    try:
        heartbeat_timestamp = float(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    current_timestamp = (now or datetime.now(UTC)).timestamp()
    age_seconds = current_timestamp - heartbeat_timestamp
    return 0 <= age_seconds <= max_age_seconds


def run_once(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    heartbeat_path: str | Path | None = None,
) -> int:
    with SessionLocal() as db:
        processed = process_due_attempts(db, batch_size=batch_size)
    write_heartbeat(heartbeat_path or settings.auto_submit_heartbeat_path)
    return processed


def run_forever(
    *,
    interval_seconds: int = CHECK_INTERVAL_SECONDS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    heartbeat_path: str | Path | None = None,
) -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            processed = run_once(
                batch_size=batch_size,
                heartbeat_path=heartbeat_path or settings.auto_submit_heartbeat_path,
            )
            if processed:
                logger.info("自动提交 %d 条超时考试记录", processed)
        except Exception:
            logger.exception("自动提交 worker 批处理失败")
        time.sleep(interval_seconds)


def worker_healthcheck() -> int:
    return (
        0
        if is_heartbeat_fresh(
            settings.auto_submit_heartbeat_path,
            max_age_seconds=settings.auto_submit_heartbeat_max_age_seconds,
        )
        else 1
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["healthcheck"]:
        raise SystemExit(worker_healthcheck())
    if args:
        raise SystemExit("usage: python -m app.core.auto_submit_worker [healthcheck]")
    run_forever()


if __name__ == "__main__":
    main()
