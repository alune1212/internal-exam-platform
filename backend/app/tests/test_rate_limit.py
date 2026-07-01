import hashlib

import pytest
from fastapi import Request
from pydantic import ValidationError

from app.core import rate_limit
from app.core.config import settings
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
    valid_password = "x" * 8

    with pytest.raises(ValidationError):
        AdminLoginRequest(username="u" * 129, password=valid_password)

    with pytest.raises(ValidationError):
        CandidateLoginRequest(name="考" * 101, phone_suffix="1234")

    with pytest.raises(ValidationError):
        CandidateLoginRequest(name="张三", employee_no="E" * 101, phone_suffix="1234")

    with pytest.raises(ValidationError):
        CandidateLoginRequest(name="张三", employee_no="E001", phone_suffix="1" * 21)
