import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.models import Exam, ExamAttempt
from app.services.exam_attempts import get_attempt, get_attempt_result

POSTGRES_TEST_DATABASE_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")
BACKEND_ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_REVISION = "202608070001"
CURRENT_REVISION = "202608110001"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _assert_isolated_database(engine: Engine) -> None:
    database_name = engine.url.database or ""
    if not engine.url.drivername.startswith("postgresql") or not database_name.endswith(
        "_test"
    ):
        raise RuntimeError(
            "migration tests require a PostgreSQL database ending in _test"
        )


@pytest.fixture
def migrated_postgres() -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    if POSTGRES_TEST_DATABASE_URL is None:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is required for migration tests")
    engine = create_engine(POSTGRES_TEST_DATABASE_URL, pool_pre_ping=True)
    _assert_isolated_database(engine)
    config = _alembic_config(POSTGRES_TEST_DATABASE_URL)
    # The new migration's downgrade is intentionally restore-only and raises;
    # reset this disposable database explicitly before each upgrade test.
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")
    command.upgrade(config, PREVIOUS_REVISION)
    try:
        yield engine, sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        engine.dispose()


def _seed_legacy_submitted_attempt(engine: Engine) -> tuple[int, int]:
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE exam_attempt_answer, exam_attempt_question, exam_attempt, "
                "exam_retake_grant, exam_candidate_scope, exam_question_pool, "
                "practice_answer, question_option, question, exam, candidate "
                "RESTART IDENTITY CASCADE"
            )
        )
        connection.execute(
            text(
                "INSERT INTO candidate "
                "(id, name, email, should_attend, status, is_login_sentinel, "
                "department, position, exam_group, remark, created_at, updated_at) "
                "VALUES (1, '历史考生', 'history@example.com', true, 'active', false, "
                "'历史部门', '历史岗位', '历史组', '历史备注', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO candidate "
                "(id, name, email, should_attend, status, is_login_sentinel, "
                "created_at, updated_at) "
                "VALUES (2, '__candidate_login_sentinel__', NULL, false, "
                "'inactive', true, :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO candidate_login_challenge "
                "(id, candidate_id, delivery_channel, otp_hash, expires_at, "
                "consumed_at, attempt_count, request_ip_hash, created_at, updated_at) "
                "VALUES (1, 1, 'email', 'real-otp', :expires, NULL, 0, NULL, :now, :now), "
                "(2, 2, 'email', 'sentinel-otp', :expires, NULL, 0, NULL, :now, :now)"
            ),
            {"expires": now + timedelta(minutes=5), "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO exam "
                "(id, title, duration_minutes, question_rule, status, "
                "show_answer_after_submit, show_ranking, "
                "result_details_released_at, result_details_released_by, "
                "created_at, updated_at) "
                "VALUES (1, '历史考试', 60, CAST(:rule AS json), 'active', "
                "true, true, :now, 'migration', :now, :now)"
            ),
            {"rule": "{}", "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO exam_attempt "
                "(id, exam_id, candidate_id, status, started_at, ends_at, "
                "duration_minutes_snapshot, show_answer_after_submit_snapshot, "
                "submitted_at, submit_type, score, total_score, correct_count, "
                "wrong_count, duration_seconds, attempt_no, attempt_kind, "
                "created_at, updated_at) "
                "VALUES (1, 1, 1, 'submitted', :started, :ends, 60, true, "
                ":submitted, 'manual', 2, 2, 1, 0, 120, 1, 'initial', :now, :now)"
            ),
            {
                "started": now - timedelta(minutes=2),
                "ends": now + timedelta(minutes=58),
                "submitted": now,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO exam_candidate_scope "
                "(exam_id, candidate_id, created_at, updated_at) "
                "VALUES (1, 1, :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO exam_attempt_question "
                "(id, attempt_id, question_type, stem_snapshot, options_snapshot, "
                "correct_answer_snapshot, analysis_snapshot, score, sort_order, "
                "created_at, updated_at) "
                "VALUES (1, 1, 'single', '历史快照题', CAST(:options AS json), "
                "'A', '历史解析', 2, 0, :now, :now)"
            ),
            {
                "options": '[{"label":"A","content":"正确","sort_order":0}]',
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO exam_attempt_answer "
                "(id, attempt_question_id, selected_answer, is_correct, "
                "score_awarded, answered_at, created_at, updated_at) "
                "VALUES (1, 1, 'A', true, 2, :now, :now, :now)"
            ),
            {"now": now},
        )
    return 1, 1


def test_upgrade_preserves_historical_visibility_snapshots_and_submission(
    migrated_postgres: tuple[Engine, sessionmaker[Session]],
) -> None:
    engine, session_factory = migrated_postgres
    exam_id, attempt_id = _seed_legacy_submitted_attempt(engine)
    config = _alembic_config(POSTGRES_TEST_DATABASE_URL or "")

    command.upgrade(config, "head")

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar() == (CURRENT_REVISION)
    with session_factory() as db:
        exam = db.get(Exam, exam_id)
        attempt = db.get(ExamAttempt, attempt_id)
        assert exam is not None
        assert attempt is not None
        assert exam.result_details_released_at is not None
        assert exam.result_details_released_by == "migration"
        assert attempt.status == "submitted"
        assert attempt.answer_revision == 0

        attempt_read = get_attempt(db, attempt_id)
        result = get_attempt_result(db, attempt_id)

    assert attempt_read.questions[0].stem_snapshot == "历史快照题"
    assert result.show_answer_after_submit is True
    assert result.questions[0].correct_answer_snapshot == "A"
    assert result.questions[0].analysis_snapshot == "历史解析"
    with engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'candidate'"
                )
            )
        }
        assert {
            "employee_no",
            "phone_suffix",
            "should_attend",
            "department",
            "position",
            "exam_group",
            "remark",
            "is_login_sentinel",
        }.isdisjoint(columns)
        scope = connection.execute(
            text(
                "SELECT roster_email, roster_name, department, position, "
                "exam_group, roster_remark, invitation_status "
                "FROM exam_candidate_scope WHERE exam_id = 1 AND candidate_id = 1"
            )
        ).one()
        assert tuple(scope) == (
            "history@example.com",
            "历史考生",
            "历史部门",
            "历史岗位",
            "历史组",
            "历史备注",
            "not_sent",
        )
        challenges = connection.execute(
            text(
                "SELECT id, candidate_id, email, consumed_at "
                "FROM candidate_login_challenge ORDER BY id"
            )
        ).all()
        assert len(challenges) == 1
        assert challenges[0][0] == 1
        assert challenges[0][1] == 1
        assert challenges[0][2] == "history@example.com"
        assert challenges[0][3] is not None
