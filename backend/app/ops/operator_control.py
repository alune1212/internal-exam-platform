"""Containerized audit helpers for protected local Windows operations."""

from __future__ import annotations

import argparse
import sys

from app.core.database import SessionLocal
from app.services.audit_service import record_admin_event
from app.services.session_control_service import get_session_closure_readiness


def check_session_closure() -> int:
    with SessionLocal() as db:
        readiness = get_session_closure_readiness(db)
    if not readiness.ready:
        sys.stderr.write(
            "session_closure_blocked "
            f"in_progress={readiness.in_progress_attempt_count}\n"
        )
        return 1
    sys.stdout.write("session_closure_ready in_progress=0\n")
    return 0


def record_local_operation(
    *, operator_subject: str, action: str, target_id: str, enabled: bool | None
) -> int:
    metadata = {"operator_enabled": enabled} if enabled is not None else {}
    with SessionLocal() as db:
        record_admin_event(
            db,
            operator_subject=operator_subject,
            action=action,
            target_type="operator" if enabled is not None else "session",
            target_id=target_id,
            metadata=metadata,
        )
        db.commit()
    sys.stdout.write(f"audit_recorded action={action}\n")
    return 0


def record_lifecycle_operation(
    *, operator_subject: str, action: str, target_id: str, artifact: str
) -> int:
    allowed_actions = {"restore_drill_completed", "second_copy_sync_completed"}
    if action not in allowed_actions:
        raise ValueError("Unsupported lifecycle audit action.")
    with SessionLocal() as db:
        record_admin_event(
            db,
            operator_subject=operator_subject,
            action=action,
            target_type="lifecycle",
            target_id=target_id,
            metadata={"outcome_artifact": artifact},
        )
        db.commit()
    sys.stdout.write(f"audit_recorded action={action}\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Protected local operator controls")
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("check-session-closure")

    backup_parser = subparsers.add_parser("record-backup-operator")
    backup_parser.add_argument("--operator-subject", required=True)
    backup_parser.add_argument("--target", required=True)
    backup_parser.add_argument("--enabled", choices=("true", "false"), required=True)

    close_parser = subparsers.add_parser("record-session-closure")
    close_parser.add_argument("--operator-subject", required=True)

    lifecycle_parser = subparsers.add_parser("record-lifecycle")
    lifecycle_parser.add_argument(
        "--lifecycle-action",
        choices=("restore_drill_completed", "second_copy_sync_completed"),
        required=True,
    )
    lifecycle_parser.add_argument("--operator-subject", required=True)
    lifecycle_parser.add_argument("--target", required=True)
    lifecycle_parser.add_argument("--artifact", required=True)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.action == "check-session-closure":
        return check_session_closure()
    if args.action == "record-backup-operator":
        return record_local_operation(
            operator_subject=args.operator_subject,
            action="backup_operator_access_changed",
            target_id=args.target,
            enabled=args.enabled == "true",
        )
    if args.action == "record-lifecycle":
        return record_lifecycle_operation(
            operator_subject=args.operator_subject,
            action=args.lifecycle_action,
            target_id=args.target,
            artifact=args.artifact,
        )
    return record_local_operation(
        operator_subject=args.operator_subject,
        action="all_sessions_closed",
        target_id="global",
        enabled=None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
