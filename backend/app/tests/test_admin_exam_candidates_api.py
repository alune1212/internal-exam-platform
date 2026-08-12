from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import Candidate, Exam, ExamCandidateScope
from app.services import invitation_service
from app.tests.conftest import build_workbook


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


def _draft_exam(db: Session) -> Exam:
    exam = Exam(title="安全考试", duration_minutes=60, status="draft")
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def _roster_workbook(*rows: dict[str, object]):
    return build_workbook(
        ["email", "candidate_name", "department", "position", "exam_group", "remark"],
        list(rows),
    )


def test_import_exam_roster_creates_pending_scope() -> None:
    client, db = _build_client()
    exam = _draft_exam(db)
    workbook = _roster_workbook(
        {"email": "u@example.com", "candidate_name": "用户", "department": "研发"}
    )

    response = client.post(
        f"/api/admin/exams/{exam.id}/candidates/import",
        headers=_admin_headers(client),
        files={
            "file": (
                "roster.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["success_count"] == 1
    candidate = db.query(Candidate).one()
    scope = db.query(ExamCandidateScope).one()
    assert candidate.status == "pending"
    assert scope.roster_email == "u@example.com"
    assert scope.roster_name == "用户"


def test_draft_roster_crud_and_published_lock() -> None:
    client, db = _build_client()
    exam = _draft_exam(db)
    headers = _admin_headers(client)

    created = client.post(
        f"/api/admin/exams/{exam.id}/candidates",
        headers=headers,
        json={"email": "u@example.com", "candidate_name": "用户"},
    )
    assert created.status_code == 200
    row = created.json()["data"]
    assert row["roster_email"] == "u@example.com"
    assert row["invitation_status"] == "not_sent"

    updated = client.patch(
        f"/api/admin/exams/{exam.id}/candidates/{row['candidate_id']}",
        headers=headers,
        json={"candidate_name": "新名单名", "remark": "备注"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["roster_name"] == "新名单名"

    listed = client.get(f"/api/admin/exams/{exam.id}/candidates", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"][0]["roster_name"] == "新名单名"

    db.refresh(exam)
    exam.status = "active"
    db.commit()
    blocked = client.patch(
        f"/api/admin/exams/{exam.id}/candidates/{row['candidate_id']}",
        headers=headers,
        json={"candidate_name": "不应修改"},
    )
    assert blocked.status_code == 409


def test_invitation_send_is_explicit_and_failed_only_resend() -> None:
    client, db = _build_client()
    exam = _draft_exam(db)
    candidate = Candidate(name="用户", email="u@example.com", status="active")
    db.add(candidate)
    db.flush()
    scope = ExamCandidateScope(
        exam_id=exam.id,
        candidate_id=candidate.id,
        roster_email="u@example.com",
        roster_name="名单名",
    )
    db.add(scope)
    exam.status = "active"
    db.commit()
    headers = _admin_headers(client)
    invitation_service.clear_invitation_email_outbox()

    send = client.post(
        f"/api/admin/exams/{exam.id}/invitations/send",
        headers=headers,
    )
    assert send.status_code == 200
    assert send.json()["data"]["accepted_count"] == 1
    assert len(invitation_service.invitation_email_outbox) == 1
    db.refresh(scope)
    assert scope.invitation_status == "sent"

    # A resend does not select the successful row.
    resend = client.post(
        f"/api/admin/exams/{exam.id}/invitations/resend",
        headers=headers,
    )
    assert resend.status_code == 200
    assert resend.json()["data"]["accepted_count"] == 0
    assert len(invitation_service.invitation_email_outbox) == 1


def test_invitation_url_is_bearer_free() -> None:
    url = invitation_service.build_invitation_url(42)
    assert url.endswith("/exams/42/start")
    assert all(secret not in url for secret in ("token", "otp", "email", "scope"))
