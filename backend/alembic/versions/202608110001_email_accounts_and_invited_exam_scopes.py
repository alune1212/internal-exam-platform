"""Migrate roster-bound candidates to normalized email accounts.

This revision deliberately keeps the historical ``candidate`` primary key and
all ``candidate_id`` foreign keys.  It performs a read-only preflight before
any DDL, writes the immutable exam-scope snapshots, verifies the backfill, and
only then removes the sentinel and legacy personnel columns.  A downgrade is
not a data-recovery mechanism; operators must restore the paired backup.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa

from alembic import op
from app.ops.account_migration_preflight import (
    LEGACY_SENTINEL_NULL_FIELDS,
    SENTINEL_NAME,
    acquire_account_migration_advisory_lock,
    check_maintenance_gate,
    run_account_migration_preflight,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "202608110001"
down_revision: str | Sequence[str] | None = "202608070001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_CANDIDATE_COLUMNS = (
    "employee_no",
    "phone_suffix",
    "should_attend",
    "department",
    "position",
    "exam_group",
    "remark",
    "is_login_sentinel",
)
SCOPE_COLUMNS = (
    ("roster_email", sa.String(length=255)),
    ("roster_name", sa.String(length=100)),
    ("department", sa.String(length=100)),
    ("position", sa.String(length=100)),
    ("exam_group", sa.String(length=100)),
    ("roster_remark", sa.Text()),
    ("invitation_status", sa.String(length=20)),
    ("last_invitation_attempt_at", sa.DateTime(timezone=True)),
    ("invitation_sent_at", sa.DateTime(timezone=True)),
    ("invitation_error_class", sa.String(length=100)),
    ("invitation_claimed_at", sa.DateTime(timezone=True)),
    ("invitation_claim_owner", sa.String(length=200)),
)


def _bind() -> sa.Connection:
    return op.get_bind()


def _dialect_name() -> str:
    return _bind().dialect.name


def _table_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(_bind()).get_table_names()


def _validated_sentinel_id() -> int:
    """Return the sole sentinel only when its immutable identity is exact."""

    columns = _table_columns("candidate")
    required = {
        "id",
        "is_login_sentinel",
        "name",
        "email",
        "status",
        "should_attend",
        *LEGACY_SENTINEL_NULL_FIELDS,
    }
    if not required.issubset(columns):
        raise RuntimeError("account migration sentinel identity columns are missing")
    rows = (
        _bind()
        .execute(
            sa.text(
                "SELECT id FROM candidate "
                "WHERE is_login_sentinel = true "
                "AND name = :sentinel_name AND email IS NULL "
                "AND status = 'inactive' AND should_attend = false "
                "AND employee_no IS NULL AND phone_suffix IS NULL "
                "AND department IS NULL AND position IS NULL "
                "AND exam_group IS NULL AND remark IS NULL"
            ),
            {"sentinel_name": SENTINEL_NAME},
        )
        .scalars()
        .all()
    )
    if len(rows) != 1 or not isinstance(rows[0], int):
        raise RuntimeError("account migration sentinel identity is ambiguous")
    return rows[0]


def _preflight() -> None:
    bind = _bind()
    # This is deliberately the first formal SQL in the migration. The
    # transaction-scoped mutex prevents a writer/fence transition between the
    # read-only checks and the first DDL statement, and is held until Alembic
    # commits the revision.
    acquire_account_migration_advisory_lock(bind)
    report = run_account_migration_preflight(bind)
    if report.blocked:
        codes = ",".join(sorted({finding.code for finding in report.findings}))
        raise RuntimeError(f"account migration preflight blocked: {codes}")

    require_gate = os.getenv(
        "ACCOUNT_MIGRATION_REQUIRE_GATE", "false"
    ).strip().lower() == "true" or os.getenv(
        "ENVIRONMENT", "development"
    ).strip().lower() in {"internal", "production", "formal"}
    if not require_gate:
        return
    try:
        writer_generation = int(os.getenv("ACCOUNT_MIGRATION_WRITER_GENERATION", "0"))
    except ValueError:
        writer_generation = 0
    gate_finding = check_maintenance_gate(
        bind,
        dataset_id=os.getenv("ACCOUNT_MIGRATION_DATASET_ID", ""),
        host_id=os.getenv("ACCOUNT_MIGRATION_HOST_ID", ""),
        writer_generation=writer_generation,
        backup_path=os.getenv("ACCOUNT_MIGRATION_BACKUP_PATH", ""),
        second_copy_path=os.getenv("ACCOUNT_MIGRATION_SECOND_COPY_PATH", ""),
        second_copy_encrypted=(
            os.getenv("ACCOUNT_MIGRATION_SECOND_COPY_ENCRYPTED", "false")
            .strip()
            .lower()
            == "true"
        ),
        write_freeze_owner=os.getenv("ACCOUNT_MIGRATION_WRITE_FREEZE_OWNER") or None,
        second_copy_storage_evidence_path=(
            os.getenv("ACCOUNT_MIGRATION_SECOND_COPY_STORAGE_EVIDENCE_PATH") or None
        ),
        restore_drill_evidence_path=(
            os.getenv("ACCOUNT_MIGRATION_RESTORE_DRILL_EVIDENCE_PATH") or None
        ),
    )
    if gate_finding is not None:
        raise RuntimeError(
            f"account migration maintenance gate blocked: {gate_finding.code}"
        )


def _add_column_if_missing(
    table_name: str,
    column_name: str,
    column_type: sa.types.TypeEngine,
    *,
    nullable: bool = True,
    server_default: str | None = None,
) -> None:
    if column_name in _table_columns(table_name):
        return
    if server_default is None:
        column = sa.Column(column_name, column_type, nullable=nullable)
    else:
        column = sa.Column(
            column_name,
            column_type,
            nullable=nullable,
            server_default=server_default,
        )
    op.add_column(table_name, column)


def _alter_nullable(table_name: str, column_name: str, nullable: bool) -> None:
    if _dialect_name() == "sqlite":
        with op.batch_alter_table(table_name, recreate="always") as batch:
            batch.alter_column(column_name, nullable=nullable)
        return
    op.alter_column(table_name, column_name, nullable=nullable)


def _additive_columns() -> None:
    _alter_nullable("candidate", "name", True)
    _add_column_if_missing("candidate_login_challenge", "email", sa.String(255))
    _add_column_if_missing(
        "candidate_login_challenge", "registration_credential_hash", sa.String(128)
    )
    _add_column_if_missing(
        "candidate_login_challenge",
        "registration_credential_expires_at",
        sa.DateTime(timezone=True),
    )
    _add_column_if_missing(
        "candidate_login_challenge",
        "registration_credential_consumed_at",
        sa.DateTime(timezone=True),
    )
    _alter_nullable("candidate_login_challenge", "candidate_id", True)

    for column_name, column_type in SCOPE_COLUMNS:
        _add_column_if_missing("exam_candidate_scope", column_name, column_type)


def _expire_open_challenges() -> None:
    if not _table_exists("candidate_login_challenge"):
        return
    now = datetime.now(UTC)
    _bind().execute(
        sa.text(
            "UPDATE candidate_login_challenge "
            "SET consumed_at = COALESCE(consumed_at, :now), expires_at = "
            "CASE WHEN consumed_at IS NULL THEN :now ELSE expires_at END "
            "WHERE consumed_at IS NULL"
        ),
        {"now": now},
    )


def _remove_sentinel_challenges(sentinel_id: int) -> None:
    """Discard ephemeral unknown-login challenges before email becomes required."""

    if not _table_exists("candidate_login_challenge"):
        return
    _bind().execute(
        sa.text(
            "DELETE FROM candidate_login_challenge "
            "WHERE candidate_id = :sentinel_id AND candidate_id IN ("
            "SELECT id FROM candidate WHERE id = :sentinel_id "
            "AND is_login_sentinel = true AND name = :sentinel_name "
            "AND email IS NULL AND status = 'inactive' AND should_attend = false "
            "AND employee_no IS NULL AND phone_suffix IS NULL "
            "AND department IS NULL AND position IS NULL "
            "AND exam_group IS NULL AND remark IS NULL)"
        ),
        {"sentinel_id": sentinel_id, "sentinel_name": SENTINEL_NAME},
    )


def _normalise_account_emails() -> None:
    _bind().execute(
        sa.text(
            "UPDATE candidate SET email = lower(trim(email)) "
            "WHERE email IS NOT NULL "
            "AND (is_login_sentinel IS NULL OR is_login_sentinel = false)"
        )
    )


def _backfill_challenge_emails() -> None:
    if _dialect_name() == "postgresql":
        _bind().execute(
            sa.text(
                "UPDATE candidate_login_challenge AS challenge "
                "SET email = candidate.email "
                "FROM candidate "
                "WHERE challenge.candidate_id = candidate.id "
                "AND challenge.email IS NULL"
            )
        )
        return
    _bind().execute(
        sa.text(
            "UPDATE candidate_login_challenge SET email = ("
            "SELECT candidate.email FROM candidate "
            "WHERE candidate.id = candidate_login_challenge.candidate_id"
            ") WHERE email IS NULL"
        )
    )


def _backfill_scope_snapshots() -> None:
    if _dialect_name() == "postgresql":
        _bind().execute(
            sa.text(
                "UPDATE exam_candidate_scope AS scope SET "
                "roster_email = candidate.email, roster_name = candidate.name, "
                "department = candidate.department, position = candidate.position, "
                "exam_group = candidate.exam_group, roster_remark = candidate.remark "
                "FROM candidate WHERE scope.candidate_id = candidate.id "
                "AND (scope.roster_email IS NULL OR scope.roster_name IS NULL)"
            )
        )
    else:
        _bind().execute(
            sa.text(
                "UPDATE exam_candidate_scope SET "
                "roster_email = (SELECT email FROM candidate WHERE candidate.id = exam_candidate_scope.candidate_id), "
                "roster_name = (SELECT name FROM candidate WHERE candidate.id = exam_candidate_scope.candidate_id), "
                "department = (SELECT department FROM candidate WHERE candidate.id = exam_candidate_scope.candidate_id), "
                "position = (SELECT position FROM candidate WHERE candidate.id = exam_candidate_scope.candidate_id), "
                "exam_group = (SELECT exam_group FROM candidate WHERE candidate.id = exam_candidate_scope.candidate_id), "
                "roster_remark = (SELECT remark FROM candidate WHERE candidate.id = exam_candidate_scope.candidate_id) "
                "WHERE roster_email IS NULL OR roster_name IS NULL"
            )
        )


def _set_scope_defaults() -> None:
    _bind().execute(
        sa.text(
            "UPDATE exam_candidate_scope SET invitation_status = 'not_sent' "
            "WHERE invitation_status IS NULL"
        )
    )


def _assert_backfill(
    before_scope_count: int,
    before_attempt_count: int,
    *,
    before_candidate_count: int,
    before_real_account_count: int,
) -> None:
    bind = _bind()
    checks = {
        "scope_count": int(
            bind.execute(sa.text("SELECT count(*) FROM exam_candidate_scope")).scalar()
            or 0
        ),
        "attempt_count": int(
            bind.execute(sa.text("SELECT count(*) FROM exam_attempt")).scalar() or 0
        ),
        "candidate_count": int(
            bind.execute(sa.text("SELECT count(*) FROM candidate")).scalar() or 0
        ),
        "real_account_count": int(
            bind.execute(
                sa.text(
                    "SELECT count(*) FROM candidate "
                    "WHERE is_login_sentinel IS NULL OR is_login_sentinel = false"
                )
            ).scalar()
            or 0
        ),
        "incomplete_scope": int(
            bind.execute(
                sa.text(
                    "SELECT count(*) FROM exam_candidate_scope "
                    "WHERE roster_email IS NULL OR roster_name IS NULL "
                    "OR length(trim(roster_name)) = 0 "
                    "OR roster_email <> lower(trim(roster_email))"
                )
            ).scalar()
            or 0
        ),
        "missing_attempt_scope": int(
            bind.execute(
                sa.text(
                    "SELECT count(*) FROM exam_attempt AS attempt "
                    "WHERE NOT EXISTS (SELECT 1 FROM exam_candidate_scope AS scope "
                    "WHERE scope.exam_id = attempt.exam_id "
                    "AND scope.candidate_id = attempt.candidate_id)"
                )
            ).scalar()
            or 0
        ),
        "null_challenge_email": int(
            bind.execute(
                sa.text(
                    "SELECT count(*) FROM candidate_login_challenge "
                    "WHERE email IS NULL OR length(trim(email)) = 0"
                )
            ).scalar()
            or 0
        ),
        "duplicate_account_email": int(
            bind.execute(
                sa.text(
                    "SELECT count(*) FROM (SELECT lower(trim(email)) FROM candidate "
                    "WHERE email IS NOT NULL GROUP BY lower(trim(email)) HAVING count(*) > 1) AS duplicates"
                )
            ).scalar()
            or 0
        ),
        "duplicate_scope_email": int(
            bind.execute(
                sa.text(
                    "SELECT count(*) FROM (SELECT exam_id, lower(trim(roster_email)) "
                    "FROM exam_candidate_scope GROUP BY exam_id, lower(trim(roster_email)) "
                    "HAVING count(*) > 1) AS duplicates"
                )
            ).scalar()
            or 0
        ),
    }
    if checks["scope_count"] < before_scope_count:
        raise RuntimeError("account migration scope count decreased during backfill")
    if checks["attempt_count"] != before_attempt_count:
        raise RuntimeError("account migration attempt count changed during backfill")
    if checks["candidate_count"] != before_candidate_count:
        raise RuntimeError("account migration candidate count changed during backfill")
    if checks["real_account_count"] != before_real_account_count:
        raise RuntimeError(
            "account migration real-account count changed during backfill"
        )
    failures = {
        key: value
        for key, value in checks.items()
        if key
        not in {
            "scope_count",
            "attempt_count",
            "candidate_count",
            "real_account_count",
        }
        and value
    }
    if failures:
        raise RuntimeError(
            f"account migration backfill assertions failed: {','.join(failures)}"
        )


def _drop_legacy_indexes() -> None:
    inspector = sa.inspect(_bind())
    indexes = {
        index["name"]
        for index in inspector.get_indexes("candidate")
        if index.get("name")
    }
    for index_name in (
        "ix_candidate_employee_no",
        "ix_candidate_exam_group",
        "ix_candidate_is_login_sentinel",
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="candidate")


def _drop_legacy_candidate_columns() -> None:
    columns = _table_columns("candidate")
    drop_columns = [column for column in LEGACY_CANDIDATE_COLUMNS if column in columns]
    if not drop_columns:
        return
    if _dialect_name() == "sqlite":
        with op.batch_alter_table("candidate", recreate="always") as batch:
            for column_name in drop_columns:
                batch.drop_column(column_name)
        return
    for column_name in drop_columns:
        op.drop_column("candidate", column_name)


def _create_constraints_and_indexes() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        # SQLite's batch implementation is the only portable way to attach
        # CHECK constraints while preserving existing foreign keys.  The
        # application model carries the same checks for fast SQLite tests.
        with op.batch_alter_table("candidate", recreate="always") as batch:
            batch.alter_column("email", nullable=False)
            batch.create_check_constraint(
                "ck_candidate_status",
                "status IN ('pending', 'active', 'inactive')",
            )
            batch.create_check_constraint(
                "ck_candidate_email_normalized",
                "email = lower(trim(email)) AND length(trim(email)) > 3",
            )
            batch.create_check_constraint(
                "ck_candidate_name_nonblank",
                "name IS NULL OR length(trim(name)) > 0",
            )
            batch.create_check_constraint(
                "ck_candidate_completed_name",
                "status = 'pending' OR (name IS NOT NULL AND length(trim(name)) > 0)",
            )
        with op.batch_alter_table(
            "candidate_login_challenge", recreate="always"
        ) as batch:
            batch.alter_column("email", nullable=False)
            batch.create_check_constraint(
                "ck_candidate_login_challenge_email_normalized",
                "email = lower(trim(email)) AND length(trim(email)) > 3",
            )
        with op.batch_alter_table("exam_candidate_scope", recreate="always") as batch:
            batch.alter_column("roster_email", nullable=False)
            batch.alter_column("roster_name", nullable=False)
            batch.alter_column("invitation_status", nullable=False)
            batch.create_check_constraint(
                "ck_exam_candidate_scope_roster_email_normalized",
                "roster_email = lower(trim(roster_email)) AND length(trim(roster_email)) > 3",
            )
            batch.create_check_constraint(
                "ck_exam_candidate_scope_roster_name_nonblank",
                "length(trim(roster_name)) > 0",
            )
            batch.create_check_constraint(
                "ck_exam_candidate_scope_invitation_status",
                "invitation_status IN ('not_sent', 'sent', 'failed')",
            )
    else:
        op.alter_column("candidate", "email", nullable=False)
        op.create_check_constraint(
            "ck_candidate_status",
            "candidate",
            "status IN ('pending', 'active', 'inactive')",
        )
        op.create_check_constraint(
            "ck_candidate_email_normalized",
            "candidate",
            "email = lower(trim(email)) AND length(trim(email)) > 3",
        )
        op.create_check_constraint(
            "ck_candidate_name_nonblank",
            "candidate",
            "name IS NULL OR length(trim(name)) > 0",
        )
        op.create_check_constraint(
            "ck_candidate_completed_name",
            "candidate",
            "status = 'pending' OR (name IS NOT NULL AND length(trim(name)) > 0)",
        )
        op.alter_column("candidate_login_challenge", "email", nullable=False)
        op.create_check_constraint(
            "ck_candidate_login_challenge_email_normalized",
            "candidate_login_challenge",
            "email = lower(trim(email)) AND length(trim(email)) > 3",
        )
        op.alter_column("exam_candidate_scope", "roster_email", nullable=False)
        op.alter_column("exam_candidate_scope", "roster_name", nullable=False)
        op.alter_column("exam_candidate_scope", "invitation_status", nullable=False)
        op.create_check_constraint(
            "ck_exam_candidate_scope_roster_email_normalized",
            "exam_candidate_scope",
            "roster_email = lower(trim(roster_email)) AND length(trim(roster_email)) > 3",
        )
        op.create_check_constraint(
            "ck_exam_candidate_scope_roster_name_nonblank",
            "exam_candidate_scope",
            "length(trim(roster_name)) > 0",
        )
        op.create_check_constraint(
            "ck_exam_candidate_scope_invitation_status",
            "exam_candidate_scope",
            "invitation_status IN ('not_sent', 'sent', 'failed')",
        )

    existing_indexes = {
        index["name"]
        for index in sa.inspect(_bind()).get_indexes("candidate")
        if index.get("name")
    }
    if "ux_candidate_email" not in existing_indexes:
        op.create_index("ux_candidate_email", "candidate", ["email"], unique=True)

    scope_indexes = {
        index["name"]
        for index in sa.inspect(_bind()).get_indexes("exam_candidate_scope")
        if index.get("name")
    }
    if "ux_exam_candidate_scope_exam_roster_email" not in scope_indexes:
        op.create_index(
            "ux_exam_candidate_scope_exam_roster_email",
            "exam_candidate_scope",
            ["exam_id", "roster_email"],
            unique=True,
        )
    for index_name, columns in (
        ("ix_exam_candidate_scope_invitation_status", ["invitation_status"]),
        (
            "ix_exam_candidate_scope_invitation_claim",
            ["invitation_status", "invitation_claimed_at"],
        ),
    ):
        if index_name not in scope_indexes:
            op.create_index(index_name, "exam_candidate_scope", columns)

    challenge_indexes = {
        index["name"]
        for index in sa.inspect(_bind()).get_indexes("candidate_login_challenge")
        if index.get("name")
    }
    for index_name, columns in (
        ("ix_candidate_login_challenge_email", ["email"]),
        ("ix_candidate_login_challenge_email_consumed", ["email", "consumed_at"]),
        (
            "ix_candidate_login_challenge_registration_credential",
            ["registration_credential_hash", "registration_credential_consumed_at"],
        ),
    ):
        if index_name not in challenge_indexes:
            op.create_index(index_name, "candidate_login_challenge", columns)


def upgrade() -> None:
    _preflight()
    bind = _bind()
    sentinel_id = _validated_sentinel_id()
    before_scope_count = int(
        bind.execute(sa.text("SELECT count(*) FROM exam_candidate_scope")).scalar() or 0
    )
    before_candidate_count = int(
        bind.execute(sa.text("SELECT count(*) FROM candidate")).scalar() or 0
    )
    before_real_account_count = int(
        bind.execute(
            sa.text(
                "SELECT count(*) FROM candidate "
                "WHERE is_login_sentinel IS NULL OR is_login_sentinel = false"
            )
        ).scalar()
        or 0
    )
    before_attempt_count = int(
        bind.execute(sa.text("SELECT count(*) FROM exam_attempt")).scalar() or 0
    )

    _additive_columns()
    _expire_open_challenges()
    _remove_sentinel_challenges(sentinel_id)
    _normalise_account_emails()
    _backfill_challenge_emails()
    _backfill_scope_snapshots()
    _set_scope_defaults()
    _assert_backfill(
        before_scope_count,
        before_attempt_count,
        before_candidate_count=before_candidate_count,
        before_real_account_count=before_real_account_count,
    )

    deleted = bind.execute(
        sa.text(
            "DELETE FROM candidate WHERE id = :sentinel_id "
            "AND is_login_sentinel = true AND name = :sentinel_name "
            "AND email IS NULL AND status = 'inactive' AND should_attend = false "
            "AND employee_no IS NULL AND phone_suffix IS NULL "
            "AND department IS NULL AND position IS NULL "
            "AND exam_group IS NULL AND remark IS NULL"
        ),
        {"sentinel_id": sentinel_id, "sentinel_name": SENTINEL_NAME},
    )
    if deleted.rowcount != 1:
        raise RuntimeError("account migration sentinel cleanup identity changed")
    _drop_legacy_indexes()
    _drop_legacy_candidate_columns()
    remaining_candidate_count = int(
        bind.execute(sa.text("SELECT count(*) FROM candidate")).scalar() or 0
    )
    if remaining_candidate_count != before_real_account_count:
        raise RuntimeError(
            "account migration real-account count changed during sentinel cleanup"
        )
    _create_constraints_and_indexes()


def downgrade() -> None:
    raise RuntimeError(
        "This migration is intentionally non-lossless. Restore the verified "
        "paired PostgreSQL/media backup with the previous release instead of "
        "fabricating deleted personnel, attendance, or sentinel data."
    )
