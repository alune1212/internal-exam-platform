"""candidate_login_sentinel

Revision ID: 202607030002
Revises: 202607030001
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607030002"
down_revision: str | Sequence[str] | None = "202607030001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SENTINEL_NAME = "__candidate_login_sentinel__"


def upgrade() -> None:
    op.add_column(
        "candidate",
        sa.Column(
            "is_login_sentinel",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_candidate_is_login_sentinel",
        "candidate",
        ["is_login_sentinel"],
        unique=False,
    )

    # Idempotently ensure exactly one sentinel row exists with the flag set.
    # Operators must not delete or rename this row — it backs the uniform
    # response contract for unknown candidate login identities.
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT id FROM candidate WHERE is_login_sentinel = true LIMIT 1")
    ).first()
    if existing is None:
        bind.execute(
            sa.text(
                "INSERT INTO candidate "
                "(name, status, should_attend, is_login_sentinel) "
                "VALUES (:name, :status, :should_attend, :is_sentinel)"
            ),
            {
                "name": SENTINEL_NAME,
                "status": "inactive",
                "should_attend": False,
                "is_sentinel": True,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM candidate WHERE is_login_sentinel = true"))
    op.drop_index(
        "ix_candidate_is_login_sentinel",
        table_name="candidate",
    )
    op.drop_column("candidate", "is_login_sentinel")
