from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import MetaData, Table, func, inspect, literal, select

from app.core.time import to_utc
from app.models import OperationalLock
from app.ops.internal_backup import (
    BACKUP_KINDS,
    CUTOVER_BACKUP_KIND,
    BackupError,
    prune_verified_local_backups,
    validate_backup,
    validate_cutover_backup,
)
from app.services.audit_service import record_admin_event
from app.services.operational_lock_service import (
    BACKUP_WRITE_FREEZE,
    FormalAttemptWriteGateError,
    OperationalLockConflictError,
    WriterFenceActiveError,
    WriterFenceConflictError,
    acquire_backup_write_freeze,
    acquire_fenced_backup_write_freeze,
    is_lock_active,
    release_lock,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from sqlalchemy.orm import Session

DATA_TABLES = (
    "candidate",
    "question",
    "question_option",
    "exam",
    "exam_question_pool",
    "exam_candidate_scope",
    "exam_retake_grant",
    "exam_attempt",
    "exam_attempt_question",
    "exam_attempt_answer",
    "practice_answer",
    "learning_video",
    "learning_video_progress",
    # Audit/import metadata are formal dataset state too.  Keep operational
    # lock rows out intentionally: lock churn must not make opportunistic
    # backups perpetually look dirty.
    "admin_audit_event",
    "import_batch",
)
STATE_NAME = ".opportunistic-backup-state.json"


@dataclass(frozen=True)
class BackupRunResult:
    status: str
    reason: str
    backup_id: str | None
    data_fingerprint: str
    evidence_path: Path
    pruned_backup_ids: list[str]
    fence_boundary: dict[str, object] | None = None


def data_change_fingerprint(db: Session, media_root: Path) -> str:
    inspector = inspect(db.get_bind())
    snapshots: list[dict[str, object]] = []
    existing_tables = set(inspector.get_table_names())
    for table_name in DATA_TABLES:
        if table_name not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        timestamp_column = next(
            (
                name
                for name in ("updated_at", "practiced_at", "answered_at", "created_at")
                if name in columns
            ),
            None,
        )
        table = Table(table_name, MetaData(), autoload_with=db.get_bind())
        row = db.execute(
            select(
                func.count(),
                func.max(table.c.id) if "id" in columns else literal(None),
                func.max(table.c[timestamp_column])
                if timestamp_column
                else literal(None),
            ).select_from(table)
        ).one()
        snapshots.append(
            {
                "table": table_name,
                "count": int(row[0]),
                "max_id": row[1],
                "latest": str(row[2]) if row[2] is not None else None,
            }
        )
    media = (
        [
            {
                "path": path.relative_to(media_root).as_posix(),
                "size": path.stat().st_size,
                "modified_ns": path.stat().st_mtime_ns,
            }
            for path in sorted(media_root.rglob("*"))
            if path.is_file()
        ]
        if media_root.is_dir()
        else []
    )
    return hashlib.sha256(
        json.dumps(
            {"tables": snapshots, "media": media},
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _state_fingerprint(output_root: Path) -> str | None:
    path = output_root / STATE_NAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("data_fingerprint")
    return value if isinstance(value, str) else None


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_evidence(
    output_root: Path,
    *,
    now: datetime,
    status: str,
    reason: str,
    fingerprint: str,
    backup_id: str | None,
    fence_boundary: dict[str, object] | None = None,
) -> Path:
    evidence_path = (
        output_root
        / "evidence"
        / now.strftime("backup-opportunity-%Y%m%dT%H%M%SZ.json")
    )
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "paired-backup",
        "checked_at": now.isoformat(),
        "status": status,
        "reason": reason,
        "data_fingerprint": fingerprint,
        "backup_id": backup_id,
        "secrets": "excluded",
    }
    if fence_boundary is not None:
        payload["writer_fence_boundary"] = dict(fence_boundary)
    _write_json_atomic(evidence_path, payload)
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    evidence_path.with_suffix(".json.sha256").write_text(
        f"{digest}  {evidence_path.name}\n", encoding="ascii"
    )
    return evidence_path


def _fence_boundary(
    *,
    under_writer_fence: bool,
    dataset_id: str | None,
    host_id: str | None,
    writer_generation: int | None,
) -> dict[str, object] | None:
    supplied = (dataset_id, host_id, writer_generation)
    if any(value is not None for value in supplied) and not all(
        value is not None for value in supplied
    ):
        raise ValueError(
            "dataset_id, host_id, and writer_generation must be supplied together"
        )
    if not under_writer_fence:
        return None
    if all(value is None for value in supplied):
        raise ValueError(
            "under_writer_fence requires dataset_id, host_id, and writer_generation"
        )
    return {
        "dataset_id": dataset_id,
        "source_host_id": host_id,
        "writer_generation": writer_generation,
    }


def _validate_fence_boundary(
    backup_dir: Path, *, fence_boundary: dict[str, object]
) -> None:
    """Ensure a fenced backup artifact records the exact active boundary."""

    expected = {
        "dataset_id": fence_boundary["dataset_id"],
        "source_host_id": fence_boundary["source_host_id"],
        "writer_generation": fence_boundary["writer_generation"],
    }
    expected_generation = expected["writer_generation"]
    if isinstance(expected_generation, bool) or not isinstance(
        expected_generation, int
    ):
        raise BackupError("writer-fence boundary writer_generation 无效。")
    validate_cutover_backup(
        backup_dir,
        dataset_id=str(expected["dataset_id"]),
        source_host_id=str(expected["source_host_id"]),
        writer_generation=expected_generation,
    )


def _release_owned_backup_lock(db: Session, *, owner: str) -> None:
    """Release the explicit-owner backup lock without committing."""

    lock = db.get(OperationalLock, BACKUP_WRITE_FREEZE)
    if (
        is_lock_active(lock, now=datetime.now(UTC))
        and lock is not None
        and lock.owner == owner
    ):
        release_lock(db, name=BACKUP_WRITE_FREEZE, owner=owner)


def run_paired_backup(
    db: Session,
    *,
    output_root: Path,
    media_root: Path,
    create_backup: Callable[[str], Path],
    owner: str,
    opportunistic: bool,
    now: datetime | None = None,
    lock_ttl_seconds: int = 1800,
    fence_dataset_id: str | None = None,
    fence_host_id: str | None = None,
    fence_writer_generation: int | None = None,
    under_writer_fence: bool = False,
    backup_kind: str = "daily",
) -> BackupRunResult:
    if backup_kind not in BACKUP_KINDS:
        raise ValueError("backup_kind must be a supported paired-backup kind")
    if under_writer_fence != (backup_kind == CUTOVER_BACKUP_KIND):
        raise BackupError(
            "cutover final backup 必须同时使用 backup_kind=cutover 与 "
            "under_writer_fence。"
        )
    checked_at = to_utc(now or datetime.now(UTC))
    fence_boundary = _fence_boundary(
        under_writer_fence=under_writer_fence,
        dataset_id=fence_dataset_id,
        host_id=fence_host_id,
        writer_generation=fence_writer_generation,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    fingerprint = data_change_fingerprint(db, media_root)
    if opportunistic and _state_fingerprint(output_root) == fingerprint:
        evidence = _write_evidence(
            output_root,
            now=checked_at,
            status="skipped",
            reason="no-data-change",
            fingerprint=fingerprint,
            backup_id=None,
            fence_boundary=fence_boundary,
        )
        return BackupRunResult(
            "skipped",
            "no-data-change",
            None,
            fingerprint,
            evidence,
            [],
            fence_boundary,
        )

    try:
        if fence_boundary is None:
            acquire_backup_write_freeze(
                db, owner=owner, ttl_seconds=lock_ttl_seconds, now=checked_at
            )
        else:
            assert fence_dataset_id is not None
            assert fence_host_id is not None
            assert fence_writer_generation is not None
            acquire_fenced_backup_write_freeze(
                db,
                owner=owner,
                dataset_id=fence_dataset_id,
                host_id=fence_host_id,
                writer_generation=fence_writer_generation,
                ttl_seconds=lock_ttl_seconds,
                now=checked_at,
            )
        db.commit()
    except (
        FormalAttemptWriteGateError,
        OperationalLockConflictError,
        WriterFenceActiveError,
        WriterFenceConflictError,
    ) as exc:
        db.rollback()
        reason = (
            "formal-attempt-in-progress"
            if isinstance(exc, FormalAttemptWriteGateError)
            else "writer-fence-active"
            if isinstance(exc, WriterFenceActiveError)
            else "writer-fence-owner-mismatch"
            if isinstance(exc, WriterFenceConflictError)
            else "operational-lock-conflict"
        )
        evidence = _write_evidence(
            output_root,
            now=checked_at,
            status="skipped",
            reason=reason,
            fingerprint=fingerprint,
            backup_id=None,
            fence_boundary=fence_boundary,
        )
        # A writer fence also forbids the audit-row write.  The filesystem
        # evidence remains the safe, non-dataset skip signal; do not attempt a
        # second database write while the fence is active.
        if fence_boundary is None and not isinstance(exc, WriterFenceActiveError):
            record_admin_event(
                db,
                operator_subject=owner,
                action="paired_backup_skipped",
                target_type="backup",
                result="skipped",
                metadata={"reason_code": reason, "outcome_artifact": evidence.name},
            )
            db.commit()
        return BackupRunResult(
            "skipped",
            reason,
            None,
            fingerprint,
            evidence,
            [],
            fence_boundary,
        )

    backup_id: str | None = None
    status = "failed"
    reason = "backup-failed"
    pruned: list[str] = []
    caught_error: Exception | None = None
    try:
        locked_fingerprint = data_change_fingerprint(db, media_root)
        if opportunistic and _state_fingerprint(output_root) == locked_fingerprint:
            status = "skipped"
            reason = "no-data-change-after-lock"
            fingerprint = locked_fingerprint
        else:
            fingerprint = locked_fingerprint
            backup_dir = create_backup(fingerprint)
            if fence_boundary is not None:
                _validate_fence_boundary(
                    backup_dir,
                    fence_boundary=fence_boundary,
                )
            manifest = validate_backup(backup_dir)
            manifest_kind = manifest.get("backup_kind")
            if manifest_kind is not None and manifest_kind != backup_kind:
                raise BackupError(
                    "backup manifest 的 backup_kind 与本次 backup 请求不一致。"
                )
            backup_id = backup_dir.name
            pruned = prune_verified_local_backups(output_root, keep=3)
            status = "passed"
            reason = "verified"
    except (OSError, BackupError) as exc:
        caught_error = exc

    try:
        evidence = _write_evidence(
            output_root,
            now=checked_at,
            status=status,
            reason=reason,
            fingerprint=fingerprint,
            backup_id=backup_id,
            fence_boundary=fence_boundary,
        )
    except OSError:
        # Filesystem evidence is written while the lock is still held.  If
        # the evidence path is unavailable, do not strand the backup freeze.
        db.rollback()
        _release_owned_backup_lock(db, owner=owner)
        db.commit()
        raise
    if fence_boundary is None:
        try:
            # Release and audit in one transaction.  The advisory transaction
            # mutex acquired by release_lock remains held until this commit,
            # so a writer fence cannot become active in the gap between the
            # backup lock release and the audit-row write.
            _release_owned_backup_lock(db, owner=owner)
            record_admin_event(
                db,
                operator_subject=owner,
                action=f"paired_backup_{status}",
                target_type="backup",
                target_id=backup_id,
                result="success" if status == "passed" else status,
                metadata={"reason_code": reason, "outcome_artifact": evidence.name},
            )
            if status == "passed":
                # The audit row above is part of DATA_TABLES.  Advance the
                # opportunistic baseline after recording it, otherwise the
                # backup's own audit event would force an immediate duplicate
                # backup while external audit/import changes still invalidate
                # the baseline as intended.
                _write_json_atomic(
                    output_root / STATE_NAME,
                    {
                        "data_fingerprint": data_change_fingerprint(db, media_root),
                        "backup_id": backup_id,
                        "verified_at": checked_at.isoformat(),
                    },
                )
            db.commit()
        except WriterFenceActiveError:
            # A fence that was already active before the finalization phase
            # must still block the dataset audit write.  Roll back the local
            # release, then release only the backup freeze in a separate
            # transaction and leave a non-DB skipped evidence record.  This
            # keeps the fence fail-closed without reporting a passed audit.
            db.rollback()
            _release_owned_backup_lock(db, owner=owner)
            db.commit()
            if caught_error is None:
                status = "skipped"
                reason = "writer-fence-active-before-audit"
                evidence = _write_evidence(
                    output_root,
                    now=checked_at,
                    status=status,
                    reason=reason,
                    fingerprint=fingerprint,
                    backup_id=backup_id,
                    fence_boundary=fence_boundary,
                )
        except Exception:
            db.rollback()
            _release_owned_backup_lock(db, owner=owner)
            db.commit()
            raise
    else:
        try:
            if status == "passed":
                _write_json_atomic(
                    output_root / STATE_NAME,
                    {
                        "data_fingerprint": fingerprint,
                        "backup_id": backup_id,
                        "verified_at": checked_at.isoformat(),
                    },
                )
            _release_owned_backup_lock(db, owner=owner)
            db.commit()
        except Exception:
            db.rollback()
            _release_owned_backup_lock(db, owner=owner)
            db.commit()
            raise
    if caught_error is not None:
        raise caught_error
    return BackupRunResult(
        status,
        reason,
        backup_id,
        fingerprint,
        evidence,
        pruned,
        fence_boundary,
    )
