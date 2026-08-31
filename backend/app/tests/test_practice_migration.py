import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Candidate, PracticeAnswer, Question


def test_practice_aggregate_migration_backfills_without_deleting_details() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "202608300001_practice_answer_aggregate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "practice_aggregate_migration", migration_path
    )
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    old_tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name != "practice_answer_aggregate"
    ]
    Base.metadata.create_all(engine, tables=old_tables)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DROP INDEX ix_practice_answer_candidate_question_practiced"
        )
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    with Session(engine) as db:
        candidate = Candidate(
            name="迁移考生", email="migration@example.com", status="active"
        )
        question = Question(
            question_type="single", stem="迁移题", score=1, status="active"
        )
        db.add_all([candidate, question])
        db.flush()
        db.add_all(
            [
                PracticeAnswer(
                    candidate_id=candidate.id,
                    question_id=question.id,
                    selected_answer="B",
                    is_correct=False,
                    practiced_at=now,
                ),
                PracticeAnswer(
                    candidate_id=candidate.id,
                    question_id=question.id,
                    selected_answer="A",
                    is_correct=True,
                    practiced_at=now,
                ),
            ]
        )
        db.commit()

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
        detail_count = connection.exec_driver_sql(
            "SELECT count(*) FROM practice_answer"
        ).scalar_one()
        aggregate = connection.exec_driver_sql(
            "SELECT total_attempts, incorrect_count, latest_selected_answer, "
            "latest_is_correct, latest_practice_answer_id "
            "FROM practice_answer_aggregate"
        ).one()

    assert detail_count == 2
    assert tuple(aggregate) == (2, 1, "A", True, 2)
    assert "ix_practice_answer_candidate_question_practiced" in {
        index["name"] for index in inspect(engine).get_indexes("practice_answer")
    }
