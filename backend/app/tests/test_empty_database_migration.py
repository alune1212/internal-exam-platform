from __future__ import annotations

from contextlib import nullcontext
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text


def _load_account_migration_module():
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "202608110001_email_accounts_and_invited_exam_scopes.py"
    )
    spec = spec_from_file_location("empty_database_account_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_alembic_env_module(monkeypatch: pytest.MonkeyPatch):
    import alembic

    class FakeConfig:
        config_file_name = None

        def set_main_option(self, *_args: object) -> None:
            return None

        def get_main_option(self, _name: str) -> str:
            return "sqlite:///:memory:"

    class FakeContext:
        config = FakeConfig()

        @staticmethod
        def get_x_argument(*, as_dictionary: bool) -> dict[str, str]:
            assert as_dictionary is True
            return {}

        @staticmethod
        def is_offline_mode() -> bool:
            return True

        @staticmethod
        def configure(**_kwargs: object) -> None:
            return None

        @staticmethod
        def begin_transaction():
            return nullcontext()

        @staticmethod
        def run_migrations() -> None:
            return None

    monkeypatch.setattr(alembic, "context", FakeContext)
    env_path = Path(__file__).parents[2] / "alembic" / "env.py"
    spec = spec_from_file_location("empty_database_alembic_env", env_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_empty_database_guard_rejects_existing_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_alembic_env_module(monkeypatch)
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as connection:
        module._assert_empty_database(connection)
        connection.execute(text("CREATE TABLE existing_data (id INTEGER PRIMARY KEY)"))
        with pytest.raises(RuntimeError, match="no existing tables"):
            module._assert_empty_database(connection)
        connection.execute(text("DROP TABLE existing_data"))
        connection.execute(text("CREATE VIEW existing_view AS SELECT 1 AS id"))
        with pytest.raises(RuntimeError, match="no existing tables"):
            module._assert_empty_database(connection)


def test_only_verified_context_option_skips_formal_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_account_migration_module()
    bind = object()
    gate_calls: list[object] = []

    monkeypatch.setattr(module, "_bind", lambda: bind)
    monkeypatch.setattr(
        module, "acquire_account_migration_advisory_lock", lambda _: None
    )
    monkeypatch.setattr(
        module,
        "run_account_migration_preflight",
        lambda _: SimpleNamespace(blocked=False),
    )
    monkeypatch.setattr(
        module,
        "check_maintenance_gate",
        lambda *_args, **_kwargs: gate_calls.append(True),
    )
    monkeypatch.setenv("ENVIRONMENT", "internal")
    monkeypatch.setattr(
        module.op,
        "get_context",
        lambda: SimpleNamespace(opts={"initialize_empty_database": True}),
    )

    module._preflight()

    assert gate_calls == []


def test_string_context_option_does_not_bypass_formal_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_account_migration_module()
    bind = object()

    monkeypatch.setattr(module, "_bind", lambda: bind)
    monkeypatch.setattr(
        module, "acquire_account_migration_advisory_lock", lambda _: None
    )
    monkeypatch.setattr(
        module,
        "run_account_migration_preflight",
        lambda _: SimpleNamespace(blocked=False),
    )
    monkeypatch.setattr(
        module,
        "check_maintenance_gate",
        lambda *_args, **_kwargs: SimpleNamespace(code="missing_evidence"),
    )
    monkeypatch.setenv("ENVIRONMENT", "internal")
    monkeypatch.setattr(
        module.op,
        "get_context",
        lambda: SimpleNamespace(opts={"initialize_empty_database": "true"}),
    )

    with pytest.raises(RuntimeError, match="maintenance gate blocked"):
        module._preflight()
