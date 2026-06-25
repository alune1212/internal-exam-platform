from fastapi import Request

from app.core import rate_limit
from app.core.config import settings


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
