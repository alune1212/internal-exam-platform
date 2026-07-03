"""candidate_login_challenge

Revision ID: 202607030001
Revises: 202607020001
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607030001"
down_revision: str | Sequence[str] | None = "202607020001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_login_challenge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column(
            "delivery_channel",
            sa.String(length=20),
            nullable=False,
            server_default="email",
        ),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_ip_hash", sa.String(length=128), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_login_challenge_candidate_id",
        "candidate_login_challenge",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_login_challenge_expires_at",
        "candidate_login_challenge",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_login_challenge_candidate_consumed",
        "candidate_login_challenge",
        ["candidate_id", "consumed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_login_challenge_candidate_consumed",
        table_name="candidate_login_challenge",
    )
    op.drop_index(
        "ix_candidate_login_challenge_expires_at",
        table_name="candidate_login_challenge",
    )
    op.drop_index(
        "ix_candidate_login_challenge_candidate_id",
        table_name="candidate_login_challenge",
    )
    op.drop_table("candidate_login_challenge")
