"""One-shot operational-lock commands for Windows backup orchestration."""

from __future__ import annotations

import argparse
import json
import sys

from app.core.database import SessionLocal
from app.services.operational_lock_service import (
    BACKUP_WRITE_FREEZE,
    FormalAttemptWriteGateError,
    OperationalLockConflictError,
    WriterFenceConflictError,
    acquire_backup_write_freeze,
    acquire_writer_fence,
    inspect_writer_fence,
    release_lock,
    release_writer_fence,
    transfer_writer_fence,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coordinated operational lock")
    subparsers = parser.add_subparsers(dest="action", required=True)
    acquire = subparsers.add_parser("acquire-backup")
    acquire.add_argument("--owner", required=True)
    acquire.add_argument("--ttl-seconds", type=int, default=1800)
    release = subparsers.add_parser("release-backup")
    release.add_argument("--owner", required=True)

    acquire_fence = subparsers.add_parser(
        "acquire-fence",
        aliases=("writer-fence-acquire", "fence-acquire", "acquire"),
        help="Acquire the persistent formal cutover writer fence",
    )
    acquire_fence.add_argument("--dataset-id", "--datasetId", required=True)
    acquire_fence.add_argument("--host-id", "--hostId", required=True)
    acquire_fence.add_argument(
        "--writer-generation", "--writerGeneration", type=int, required=True
    )
    acquire_fence.add_argument("--reason", required=True)
    acquire_fence.add_argument("--ttl-seconds", "--ttl", type=int, default=3600)

    release_fence = subparsers.add_parser(
        "release-fence",
        aliases=("writer-fence-release", "fence-release", "release"),
        help="Release the persistent formal cutover writer fence",
    )
    release_fence.add_argument("--host-id", "--hostId", required=True)
    release_fence.add_argument("--dataset-id", "--datasetId", required=True)
    release_fence.add_argument(
        "--writer-generation", "--writerGeneration", type=int, required=True
    )

    transfer_fence = subparsers.add_parser(
        "transfer-fence",
        aliases=(
            "accept-fence",
            "writer-fence-transfer",
            "fence-transfer",
            "transfer",
            "accept",
        ),
        help="Atomically accept the persistent fence on a restored target host",
    )
    transfer_fence.add_argument("--dataset-id", "--datasetId", required=True)
    transfer_fence.add_argument("--source-host-id", "--sourceHostId", required=True)
    transfer_fence.add_argument(
        "--source-writer-generation",
        "--sourceWriterGeneration",
        type=int,
        required=True,
    )
    transfer_fence.add_argument("--target-host-id", "--targetHostId", required=True)
    transfer_fence.add_argument(
        "--target-writer-generation",
        "--targetWriterGeneration",
        type=int,
        required=True,
    )
    transfer_fence.add_argument("--reason", required=True)
    transfer_fence.add_argument("--ttl-seconds", "--ttl", type=int, default=3600)
    transfer_fence.add_argument(
        "--restored-cutover-backup",
        "--restoredCutoverBackup",
        help=(
            "Verified cutover backup directory restored with the target DB; "
            "required when backup-write-freeze was restored unreleased"
        ),
    )

    subparsers.add_parser(
        "inspect-fence",
        aliases=("writer-fence-inspect", "fence-inspect", "inspect"),
        help="Inspect the persistent formal cutover writer fence",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        with SessionLocal() as db:
            if args.action == "acquire-backup":
                lock = acquire_backup_write_freeze(
                    db, owner=args.owner, ttl_seconds=args.ttl_seconds
                )
                action = "acquired"
            elif args.action == "release-backup":
                lock = release_lock(
                    db,
                    name=BACKUP_WRITE_FREEZE,
                    owner=args.owner,
                )
                action = "released"
            elif args.action in {
                "acquire-fence",
                "writer-fence-acquire",
                "fence-acquire",
                "acquire",
            }:
                lock = acquire_writer_fence(
                    db,
                    dataset_id=args.dataset_id,
                    host_id=args.host_id,
                    writer_generation=args.writer_generation,
                    reason=args.reason,
                    ttl_seconds=args.ttl_seconds,
                )
                action = "acquired"
            elif args.action in {
                "release-fence",
                "writer-fence-release",
                "fence-release",
                "release",
            }:
                lock = release_writer_fence(
                    db,
                    host_id=args.host_id,
                    dataset_id=args.dataset_id,
                    writer_generation=args.writer_generation,
                )
                action = "released"
            elif args.action in {
                "transfer-fence",
                "accept-fence",
                "writer-fence-transfer",
                "fence-transfer",
                "transfer",
                "accept",
            }:
                lock = transfer_writer_fence(
                    db,
                    dataset_id=args.dataset_id,
                    source_host_id=args.source_host_id,
                    source_writer_generation=args.source_writer_generation,
                    target_host_id=args.target_host_id,
                    target_writer_generation=args.target_writer_generation,
                    reason=args.reason,
                    ttl_seconds=args.ttl_seconds,
                    restored_cutover_backup=args.restored_cutover_backup,
                )
                action = "transferred"
            else:
                result = inspect_writer_fence(db)
                result.update({"status": "passed", "action": "inspected"})
                db.rollback()
                sys.stdout.write(
                    json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n"
                )
                return 0
            db.commit()
            result: dict[str, object] = {
                "status": "passed",
                "action": action,
                "name": lock.name,
                "owner": lock.owner,
                "expires_at": lock.expires_at.isoformat(),
                "expiresAt": lock.expires_at.isoformat(),
            }
            if lock.name == "formal-writer-fence":
                result.update(
                    {
                        "active": action in {"acquired", "transferred"},
                        "datasetId": lock.dataset_id,
                        "dataset_id": lock.dataset_id,
                        "hostId": lock.host_id,
                        "host_id": lock.host_id,
                        "writerGeneration": lock.writer_generation,
                        "writer_generation": lock.writer_generation,
                        "reason": lock.reason,
                        "releasedAt": (
                            lock.released_at.isoformat()
                            if lock.released_at is not None
                            else None
                        ),
                    }
                )
    except (
        FormalAttemptWriteGateError,
        OperationalLockConflictError,
        WriterFenceConflictError,
        ValueError,
    ) as exc:
        sys.stderr.write(f"operational_lock_skipped error={type(exc).__name__}\n")
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
