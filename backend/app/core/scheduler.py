"""后台定时任务：自动提交超时考试。"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.time import ensure_aware
from app.models import Exam, ExamAttempt
from app.services.exam_service import submit_attempt

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30


def _find_expired_attempts(db) -> list[int]:
    """查找已超时的 in_progress attempt。"""
    now = datetime.now(UTC)
    rows = db.execute(
        select(ExamAttempt.id, ExamAttempt.started_at, Exam.duration_minutes)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(ExamAttempt.status == "in_progress")
    ).all()
    return [
        attempt_id
        for attempt_id, started_at, duration_minutes in rows
        if ensure_aware(started_at) + timedelta(minutes=duration_minutes) < now
    ]


async def auto_submit_loop() -> None:
    """定时检查并自动提交超时考试。"""
    while True:
        try:
            with SessionLocal() as db:
                expired_ids = _find_expired_attempts(db)
                for attempt_id in expired_ids:
                    try:
                        submit_attempt(db, attempt_id, "auto")
                        logger.info("自动提交考试记录 #%d", attempt_id)
                    except Exception:
                        logger.exception("自动提交 #%d 失败", attempt_id)
        except Exception:
            logger.exception("自动提交检查循环异常")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
