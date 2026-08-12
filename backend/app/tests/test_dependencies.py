from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from app.core import dependencies
from app.core.config import settings
from app.core.dependencies import CandidateAuthError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class _SessionProbe:
    def __init__(self, candidate_status: str | None) -> None:
        self.candidate_status = candidate_status
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def get(self, _model: object, _candidate_id: int, **_kwargs: object):
        if self.candidate_status is None:
            return None
        return SimpleNamespace(status=self.candidate_status)


def test_candidate_auth_closes_short_lived_session_for_active_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _SessionProbe("active")
    monkeypatch.setattr(dependencies, "parse_candidate_token", lambda _token: 42)

    assert (
        dependencies.get_current_candidate_id(
            "candidate-token", cast("Session", session)
        )
        == 42
    )
    assert session.closed


def test_candidate_auth_closes_session_before_rejecting_inactive_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _SessionProbe("inactive")
    monkeypatch.setattr(dependencies, "parse_candidate_token", lambda _token: 42)

    with pytest.raises(CandidateAuthError, match="账号暂不可用"):
        dependencies.get_current_candidate_id(
            "candidate-token", cast("Session", session)
        )
    assert session.closed


def test_candidate_auth_closes_session_before_rejecting_missing_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _SessionProbe(None)
    monkeypatch.setattr(dependencies, "parse_candidate_token", lambda _token: 42)

    with pytest.raises(CandidateAuthError, match="无效的考试人身份"):
        dependencies.get_current_candidate_id(
            "candidate-token", cast("Session", session)
        )
    assert session.closed


def test_fresh_candidate_auth_uses_and_closes_short_lived_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _SessionProbe("active")
    observed: dict[str, int | None] = {}

    def parse(token: str, *, max_age_seconds: int | None = None) -> int:
        assert token
        observed["max_age_seconds"] = max_age_seconds
        return 42

    monkeypatch.setattr(dependencies, "parse_candidate_token", parse)

    assert (
        dependencies.get_fresh_candidate_id("opaque-value", cast("Session", session))
        == 42
    )
    assert observed["max_age_seconds"] == settings.candidate_login_otp_ttl_seconds
    assert session.closed
