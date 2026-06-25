"""Legacy auto-submit helpers kept for tests and backwards-compatible imports."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import ExamAttempt
from app.services.exam_service import submit_attempt

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30


def _find_expired_attempts(db) -> list[int]:
    """查找已超时的 in_progress attempt。"""
    now = datetime.now(UTC)
    rows = db.execute(
        select(ExamAttempt.id)
        .where(ExamAttempt.status == "in_progress")
        .where(ExamAttempt.ends_at <= now)
    ).all()
    return [attempt_id for (attempt_id,) in rows]


async def auto_submit_loop() -> None:
    """定时检查并自动提交超时考试。

    每条 attempt 使用独立的数据库会话：
    - 查询过期列表用一个 session
    - 每条 submit 用一个独立 session（失败自动回滚，不影响下一条）
    """
    while True:
        try:
            with SessionLocal() as scan_db:
                expired_ids = _find_expired_attempts(scan_db)
        except Exception:
            logger.exception("过期 attempt 扫描异常")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            continue

        for attempt_id in expired_ids:
            try:
                with SessionLocal() as submit_db:
                    submit_attempt(submit_db, attempt_id, "auto")
                    logger.info("自动提交考试记录 #%d", attempt_id)
            except Exception:
                logger.exception("自动提交 #%d 失败", attempt_id)

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
