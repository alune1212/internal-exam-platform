from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.time import to_utc
from app.models import ExamAttempt, OperationalLock
from app.ops.internal_backup import BackupError, validate_cutover_backup

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.orm import Session

BACKUP_WRITE_FREEZE = "backup-write-freeze"
FORMAL_WRITER_FENCE = "formal-writer-fence"
FORMAL_WRITE_GATE_ADVISORY_KEY = 4_981_031_177
_FENCE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
_FENCE_REASON_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{1,500}$")


class OperationalLockConflictError(DomainError):
    status_code = 409

    def __init__(self, detail: str = "系统正在执行受保护运维，请稍后重试。") -> None:
        super().__init__(detail)


class FormalAttemptWriteGateError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("正式考试正在进行，当前管理操作已暂停。")


class WriterFenceActiveError(DomainError):
    """Raised when a formal cutover writer fence is active."""

    status_code = 409

    def __init__(self, fence: OperationalLock | None = None) -> None:
        details = ""
        if fence is not None:
            identity = []
            if fence.dataset_id:
                identity.append(f"datasetId={fence.dataset_id}")
            if fence.host_id:
                identity.append(f"hostId={fence.host_id}")
            if fence.writer_generation is not None:
                identity.append(f"writerGeneration={fence.writer_generation}")
            if fence.reason:
                identity.append(f"reason={fence.reason}")
            if identity:
                details = "（" + ", ".join(identity) + "）"
        super().__init__(f"正式切换写栅栏生效，当前写入已暂停{details}。")


class WriterFenceConflictError(DomainError):
    """Raised when a host attempts an unsafe fence transition."""

    status_code = 409

    def __init__(self, detail: str = "正式切换写栅栏状态冲突。") -> None:
        super().__init__(detail)


def _acquire_transaction_mutex(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": FORMAL_WRITE_GATE_ADVISORY_KEY},
        )


def _locked_row(db: Session, name: str) -> OperationalLock | None:
    return db.get(OperationalLock, name, with_for_update=True)


def is_lock_active(lock: OperationalLock | None, *, now: datetime) -> bool:
    """Return whether the backup write-freeze remains explicitly held.

    ``expires_at`` is retained for operator diagnostics and stale-lock
    recovery decisions.  It is not an automatic release boundary: a database
    dump or media archive has no reliable upper bound, so reopening writers at
    the TTL would corrupt the paired-backup consistency boundary.
    """

    _ = now
    return bool(lock is not None and lock.released_at is None)


def _formal_write_environment() -> bool:
    """Return whether persistent formal write fencing is enforced.

    Development and test sessions intentionally retain the existing behavior;
    internal/production containers are the only profiles that reject writes
    while a fence is active.
    """

    return settings.environment in {"internal", "production", "formal"}


