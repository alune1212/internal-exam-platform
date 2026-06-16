"""add_exam_rigor_controls

Revision ID: 202606160001
Revises: e2a085da7a47
Create Date: 2026-06-16 09:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606160001"
down_revision: str | Sequence[str] | None = "e2a085da7a47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exam_attempt",
        sa.Column("attempt_no", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "exam_attempt",
        sa.Column(
            "attempt_kind",
            sa.String(length=20),
            server_default="initial",
            nullable=False,
        ),
    )
    op.add_column(
        "exam_attempt", sa.Column("paper_seed", sa.String(length=64), nullable=True)
    )
    op.execute(
        """
        WITH numbered AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY exam_id, candidate_id
                    ORDER BY created_at, id
                ) AS next_attempt_no
            FROM exam_attempt
        )
        UPDATE exam_attempt
        SET
            attempt_no = numbered.next_attempt_no,
            attempt_kind = CASE
                WHEN numbered.next_attempt_no = 1 THEN 'initial'
                ELSE 'retake'
            END
        FROM numbered
        WHERE exam_attempt.id = numbered.id
        """
    )
    op.create_unique_constraint(
        "uq_exam_attempt_no", "exam_attempt", ["exam_id", "candidate_id", "attempt_no"]
    )

    op.create_table(
        "exam_candidate_scope",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exam_id"], ["exam.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "candidate_id", name="uq_exam_candidate_scope"),
    )
    op.create_index(
        op.f("ix_exam_candidate_scope_exam_id"),
        "exam_candidate_scope",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exam_candidate_scope_candidate_id"),
        "exam_candidate_scope",
        ["candidate_id"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO exam_candidate_scope (exam_id, candidate_id)
        SELECT DISTINCT exam_id, candidate_id
        FROM exam_attempt
        ON CONFLICT (exam_id, candidate_id) DO NOTHING
        """
    )

    op.create_table(
        "exam_retake_grant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("used_attempt_id", sa.Integer(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exam_id"], ["exam.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["used_attempt_id"], ["exam_attempt.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exam_retake_grant_exam_id"),
        "exam_retake_grant",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exam_retake_grant_candidate_id"),
        "exam_retake_grant",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exam_retake_grant_used_attempt_id"),
        "exam_retake_grant",
        ["used_attempt_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_exam_retake_grant_used_attempt_id"), table_name="exam_retake_grant"
    )
    op.drop_index(
        op.f("ix_exam_retake_grant_candidate_id"), table_name="exam_retake_grant"
    )
    op.drop_index(op.f("ix_exam_retake_grant_exam_id"), table_name="exam_retake_grant")
    op.drop_table("exam_retake_grant")
    op.drop_index(
        op.f("ix_exam_candidate_scope_candidate_id"), table_name="exam_candidate_scope"
    )
    op.drop_index(
        op.f("ix_exam_candidate_scope_exam_id"), table_name="exam_candidate_scope"
    )
    op.drop_table("exam_candidate_scope")
    op.drop_constraint("uq_exam_attempt_no", "exam_attempt", type_="unique")
    op.drop_column("exam_attempt", "paper_seed")
    op.drop_column("exam_attempt", "attempt_kind")
    op.drop_column("exam_attempt", "attempt_no")
