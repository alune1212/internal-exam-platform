from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamCandidateScope,
    ExamRetakeGrant,
)
from app.services import exam_service
from app.tests.conftest import create_question_with_options


def _build_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_local()
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), db


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    assert response.status_code == 200
    return {"X-Admin-Token": response.json()["data"]["token"]}


def _exam(
    db: Session,
    *,
    status: str = "active",
    available_from: datetime | None = None,
    available_until: datetime | None = None,
) -> Exam:
    exam = Exam(
        title="工作区考试",
        duration_minutes=60,
        status=status,
        available_from=available_from,
        available_until=available_until,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def _scope(
    db: Session,
    exam: Exam,
    *,
    status: str = "active",
    invitation_status: str = "sent",
    invitation_claimed_at: datetime | None = None,
) -> Candidate:
    sequence = db.info.get("workspace_candidate_sequence", 0) + 1
    db.info["workspace_candidate_sequence"] = sequence
    candidate = Candidate(
        name=f"工作区用户{sequence}",
        email=f"workspace-{sequence}@example.com",
        status=status,
    )
    db.add(candidate)
    db.flush()
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name or "工作区用户",
            invitation_status=invitation_status,
            invitation_claimed_at=invitation_claimed_at,
        )
    )
    db.commit()
    return candidate


def _attempt(
    db: Session,
    exam: Exam,
    candidate: Candidate,
    *,
    status: str,
    attempt_no: int,
) -> ExamAttempt:
    now = datetime.now(UTC)
    attempt = ExamAttempt(
        exam_id=exam.id,
        candidate_id=candidate.id,
        status=status,
        started_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(minutes=55),
        duration_minutes_snapshot=60,
        attempt_no=attempt_no,
        attempt_kind="retake" if attempt_no > 1 else "initial",
        submitted_at=now if status in {"submitted", "auto_submitted"} else None,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def test_workspace_aggregates_latest_attendance_and_raw_attempts(db: Session) -> None:
    exam = _exam(db)
    submitted = _scope(db, exam)
    voided_retake = _scope(db, exam)
    in_progress = _scope(db, exam, status="pending")
    auto_submitted = _scope(db, exam)
    _scope(db, exam, status="inactive", invitation_status="failed")

    _attempt(db, exam, submitted, status="submitted", attempt_no=1)
    _attempt(db, exam, voided_retake, status="submitted", attempt_no=1)
    _attempt(db, exam, voided_retake, status="voided", attempt_no=2)
    _attempt(db, exam, in_progress, status="in_progress", attempt_no=1)
    _attempt(db, exam, auto_submitted, status="auto_submitted", attempt_no=1)
    db.add(ExamRetakeGrant(exam_id=exam.id, candidate_id=voided_retake.id))
    db.commit()

    workspace = exam_service.get_exam_workspace(db, exam.id)

    assert workspace.roster_summary.total_count == 5
    assert workspace.roster_summary.active_count == 3
    assert workspace.roster_summary.pending_count == 1
    assert workspace.roster_summary.inactive_count == 1
    assert workspace.invitation_summary.sent_count == 4
    assert workspace.invitation_summary.failed_count == 1
    assert workspace.attendance_summary.not_started_count == 2
    assert workspace.attendance_summary.in_progress_count == 1
    assert workspace.attendance_summary.submitted_count == 2
    assert (
        workspace.attendance_summary.not_started_count
        + workspace.attendance_summary.in_progress_count
        + workspace.attendance_summary.submitted_count
        == workspace.roster_summary.total_count
    )
    assert workspace.attempt_summary.submitted_count == 2
    assert workspace.attempt_summary.auto_submitted_count == 1
    assert workspace.attempt_summary.in_progress_count == 1
    assert workspace.attempt_summary.voided_count == 1
    assert workspace.incident_summary.voided_count == 1
    assert workspace.incident_summary.unused_retake_count == 1
    assert workspace.next_action == "resend_failed_invitations"
    assert workspace.next_action_reason


def test_workspace_draft_readiness_and_active_window_actions(db: Session) -> None:
    draft_fix = _exam(db, status="draft")
    _scope(db, draft_fix, invitation_status="not_sent")
    assert exam_service.get_exam_workspace(db, draft_fix.id).next_action == (
        "fix_readiness"
    )

    draft_ready = _exam(db, status="draft")
    _scope(db, draft_ready, invitation_status="not_sent")
    create_question_with_options(db)
    assert exam_service.get_exam_workspace(db, draft_ready.id).next_action == "publish"

    now = datetime.now(UTC)
    upcoming = _exam(db, available_from=now + timedelta(hours=1))
    _scope(db, upcoming, invitation_status="sent")
    upcoming_workspace = exam_service.get_exam_workspace(db, upcoming.id)
    assert upcoming_workspace.next_action == "wait_for_open"
    assert upcoming_workspace.exam.availability_status == "not_started"

    ended = _exam(
        db,
        available_from=now - timedelta(hours=2),
        available_until=now - timedelta(hours=1),
    )
    _scope(db, ended, invitation_status="sent")
    assert exam_service.get_exam_workspace(db, ended.id).next_action == (
        "review_incidents"
    )


def test_workspace_next_action_precedence_covers_delivery_and_results(
    db: Session,
) -> None:
    now = datetime.now(UTC)
    exam = _exam(
        db,
        available_from=now - timedelta(hours=1),
        available_until=now + timedelta(hours=1),
    )
    candidate = _scope(
        db,
        exam,
        invitation_status="not_sent",
        invitation_claimed_at=now,
    )

    assert exam_service.get_exam_workspace(db, exam.id).next_action == (
        "wait_invitation_delivery"
    )
    invitation_summary = exam_service.get_exam_workspace(db, exam.id).invitation_summary
    assert invitation_summary.not_sent_count == 1
    assert invitation_summary.sent_count == 0
    assert invitation_summary.failed_count == 0
    assert invitation_summary.in_flight_count == 1

    scope = (
        db.query(ExamCandidateScope)
        .filter_by(exam_id=exam.id, candidate_id=candidate.id)
        .one()
    )
    scope.invitation_claimed_at = None
    scope.invitation_status = "sent"
    db.commit()
    assert exam_service.get_exam_workspace(db, exam.id).next_action == "monitor_exam"

    _attempt(db, exam, candidate, status="submitted", attempt_no=1)
    assert exam_service.get_exam_workspace(db, exam.id).next_action == (
        "release_result_details"
    )

    exam.result_details_released_at = datetime.now(UTC)
    db.commit()
    assert exam_service.get_exam_workspace(db, exam.id).next_action == "archive_exam"

    exam.status = "archived"
    db.commit()
    assert exam_service.get_exam_workspace(db, exam.id).next_action == "complete"


def test_workspace_route_is_admin_only_and_missing_exam_is_not_empty() -> None:
    client, db = _build_client()
    exam = _exam(db, status="draft")

    unauthorized = client.get(f"/api/admin/exams/{exam.id}/workspace")
    missing = client.get(
        "/api/admin/exams/999999/workspace", headers=_admin_headers(client)
    )
    authorized = client.get(
        f"/api/admin/exams/{exam.id}/workspace", headers=_admin_headers(client)
    )

    assert unauthorized.status_code == 401
    assert missing.status_code == 404
    assert authorized.status_code == 200
    payload = authorized.json()["data"]
    assert payload["exam"]["id"] == exam.id
    assert payload["readiness"]["exam_id"] == exam.id
    assert payload["next_action"] == "manage_roster"
    assert "roster_name" not in str(payload)
    assert "roster_email" not in str(payload)
