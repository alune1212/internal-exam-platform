"""Focused email-account authentication and active-session authorization tests."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.dependencies import require_admin
from app.main import create_app
from app.models import (
    AdminAuditEvent,
    Candidate,
    CandidateLoginChallenge,
    Exam,
    ExamCandidateScope,
)
from app.services import candidate_service
from app.services.email_service import candidate_login_email_outbox


def _build_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_factory()
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    # The account-directory router is still behind the production admin
    # dependency; this local test override avoids coupling auth tests to the
    # operator credential fixture.
    app.dependency_overrides[require_admin] = lambda: "test-operator"
    return TestClient(app), db


@pytest.fixture(autouse=True)
def test_otp(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "candidate_login_test_otp", "123456")
    monkeypatch.setattr(settings, "candidate_login_email_delivery_mode", "memory")
    candidate_login_email_outbox.clear()
    yield
    candidate_login_email_outbox.clear()


def _request_and_verify(client: TestClient, email: str) -> dict:
    requested = client.post("/api/candidates/login", json={"email": email})
    assert requested.status_code == 200, requested.text
    challenge_id = requested.json()["data"]["challenge_id"]
    verified = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": challenge_id, "otp": "123456"},
    )
    assert verified.status_code == 200, verified.text
    return verified.json()["data"]


def test_login_schema_is_email_only_and_forbids_legacy_identity_fields() -> None:
    client, _db = _build_client()
    legacy_employee_key = "employee" + "_no"
    response = client.post(
        "/api/candidates/login",
        json={"email": "user@example.com", "name": "legacy", legacy_employee_key: "E1"},
    )
    assert response.status_code == 422


def test_existing_active_account_returns_authenticated_outcome() -> None:
    client, db = _build_client()
    db.add(Candidate(email="active@example.com", name="Active", status="active"))
    db.commit()

    data = _request_and_verify(client, " ACTIVE@Example.com ")

    assert data["outcome"] == "authenticated"
    assert data["account"]["email"] == "active@example.com"
    assert data["account"]["display_name"] == "Active"
    assert data["token"]
    token_expires_at = datetime.fromisoformat(
        data["token_expires_at"].replace("Z", "+00:00")
    )
    assert timedelta(0) < token_expires_at - datetime.now(UTC) <= timedelta(hours=4)


def test_unknown_mailbox_receives_real_otp_and_registration_credential() -> None:
    client, db = _build_client()

    data = _request_and_verify(client, "new@example.com")

    assert data["outcome"] == "registration_required"
    assert data["email"] == "new@example.com"
    assert data["registration_credential"]
    assert data["registration_expires_at"]
    assert candidate_login_email_outbox[-1].to_email == "new@example.com"
    assert db.query(Candidate).count() == 0


def test_pending_account_registration_activates_without_overwriting_scope_name() -> (
    None
):
    client, db = _build_client()
    pending = Candidate(email="pending@example.com", name=None, status="pending")
    db.add(pending)
    db.commit()

    data = _request_and_verify(client, "pending@example.com")
    assert data["outcome"] == "registration_required"
    completed = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Confirmed Name",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["data"]["outcome"] == "authenticated"
    db.refresh(pending)
    assert pending.status == "active"
    assert pending.name == "Confirmed Name"


def test_pending_scoped_account_returns_roster_name_suggestion_only() -> None:
    client, db = _build_client()
    pending = Candidate(email="invited@example.com", name=None, status="pending")
    exam = Exam(title="Invited", duration_minutes=30, status="draft")
    db.add_all([pending, exam])
    db.flush()
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=pending.id,
            roster_email="invited@example.com",
            roster_name="Roster Name",
        )
    )
    db.commit()

    data = _request_and_verify(client, "invited@example.com")
    assert data["outcome"] == "registration_required"
    assert data["suggested_display_name"] == "Roster Name"
    db.refresh(pending)
    assert pending.name is None


def test_inactive_account_correct_otp_returns_account_unavailable() -> None:
    client, _db = _build_client()
    _db.add(Candidate(email="inactive@example.com", name="Inactive", status="inactive"))
    _db.commit()

    data = _request_and_verify(client, "inactive@example.com")

    assert data["outcome"] == "account_unavailable"
    assert "token" not in data
    assert "registration_credential" not in data


def test_registration_credential_is_single_use_and_expiring() -> None:
    client, db = _build_client()
    data = _request_and_verify(client, "replay@example.com")
    payload = {
        "registration_credential": data["registration_credential"],
        "display_name": "Replay User",
    }
    first = client.post("/api/candidates/register/complete", json=payload)
    second = client.post("/api/candidates/register/complete", json=payload)
    assert first.status_code == 200
    assert second.status_code == 400

    data = _request_and_verify(client, "expired@example.com")
    challenge = (
        db.query(CandidateLoginChallenge)
        .filter(CandidateLoginChallenge.email == "expired@example.com")
        .one()
    )
    challenge.registration_credential_expires_at = datetime.now(UTC) - timedelta(
        seconds=1
    )
    db.commit()
    expired = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Expired User",
        },
    )
    assert expired.status_code == 400


def test_registration_completion_does_not_overwrite_a_racing_active_name() -> None:
    client, db = _build_client()
    data = _request_and_verify(client, "race@example.com")
    db.add(Candidate(email="race@example.com", name="Winning Name", status="active"))
    db.commit()

    completed = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Losing Name",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["account"]["display_name"] == "Winning Name"
    replay = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Another Name",
        },
    )
    assert replay.status_code == 400


def test_registration_unique_race_pending_winner_is_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = _build_client()
    data = _request_and_verify(client, "pending-race@example.com")
    winner = Candidate(email="pending-race@example.com", name=None, status="pending")
    db.add(winner)
    db.commit()

    original_lookup = candidate_service._find_account_by_email
    lookup_count = 0

    def race_lookup(db_session: Session, email: str) -> Candidate | None:
        nonlocal lookup_count
        lookup_count += 1
        if lookup_count == 1:
            return None
        return original_lookup(db_session, email)

    monkeypatch.setattr(candidate_service, "_find_account_by_email", race_lookup)
    completed = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Pending Winner",
        },
    )

    assert completed.status_code == 200, completed.text
    assert completed.json()["data"]["account"]["display_name"] == "Pending Winner"
    db.refresh(winner)
    assert winner.status == "active"
    assert winner.name == "Pending Winner"
    challenge = (
        db.query(CandidateLoginChallenge)
        .filter(CandidateLoginChallenge.email == "pending-race@example.com")
        .one()
    )
    db.refresh(challenge)
    assert challenge.registration_credential_consumed_at is not None
    replay = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Replay",
        },
    )
    assert replay.status_code == 400


def test_registration_unique_race_inactive_winner_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = _build_client()
    data = _request_and_verify(client, "inactive-race@example.com")
    winner = Candidate(
        email="inactive-race@example.com", name="Inactive Winner", status="inactive"
    )
    db.add(winner)
    db.commit()

    original_lookup = candidate_service._find_account_by_email
    lookup_count = 0

    def race_lookup(db_session: Session, email: str) -> Candidate | None:
        nonlocal lookup_count
        lookup_count += 1
        if lookup_count == 1:
            return None
        return original_lookup(db_session, email)

    monkeypatch.setattr(candidate_service, "_find_account_by_email", race_lookup)
    completed = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Should Not Activate",
        },
    )

    assert completed.status_code == 403, completed.text
    db.refresh(winner)
    assert winner.status == "inactive"
    assert winner.name == "Inactive Winner"
    challenge = (
        db.query(CandidateLoginChallenge)
        .filter(CandidateLoginChallenge.email == "inactive-race@example.com")
        .one()
    )
    db.refresh(challenge)
    assert challenge.registration_credential_consumed_at is not None
    replay = client.post(
        "/api/candidates/register/complete",
        json={
            "registration_credential": data["registration_credential"],
            "display_name": "Replay",
        },
    )
    assert replay.status_code == 400


def test_challenge_cleanup_keeps_recent_expired_rows_for_quota_evidence() -> None:
    client, db = _build_client()
    requested = client.post(
        "/api/candidates/login", json={"email": "recent-expired@example.com"}
    )
    assert requested.status_code == 200
    challenge = db.get(
        CandidateLoginChallenge, requested.json()["data"]["challenge_id"]
    )
    assert challenge is not None
    challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    # A subsequent request runs bounded opportunistic cleanup, but the row is
    # still inside the configured retention window and must remain queryable.
    next_request = client.post(
        "/api/candidates/login", json={"email": "other@example.com"}
    )
    assert next_request.status_code == 200
    assert db.get(CandidateLoginChallenge, challenge.id) is not None


def test_profile_exposes_read_only_email_and_only_allows_display_name_edit() -> None:
    client, db = _build_client()
    db.add(Candidate(email="profile@example.com", name="Before", status="active"))
    db.commit()
    token = _request_and_verify(client, "profile@example.com")["token"]

    profile = client.get("/api/account/profile", headers={"X-Candidate-Token": token})
    assert profile.status_code == 200
    assert profile.json()["data"]["email"] == "profile@example.com"
    assert "token" not in profile.json()["data"]

    edited = client.patch(
        "/api/account/profile",
        headers={"X-Candidate-Token": token},
        json={"display_name": "After"},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["display_name"] == "After"
    rejected_email = client.patch(
        "/api/account/profile",
        headers={"X-Candidate-Token": token},
        json={"display_name": "Nope", "email": "other@example.com"},
    )
    assert rejected_email.status_code == 422


def test_admin_search_and_status_controls_take_effect_on_existing_token() -> None:
    client, db = _build_client()
    db.add(
        Candidate(email="operator-target@example.com", name="Target", status="active")
    )
    db.commit()
    target = (
        db.query(Candidate)
        .filter(Candidate.email == "operator-target@example.com")
        .one()
    )
    token = _request_and_verify(client, target.email)["token"]

    found = client.get("/api/admin/accounts", params={"search": "OPERATOR-TARGET"})
    assert found.status_code == 200
    assert found.json()["data"][0]["email"] == "operator-target@example.com"

    deactivated = client.patch(
        f"/api/admin/accounts/{target.id}/status", json={"status": "inactive"}
    )
    assert deactivated.status_code == 200
    event = (
        db.query(AdminAuditEvent)
        .filter(AdminAuditEvent.action == "account_deactivated")
        .order_by(AdminAuditEvent.id.desc())
        .first()
    )
    assert event is not None
    assert event.target_id == str(target.id)
    assert event.metadata_json == {
        "account_id": target.id,
        "from_status": "active",
        "to_status": "inactive",
    }
    assert "operator-target@example.com" not in str(event.metadata_json)
    blocked = client.get("/api/account/profile", headers={"X-Candidate-Token": token})
    assert blocked.status_code == 401

    reactivated = client.post(f"/api/admin/accounts/{target.id}/activate")
    assert reactivated.status_code == 200
    restored = client.get("/api/account/profile", headers={"X-Candidate-Token": token})
    assert restored.status_code == 200
