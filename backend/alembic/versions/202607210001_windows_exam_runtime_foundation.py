"""windows exam runtime foundation

Revision ID: 202607210001
Revises: 202607030002
Create Date: 2026-07-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607210001"
down_revision: str | Sequence[str] | None = "202607030002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exam",
        sa.Column("result_details_released_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "exam",
        sa.Column("result_details_released_by", sa.String(length=100)),
    )
    op.execute(
        sa.text(
            "UPDATE exam SET result_details_released_at = "
            "COALESCE(updated_at, created_at, CURRENT_TIMESTAMP), "
            "result_details_released_by = 'migration' "
            "WHERE show_answer_after_submit = true"
        )
    )

    op.add_column(
        "exam_attempt",
        sa.Column("attempt_session_hash", sa.String(length=128)),
    )
    op.add_column(
        "exam_attempt",
        sa.Column(
            "attempt_session_generation",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "exam_attempt",
        sa.Column("answer_revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("exam_attempt", sa.Column("voided_at", sa.DateTime(timezone=True)))
    op.add_column("exam_attempt", sa.Column("voided_by", sa.String(length=100)))
    op.add_column("exam_attempt", sa.Column("void_reason", sa.Text()))

    op.create_table(
        "operational_lock",
        sa.Column("name", sa.String(length=100), primary_key=True),
        sa.Column("owner", sa.String(length=200), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_operational_lock_expires_at",
        "operational_lock",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "admin_audit_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operator_subject", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=200)),
        sa.Column("result", sa.String(length=40), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("request_source_hash", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_admin_audit_event_created_at",
        "admin_audit_event",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_event_action",
        "admin_audit_event",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_event_operator_subject",
        "admin_audit_event",
        ["operator_subject"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_audit_event_operator_subject", table_name="admin_audit_event"
    )
    op.drop_index("ix_admin_audit_event_action", table_name="admin_audit_event")
    op.drop_index("ix_admin_audit_event_created_at", table_name="admin_audit_event")
    op.drop_table("admin_audit_event")
    op.drop_index("ix_operational_lock_expires_at", table_name="operational_lock")
    op.drop_table("operational_lock")

    op.drop_column("exam_attempt", "void_reason")
    op.drop_column("exam_attempt", "voided_by")
    op.drop_column("exam_attempt", "voided_at")
    op.drop_column("exam_attempt", "answer_revision")
    op.drop_column("exam_attempt", "attempt_session_generation")
    op.drop_column("exam_attempt", "attempt_session_hash")
    op.drop_column("exam", "result_details_released_by")
    op.drop_column("exam", "result_details_released_at")
