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


def test_candidate_admin_and_playback_tokens_do_not_cross_environment_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formal_key = "A" * 43
    staging_key = "B" * 43
    operator = settings.configured_active_operator[0]

    monkeypatch.setattr(settings, "token_secret", formal_key)
    formal_candidate = security.create_candidate_token(77)
    formal_admin = security.create_admin_token(operator)
    formal_playback = security.create_learning_playback_token(77, 11)
    assert security.parse_candidate_token(formal_candidate) == 77
    assert security.parse_admin_token(formal_admin) == operator
    assert security.parse_learning_playback_token(formal_playback) == (77, 11)

    monkeypatch.setattr(settings, "token_secret", staging_key)
    assert security.parse_candidate_token(formal_candidate) is None
    assert security.parse_admin_token(formal_admin) is None
    assert security.parse_learning_playback_token(formal_playback) is None

    staging_candidate = security.create_candidate_token(77)
    staging_admin = security.create_admin_token(operator)
    staging_playback = security.create_learning_playback_token(77, 11)
    assert security.parse_candidate_token(staging_candidate) == 77
    assert security.parse_admin_token(staging_admin) == operator
    assert security.parse_learning_playback_token(staging_playback) == (77, 11)

    monkeypatch.setattr(settings, "token_secret", formal_key)
    assert security.parse_candidate_token(staging_candidate) is None
    assert security.parse_admin_token(staging_admin) is None
    assert security.parse_learning_playback_token(staging_playback) is None


def test_candidate_tokens_keep_the_four_hour_boundary_and_reject_completion_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = security.create_candidate_token(42)
    monkeypatch.setattr(settings, "candidate_token_ttl_seconds", 4 * 60 * 60)
    assert security.parse_candidate_token(token) == 42
    # A registration completion credential is an opaque random value, not a
    # signed candidate subject; the shared parser must never treat it as one.
    assert security.parse_candidate_token("registration-required-credential") is None


def test_candidate_token_ttl_is_never_longer_than_four_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued_at = int((datetime.now(UTC) - timedelta(hours=4, seconds=1)).timestamp())
    payload = f"candidate:88.{issued_at}.nonce"
    token = f"{payload}.{security._sign(payload, secret=settings.token_secret)}"
    monkeypatch.setattr(settings, "candidate_token_ttl_seconds", 8 * 60 * 60)

    assert security.parse_candidate_token(token) is None


@pytest.mark.parametrize("issued_at", ["１２３", "+123", "-1", "2147483648", "9" * 11])
def test_session_tokens_reject_non_bounded_ascii_timestamps(issued_at: str) -> None:
    payload = f"admin:{settings.configured_primary_operator[0]}.{issued_at}.nonce"
    token = f"{payload}.{security._sign(payload, secret=settings.token_secret)}"

    assert not security.verify_session_token(
        token,
        subject=f"admin:{settings.configured_primary_operator[0]}",
        secret=settings.token_secret,
    )


@pytest.mark.parametrize(
    "candidate_id",
    ["0", "+1", "-1", "１２３", "2147483648", "9" * 11],
)
def test_candidate_tokens_reject_non_positive_or_out_of_range_ids(
    candidate_id: str,
) -> None:
    issued_at = int(datetime.now(UTC).timestamp())
    payload = f"candidate:{candidate_id}.{issued_at}.nonce"
    token = f"{payload}.{security._sign(payload, secret=settings.token_secret)}"

    assert security.parse_candidate_token(token) is None
