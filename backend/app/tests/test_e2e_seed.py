import pytest

from app.core.config import settings
from app.ops.e2e_seed import (
    E2E_EXAM_TITLE,
    E2E_FAILED_EMAIL,
    E2E_INACTIVE_EMAIL,
    E2E_PENDING_EMAIL,
    E2E_SCOPED_EMAIL,
    E2E_UNSCOPED_EMAIL,
    assert_disposable_database,
)


def test_e2e_seed_fixture_identity_is_email_first() -> None:
    emails = {
        E2E_SCOPED_EMAIL,
        E2E_PENDING_EMAIL,
        E2E_UNSCOPED_EMAIL,
        E2E_INACTIVE_EMAIL,
        E2E_FAILED_EMAIL,
    }
    assert all(email == email.strip().lower() for email in emails)
    assert E2E_EXAM_TITLE.startswith("E2E ")


def test_e2e_seed_requires_explicit_disposable_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+psycopg://exam:secret@db:5432/internal_exam",
    )
    monkeypatch.setenv("E2E_DISPOSABLE_DATABASE", "true")
    with pytest.raises(RuntimeError, match="disposable"):
        assert_disposable_database()


def test_e2e_seed_accepts_only_an_e2e_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+psycopg://exam:secret@db:5432/internal_exam_e2e",
    )
    monkeypatch.setenv("E2E_DISPOSABLE_DATABASE", "true")
    assert_disposable_database()
