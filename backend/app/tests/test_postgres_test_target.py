from __future__ import annotations

import pytest

from app.ops.postgres_test_target import assert_postgres_test_database_target

VALID_URL = "postgresql+psycopg://exam:super-secret@127.0.0.1:55432/internal_exam_test"
VALID_ENV = {
    "POSTGRES_TEST_DATABASE_DISPOSABLE": "true",
    "POSTGRES_TEST_DATABASE_PORT": "55432",
}


def test_postgres_test_target_accepts_the_explicit_disposable_identity() -> None:
    assert_postgres_test_database_target(VALID_URL, environ=VALID_ENV)


@pytest.mark.parametrize(
    "identity_override",
    [
        "host=remote.example",
        "dbname=other_test",
        "user=other",
        "port=5432",
        "password=other-secret",
    ],
)
def test_postgres_test_target_rejects_query_identity_overrides(
    identity_override: str,
) -> None:
    database_url = f"{VALID_URL}?{identity_override}"
    with pytest.raises(RuntimeError, match="explicit disposable target") as error:
        assert_postgres_test_database_target(database_url, environ=VALID_ENV)
    assert "super-secret" not in str(error.value)
    assert database_url not in str(error.value)


@pytest.mark.parametrize(
    ("database_url", "environment"),
    [
        (VALID_URL, {}),
        (VALID_URL, {**VALID_ENV, "POSTGRES_TEST_DATABASE_DISPOSABLE": "false"}),
        (
            "postgresql://exam:super-secret@127.0.0.1:55432/internal_exam_test",
            VALID_ENV,
        ),
        (
            "postgresql+psycopg://exam:super-secret@example.test:55432/internal_exam_test",
            VALID_ENV,
        ),
        (
            "postgresql+psycopg://other:super-secret@127.0.0.1:55432/internal_exam_test",
            VALID_ENV,
        ),
        (
            "postgresql+psycopg://exam:super-secret@127.0.0.1:55432/other_test",
            VALID_ENV,
        ),
        (VALID_URL, {"POSTGRES_TEST_DATABASE_DISPOSABLE": "true"}),
        (VALID_URL, {**VALID_ENV, "POSTGRES_TEST_DATABASE_PORT": "5432"}),
    ],
)
def test_postgres_test_target_rejects_every_mismatch(
    database_url: str, environment: dict[str, str]
) -> None:
    with pytest.raises(RuntimeError, match="explicit disposable target") as error:
        assert_postgres_test_database_target(database_url, environ=environment)
    assert "super-secret" not in str(error.value)
    assert database_url not in str(error.value)
