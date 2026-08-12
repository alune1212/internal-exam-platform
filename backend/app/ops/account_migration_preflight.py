"""Read-only preflight checks for the email-account migration.

The migration is intentionally destructive after the roster snapshots are
backfilled.  This module therefore operates on reflected tables rather than
the current ORM models: it can inspect the legacy schema before the new
columns exist and it cannot accidentally issue an UPDATE while reporting a
blocker.  The command prints counts, ids, and redacted email hints only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import MetaData, Table, inspect, select, text

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.engine import Connection, Engine
    from sqlalchemy.orm import Session


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENTINEL_NAME = "__candidate_login_sentinel__"
ALLOWED_STATUSES = frozenset({"pending", "active", "inactive"})
FORMAL_ATTEMPT_STATUSES = frozenset({"in_progress"})
# Keep the account-migration mutex named and local to this operational path.
# It intentionally uses the same PostgreSQL transaction-lock key as the
# existing writer/backup gate so the first migration SQL serializes with all
# guarded writers before the read-only checks or any DDL run.
ACCOUNT_MIGRATION_ADVISORY_KEY = 4_981_031_177
EVIDENCE_MAX_AGE = timedelta(days=7)
CLOCK_SKEW = timedelta(minutes=5)
LEGACY_SENTINEL_NULL_FIELDS = (
    "employee_no",
    "phone_suffix",
    "department",
    "position",
    "exam_group",
    "remark",
)
# Runtime tables that persist a direct Candidate foreign key.  A sentinel
# subject in any of these tables is historical-data contamination and must
# block the destructive migration.  ``candidate_login_challenge`` is
# deliberately excluded: its sentinel rows represent unknown-login attempts
# and are expired/deleted inside the migration boundary after preflight.
SENTINEL_REFERENCE_TABLES = (
    "exam_candidate_scope",
    "exam_attempt",
    "exam_retake_grant",
    "practice_answer",
    "learning_video_progress",
)


@dataclass(frozen=True)
class MigrationFinding:
    """One redacted, operator-actionable migration blocker."""

    code: str
    table: str
    row_ids: tuple[int, ...] = ()
    detail: str = ""
    email_hints: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MigrationPreflightReport:
    """Stable JSON-safe result consumed by maintenance wrappers and tests."""

    status: str
    checked_at: str
    counts: dict[str, int]
    findings: tuple[MigrationFinding, ...]

    @property
    def can_migrate(self) -> bool:
        return self.status == "passed" and not self.findings

    @property
    def blocked(self) -> bool:
        return not self.can_migrate

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "can_migrate": self.can_migrate,
            "checked_at": self.checked_at,
            "counts": dict(self.counts),
            "findings": [finding.as_dict() for finding in self.findings],
        }

    def redacted_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=True, sort_keys=True)


def redact_email(value: str | None) -> str | None:
    """Return a stable hint without exposing a local-part or full address."""

    if value is None:
        return None
    normalized = value.strip().casefold()
    if "@" not in normalized:
        return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()[:12]}"
    _, domain = normalized.rsplit("@", 1)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"sha256:{digest}@{domain}"


def _source_bind(source: Session | Connection | Engine) -> Connection | Engine:
    if hasattr(source, "get_bind"):
        return cast("Connection | Engine", cast("Any", source).get_bind())
    return source


def _run_select(
    source: Session | Connection | Engine,
    statement: Any,
) -> list[dict[str, Any]]:
    """Execute a SELECT without creating a transaction that can write."""

    if hasattr(source, "execute") and not hasattr(source, "connect"):
        result = cast("Any", source).execute(statement)
        return [dict(row) for row in result.mappings().all()]
    if hasattr(source, "get_bind"):
        result = cast("Any", source).execute(statement)
        return [dict(row) for row in result.mappings().all()]
    with cast("Any", source).connect() as connection:
        result = connection.execute(statement)
        return [dict(row) for row in result.mappings().all()]


def _table(source: Session | Connection | Engine, table_name: str) -> Table | None:
    bind = _source_bind(source)
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return None
    return Table(table_name, MetaData(), autoload_with=bind)


def _rows(
    source: Session | Connection | Engine, table_name: str
) -> list[dict[str, Any]]:
    table = _table(source, table_name)
    if table is None:
        return []
    return _run_select(source, select(table))


def acquire_account_migration_advisory_lock(
    source: Session | Connection | Engine,
) -> None:
    """Hold the account-migration advisory lock for this transaction.

    Alembic passes a live PostgreSQL ``Connection`` and the operator gate
    passes a SQLAlchemy ``Session``. Both retain the transaction-scoped lock
    until their caller commits or rolls back. SQLite smoke tests do not expose
    PostgreSQL advisory locks and are intentionally left unchanged.
    """

    bind = _source_bind(source)
    if bind.dialect.name != "postgresql":
        return
    if not hasattr(source, "execute"):
        raise TypeError("account migration lock requires a live transaction source")
    cast("Any", source).execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": ACCOUNT_MIGRATION_ADVISORY_KEY},
    )


def _value(row: dict[str, Any], name: str, default: Any = None) -> Any:
    return row.get(name, default)


def _row_id(row: dict[str, Any]) -> int | None:
    value = row.get("id")
    return value if isinstance(value, int) else None


def _canonical_email(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if normalized else None


def _email_is_valid(value: Any) -> bool:
    return isinstance(value, str) and bool(EMAIL_PATTERN.fullmatch(value.strip()))


def _add(
    findings: list[MigrationFinding],
    *,
    code: str,
    table: str,
    rows: Iterable[dict[str, Any]] = (),
    detail: str,
    emails: Iterable[Any] = (),
) -> None:
    row_ids = tuple(
        sorted(
            {row_id for row_id in (_row_id(row) for row in rows) if row_id is not None}
        )
    )
    hints = tuple(
        sorted(
            {
                hint
                for hint in (redact_email(email) for email in emails)
                if hint is not None
            }
        )
    )
    findings.append(
        MigrationFinding(
            code=code,
            table=table,
            row_ids=row_ids,
            detail=detail,
            email_hints=hints,
        )
    )


def _ids_from_row(row: dict[str, Any] | None) -> tuple[int, ...]:
    row_id = _row_id(row or {})
    return (row_id,) if row_id is not None else ()


def _is_expected_sentinel(row: dict[str, Any], *, marker_present: bool) -> bool:
    """Return whether a row matches the immutable legacy sentinel contract."""

    return bool(
        marker_present
        and _value(row, "is_login_sentinel") is True
        and _value(row, "name") == SENTINEL_NAME
        and _value(row, "email") is None
        and _value(row, "status") == "inactive"
        and _value(row, "should_attend") is False
        and all(_value(row, field) is None for field in LEGACY_SENTINEL_NULL_FIELDS)
    )


def _check_legacy_account_rows(
    candidate_rows: list[dict[str, Any]],
    findings: list[MigrationFinding],
    *,
    sentinel_column_present: bool,
) -> tuple[list[dict[str, Any]], set[int]]:
    marker_rows = [
        row
        for row in candidate_rows
        if bool(_value(row, "is_login_sentinel", False))
        or _value(row, "name") == SENTINEL_NAME
    ]
    expected_sentinels = [
        row
        for row in marker_rows
        if _is_expected_sentinel(row, marker_present=sentinel_column_present)
    ]
    sentinel_ids = {
        row_id
        for row_id in (_row_id(row) for row in expected_sentinels)
        if row_id is not None
    }
    marker_contract_invalid = bool(marker_rows) and (
        not sentinel_column_present
        or len(marker_rows) != 1
        or len(expected_sentinels) != 1
    )
    if (sentinel_column_present and len(marker_rows) != 1) or marker_contract_invalid:
        sentinel_ids = set()
        _add(
            findings,
            code="sentinel_contamination",
            table="candidate",
            rows=marker_rows or candidate_rows,
            detail=(
                "expected exactly one flagged row matching the immutable sentinel "
                "name, null email, inactive status, and false attendance"
            ),
        )
        unmarked = [
            row
            for row in marker_rows
            if _value(row, "name") == SENTINEL_NAME
            and not bool(_value(row, "is_login_sentinel", False))
        ]
        if unmarked:
            _add(
                findings,
                code="sentinel_unmarked",
                table="candidate",
                rows=unmarked,
                detail="sentinel name exists without the designated sentinel flag",
            )

    real_rows = [row for row in candidate_rows if (_row_id(row) not in sentinel_ids)]
    by_casefold: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in real_rows:
        email = _value(row, "email")
        if email is None or (isinstance(email, str) and not email.strip()):
            _add(
                findings,
                code="account_email_missing",
                table="candidate",
                rows=[row],
                detail="real account has no email",
            )
        elif not _email_is_valid(email):
            _add(
                findings,
                code="account_email_invalid",
                table="candidate",
                rows=[row],
                detail="real account email fails syntax validation",
                emails=[email],
            )
        else:
            canonical = _canonical_email(email)
            if canonical != email:
                _add(
                    findings,
                    code="account_email_noncanonical",
                    table="candidate",
                    rows=[row],
                    detail="real account email is not trim-plus-lower normalized",
                    emails=[email],
                )
            by_casefold[canonical.casefold() if canonical else ""].append(row)
        status = _value(row, "status")
        if status not in ALLOWED_STATUSES:
            _add(
                findings,
                code="account_status_invalid",
                table="candidate",
                rows=[row],
                detail="account status is outside pending/active/inactive",
            )
        name = _value(row, "name")
        if status != "pending" and (not isinstance(name, str) or not name.strip()):
            _add(
                findings,
                code="account_name_missing",
                table="candidate",
                rows=[row],
                detail="completed account has no non-empty display name",
            )
        if isinstance(name, str) and not name.strip():
            _add(
                findings,
                code="account_name_blank",
                table="candidate",
                rows=[row],
                detail="account display name is whitespace-only",
            )

    for duplicate_rows in by_casefold.values():
        if len(duplicate_rows) > 1:
            _add(
                findings,
                code="account_email_duplicate_casefold",
                table="candidate",
                rows=duplicate_rows,
                detail="multiple real accounts share one case-insensitive email",
                emails=[_value(row, "email") for row in duplicate_rows],
            )
    return real_rows, sentinel_ids


def _check_reference_contamination(
    source: Session | Connection | Engine,
    *,
    sentinel_ids: set[int],
    findings: list[MigrationFinding],
) -> None:
    if not sentinel_ids:
        return
    for table_name in SENTINEL_REFERENCE_TABLES:
        rows = _rows(source, table_name)
        contaminated = [
            row for row in rows if _value(row, "candidate_id") in sentinel_ids
        ]
        if contaminated:
            _add(
                findings,
                code="sentinel_reference",
                table=table_name,
                rows=contaminated,
                detail="historical data references the migration sentinel",
            )


def _check_login_challenges(
    source: Session | Connection | Engine,
    *,
    findings: list[MigrationFinding],
) -> None:
    """Require every legacy challenge to retain an account subject.

    Sentinel-subject challenges are intentionally allowed: they represent
    unknown-login attempts and are expired/deleted inside the destructive
    migration boundary. A null subject cannot be backfilled to an email and
    therefore blocks before any DDL.
    """

    challenge_table = _table(source, "candidate_login_challenge")
    # The current schema deliberately permits email-only challenges while an
    # unknown mailbox is completing registration. Only the legacy shape (no
    # persisted email column) must retain a candidate subject for backfill.
    if challenge_table is None or "email" in challenge_table.c:
        return
    rows = [
        row
        for row in _rows(source, "candidate_login_challenge")
        if _value(row, "candidate_id") is None
    ]
    if rows:
        _add(
            findings,
            code="challenge_missing_candidate",
            table="candidate_login_challenge",
            rows=rows,
            detail="legacy login challenge has no candidate subject for email backfill",
        )


def _check_scope_and_attempts(
    source: Session | Connection | Engine,
    *,
    real_rows: list[dict[str, Any]],
    sentinel_ids: set[int],
    findings: list[MigrationFinding],
) -> dict[str, int]:
    candidates = {_row_id(row): row for row in real_rows if _row_id(row) is not None}
    scope_rows = _rows(source, "exam_candidate_scope")
    attempt_rows = _rows(source, "exam_attempt")
    scope_pairs: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in scope_rows:
        pair = (_value(row, "exam_id"), _value(row, "candidate_id"))
        scope_pairs[pair].append(row)
        candidate = candidates.get(pair[1])
        email = _value(row, "roster_email") or (
            _value(candidate, "email") if candidate is not None else None
        )
        name = _value(row, "roster_name") or (
            _value(candidate, "name") if candidate is not None else None
        )
        if candidate is None or not _email_is_valid(email):
            _add(
                findings,
                code="scope_snapshot_unavailable",
                table="exam_candidate_scope",
                rows=[row],
                detail="scope cannot receive a valid roster email snapshot",
                emails=[email],
            )
        elif _canonical_email(email) != email:
            _add(
                findings,
                code="scope_email_noncanonical",
                table="exam_candidate_scope",
                rows=[row],
                detail="scope roster email is not trim-plus-lower normalized",
                emails=[email],
            )
        if not isinstance(name, str) or not name.strip():
            _add(
                findings,
                code="scope_snapshot_unavailable",
                table="exam_candidate_scope",
                rows=[row],
                detail="scope cannot receive a non-empty roster name snapshot",
                emails=[email],
            )

    for duplicate_rows in scope_pairs.values():
        if len(duplicate_rows) > 1:
            _add(
                findings,
                code="scope_duplicate_candidate",
                table="exam_candidate_scope",
                rows=duplicate_rows,
                detail="multiple scope rows share one exam and account",
            )

    by_exam_email: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
    for row in scope_rows:
        candidate = candidates.get(_value(row, "candidate_id"))
        email = _value(row, "roster_email") or _value(candidate or {}, "email")
        if _email_is_valid(email):
            by_exam_email[(_value(row, "exam_id"), email.strip().casefold())].append(
                row
            )
    for duplicate_rows in by_exam_email.values():
        if len(duplicate_rows) > 1:
            _add(
                findings,
                code="scope_duplicate_email",
                table="exam_candidate_scope",
                rows=duplicate_rows,
                detail="multiple scope rows share one exam and normalized roster email",
                emails=[
                    _value(row, "roster_email")
                    or _value(
                        candidates.get(_value(row, "candidate_id")) or {}, "email"
                    )
                    for row in duplicate_rows
                ],
            )

    missing_scope = [
        row
        for row in attempt_rows
        if _value(row, "candidate_id") not in sentinel_ids
        and (_value(row, "exam_id"), _value(row, "candidate_id")) not in scope_pairs
    ]
    if missing_scope:
        _add(
            findings,
            code="attempt_missing_scope",
            table="exam_attempt",
            rows=missing_scope,
            detail="historical attempt has no exam_candidate_scope row",
        )
    return {
        "scope_rows": len(scope_rows),
        "attempt_rows": len(attempt_rows),
        "attempts_missing_scope": len(missing_scope),
    }


def run_account_migration_preflight(
    source: Session | Connection | Engine,
    *,
    now: datetime | None = None,
) -> MigrationPreflightReport:
    """Inspect legacy account data without mutating any row or transaction state."""

    checked_at = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    findings: list[MigrationFinding] = []
    candidate_table = _table(source, "candidate")
    if candidate_table is None:
        findings.append(
            MigrationFinding(
                code="schema_missing",
                table="candidate",
                detail="candidate table is missing",
            )
        )
        return MigrationPreflightReport(
            status="blocked",
            checked_at=checked_at,
            counts={"real_accounts": 0, "scope_rows": 0, "attempt_rows": 0},
            findings=tuple(findings),
        )

    candidate_rows = _rows(source, "candidate")
    real_rows, sentinel_ids = _check_legacy_account_rows(
        candidate_rows,
        findings,
        sentinel_column_present="is_login_sentinel" in candidate_table.c,
    )
    _check_reference_contamination(source, sentinel_ids=sentinel_ids, findings=findings)
    _check_login_challenges(source, findings=findings)
    relation_counts = _check_scope_and_attempts(
        source,
        real_rows=real_rows,
        sentinel_ids=sentinel_ids,
        findings=findings,
    )
    in_progress_rows = [
        row
        for row in _rows(source, "exam_attempt")
        if _value(row, "status") in FORMAL_ATTEMPT_STATUSES
    ]
    if in_progress_rows:
        _add(
            findings,
            code="formal_attempt_in_progress",
            table="exam_attempt",
            rows=in_progress_rows,
            detail="migration requires a formal-attempt write freeze",
        )
    counts = {
        "accounts": len(candidate_rows),
        "real_accounts": len(real_rows),
        "sentinels": len(sentinel_ids),
        "scope_rows": relation_counts["scope_rows"],
        "attempt_rows": relation_counts["attempt_rows"],
        "attempts_missing_scope": relation_counts["attempts_missing_scope"],
        "in_progress_attempts": len(in_progress_rows),
    }
    return MigrationPreflightReport(
        status="passed" if not findings else "blocked",
        checked_at=checked_at,
        counts=counts,
        findings=tuple(findings),
    )


def check_maintenance_gate(
    source: Session | Connection | Engine,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
    backup_path: str | Path,
    second_copy_path: str | Path,
    second_copy_encrypted: bool,
    write_freeze_owner: str | None = None,
    second_copy_storage_evidence_path: str | Path | None = None,
    restore_drill_evidence_path: str | Path | None = None,
) -> MigrationFinding | None:
    """Validate the exact external fence/paired-backup boundary read-only.

    The migration invokes this in formal environments.  Development test
    databases can run the schema migration without an external host fence,
    while operators can call this function directly in a maintenance wrapper.
    """

    # Re-entering the PostgreSQL transaction lock is safe and makes direct
    # operator calls observe the same atomic writer/fence boundary as Alembic.
    acquire_account_migration_advisory_lock(source)

    if not dataset_id.strip() or not host_id.strip() or writer_generation < 1:
        return MigrationFinding(
            code="writer_fence_identity_missing",
            table="operational_lock",
            detail="datasetId/hostId/writerGeneration must be supplied exactly",
        )
    lock_rows = _rows(source, "operational_lock")
    fence = next(
        (row for row in lock_rows if _value(row, "name") == "formal-writer-fence"),
        None,
    )
    if (
        fence is None
        or _value(fence, "released_at") is not None
        or _value(fence, "owner") != host_id
        or _value(fence, "dataset_id") != dataset_id
        or _value(fence, "host_id") != host_id
        or _value(fence, "writer_generation") != writer_generation
    ):
        return MigrationFinding(
            code="writer_fence_mismatch",
            table="operational_lock",
            row_ids=_ids_from_row(fence),
            detail="active formal writer fence does not match the selected identity",
        )
    backup_lock = next(
        (row for row in lock_rows if _value(row, "name") == "backup-write-freeze"),
        None,
    )
    if backup_lock is None or _value(backup_lock, "released_at") is not None:
        return MigrationFinding(
            code="write_freeze_missing",
            table="operational_lock",
            row_ids=_ids_from_row(backup_lock),
            detail="coordinated backup write freeze is not active",
        )
    if not isinstance(write_freeze_owner, str) or not write_freeze_owner.strip():
        return MigrationFinding(
            code="write_freeze_owner_missing",
            table="operational_lock",
            row_ids=_ids_from_row(backup_lock),
            detail="exact migration write-freeze owner must be supplied",
        )
    if _value(backup_lock, "owner") != write_freeze_owner:
        return MigrationFinding(
            code="write_freeze_owner_mismatch",
            table="operational_lock",
            row_ids=_ids_from_row(backup_lock),
            detail="write freeze owner does not match the selected operator",
        )
    if not second_copy_encrypted:
        return MigrationFinding(
            code="second_copy_not_encrypted",
            table="backup_artifact",
            detail="independent second copy must be encrypted",
        )
    attempts = [
        row
        for row in _rows(source, "exam_attempt")
        if _value(row, "status") in FORMAL_ATTEMPT_STATUSES
    ]
    if attempts:
        return MigrationFinding(
            code="formal_attempt_in_progress",
            table="exam_attempt",
            row_ids=tuple(
                sorted(
                    row_id
                    for row_id in (_row_id(row) for row in attempts)
                    if row_id is not None
                )
            ),
            detail="formal attempt is still in progress",
        )
    try:
        _validate_pre_upgrade_backup(
            backup_path,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
        )
        _validate_pre_upgrade_backup(
            second_copy_path,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
        )
        _validate_second_copy_evidence(backup_path, second_copy_path)
        _validate_five_file_digests(backup_path, second_copy_path)
        _validate_second_copy_storage_evidence(
            second_copy_storage_evidence_path
            or Path(backup_path).expanduser().resolve().parent
            / "evidence"
            / "second-copy-storage.json",
            second_copy_path=second_copy_path,
            host_id=host_id,
        )
        _validate_restore_drill_evidence(
            restore_drill_evidence_path,
            backup_path=backup_path,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
        )
    except Exception as exc:  # redact all backup failures
        return MigrationFinding(
            code="paired_backup_invalid",
            table="backup_artifact",
            detail=f"paired backup validation failed: {type(exc).__name__}",
        )
    if os.path.realpath(backup_path) == os.path.realpath(second_copy_path):
        return MigrationFinding(
            code="second_copy_not_independent",
            table="backup_artifact",
            detail="paired backup and encrypted second copy must be distinct paths",
        )
    return None


def _validate_second_copy_evidence(
    backup_path: str | Path,
    second_copy_path: str | Path,
) -> None:
    """Require checksummed evidence for the selected encrypted second copy."""

    from app.ops.internal_backup import (
        SECOND_COPY_EVIDENCE_SUFFIX,
        SECOND_COPY_MARKER_NAME,
    )

    backup_dir = Path(backup_path).expanduser().resolve()
    second_copy_dir = Path(second_copy_path).expanduser().resolve()
    evidence_path = backup_dir.parent / (backup_dir.name + SECOND_COPY_EVIDENCE_SUFFIX)
    evidence_checksum = evidence_path.with_suffix(evidence_path.suffix + ".sha256")
    marker = second_copy_dir.parent / SECOND_COPY_MARKER_NAME
    if not marker.is_file():
        marker = second_copy_dir / SECOND_COPY_MARKER_NAME
    if not evidence_path.is_file() or not evidence_checksum.is_file():
        raise ValueError("second-copy checksum evidence is missing")
    if not marker.is_file():
        raise ValueError("encrypted second-copy marker is missing")
    evidence_digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    checksum_line = evidence_checksum.read_text(encoding="ascii").strip()
    expected_line = f"{evidence_digest}  {evidence_path.name}"
    if checksum_line != expected_line:
        raise ValueError("second-copy evidence checksum mismatch")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if (
        not isinstance(evidence, dict)
        or evidence.get("status") != "passed"
        or evidence.get("kind") != "second-copy-sync"
        or evidence.get("backup_id") != backup_dir.name
        or evidence.get("artifact_id") != second_copy_dir.name
        or evidence.get("error_type") is not None
        or evidence.get("errorType") is not None
    ):
        raise ValueError("second-copy evidence does not identify the selected backup")
    _validate_evidence_freshness(evidence, "checked_at", "checkedAt")


def _validate_pre_upgrade_backup(
    backup_path: str | Path,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
) -> dict[str, object]:
    """Validate a complete pre-upgrade backup bound to one writer identity."""

    from app.ops.internal_backup import validate_backup

    manifest = validate_backup(backup_path, require_cross_host_identity=True)
    expected = {
        "dataset_id": dataset_id,
        "source_host_id": host_id,
        "writer_generation": writer_generation,
    }
    if manifest.get("backup_kind") != "pre-upgrade":
        raise ValueError("migration requires a pre-upgrade backup")
    if {key: manifest.get(key) for key in expected} != expected:
        raise ValueError("pre-upgrade backup writer identity mismatch")
    return manifest


def _validate_five_file_digests(
    local_path: str | Path,
    second_copy_path: str | Path,
) -> None:
    """Compare every byte-bearing file in local and second-copy bundles."""

    filenames = (
        "database.dump",
        "learning_media.tar.gz",
        "manifest.json",
        "SHA256SUMS",
        "SUCCESS",
    )
    for filename in filenames:
        local = Path(local_path).expanduser().resolve() / filename
        copied = Path(second_copy_path).expanduser().resolve() / filename
        if not local.is_file() or not copied.is_file():
            raise ValueError("paired backup file is missing")
        if (
            hashlib.sha256(local.read_bytes()).digest()
            != hashlib.sha256(copied.read_bytes()).digest()
        ):
            raise ValueError("paired backup file digest mismatch")


def _read_checksummed_json(path: str | Path) -> dict[str, object]:
    evidence_path = Path(path).expanduser().resolve()
    checksum_path = evidence_path.with_suffix(evidence_path.suffix + ".sha256")
    if not evidence_path.is_file() or not checksum_path.is_file():
        raise ValueError("checksummed evidence is missing")
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    checksum_line = checksum_path.read_text(encoding="ascii").strip()
    if checksum_line != f"{digest}  {evidence_path.name}":
        raise ValueError("checksummed evidence digest mismatch")
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("checksummed evidence is not an object")
    return payload


def _validate_evidence_freshness(
    payload: dict[str, object], *timestamp_names: str
) -> None:
    present = [name for name in timestamp_names if name in payload]
    if len(present) != 1 or not isinstance(payload[present[0]], str):
        raise ValueError("checksummed evidence timestamp is missing")
    try:
        checked_at = datetime.fromisoformat(
            str(payload[present[0]]).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("checksummed evidence timestamp is invalid") from exc
    if checked_at.tzinfo is None:
        raise ValueError("checksummed evidence timestamp has no timezone")
    checked_at = checked_at.astimezone(UTC)
    now = datetime.now(UTC)
    if checked_at > now + CLOCK_SKEW or now - checked_at > EVIDENCE_MAX_AGE:
        raise ValueError("checksummed evidence is stale")


def _validate_second_copy_storage_evidence(
    path: str | Path,
    *,
    second_copy_path: str | Path,
    host_id: str,
) -> None:
    payload = _read_checksummed_json(path)
    _validate_evidence_freshness(payload, "checkedAt", "checked_at")
    if payload.get("status") != "passed":
        raise ValueError("second-copy storage evidence is not passed")
    for key, alias in (
        ("mounted", "mounted"),
        ("encrypted", "encrypted"),
        ("writable", "writable"),
        ("distinctPhysicalDevice", "distinct_physical_device"),
    ):
        if payload.get(key, payload.get(alias)) is not True:
            raise ValueError("second-copy storage evidence is incomplete")
    evidence_host_id = payload.get("hostId", payload.get("host_id"))
    if evidence_host_id != host_id:
        raise ValueError("second-copy storage host identity mismatch")
    device = payload.get("deviceId", payload.get("device_id"))
    whole = payload.get("wholeDeviceId", payload.get("whole_device_id"))
    formal_whole = payload.get(
        "formalWholeDeviceId", payload.get("formal_whole_device_id")
    )
    if not all(
        isinstance(value, str) and value for value in (device, whole, formal_whole)
    ):
        raise ValueError("second-copy storage device identity is missing")
    if whole == formal_whole:
        raise ValueError("second-copy storage is not a distinct physical device")
    declared_path = payload.get("path") or payload.get("mountPoint")
    selected_path = Path(second_copy_path).expanduser().resolve()
    if declared_path and Path(str(declared_path)).expanduser().resolve() not in {
        selected_path,
        selected_path.parent,
    }:
        # The evidence may describe the mount root while the selected path is
        # its direct backup child; accept either exact root or direct parent.
        raise ValueError("second-copy storage path does not match selected copy")


def _validate_restore_drill_evidence(
    path: str | Path | None,
    *,
    backup_path: str | Path,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
) -> None:
    """Require fresh restore evidence from this change's selected Mac host.

    The destructive account migration is commissioned only on the selected
    Apple-Silicon formal writer (darwin/arm64). A future Windows migration
    must provide its own host-specific workflow and evidence; it may not reuse
    this local gate as a portability claim.
    """

    if path is None:
        raise ValueError("restore-drill evidence path is required")
    payload = _read_checksummed_json(path)
    _validate_evidence_freshness(payload, "checkedAt", "checked_at")
    backup_id = Path(backup_path).expanduser().resolve().name
    backup_manifest = Path(backup_path).expanduser().resolve() / "manifest.json"
    backup_manifest_digest = hashlib.sha256(backup_manifest.read_bytes()).hexdigest()
    declared_manifest_digest = payload.get(
        "sourceBackupManifestSha256", payload.get("source_backup_manifest_sha256")
    )
    if (
        payload.get("status") != "passed"
        or payload.get("kind") != "second-copy-restore-drill"
        or payload.get("backupId", payload.get("backup_id")) != backup_id
        or payload.get("datasetId", payload.get("dataset_id")) != dataset_id
        or payload.get("hostId", payload.get("host_id")) != host_id
        or payload.get("writerGeneration", payload.get("writer_generation"))
        != writer_generation
        or payload.get("formalProjectChanged") is not False
        or payload.get("hostOS", payload.get("host_os")) != "darwin"
        or payload.get(
            "architecture", payload.get("hostArch", payload.get("host_arch"))
        )
        != "arm64"
        or declared_manifest_digest != backup_manifest_digest
    ):
        raise ValueError("restore-drill evidence identity or status is invalid")


def acquire_account_migration_write_freeze(
    source: Session,
    *,
    owner: str,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
    ttl_seconds: int,
) -> Any:
    """Acquire the migration-named exact-owner coordinated write freeze.

    The shared service implementation remains the single row-locking source
    of truth, but this named wrapper prevents account migration from calling a
    generic/cutover CLI alias that could omit the migration identity checks.
    """

    from app.services.operational_lock_service import (
        acquire_fenced_backup_write_freeze,
    )

    return acquire_fenced_backup_write_freeze(
        source,
        owner=owner,
        dataset_id=dataset_id,
        host_id=host_id,
        writer_generation=writer_generation,
        ttl_seconds=ttl_seconds,
    )


def acquire_account_migration_gate(
    source: Session,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
    backup_path: str | Path,
    second_copy_path: str | Path,
    second_copy_encrypted: bool,
    owner: str,
    ttl_seconds: int = 1800,
    second_copy_storage_evidence_path: str | Path | None = None,
    restore_drill_evidence_path: str | Path | None = None,
) -> dict[str, object]:
    """Acquire the exact-owner migration freeze after read-only checks.

    This is the only mutating operation in the module and is exposed through
    the operator CLI, never through ``run_account_migration_preflight``.  The
    service-level helper takes the PostgreSQL advisory transaction mutex and
    row-locks the writer fence before acquiring the coordinated freeze.
    """

    acquire_account_migration_advisory_lock(source)
    if not isinstance(owner, str) or not owner.strip():
        raise RuntimeError("account migration gate owner is required")
    report = run_account_migration_preflight(source)
    if report.blocked:
        codes = ",".join(sorted({finding.code for finding in report.findings}))
        raise RuntimeError(f"account migration preflight blocked: {codes}")
    lock_rows = _rows(source, "operational_lock")
    fence = next(
        (row for row in lock_rows if _value(row, "name") == "formal-writer-fence"),
        None,
    )
    if (
        fence is None
        or _value(fence, "released_at") is not None
        or _value(fence, "owner") != host_id
        or _value(fence, "dataset_id") != dataset_id
        or _value(fence, "host_id") != host_id
        or _value(fence, "writer_generation") != writer_generation
    ):
        raise RuntimeError("writer fence identity mismatch")
    attempts = [
        row
        for row in _rows(source, "exam_attempt")
        if _value(row, "status") in FORMAL_ATTEMPT_STATUSES
    ]
    if attempts:
        raise RuntimeError("formal attempt is in progress")
    if not second_copy_encrypted:
        raise RuntimeError("encrypted second-copy evidence is required")
    # Validate both primary and independently checksummed second-copy evidence
    # before the lock mutation.  check_maintenance_gate additionally requires
    # an already-active freeze, so validate artifacts directly here first.
    try:
        _validate_pre_upgrade_backup(
            backup_path,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
        )
        _validate_pre_upgrade_backup(
            second_copy_path,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
        )
        _validate_second_copy_evidence(backup_path, second_copy_path)
        _validate_five_file_digests(backup_path, second_copy_path)
        _validate_second_copy_storage_evidence(
            second_copy_storage_evidence_path
            or Path(backup_path).expanduser().resolve().parent
            / "evidence"
            / "second-copy-storage.json",
            second_copy_path=second_copy_path,
            host_id=host_id,
        )
        _validate_restore_drill_evidence(
            restore_drill_evidence_path,
            backup_path=backup_path,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
        )
    except Exception as exc:  # redact artifact paths and contents
        raise RuntimeError(
            f"paired backup validation failed: {type(exc).__name__}"
        ) from exc
    try:
        lock = acquire_account_migration_write_freeze(
            source,
            owner=owner,
            dataset_id=dataset_id,
            host_id=host_id,
            writer_generation=writer_generation,
            ttl_seconds=ttl_seconds,
        )
        source.commit()
    except Exception:
        source.rollback()
        raise
    return {
        "status": "passed",
        "action": "account_migration_gate_acquired",
        "owner": lock.owner,
        "datasetId": lock.dataset_id,
        "hostId": lock.host_id,
        "writerGeneration": lock.writer_generation,
        "expiresAt": lock.expires_at.isoformat(),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for the email-account migration"
    )
    parser.add_argument(
        "--require-maintenance-gate",
        action="store_true",
        help="also validate writer fence, paired backups, and write freeze",
    )
    parser.add_argument(
        "--acquire-maintenance-gate",
        action="store_true",
        help="acquire the exact-owner coordinated migration freeze after checks",
    )
    parser.add_argument(
        "--owner", default=os.getenv("ACCOUNT_MIGRATION_GATE_OWNER", "")
    )
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=int(os.getenv("ACCOUNT_MIGRATION_GATE_TTL_SECONDS", "1800") or 1800),
    )
    parser.add_argument(
        "--dataset-id", default=os.getenv("ACCOUNT_MIGRATION_DATASET_ID", "")
    )
    parser.add_argument("--host-id", default=os.getenv("ACCOUNT_MIGRATION_HOST_ID", ""))
    parser.add_argument(
        "--writer-generation",
        type=int,
        default=int(os.getenv("ACCOUNT_MIGRATION_WRITER_GENERATION", "0") or 0),
    )
    parser.add_argument(
        "--backup", default=os.getenv("ACCOUNT_MIGRATION_BACKUP_PATH", "")
    )
    parser.add_argument(
        "--second-copy", default=os.getenv("ACCOUNT_MIGRATION_SECOND_COPY_PATH", "")
    )
    parser.add_argument(
        "--second-copy-encrypted",
        action="store_true",
        default=os.getenv("ACCOUNT_MIGRATION_SECOND_COPY_ENCRYPTED", "false").lower()
        == "true",
    )
    parser.add_argument(
        "--second-copy-storage-evidence",
        default=os.getenv("ACCOUNT_MIGRATION_SECOND_COPY_STORAGE_EVIDENCE_PATH", ""),
    )
    parser.add_argument(
        "--restore-drill-evidence",
        default=os.getenv("ACCOUNT_MIGRATION_RESTORE_DRILL_EVIDENCE_PATH", ""),
    )
    parser.add_argument(
        "--write-freeze-owner",
        default=os.getenv("ACCOUNT_MIGRATION_WRITE_FREEZE_OWNER", ""),
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            if args.acquire_maintenance_gate:
                result = acquire_account_migration_gate(
                    db,
                    dataset_id=args.dataset_id,
                    host_id=args.host_id,
                    writer_generation=args.writer_generation,
                    backup_path=args.backup,
                    second_copy_path=args.second_copy,
                    second_copy_encrypted=args.second_copy_encrypted,
                    owner=args.owner,
                    ttl_seconds=args.ttl_seconds,
                    second_copy_storage_evidence_path=(
                        args.second_copy_storage_evidence or None
                    ),
                    restore_drill_evidence_path=(args.restore_drill_evidence or None),
                )
                sys.stdout.write(
                    json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n"
                )
                return 0
            if args.require_maintenance_gate:
                # Hold the transaction mutex before the data preflight so the
                # fence, freeze, and attempt checks cannot race a writer.
                acquire_account_migration_advisory_lock(db)
            report = run_account_migration_preflight(db)
            findings = list(report.findings)
            if args.require_maintenance_gate and not findings:
                gate_finding = check_maintenance_gate(
                    db,
                    dataset_id=args.dataset_id,
                    host_id=args.host_id,
                    writer_generation=args.writer_generation,
                    backup_path=args.backup,
                    second_copy_path=args.second_copy,
                    second_copy_encrypted=args.second_copy_encrypted,
                    write_freeze_owner=args.write_freeze_owner or None,
                    second_copy_storage_evidence_path=(
                        args.second_copy_storage_evidence or None
                    ),
                    restore_drill_evidence_path=(args.restore_drill_evidence or None),
                )
                if gate_finding is not None:
                    findings.append(gate_finding)
            if findings:
                report = MigrationPreflightReport(
                    status="blocked",
                    checked_at=report.checked_at,
                    counts=report.counts,
                    findings=tuple(findings),
                )
    except Exception as exc:  # CLI emits only type, never values
        sys.stderr.write(
            f"account_migration_preflight_failed error={type(exc).__name__}\n"
        )
        return 2
    sys.stdout.write(report.redacted_json() + "\n")
    return 0 if report.can_migrate else 2


if __name__ == "__main__":
    raise SystemExit(main())
