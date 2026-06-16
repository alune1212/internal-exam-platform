"""backfill_exam_candidate_scope

Revision ID: 202606160002
Revises: 202606160001
Create Date: 2026-06-16 09:50:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202606160002"
down_revision: str | Sequence[str] | None = "202606160001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO exam_candidate_scope (exam_id, candidate_id)
        SELECT DISTINCT exam_id, candidate_id
        FROM exam_attempt
        ON CONFLICT (exam_id, candidate_id) DO NOTHING
        """
    )


def downgrade() -> None:
    pass
