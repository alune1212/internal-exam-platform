from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import DomainError
from app.schemas.operations import StorageReserveRead

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class StorageReserveError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("存储空间低于 20 GiB 或三倍数据占用安全水位，操作已拒绝。")


def database_footprint_bytes(db: Session) -> int:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        return int(db.scalar(text("SELECT pg_database_size(current_database())")) or 0)
    database = bind.engine.url.database
    if not database or database == ":memory:":
        return 0
    path = Path(database)
    return path.stat().st_size if path.is_file() else 0


def media_footprint_bytes() -> int:
    media_dir = Path(settings.learning_media_storage_dir)
    if not media_dir.exists():
        return 0
    return sum(path.stat().st_size for path in media_dir.rglob("*") if path.is_file())


def calculate_storage_reserve(
    *,
    free_bytes: int,
    database_bytes: int,
    media_bytes: int,
    proposed_bytes: int = 0,
) -> StorageReserveRead:
    footprint_after = database_bytes + media_bytes + proposed_bytes
    free_after = free_bytes - proposed_bytes
    required_free = max(
        settings.storage_min_free_bytes,
        settings.storage_footprint_multiplier * footprint_after,
    )
    return StorageReserveRead(
        free_bytes=free_bytes,
        database_bytes=database_bytes,
        media_bytes=media_bytes,
        proposed_bytes=proposed_bytes,
        footprint_after_bytes=footprint_after,
        free_after_bytes=free_after,
        required_free_bytes=required_free,
        sufficient=free_after >= required_free,
    )


def get_storage_reserve(db: Session, *, proposed_bytes: int = 0) -> StorageReserveRead:
    media_dir = Path(settings.learning_media_storage_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(media_dir).free
    return calculate_storage_reserve(
        free_bytes=free_bytes,
        database_bytes=database_footprint_bytes(db),
        media_bytes=media_footprint_bytes(),
        proposed_bytes=proposed_bytes,
    )


def assert_storage_reserve(db: Session, *, proposed_bytes: int = 0) -> None:
    if not get_storage_reserve(db, proposed_bytes=proposed_bytes).sufficient:
        raise StorageReserveError()
