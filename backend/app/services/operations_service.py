from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.core.auto_submit_worker import is_heartbeat_fresh
from app.core.config import settings
from app.core.time import to_utc
from app.models import OperationalLock
from app.ops.internal_backup import (
    SECOND_COPY_EVIDENCE_SUFFIX,
    list_verified_backups,
)
from app.schemas.operations import OperationalSignalRead, OperationsSnapshotRead
from app.services.operational_lock_service import (
    BACKUP_WRITE_FREEZE,
    FORMAL_WRITER_FENCE,
    is_lock_active,
    writer_fence_is_active,
)
from app.services.readiness_service import check_readiness
from app.services.retention_service import preview_retention
from app.services.storage_service import get_storage_reserve

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session


def _signal(
    status: str,
    summary: str,
    checked_at: datetime,
    **details: object,
) -> OperationalSignalRead:
    return OperationalSignalRead(
        status=status, summary=summary, checked_at=checked_at, details=details
    )


def _failed_signal(checked_at: datetime, error: Exception) -> OperationalSignalRead:
    return _signal(
        "failed",
        "状态读取失败",
        checked_at,
        error_type=type(error).__name__,
    )


def _safe(
    checked_at: datetime, loader: Callable[[], OperationalSignalRead]
) -> OperationalSignalRead:
    try:
        return loader()
    except Exception as exc:
        return _failed_signal(checked_at, exc)


def _latest_json(
    directory: Path, pattern: str
) -> tuple[Path, dict[str, object]] | None:
    if not directory.is_dir():
        return None
    paths = sorted(
        directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True
    )
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return path, payload
    return None


