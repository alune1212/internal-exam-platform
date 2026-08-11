"""persist formal cutover writer-fence identity"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202608070001"
down_revision: str | Sequence[str] | None = "202607210001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Reuse operational_lock so the existing PostgreSQL advisory transaction
    # mutex serializes fence transitions with backup and application writers.
    op.add_column(
        "operational_lock",
        sa.Column("dataset_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "operational_lock",
        sa.Column("host_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "operational_lock",
        sa.Column("writer_generation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "operational_lock",
        sa.Column("reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("operational_lock", "reason")
    op.drop_column("operational_lock", "writer_generation")
    op.drop_column("operational_lock", "host_id")
    op.drop_column("operational_lock", "dataset_id")
