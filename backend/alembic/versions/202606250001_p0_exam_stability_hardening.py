"""p0_exam_stability_hardening

Revision ID: 202606250001
Revises: 202606170001
Create Date: 2026-06-25 11:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606250001"
down_revision: str | Sequence[str] | None = "202606170001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPAIR_LOG_TABLE = "_migration_exam_question_pool_repair_202606250001"


def upgrade() -> None:
    op.add_column(
        "exam_attempt",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "exam_attempt",
        sa.Column("duration_minutes_snapshot", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exam_attempt",
        sa.Column("pass_score_snapshot", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "exam_attempt",
        sa.Column("show_answer_after_submit_snapshot", sa.Boolean(), nullable=True),
    )

    op.execute(
        """
        UPDATE exam_attempt AS attempt
        SET
            ends_at = attempt.started_at + (exam.duration_minutes * INTERVAL '1 minute'),
            duration_minutes_snapshot = exam.duration_minutes,
            pass_score_snapshot =
                CASE
                    WHEN exam.question_rule::jsonb ? 'pass_score'
                    THEN (exam.question_rule ->> 'pass_score')::numeric
                    ELSE NULL
                END,
            show_answer_after_submit_snapshot = exam.show_answer_after_submit
        FROM exam
        WHERE attempt.exam_id = exam.id
        """
    )

    op.alter_column("exam_attempt", "ends_at", nullable=False)
    op.alter_column("exam_attempt", "duration_minutes_snapshot", nullable=False)
    op.alter_column("exam_attempt", "show_answer_after_submit_snapshot", nullable=False)

    op.create_index(
        "ux_exam_attempt_one_in_progress",
        "exam_attempt",
        ["exam_id", "candidate_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )
    op.create_index(
        "ux_exam_retake_grant_one_unused",
        "exam_retake_grant",
        ["exam_id", "candidate_id"],
        unique=True,
        postgresql_where=sa.text("used_at IS NULL"),
    )

    op.create_table(
        REPAIR_LOG_TABLE,
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("exam_id", "question_id"),
    )
    op.execute(
        """
        INSERT INTO _migration_exam_question_pool_repair_202606250001 (exam_id, question_id)
        SELECT exam.id, question.id
        FROM exam
        CROSS JOIN question
        WHERE exam.status = 'active'
          AND question.status = 'active'
          AND NOT EXISTS (
              SELECT 1
              FROM exam_question_pool pool
              WHERE pool.exam_id = exam.id
          )
        ORDER BY exam.id, question.id
        """
    )
    op.execute(
        """
        INSERT INTO exam_question_pool (
            exam_id,
            question_id,
            sort_order,
            created_at,
            updated_at
        )
        SELECT
            repair.exam_id,
            repair.question_id,
            ROW_NUMBER() OVER (
                PARTITION BY repair.exam_id ORDER BY repair.question_id
            ) - 1 AS sort_order,
            NOW(),
            NOW()
        FROM _migration_exam_question_pool_repair_202606250001 AS repair
        ON CONFLICT (exam_id, question_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM exam_question_pool AS pool
        USING _migration_exam_question_pool_repair_202606250001 AS repair
        WHERE pool.exam_id = repair.exam_id
          AND pool.question_id = repair.question_id
        """
    )
    op.drop_table(REPAIR_LOG_TABLE)

    op.drop_index("ux_exam_retake_grant_one_unused", table_name="exam_retake_grant")
    op.drop_index("ux_exam_attempt_one_in_progress", table_name="exam_attempt")
    op.drop_column("exam_attempt", "show_answer_after_submit_snapshot")
    op.drop_column("exam_attempt", "pass_score_snapshot")
    op.drop_column("exam_attempt", "duration_minutes_snapshot")
    op.drop_column("exam_attempt", "ends_at")
