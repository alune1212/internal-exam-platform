import hashlib
import time
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
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


class _YieldingQueue(deque[float]):
    def __len__(self) -> int:
        length = super().__len__()
        time.sleep(0.001)
        return length


class _YieldingAttempts(OrderedDict[tuple[str, str], deque[float]]):
    def __getitem__(self, key: object) -> deque[float]:
        time.sleep(0.001)
        return super().__getitem__(cast("tuple[str, str]", key))


def _request_for_ip(ip: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/admin/login",
            "headers": headers,
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


def test_public_token_rate_limit_caps_rejected_identifier_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limit._attempts.clear()
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)
    monkeypatch.setattr(settings, "public_token_rate_limit_window_seconds", 60)
    monkeypatch.setattr(settings, "public_token_rate_limit_max_keys", 4)
    monkeypatch.setattr(rate_limit, "monotonic", lambda: 0.0)

    rate_limit.check_public_token_rate_limit(
        _request_for_ip("192.0.2.1"),
        bucket="candidate-login-verify",
        identifier="first",
    )
    for index in range(20):
        with pytest.raises(rate_limit.PublicTokenRateLimitError):
            rate_limit.check_public_token_rate_limit(
                _request_for_ip("192.0.2.1"),
                bucket="candidate-login-verify",
                identifier=f"challenge:{index}",
            )

    assert len(rate_limit._attempts) <= settings.public_token_rate_limit_max_keys
    assert set(rate_limit._attempts) == {
        ("candidate-login-verify", "ip:192.0.2.1"),
        (
            "candidate-login-verify",
            "id:sha256:" + hashlib.sha256(b"first").hexdigest(),
        ),
    }


def test_public_token_rate_limit_concurrent_same_bucket_stays_within_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)
    monkeypatch.setattr(settings, "public_token_rate_limit_window_seconds", 60)
    monkeypatch.setattr(settings, "public_token_rate_limit_max_keys", 8)
    rate_limit._attempts[
        ("candidate-login", f"id:{rate_limit._normalize_identifier('same-account')}")
    ] = _YieldingQueue()

    def attempt(_index: int) -> bool:
        try:
            rate_limit.check_public_token_rate_limit(
                _request_for_ip("192.0.2.1"),
                bucket="candidate-login",
                identifier="same-account",
                include_client_ip=False,
            )
        except rate_limit.PublicTokenRateLimitError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=32) as executor:
        accepted = sum(executor.map(attempt, range(32)))

    assert accepted <= settings.public_token_rate_limit_count


def test_public_token_rate_limit_concurrent_distinct_key_churn_stays_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "_attempts", _YieldingAttempts())
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 100)
    monkeypatch.setattr(settings, "public_token_rate_limit_window_seconds", 1)

    current_time = -10.0

    def current_monotonic() -> float:
        return current_time

    monkeypatch.setattr(rate_limit, "monotonic", current_monotonic)
    monkeypatch.setattr(
        settings, "public_token_rate_limit_max_keys", 100, raising=False
    )
    for index in range(16):
        rate_limit.check_public_token_rate_limit(
            _request_for_ip("192.0.2.1"),
            bucket="candidate-login",
            identifier=f"seed-{index}",
            include_client_ip=False,
        )

    current_time = 0.0
    monkeypatch.setattr(settings, "public_token_rate_limit_max_keys", 4)
    original_prune = rate_limit._prune

    def delayed_prune(queue: deque[float], now: float, window_seconds: int) -> None:
        time.sleep(0.001)
        original_prune(queue, now, window_seconds)

    monkeypatch.setattr(rate_limit, "_prune", delayed_prune)

    def attempt(index: int) -> None:
        rate_limit.check_public_token_rate_limit(
            _request_for_ip("192.0.2.1"),
            bucket="candidate-login",
            identifier=f"account-{index}",
            include_client_ip=False,
        )

    with ThreadPoolExecutor(max_workers=32) as executor:
        list(executor.map(attempt, range(128)))

    assert len(rate_limit._attempts) <= settings.public_token_rate_limit_max_keys


def test_public_token_rate_limit_uses_peer_ip_not_forged_forwarded_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limit._attempts.clear()
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)
    monkeypatch.setattr(settings, "public_token_rate_limit_window_seconds", 60)

    rate_limit.check_public_token_rate_limit(
        _request_for_ip("172.30.0.2", "198.51.100.1"),
        bucket="candidate",
        identifier=None,
    )
    with pytest.raises(rate_limit.PublicTokenRateLimitError):
        rate_limit.check_public_token_rate_limit(
            _request_for_ip("172.30.0.2", "198.51.100.2"),
            bucket="candidate",
            identifier=None,
        )


def test_authenticated_candidates_do_not_share_one_source_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limit._attempts.clear()
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)
    monkeypatch.setattr(settings, "public_token_rate_limit_window_seconds", 60)
    request = _request_for_ip("192.0.2.1")

    rate_limit.check_public_token_rate_limit(
        request,
        bucket="attempt-write",
        identifier="candidate:1",
        include_client_ip=False,
    )
    with pytest.raises(rate_limit.PublicTokenRateLimitError):
        rate_limit.check_public_token_rate_limit(
            request,
            bucket="attempt-write",
            identifier="candidate:1",
            include_client_ip=False,
        )
    rate_limit.check_public_token_rate_limit(
        request,
        bucket="attempt-write",
        identifier="candidate:2",
        include_client_ip=False,
    )
    assert not any(key[1].startswith("ip:") for key in rate_limit._attempts)


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
