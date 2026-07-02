"""video_learning

Revision ID: 202607020001
Revises: 202606250001
Create Date: 2026-07-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607020001"
down_revision: str | Sequence[str] | None = "202606250001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_video",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "completion_threshold_percent",
            sa.Integer(),
            nullable=False,
            server_default="90",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_learning_video_status"), "learning_video", ["status"], unique=False
    )
    op.create_index(
        "ix_learning_video_status_created",
        "learning_video",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "learning_video_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column(
            "last_position_seconds",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("watched_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_percent",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "watched_intervals",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["video_id"], ["learning_video.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "video_id", "candidate_id", name="uq_learning_video_progress"
        ),
    )
    op.create_index(
        op.f("ix_learning_video_progress_candidate_id"),
        "learning_video_progress",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_learning_progress_candidate_completed",
        "learning_video_progress",
        ["candidate_id", "completed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_video_progress_video_id"),
        "learning_video_progress",
        ["video_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_learning_video_progress_video_id"),
        table_name="learning_video_progress",
    )
    op.drop_index(
        "ix_learning_progress_candidate_completed",
        table_name="learning_video_progress",
    )
    op.drop_index(
        op.f("ix_learning_video_progress_candidate_id"),
        table_name="learning_video_progress",
    )
    op.drop_table("learning_video_progress")
    op.drop_index("ix_learning_video_status_created", table_name="learning_video")
    op.drop_index(op.f("ix_learning_video_status"), table_name="learning_video")
    op.drop_table("learning_video")
