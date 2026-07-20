import logging
import smtplib
from datetime import UTC, datetime, timedelta
from typing import TypedDict

import pytest

from app.core.config import settings
from app.services import email_service


class DeliveryKwargs(TypedDict):
    challenge_id: int
    to_email: str
    candidate_name: str
    otp: str
    expires_at: datetime


def _delivery_kwargs() -> DeliveryKwargs:
    return {
        "challenge_id": 42,
        "to_email": "candidate-secret@example.com",
        "candidate_name": "Sensitive Candidate",
        "otp": "654321",
        "expires_at": datetime.now(UTC) + timedelta(minutes=10),
    }


def test_delivery_succeeds_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    attempts: list[dict[str, object]] = []
    monkeypatch.setattr(
        email_service,
        "send_candidate_login_otp",
        lambda **kwargs: attempts.append(kwargs),
    )

    with caplog.at_level(logging.INFO, logger="app.services.email_service"):
        delivered = email_service.deliver_candidate_login_otp(**_delivery_kwargs())

    assert delivered is True
    assert len(attempts) == 1
    success = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "candidate_login.email_delivery_succeeded"
    ]
    assert len(success) == 1
    assert success[0].__dict__["challenge_id"] == 42
    assert success[0].__dict__["attempt"] == 1


def test_transient_delivery_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    attempts = 0
    sleeps: list[float] = []
    monkeypatch.setattr(settings, "candidate_login_email_max_attempts", 3)
    monkeypatch.setattr(settings, "candidate_login_email_retry_base_seconds", 0.25)

    def send(**_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise email_service.TransientEmailDeliveryError()

    monkeypatch.setattr(email_service, "send_candidate_login_otp", send)

    with caplog.at_level(logging.INFO, logger="app.services.email_service"):
        delivered = email_service.deliver_candidate_login_otp(
            **_delivery_kwargs(), sleep=sleeps.append
        )

    assert delivered is True
    assert attempts == 3
    assert sleeps == [0.25, 0.5]
    retries = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "candidate_login.email_delivery_retry"
    ]
    assert [record.__dict__["attempt"] for record in retries] == [1, 2]


def test_transient_delivery_stops_after_bounded_attempts(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    attempts = 0
    monkeypatch.setattr(settings, "candidate_login_email_max_attempts", 2)
    monkeypatch.setattr(settings, "candidate_login_email_retry_base_seconds", 0.0)

    def fail(**_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        raise email_service.TransientEmailDeliveryError()

    monkeypatch.setattr(email_service, "send_candidate_login_otp", fail)

    with caplog.at_level(logging.WARNING, logger="app.services.email_service"):
        delivered = email_service.deliver_candidate_login_otp(
            **_delivery_kwargs(), sleep=lambda _seconds: None
        )

    assert delivered is False
    assert attempts == 2
    failures = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "candidate_login.email_delivery_failed"
    ]
    assert len(failures) == 1
    assert failures[0].__dict__["attempt"] == 2


def test_permanent_delivery_failure_does_not_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    sleeps: list[float] = []

    def fail(**_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        raise email_service.PermanentEmailDeliveryError()

    monkeypatch.setattr(email_service, "send_candidate_login_otp", fail)

    delivered = email_service.deliver_candidate_login_otp(
        **_delivery_kwargs(), sleep=sleeps.append
    )

    assert delivered is False
    assert attempts == 1
    assert sleeps == []


def test_delivery_logs_exclude_sensitive_values(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "candidate_login_smtp_password", "smtp-secret")
    monkeypatch.setattr(
        email_service,
        "send_candidate_login_otp",
        lambda **_kwargs: (_ for _ in ()).throw(
            email_service.PermanentEmailDeliveryError()
        ),
    )

    with caplog.at_level(logging.WARNING, logger="app.services.email_service"):
        email_service.deliver_candidate_login_otp(**_delivery_kwargs())

    rendered = " ".join(
        f"{record.getMessage()} {record.__dict__}" for record in caplog.records
    )
    assert "candidate-secret@example.com" not in rendered
    assert "Sensitive Candidate" not in rendered
    assert "654321" not in rendered
    assert "smtp-secret" not in rendered


def test_smtp_oserror_is_classified_as_transient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "candidate_login_email_delivery_mode", "smtp")

    def fail_smtp(*_args: object, **_kwargs: object) -> None:
        raise OSError("network unavailable")

    monkeypatch.setattr(email_service.smtplib, "SMTP", fail_smtp)

    with pytest.raises(email_service.TransientEmailDeliveryError):
        email_service.send_candidate_login_otp(
            to_email="candidate@example.com",
            candidate_name="Candidate",
            otp="123456",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )


def test_smtp_authentication_error_is_classified_as_permanent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "candidate_login_email_delivery_mode", "smtp")

    def fail_smtp(*_args: object, **_kwargs: object) -> None:
        raise smtplib.SMTPAuthenticationError(535, b"authentication failed")

    monkeypatch.setattr(email_service.smtplib, "SMTP", fail_smtp)

    with pytest.raises(email_service.PermanentEmailDeliveryError):
        email_service.send_candidate_login_otp(
            to_email="candidate@example.com",
            candidate_name="Candidate",
            otp="123456",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