def get_operations_snapshot(
    db: Session, *, now: datetime | None = None
) -> OperationsSnapshotRead:
    checked_at = to_utc(now or datetime.now(UTC))

    def version() -> OperationalSignalRead:
        status = "current" if settings.git_commit != "development" else "degraded"
        return _signal(
            status,
            f"{settings.app_version} · {settings.git_commit[:12]}",
            checked_at,
            application_version=settings.app_version,
            git_commit=settings.git_commit,
        )

    def migration() -> OperationalSignalRead:
        head = str(db.scalar(text("SELECT version_num FROM alembic_version")) or "")
        return _signal(
            "current" if head else "degraded",
            head or "无法确认迁移版本",
            checked_at,
            migration_head=head or None,
        )

    def service_health() -> OperationalSignalRead:
        readiness = check_readiness(db)
        return _signal(
            "current",
            "后端、数据库与媒体目录就绪",
            checked_at,
            database=readiness.database,
            learning_media=readiness.learning_media,
        )

    def worker_health() -> OperationalSignalRead:
        fresh = is_heartbeat_fresh(
            settings.auto_submit_heartbeat_path,
            max_age_seconds=settings.auto_submit_heartbeat_max_age_seconds,
            now=checked_at,
        )
        return _signal(
            "current" if fresh else "stale",
            "自动交卷 worker 心跳正常" if fresh else "自动交卷 worker 心跳陈旧或缺失",
            checked_at,
            heartbeat_fresh=fresh,
        )

    def operational_lock() -> OperationalSignalRead:
        lock = db.get(OperationalLock, BACKUP_WRITE_FREEZE)
        active = is_lock_active(lock, now=checked_at)
        return _signal(
            "degraded" if active else "current",
            "配对备份写冻结生效中" if active else "当前无活动写冻结",
            checked_at,
            active=active,
            owner=lock.owner if active and lock is not None else None,
            expires_at=lock.expires_at.isoformat()
            if active and lock is not None
            else None,
        )

    def writer_fence() -> OperationalSignalRead:
        fence = db.get(OperationalLock, FORMAL_WRITER_FENCE)
        # Formal cutover fences are persistent.  ``expires_at`` is retained
        # for inspection/audit metadata and must not reopen writers.
        active = writer_fence_is_active(db, now=checked_at)
        return _signal(
            "degraded" if active else "current",
            "正式切换写栅栏生效中" if active else "当前无活动正式切换写栅栏",
            checked_at,
            active=active,
            dataset_id=fence.dataset_id if active and fence is not None else None,
            host_id=fence.host_id if active and fence is not None else None,
            writer_generation=(
                fence.writer_generation if active and fence is not None else None
            ),
            reason=fence.reason if active and fence is not None else None,
            expires_at=fence.expires_at.isoformat()
            if active and fence is not None
            else None,
        )

    def disk_reserve() -> OperationalSignalRead:
        reserve = get_storage_reserve(db)
        return _signal(
            "current" if reserve.sufficient else "degraded",
            "磁盘安全水位充足" if reserve.sufficient else "磁盘低于动态安全水位",
            checked_at,
            free_bytes=reserve.free_bytes,
            required_free_bytes=reserve.required_free_bytes,
            footprint_after_bytes=reserve.footprint_after_bytes,
        )

    def backup() -> OperationalSignalRead:
        rows = list_verified_backups(Path(settings.backup_storage_dir))
        if not rows:
            return _signal("failed", "尚无已验证配对备份", checked_at)
        path, manifest = rows[0]
        created_at = to_utc(datetime.fromisoformat(str(manifest["created_at"])))
        stale = (checked_at - created_at).total_seconds() > 48 * 60 * 60
        return _signal(
            "stale" if stale else "current",
            "最近备份超过 48 小时" if stale else "最近配对备份已验证",
            checked_at,
            backup_id=path.name,
            created_at=created_at.isoformat(),
            local_verified_count=len(rows),
        )

    def second_copy() -> OperationalSignalRead:
        latest = _latest_json(
            Path(settings.backup_storage_dir), f"backup-*{SECOND_COPY_EVIDENCE_SUFFIX}"
        )
        if latest is None:
            return _signal("skipped", "尚无第二副本同步记录", checked_at)
        path, payload = latest
        passed = payload.get("status") == "passed"
        return _signal(
            "current" if passed else "failed",
            "第二副本已验证" if passed else "第二副本不可用或未验证",
            checked_at,
            evidence_id=path.name,
            backup_id=payload.get("backup_id"),
        )

    def restore_drill() -> OperationalSignalRead:
        latest = _latest_json(
            Path(settings.operations_evidence_dir), "restore-drill-*.json"
        )
        if latest is None:
            return _signal("skipped", "尚无隔离恢复演练记录", checked_at)
        path, payload = latest
        passed = payload.get("status") == "passed"
        checked = payload.get("checkedAt")
        stale = False
        if passed and isinstance(checked, str):
            stale = (checked_at - to_utc(datetime.fromisoformat(checked))).days > 100
        status = "failed" if not passed else "stale" if stale else "current"
        return _signal(
            status,
            "隔离恢复演练通过" if status == "current" else "恢复演练需处理或更新",
            checked_at,
            evidence_id=path.name,
            backup_id=payload.get("backupId"),
        )

    def retention() -> OperationalSignalRead:
        preview = preview_retention(db, now=checked_at)
        eligible = sum(row.eligible for row in preview.exams)
        return _signal(
            "current",
            f"{eligible} 场考试等待人工归档确认" if eligible else "暂无到期考试",
            checked_at,
            eligible_exam_count=eligible,
            preview_fingerprint=preview.fingerprint,
        )

    def security_scan() -> OperationalSignalRead:
        latest = _latest_json(
            Path(settings.operations_evidence_dir), "security-scan-*.json"
        )
        if latest is None:
            return _signal("stale", "尚无安全扫描结果", checked_at)
        path, payload = latest
        status_value = str(payload.get("status", "failed"))
        status = "current" if status_value == "passed" else "failed"
        return _signal(
            status,
            "安全扫描通过" if status == "current" else "安全扫描存在阻断项",
            checked_at,
            evidence_id=path.name,
            blocking_count=payload.get("blocking_count"),
        )

    return OperationsSnapshotRead(
        checked_at=checked_at,
        version=_safe(checked_at, version),
        migration=_safe(checked_at, migration),
        service_health=_safe(checked_at, service_health),
        worker_health=_safe(checked_at, worker_health),
        operational_lock=_safe(checked_at, operational_lock),
        writer_fence=_safe(checked_at, writer_fence),
        disk_reserve=_safe(checked_at, disk_reserve),
        backup=_safe(checked_at, backup),
        second_copy=_safe(checked_at, second_copy),
        restore_drill=_safe(checked_at, restore_drill),
        retention=_safe(checked_at, retention),
        security_scan=_safe(checked_at, security_scan),
    )
