"""Add all-time practice-answer aggregates without touching detail history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "202608300001"
down_revision: str | Sequence[str] | None = "202608110001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utc(value: datetime) -> datetime:
    """Normalize SQLite's naive datetime values for deterministic comparison."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise RuntimeError("practice aggregate backfill found an invalid timestamp")


def _expected_aggregates(
    bind: sa.Connection,
) -> tuple[dict[tuple[int, int], dict], set[int]]:
    rows = bind.execute(
        sa.text(
            "SELECT id, candidate_id, question_id, selected_answer, is_correct, "
            "practiced_at FROM practice_answer "
            "ORDER BY candidate_id, question_id, practiced_at, id"
        )
    ).mappings()
    expected: dict[tuple[int, int], dict] = {}
    detail_ids: set[int] = set()
    for row in rows:
        detail_id = int(row["id"])
        candidate_id = int(row["candidate_id"])
        question_id = int(row["question_id"])
        practiced_at = row["practiced_at"]
        if practiced_at is None:
            raise RuntimeError("practice aggregate backfill found a null timestamp")
        practiced_at = _as_datetime(practiced_at)
        key = (candidate_id, question_id)
        detail_ids.add(detail_id)
        aggregate = expected.setdefault(
            key,
            {
                "candidate_id": candidate_id,
                "question_id": question_id,
                "total_attempts": 0,
                "incorrect_count": 0,
                "latest_selected_answer": row["selected_answer"],
                "latest_is_correct": bool(row["is_correct"]),
                "latest_practiced_at": practiced_at,
                "latest_practice_answer_id": detail_id,
                "_latest_key": (_utc(practiced_at), detail_id),
            },
        )
        aggregate["total_attempts"] += 1
        if not bool(row["is_correct"]):
            aggregate["incorrect_count"] += 1
        row_key = (_utc(practiced_at), detail_id)
        if row_key > aggregate["_latest_key"]:
            aggregate.update(
                latest_selected_answer=row["selected_answer"],
                latest_is_correct=bool(row["is_correct"]),
                latest_practiced_at=practiced_at,
                latest_practice_answer_id=detail_id,
                _latest_key=row_key,
            )
    for aggregate in expected.values():
        aggregate.pop("_latest_key", None)
    return expected, detail_ids


def _validate_backfill(
    bind: sa.Connection,
    expected: dict[tuple[int, int], dict],
    detail_ids: set[int],
) -> None:
    actual_detail_ids = {
        int(row[0]) for row in bind.execute(sa.text("SELECT id FROM practice_answer"))
    }
    if actual_detail_ids != detail_ids:
        raise RuntimeError("practice aggregate backfill changed practice details")

    actual_rows = bind.execute(
        sa.text(
            "SELECT candidate_id, question_id, total_attempts, incorrect_count, "
            "latest_selected_answer, latest_is_correct, latest_practiced_at, "
            "latest_practice_answer_id FROM practice_answer_aggregate"
        )
    ).mappings()
    actual_by_key = {
        (int(row["candidate_id"]), int(row["question_id"])): row for row in actual_rows
    }
    if set(actual_by_key) != set(expected):
        raise RuntimeError("practice aggregate backfill key validation failed")
    for key, expected_row in expected.items():
        actual = actual_by_key[key]
        if (
            int(actual["total_attempts"]) != expected_row["total_attempts"]
            or int(actual["incorrect_count"]) != expected_row["incorrect_count"]
            or actual["latest_selected_answer"]
            != expected_row["latest_selected_answer"]
            or bool(actual["latest_is_correct"]) != expected_row["latest_is_correct"]
            or _utc(_as_datetime(actual["latest_practiced_at"]))
            != _utc(expected_row["latest_practiced_at"])
            or int(actual["latest_practice_answer_id"])
            != expected_row["latest_practice_answer_id"]
        ):
            raise RuntimeError(
                f"practice aggregate backfill value validation failed: {key}"
            )


def upgrade() -> None:
    bind = op.get_bind()
    expected, detail_ids = _expected_aggregates(bind)
    aggregate_table = op.create_table(
        "practice_answer_aggregate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidate.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("question.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_attempts", sa.Integer(), nullable=False),
        sa.Column("incorrect_count", sa.Integer(), nullable=False),
        sa.Column("latest_selected_answer", sa.Text(), nullable=False),
        sa.Column("latest_is_correct", sa.Boolean(), nullable=False),
        sa.Column("latest_practiced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_practice_answer_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "candidate_id",
            "question_id",
            name="uq_practice_answer_aggregate_candidate_question",
        ),
        sa.CheckConstraint(
            "total_attempts >= 0",
            name="ck_practice_answer_aggregate_total_attempts_nonnegative",
        ),
        sa.CheckConstraint(
            "incorrect_count >= 0",
            name="ck_practice_answer_aggregate_incorrect_count_nonnegative",
        ),
        sa.CheckConstraint(
            "incorrect_count <= total_attempts",
            name="ck_practice_answer_aggregate_incorrect_count_lte_total",
        ),
    )
    op.create_index(
        "ix_practice_answer_aggregate_candidate_latest",
        "practice_answer_aggregate",
        ["candidate_id", "latest_practiced_at", "question_id"],
    )
    op.create_index(
        "ix_practice_answer_aggregate_candidate_incorrect_latest",
        "practice_answer_aggregate",
        [
            "candidate_id",
            "incorrect_count",
            "latest_practiced_at",
            "question_id",
        ],
    )
    op.create_index(
        "ix_practice_answer_candidate_question_practiced",
        "practice_answer",
        ["candidate_id", "question_id", "practiced_at", "id"],
    )
    if expected:
        bind.execute(
            aggregate_table.insert(),
            list(expected.values()),
        )
    _validate_backfill(bind, expected, detail_ids)


def downgrade() -> None:
    op.drop_table("practice_answer_aggregate")