def _required_fence_identifier(value: str, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or _FENCE_IDENTIFIER_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(f"{field_name} must be a bounded identifier")
    return value


def _required_fence_generation(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("writer_generation must be a positive integer")
    return value


def _required_fence_reason(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or _FENCE_REASON_PATTERN.fullmatch(value) is None
    ):
        raise ValueError("reason must be a bounded non-empty string")
    return value


def _validate_fence_ttl(ttl_seconds: int) -> None:
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
        raise ValueError("ttl_seconds must be an integer")
    if ttl_seconds < 1:
        raise ValueError("ttl_seconds must be positive")


def _writer_fence_row(
    db: Session, *, for_update: bool = False
) -> OperationalLock | None:
    if for_update:
        return _locked_row(db, FORMAL_WRITER_FENCE)
    return db.get(OperationalLock, FORMAL_WRITER_FENCE)


def _assert_writer_fence_clear_locked(db: Session, *, now: datetime) -> None:
    if not _formal_write_environment():
        return
    fence = _writer_fence_row(db, for_update=True)
    # ``expires_at`` is retained as operational metadata, but it is not a
    # release mechanism for a formal cutover fence.  A source host may not
    # silently reopen writers just because its clock/TTL elapsed.
    _ = now
    if fence is not None and fence.released_at is None:
        raise WriterFenceActiveError(fence)


def writer_fence_is_active(db: Session, *, now: datetime | None = None) -> bool:
    """Return whether the DB-backed formal writer fence is currently active."""

    # Like the backup write-freeze, a formal cutover fence is a durable
    # hand-off state.  A clock/TTL rollover must never reopen writers; only an
    # explicit release or source-authenticated transfer can clear it.
    _ = now
    fence = _writer_fence_row(db)
    return bool(fence is not None and fence.released_at is None)


def inspect_writer_fence(
    db: Session, *, now: datetime | None = None
) -> dict[str, object]:
    """Return a stable, non-secret writer-fence inspection payload."""

    checked_at = now or datetime.now(UTC)
    fence = _writer_fence_row(db)
    active = bool(fence is not None and fence.released_at is None)
    return {
        "name": FORMAL_WRITER_FENCE,
        "active": active,
        "enforced": _formal_write_environment(),
        "datasetId": fence.dataset_id if fence is not None else None,
        "dataset_id": fence.dataset_id if fence is not None else None,
        "hostId": fence.host_id if fence is not None else None,
        "host_id": fence.host_id if fence is not None else None,
        "writerGeneration": (fence.writer_generation if fence is not None else None),
        "writer_generation": (fence.writer_generation if fence is not None else None),
        "reason": fence.reason if fence is not None else None,
        "acquiredAt": (
            to_utc(fence.acquired_at).isoformat() if fence is not None else None
        ),
        "expiresAt": (
            to_utc(fence.expires_at).isoformat() if fence is not None else None
        ),
        "releasedAt": (
            to_utc(fence.released_at).isoformat()
            if fence is not None and fence.released_at is not None
            else None
        ),
        "checkedAt": to_utc(checked_at).isoformat(),
    }


def acquire_writer_fence(
    db: Session,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
    reason: str,
    ttl_seconds: int = 3600,
    now: datetime | None = None,
) -> OperationalLock:
    """Atomically acquire or renew the persistent formal writer fence.

    The existing PostgreSQL advisory transaction mutex and row lock serialize
    this operation with every guarded writer and reject a normal backup until
    its write-freeze is explicitly released.  Backup expiry is not proof that
    an unbounded pg_dump/media archive has stopped; a generation may only move
    forward, preventing an old host wrapper from re-acquiring a stale fence.
    """

    dataset_id = _required_fence_identifier(dataset_id, "dataset_id")
    host_id = _required_fence_identifier(host_id, "host_id")
    writer_generation = _required_fence_generation(writer_generation)
    reason = _required_fence_reason(reason)
    _validate_fence_ttl(ttl_seconds)

    acquired_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    backup_lock = _locked_row(db, BACKUP_WRITE_FREEZE)
    # A normal backup can legitimately run longer than its advisory TTL.  The
    # owner releases this row only after the artifact and audit transaction are
    # complete, so treating expiry as permission to cut over would allow a
    # writer fence to overlap an in-flight dump.  Fail closed until an explicit
    # release (or a separately audited recovery action) closes the boundary.
    if backup_lock is not None and backup_lock.released_at is None:
        raise WriterFenceConflictError(
            "backup-write-freeze 尚未显式释放，正式切换写栅栏暂不可获取。"
        )
    fence = _writer_fence_row(db, for_update=True)
    if fence is not None and fence.released_at is None:
        same_identity = bool(
            fence is not None
            and fence.dataset_id == dataset_id
            and fence.host_id == host_id
            and fence.writer_generation == writer_generation
        )
        if same_identity:
            return fence
        raise WriterFenceConflictError("已有其他正式切换写栅栏生效中。")

    if fence is not None:
        same_released_writer = bool(
            fence.dataset_id == dataset_id
            and fence.host_id == host_id
            and fence.owner == host_id
            and writer_generation == fence.writer_generation
        )
        if not same_released_writer:
            # Ordinary acquire never advances ownership.  A released target
            # row records the accepted writer; every different host or
            # generation must arrive through source-authenticated transfer.
            raise WriterFenceConflictError(
                "released writer-fence 仅允许 accepted host 使用当前 generation "
                "重新 acquire；跨 host/generation 必须通过 transfer。"
            )

    expires_at = acquired_at + timedelta(seconds=ttl_seconds)
    if fence is None:
        fence = OperationalLock(
            name=FORMAL_WRITER_FENCE,
            owner=host_id,
            acquired_at=acquired_at,
            expires_at=expires_at,
            released_at=None,
            updated_at=acquired_at,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
            reason=reason,
        )
        db.add(fence)
    else:
        fence.owner = host_id
        fence.acquired_at = acquired_at
        fence.expires_at = expires_at
        fence.released_at = None
        fence.updated_at = acquired_at
        fence.dataset_id = dataset_id
        fence.host_id = host_id
        fence.writer_generation = writer_generation
        fence.reason = reason
    db.flush()
    return fence


def _assert_writer_fence_owner_locked(
    db: Session,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
) -> OperationalLock:
    """Require the exact active fence identity for a controlled operation.

    This helper intentionally does not consult ``settings.environment``.  A
    caller asking for the exceptional final-backup path must prove that a
    durable fence exists and belongs to the supplied host/dataset/generation;
    it can never turn an unfenced generic backup into an owner operation.
    """

    dataset_id = _required_fence_identifier(dataset_id, "dataset_id")
    host_id = _required_fence_identifier(host_id, "host_id")
    writer_generation = _required_fence_generation(writer_generation)
    fence = _writer_fence_row(db, for_update=True)
    if (
        fence is None
        or fence.released_at is not None
        or fence.owner != host_id
        or fence.host_id != host_id
        or fence.dataset_id != dataset_id
        or fence.writer_generation != writer_generation
    ):
        raise WriterFenceConflictError(
            "final backup 必须绑定当前活动的 dataset/host/writerGeneration。"
        )
    return fence


def assert_writer_fence_owner(
    db: Session,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
) -> OperationalLock:
    """Return the exact active fence row for a controlled cutover operation."""

    _acquire_transaction_mutex(db)
    return _assert_writer_fence_owner_locked(
        db,
        dataset_id=dataset_id,
        host_id=host_id,
        writer_generation=writer_generation,
    )


assert_formal_writer_fence_owner = assert_writer_fence_owner


def transfer_writer_fence(
    db: Session,
    *,
    dataset_id: str,
    source_host_id: str,
    source_writer_generation: int,
    target_host_id: str,
    target_writer_generation: int,
    reason: str,
    ttl_seconds: int = 3600,
    now: datetime | None = None,
    restored_cutover_backup: str | Path | None = None,
) -> OperationalLock:
    """Atomically accept a persistent fence on a restored target host.

    The source identity and the exact next generation are checked while the
    shared row is locked.  Updating owner/host/generation in that same
    transaction means a source host can neither release nor reacquire the
    target fence after this call succeeds.
    """

    dataset_id = _required_fence_identifier(dataset_id, "dataset_id")
    source_host_id = _required_fence_identifier(source_host_id, "source_host_id")
    target_host_id = _required_fence_identifier(target_host_id, "target_host_id")
    source_writer_generation = _required_fence_generation(source_writer_generation)
    target_writer_generation = _required_fence_generation(target_writer_generation)
    reason = _required_fence_reason(reason)
    _validate_fence_ttl(ttl_seconds)
    if source_host_id == target_host_id:
        raise WriterFenceConflictError("sourceHostId 与 targetHostId 必须不同。")
    if target_writer_generation != source_writer_generation + 1:
        raise WriterFenceConflictError(
            "targetWriterGeneration 必须是 sourceWriterGeneration 的下一个 generation。"
        )

    transferred_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    fence = _writer_fence_row(db, for_update=True)
    if (
        fence is None
        or fence.released_at is not None
        or fence.owner != source_host_id
        or fence.host_id != source_host_id
        or fence.dataset_id != dataset_id
        or fence.writer_generation != source_writer_generation
    ):
        raise WriterFenceConflictError(
            "source dataset/host/writerGeneration 与当前活动写栅栏不匹配。"
        )
    # A final backup is the source boundary being handed off.  A PostgreSQL
    # dump made after the backup freeze is committed can restore that lock row
    # with ``released_at=NULL`` on the target.  Only a completed, checksummed
    # cutover artifact with the exact source identity can prove that this is a
    # restored snapshot rather than a live in-flight source.  The row is
    # released and the fence owner is transferred in this same transaction.
    backup_lock = _locked_row(db, BACKUP_WRITE_FREEZE)
    if backup_lock is not None and backup_lock.released_at is None:
        if restored_cutover_backup is None:
            raise WriterFenceConflictError(
                "恢复目标仍有未释放 backup-write-freeze，必须提供"
                " --restored-cutover-backup；live source 无法绕过。"
            )
        try:
            validate_cutover_backup(
                restored_cutover_backup,
                dataset_id=dataset_id,
                source_host_id=source_host_id,
                writer_generation=source_writer_generation,
            )
        except (BackupError, OSError, ValueError) as exc:
            raise WriterFenceConflictError(
                "restored cutover backup 未通过 SUCCESS/checksum/cutover identity 校验。"
            ) from exc
        backup_lock.released_at = transferred_at
        backup_lock.updated_at = transferred_at

    fence.owner = target_host_id
    fence.host_id = target_host_id
    fence.writer_generation = target_writer_generation
    fence.reason = reason
    fence.acquired_at = transferred_at
    fence.expires_at = transferred_at + timedelta(seconds=ttl_seconds)
    fence.released_at = None
    fence.updated_at = transferred_at
    db.flush()
    return fence


# Host adapters historically used both names; they intentionally share the
# same atomic implementation rather than introducing a second transition.


def release_writer_fence(
    db: Session,
    *,
    host_id: str,
    dataset_id: str | None = None,
    writer_generation: int | None = None,
    now: datetime | None = None,
) -> OperationalLock:
    """Atomically release a fence owned by the expected host/generation."""

    host_id = _required_fence_identifier(host_id, "host_id")
    if dataset_id is not None:
        dataset_id = _required_fence_identifier(dataset_id, "dataset_id")
    if writer_generation is not None:
        writer_generation = _required_fence_generation(writer_generation)

    released_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    fence = _writer_fence_row(db, for_update=True)
    if (
        fence is None
        or fence.owner != host_id
        or fence.released_at is not None
        or (dataset_id is not None and fence.dataset_id != dataset_id)
        or (
            writer_generation is not None
            and fence.writer_generation != writer_generation
        )
    ):
        raise WriterFenceConflictError(
            "写栅栏不存在、已释放、或不属于当前 host/generation。"
        )
    fence.released_at = released_at
    fence.updated_at = released_at
    db.flush()
    return fence


def acquire_lock(
    db: Session,
    *,
    name: str,
    owner: str,
    ttl_seconds: int,
    now: datetime | None = None,
) -> OperationalLock:
    if not name.strip() or not owner.strip() or ttl_seconds < 1:
        raise ValueError("Operational lock name, owner, and TTL are required.")
    acquired_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    lock = _locked_row(db, name)
    if is_lock_active(lock, now=acquired_at):
        if lock is not None and lock.owner == owner:
            return lock
        raise OperationalLockConflictError()

    expires_at = acquired_at + timedelta(seconds=ttl_seconds)
    if lock is None:
        lock = OperationalLock(
            name=name,
            owner=owner,
            acquired_at=acquired_at,
            expires_at=expires_at,
            released_at=None,
            updated_at=acquired_at,
        )
        db.add(lock)
    else:
        lock.owner = owner
        lock.acquired_at = acquired_at
        lock.expires_at = expires_at
        lock.released_at = None
        lock.updated_at = acquired_at
    db.flush()
    return lock


def release_lock(
    db: Session,
    *,
    name: str,
    owner: str,
    now: datetime | None = None,
) -> OperationalLock:
    released_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    lock = _locked_row(db, name)
    if lock is None or lock.owner != owner or lock.released_at is not None:
        raise OperationalLockConflictError("运维锁不存在、已释放或不属于当前 owner。")
    lock.released_at = released_at
    lock.updated_at = released_at
    db.flush()
    return lock


def assert_writer_fence_clear(db: Session, *, now: datetime | None = None) -> None:
    """Fail closed for formal/internal writes while cutover is fenced."""

    checked_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    _assert_writer_fence_clear_locked(db, now=checked_at)


# Compatibility names for host adapters and service callers.


def assert_backup_write_allowed(db: Session, *, now: datetime | None = None) -> None:
    checked_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    _assert_writer_fence_clear_locked(db, now=checked_at)
    lock = _locked_row(db, BACKUP_WRITE_FREEZE)
    if is_lock_active(lock, now=checked_at):
        raise OperationalLockConflictError("系统正在创建配对备份，请稍后重试。")


def count_in_progress_attempts(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(ExamAttempt.id)).where(
                ExamAttempt.status == "in_progress"
            )
        )
        or 0
    )


