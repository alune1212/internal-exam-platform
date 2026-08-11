import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.auto_submit_worker import write_heartbeat
from app.core.config import settings
from app.ops import internal_backup
from app.services import operations_service


def _verified_backup(directory: Path) -> None:
    directory.mkdir(parents=True)
    (directory / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"database")
    (directory / internal_backup.MEDIA_ARCHIVE_NAME).write_bytes(b"media")
    internal_backup.finalize_backup(
        directory,
        {
            "format_version": 1,
            "created_at": "2026-07-21T08:00:00+00:00",
            "migration_head": "202607210001",
            "table_counts": dict.fromkeys(internal_backup.TABLE_NAMES, 0),
            "media_file_count": 0,
        },
    )


def test_operations_snapshot_keeps_distinct_current_and_partial_states(
    db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checked_at = datetime(2026, 7, 21, 9, tzinfo=UTC)
    Path(settings.learning_media_storage_dir).mkdir(parents=True, exist_ok=True)
    backup_root = tmp_path / "backups"
    evidence_root = tmp_path / "evidence"
    backup = backup_root / "backup-20260721T080000Z"
    _verified_backup(backup)
    (
        backup_root / f"{backup.name}{internal_backup.SECOND_COPY_EVIDENCE_SUFFIX}"
    ).write_text(
        json.dumps({"status": "passed", "backup_id": backup.name}), encoding="utf-8"
    )
    evidence_root.mkdir()
    (evidence_root / "restore-drill-20260721T083000Z.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "checkedAt": "2026-07-21T08:30:00+00:00",
                "backupId": backup.name,
            }
        ),
        encoding="utf-8",
    )
    (evidence_root / "security-scan-20260721T083500Z.json").write_text(
        json.dumps({"status": "passed", "blocking_count": 0}), encoding="utf-8"
    )
    heartbeat = tmp_path / "worker.heartbeat"
    write_heartbeat(heartbeat, now=checked_at)
    monkeypatch.setattr(settings, "backup_storage_dir", str(backup_root))
    monkeypatch.setattr(settings, "operations_evidence_dir", str(evidence_root))
    monkeypatch.setattr(settings, "auto_submit_heartbeat_path", str(heartbeat))
    monkeypatch.setattr(settings, "git_commit", "a" * 40)
    monkeypatch.setattr(
        operations_service,
        "get_storage_reserve",
        lambda _db: SimpleNamespace(
            sufficient=True,
            free_bytes=100,
            required_free_bytes=20,
            footprint_after_bytes=10,
        ),
    )

    snapshot = operations_service.get_operations_snapshot(db, now=checked_at)

    assert snapshot.version.status == "current"
    assert snapshot.migration.status == "failed"
    assert snapshot.service_health.status == "current"
    assert snapshot.worker_health.status == "current"
    assert snapshot.operational_lock.status == "current"
    assert snapshot.disk_reserve.status == "current"
    assert snapshot.backup.status == "current"
    assert snapshot.second_copy.status == "current"
    assert snapshot.restore_drill.status == "current"
    assert snapshot.retention.status == "current"
    assert snapshot.security_scan.status == "current"


def test_operations_snapshot_does_not_collapse_when_one_signal_fails(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        operations_service,
        "check_readiness",
        lambda _db: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    monkeypatch.setattr(
        operations_service,
        "get_storage_reserve",
        lambda _db: SimpleNamespace(
            sufficient=False,
            free_bytes=1,
            required_free_bytes=20,
            footprint_after_bytes=10,
        ),
    )

    snapshot = operations_service.get_operations_snapshot(db)

    assert snapshot.service_health.status == "failed"
    assert snapshot.disk_reserve.status == "degraded"
    assert snapshot.operational_lock.status == "current"
