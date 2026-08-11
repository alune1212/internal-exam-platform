from datetime import UTC, datetime, timedelta

import pytest

from app.core import security
from app.core.config import settings


def test_admin_and_candidate_tokens_use_separate_ttls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued_at = int((datetime.now(UTC) - timedelta(seconds=120)).timestamp())
    admin_payload = f"admin:{settings.configured_primary_operator[0]}.{issued_at}.nonce"
    candidate_payload = f"candidate:77.{issued_at}.nonce"
    admin_token = (
        f"{admin_payload}.{security._sign(admin_payload, secret=settings.token_secret)}"
    )
    candidate_token = f"{candidate_payload}.{security._sign(candidate_payload, secret=settings.token_secret)}"

    monkeypatch.setattr(settings, "admin_token_ttl_seconds", 60)
    monkeypatch.setattr(settings, "candidate_token_ttl_seconds", 180)

    assert security.parse_admin_token(admin_token) is None
    assert security.parse_candidate_token(candidate_token) == 77


def test_rotated_secret_rejects_previously_signed_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = security.create_admin_token(settings.configured_primary_operator[0])
    candidate_token = security.create_candidate_token(77)

    monkeypatch.setattr(settings, "token_secret", "fresh-rotated-secret-value")

    assert security.parse_admin_token(admin_token) is None
    assert security.parse_candidate_token(candidate_token) is None
