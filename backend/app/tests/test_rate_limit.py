import hashlib
from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi import Request
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import rate_limit
from app.core.config import settings
from app.core.database import Base
from app.core.rate_limit import check_candidate_otp_send_rate_limit
from app.models import CandidateLoginChallenge
from app.schemas.auth import AdminLoginRequest
from app.schemas.candidate import CandidateLoginRequest


def _request_for_ip(ip: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/admin/login",
            "headers": [],
            "client": (ip, 50000),
        }
    )


def test_public_token_rate_limit_prunes_expired_identifier_buckets(
    monkeypatch,
) -> None:
    rate_limit._attempts.clear()
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 10, raising=False)
    monkeypatch.setattr(
        settings, "public_token_rate_limit_window_seconds", 1, raising=False
    )
    assert hasattr(settings, "public_token_rate_limit_max_keys")
    monkeypatch.setattr(settings, "public_token_rate_limit_max_keys", 4)
    current_time = 0.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: current_time)

    rate_limit.check_public_token_rate_limit(
        _request_for_ip("192.0.2.1"), bucket="admin", identifier="old-user"
    )

    current_time = 2.0
    for index in range(10):
        rate_limit.check_public_token_rate_limit(
            _request_for_ip("192.0.2.1"),
            bucket="admin",
            identifier=f"user-{index}",
        )

    assert len(rate_limit._attempts) <= settings.public_token_rate_limit_max_keys
    assert ("admin", "id:old-user") not in rate_limit._attempts


def test_public_token_rate_limit_hashes_identifier_key() -> None:
    rate_limit._attempts.clear()
    identifier = "  " + ("A" * 10_000) + "  "

    rate_limit.check_public_token_rate_limit(
        _request_for_ip("192.0.2.1"), bucket="admin", identifier=identifier
    )

    identifier_keys = [key for key in rate_limit._attempts if key[1].startswith("id:")]
    normalized = identifier.strip().lower()
    expected_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    assert identifier_keys == [("admin", f"id:sha256:{expected_digest}")]
    assert normalized not in identifier_keys[0][1]
    assert len(identifier_keys[0][1]) == len("id:sha256:") + 64


def test_login_request_schemas_reject_oversized_identifiers() -> None:
    with pytest.raises(ValidationError):
        AdminLoginRequest(username="u" * 129, password="x" * 8)

    with pytest.raises(ValidationError):
        CandidateLoginRequest(email="not-an-email")

    with pytest.raises(ValidationError):
        CandidateLoginRequest.model_validate(
            {"email": "user@example.com", "name": "legacy"}
        )


def test_persisted_candidate_otp_limits_survive_without_in_memory_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        monkeypatch.setattr(settings, "candidate_login_email_rate_limit_count", 1)
        now = datetime.now(UTC)
        db.add(
            CandidateLoginChallenge(
                email="quota@example.com",
                otp_hash="hash",
                expires_at=now,
                created_at=now,
                request_ip_hash="sha256:source",
            )
        )
        db.commit()
        with pytest.raises(rate_limit.PublicTokenRateLimitError):
            check_candidate_otp_send_rate_limit(
                db,
                normalized_email="quota@example.com",
                request_ip_hash="sha256:source",
                now=now,
            )


def test_postgres_quota_check_uses_transaction_advisory_lock() -> None:
    class _Dialect:
        name = "postgresql"

    class _Bind:
        dialect = _Dialect()

    class _DB:
        def __init__(self) -> None:
            self.calls: list[tuple[object, dict[str, int]]] = []

        def get_bind(self) -> _Bind:
            return _Bind()

        def execute(self, statement: object, params: dict[str, int]) -> None:
            self.calls.append((statement, params))

    db = _DB()
    rate_limit._acquire_otp_quota_lock(cast("Session", db))
    assert len(db.calls) == 1
    statement, params = db.calls[0]
    assert "pg_advisory_xact_lock" in str(statement)
    assert params["lock_key"] == rate_limit._OTP_QUOTA_ADVISORY_LOCK_KEY
