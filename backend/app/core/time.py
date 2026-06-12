"""时间工具函数。"""

from datetime import UTC, datetime


def ensure_aware(dt: datetime) -> datetime:
    """确保 datetime 带时区信息。

    SQLite 返回 naive datetime，需要手动附加 UTC。PostgreSQL 的 timezone=True
    列已经返回 aware datetime，此函数仅在 SQLite（测试）环境下实际生效。
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
