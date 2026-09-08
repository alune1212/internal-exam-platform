from logging.config import fileConfig

from sqlalchemy import engine_from_config, inspect, pool
from sqlalchemy.engine import Connection

from alembic import context
from app import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
SYSTEM_SCHEMAS = frozenset({"information_schema", "pg_catalog"})


def _database_objects(connection: Connection) -> list[str]:
    inspector = inspect(connection)
    objects: list[str] = []
    for schema in inspector.get_schema_names():
        if schema in SYSTEM_SCHEMAS or schema.startswith(("pg_toast", "pg_temp_")):
            continue
        table_names = inspector.get_table_names(schema=schema)
        view_names = inspector.get_view_names(schema=schema)
        materialized_view_names = (
            inspector.get_materialized_view_names(schema=schema)
            if connection.dialect.name == "postgresql"
            else []
        )
        objects.extend(f"{schema}.{name}" for name in table_names)
        objects.extend(f"{schema}.{name}" for name in view_names)
        objects.extend(f"{schema}.{name}" for name in materialized_view_names)
    return sorted(set(objects))


def _initialize_empty_database_requested() -> bool:
    """Return whether the operator explicitly requested first-time bootstrap."""

    value = context.get_x_argument(as_dictionary=True).get(
        "initialize_empty_database", ""
    )
    return value.strip().lower() == "true"


def _assert_empty_database(connection: Connection) -> None:
    """Reject the bootstrap escape hatch once any table already exists."""

    objects = _database_objects(connection)
    if objects:
        raise RuntimeError(
            "initialize_empty_database requires a database with no existing tables; "
            f"found: {', '.join(objects)}"
        )


def run_migrations_offline() -> None:
    if _initialize_empty_database_requested():
        raise RuntimeError(
            "initialize_empty_database requires an online connection and transaction"
        )
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        initialize_empty_database=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    initialize_empty_database = _initialize_empty_database_requested()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            initialize_empty_database=False,
        )

        with context.begin_transaction():
            if initialize_empty_database:
                _assert_empty_database(connection)
            # Set the internal migration option only after the same-transaction
            # empty-database check has passed.  The migration chain then runs
            # on this connection and transaction without an environment flag.
            context.get_context().opts["initialize_empty_database"] = (
                initialize_empty_database
            )
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
