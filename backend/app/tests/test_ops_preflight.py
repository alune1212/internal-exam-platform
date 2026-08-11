from datetime import UTC, datetime
from typing import cast

import pytest

from app.ops import preflight


def test_smtp_probe_rejects_non_formal_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight.settings, "environment", "development")

    with pytest.raises(preflight.PreflightError):
        preflight.send_smtp_probe("operator@example.com")


def test_smtp_probe_sends_redacted_formal_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deliveries: list[dict[str, object]] = []
    monkeypatch.setattr(preflight.settings, "environment", "internal")
    monkeypatch.setattr(
        preflight.settings, "candidate_login_email_delivery_mode", "smtp"
    )
    monkeypatch.setattr(
        preflight,
        "send_candidate_login_otp",
        lambda **kwargs: deliveries.append(kwargs),
    )

    result = preflight.send_smtp_probe("Operator@Example.com")

    assert result["status"] == "passed"
    assert result["recipient_domain"] == "example.com"
    assert "operator" not in str(result).lower()
    assert deliveries[0]["otp"] == "000000"
    assert cast("datetime", deliveries[0]["expires_at"]) > datetime.now(UTC)
