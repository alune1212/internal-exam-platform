"""exam_time_window_and_question_pool

Revision ID: 202606170001
Revises: 202606160002
Create Date: 2026-06-17 10:58:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606170001"
down_revision: str | Sequence[str] | None = "202606160002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exam", sa.Column("available_from", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "exam", sa.Column("available_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "exam_question_pool",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["exam_id"], ["exam.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "question_id", name="uq_exam_question_pool"),
    )
    op.create_index(
        op.f("ix_exam_question_pool_exam_id"),
        "exam_question_pool",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exam_question_pool_question_id"),
        "exam_question_pool",
        ["question_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_exam_question_pool_question_id"), table_name="exam_question_pool"
    )
    op.drop_index(
        op.f("ix_exam_question_pool_exam_id"), table_name="exam_question_pool"
    )
    op.drop_table("exam_question_pool")
    op.drop_column("exam", "available_until")
    op.drop_column("exam", "available_from")
