"""Standalone auto-submit worker.

Run with:
    python -m app.core.auto_submit_worker
"""

import logging
import time
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import SessionLocal
from app.core.time import ensure_aware
from app.models import ExamAttempt, ExamAttemptQuestion
from app.services.exam_service import score_and_mark_attempt_submitted

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
    attempts = (
        db.execute(
            _expired_attempts_query(due_at, batch_size).options(
                selectinload(ExamAttempt.questions).selectinload(
                    ExamAttemptQuestion.answer
                )
            )
        )
        .scalars()
        .all()
    )
    processed = 0
    for attempt in attempts:
        if attempt.status != "in_progress" or ensure_aware(attempt.ends_at) > due_at:
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