def assert_admin_mutation_allowed(db: Session) -> None:
    assert_backup_write_allowed(db)
    if count_in_progress_attempts(db):
        raise FormalAttemptWriteGateError()


def acquire_backup_write_freeze(
    db: Session,
    *,
    owner: str,
    ttl_seconds: int,
    now: datetime | None = None,
) -> OperationalLock:
    checked_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    _assert_writer_fence_clear_locked(db, now=checked_at)
    if count_in_progress_attempts(db):
        raise FormalAttemptWriteGateError()
    return acquire_lock(
        db,
        name=BACKUP_WRITE_FREEZE,
        owner=owner,
        ttl_seconds=ttl_seconds,
        now=checked_at,
    )


def acquire_fenced_backup_write_freeze(
    db: Session,
    *,
    owner: str,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
    ttl_seconds: int,
    now: datetime | None = None,
) -> OperationalLock:
    """Acquire the explicit-release backup lock under an active writer fence.

    This is the sole exception to the normal rule that a formal fence blocks
    backup acquisition.  The caller must provide the fence identity, and the
    row check and backup-lock acquisition share the PostgreSQL advisory
    transaction mutex.  All application/business writers still call
    ``assert_backup_write_allowed`` without an identity and remain blocked.
    """

    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("backup owner is required")
    _validate_fence_ttl(ttl_seconds)
    checked_at = now or datetime.now(UTC)
    _acquire_transaction_mutex(db)
    _assert_writer_fence_owner_locked(
        db,
        dataset_id=dataset_id,
        host_id=host_id,
        writer_generation=writer_generation,
    )
    if count_in_progress_attempts(db):
        raise FormalAttemptWriteGateError()
    return acquire_lock(
        db,
        name=BACKUP_WRITE_FREEZE,
        owner=owner,
        ttl_seconds=ttl_seconds,
        now=checked_at,
    )


# Descriptive compatibility name for host wrappers.
