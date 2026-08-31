"""Guard the one PostgreSQL database allowed for destructive test suites."""

from __future__ import annotations

import os
from ipaddress import ip_address
from typing import TYPE_CHECKING

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

if TYPE_CHECKING:
    from collections.abc import Mapping

EXPECTED_POSTGRES_TEST_DATABASE = "internal_exam_test"
EXPECTED_POSTGRES_TEST_USER = "exam"
EXPECTED_POSTGRES_TEST_DRIVER = "postgresql+psycopg"


def assert_postgres_test_database_target(
    database_url: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Reject every target except the explicitly disposable local test DB.

    This function only parses the URL. Callers must invoke it before creating
    an engine or opening a connection, and before issuing any destructive SQL.
    Error text deliberately contains no URL, username, or password.
    """

    env = os.environ if environ is None else environ
    raw_url = (
        database_url
        if database_url is not None
        else env.get("POSTGRES_TEST_DATABASE_URL")
    )
    declared_port = env.get("POSTGRES_TEST_DATABASE_PORT", "")
    marker = env.get("POSTGRES_TEST_DATABASE_DISPOSABLE", "")

    if not isinstance(marker, str) or marker.strip().lower() != "true":
        raise RuntimeError("PostgreSQL tests require an explicit disposable target")
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise RuntimeError("PostgreSQL tests require an explicit disposable target")
    if (
        not isinstance(declared_port, str)
        or not declared_port.isascii()
        or not declared_port.isdecimal()
    ):
        raise RuntimeError("PostgreSQL tests require an explicit disposable target")
    try:
        expected_port = int(declared_port)
        parsed = make_url(raw_url)
        has_query_parameters = bool(parsed.query)
        actual_port = parsed.port
        host = parsed.host
        host_is_loopback = bool(host and ip_address(host).is_loopback)
    except (ArgumentError, TypeError, ValueError):
        raise RuntimeError(
            "PostgreSQL tests require an explicit disposable target"
        ) from None

    if has_query_parameters:
        raise RuntimeError("PostgreSQL tests require an explicit disposable target")

    if (
        parsed.drivername != EXPECTED_POSTGRES_TEST_DRIVER
        or not host_is_loopback
        or parsed.username != EXPECTED_POSTGRES_TEST_USER
        or parsed.database != EXPECTED_POSTGRES_TEST_DATABASE
        or actual_port != expected_port
        or not 1 <= expected_port <= 65_535
    ):
        raise RuntimeError("PostgreSQL tests require an explicit disposable target")
