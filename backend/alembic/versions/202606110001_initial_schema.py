"""initial schema

Revision ID: 202606110001
Revises:
Create Date: 2026-06-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606110001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("employee_no", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("phone_suffix", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("exam_group", sa.String(length=100), nullable=True),
        sa.Column("should_attend", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("employee_no", name="uq_candidate_employee_no"),
    )
    op.create_index("ix_candidate_employee_no", "candidate", ["employee_no"])
    op.create_index("ix_candidate_exam_group", "candidate", ["exam_group"])
    op.create_index("ix_candidate_name", "candidate", ["name"])
    op.create_index("ix_candidate_status", "candidate", ["status"])

    op.create_table(
        "question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_type", sa.String(length=20), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("category_1", sa.String(length=100), nullable=True),
        sa.Column("category_2", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("score", sa.Numeric(8, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("source_no", sa.String(length=100), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
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
    )
    op.create_index("ix_question_category", "question", ["category_1", "category_2"])
    op.create_index("ix_question_question_type", "question", ["question_type"])
    op.create_index("ix_question_status", "question", ["status"])
    op.create_index("ix_question_type_status", "question", ["question_type", "status"])

    op.create_table(
        "exam",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("question_rule", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("show_answer_after_submit", sa.Boolean(), nullable=False),
        sa.Column("show_ranking", sa.Boolean(), nullable=False),
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
    )
    op.create_index("ix_exam_status", "exam", ["status"])

    op.create_table(
        "import_batch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_type", sa.String(length=30), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_report", sa.JSON(), nullable=False),
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
    )
    op.create_index("ix_import_batch_import_type", "import_batch", ["import_type"])
    op.create_index("ix_import_batch_status", "import_batch", ["status"])

    op.create_table(
        "question_option",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("question.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
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
        sa.UniqueConstraint("question_id", "label", name="uq_question_option_label"),
    )
    op.create_index(
        "ix_question_option_question_id", "question_option", ["question_id"]
    )

    op.create_table(
        "exam_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exam.id"), nullable=False),
        sa.Column(
            "candidate_id", sa.Integer(), sa.ForeignKey("candidate.id"), nullable=False
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submit_type", sa.String(length=20), nullable=True),
        sa.Column("score", sa.Numeric(8, 2), nullable=False),
        sa.Column("total_score", sa.Numeric(8, 2), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
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
    )
    op.create_index("ix_exam_attempt_candidate_id", "exam_attempt", ["candidate_id"])
    op.create_index("ix_exam_attempt_exam_id", "exam_attempt", ["exam_id"])
    op.create_index("ix_exam_attempt_status", "exam_attempt", ["status"])

    op.create_table(
        "practice_answer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id", sa.Integer(), sa.ForeignKey("candidate.id"), nullable=False
        ),
        sa.Column(
            "question_id", sa.Integer(), sa.ForeignKey("question.id"), nullable=False
        ),
        sa.Column("selected_answer", sa.String(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("practiced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_practice_answer_candidate_id", "practice_answer", ["candidate_id"]
    )
    op.create_index(
        "ix_practice_answer_question_id", "practice_answer", ["question_id"]
    )

    op.create_table(
        "exam_attempt_question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Integer(),
            sa.ForeignKey("exam_attempt.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "original_question_id",
            sa.Integer(),
            sa.ForeignKey("question.id"),
            nullable=True,
        ),
        sa.Column("question_type", sa.String(length=20), nullable=False),
        sa.Column("stem_snapshot", sa.Text(), nullable=False),
        sa.Column("options_snapshot", sa.JSON(), nullable=False),
        sa.Column("correct_answer_snapshot", sa.String(), nullable=False),
        sa.Column("analysis_snapshot", sa.Text(), nullable=True),
        sa.Column("score", sa.Numeric(8, 2), nullable=False),
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
        sa.UniqueConstraint(
            "attempt_id", "sort_order", name="uq_attempt_question_order"
        ),
    )
    op.create_index(
        "ix_exam_attempt_question_attempt_id", "exam_attempt_question", ["attempt_id"]
    )
    op.create_index(
        "ix_exam_attempt_question_original_question_id",
        "exam_attempt_question",
        ["original_question_id"],
    )

    op.create_table(
        "exam_attempt_answer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attempt_question_id",
            sa.Integer(),
            sa.ForeignKey("exam_attempt_question.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("selected_answer", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score_awarded", sa.Numeric(8, 2), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "attempt_question_id", name="uq_exam_attempt_answer_attempt_question_id"
        ),
    )
    op.create_index(
        "ix_exam_attempt_answer_attempt_question_id",
        "exam_attempt_answer",
        ["attempt_question_id"],
    )


def downgrade() -> None:
    op.drop_table("exam_attempt_answer")
    op.drop_table("exam_attempt_question")
    op.drop_table("practice_answer")
    op.drop_table("exam_attempt")
    op.drop_table("question_option")
    op.drop_table("import_batch")
    op.drop_table("exam")
    op.drop_table("question")
    op.drop_table("candidate")
