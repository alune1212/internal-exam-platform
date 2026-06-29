"""Standalone auto-submit worker.

Run with:
    python -m app.core.auto_submit_worker
"""

import logging
import time
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import ExamAttempt
from app.services.exam_service import (
    _is_attempt_expired,
    score_and_mark_attempt_submitted,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30
DEFAULT_BATCH_SIZE = 100


def _expired_attempts_query(
    now: datetime, batch_size: int
) -> Select[tuple[ExamAttempt]]:
    return (
        select(ExamAttempt)
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


def run_once(*, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    with SessionLocal() as db:
        return process_due_attempts(db, batch_size=batch_size)


def run_forever(
    *,
    interval_seconds: int = CHECK_INTERVAL_SECONDS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            processed = run_once(batch_size=batch_size)
            if processed:
                logger.info("自动提交 %d 条超时考试记录", processed)
        except Exception:
            logger.exception("自动提交 worker 批处理失败")
        time.sleep(interval_seconds)


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
