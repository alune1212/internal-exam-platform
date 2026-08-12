from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_candidate_token
from app.main import create_app
from app.models import AdminAuditEvent, ExamAttempt, ExamCandidateScope, ExamRetakeGrant
from app.services import exam_service
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
    submit_answers,
)


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


def _seed_started_attempt(db: Session):
    exam = create_exam(db, title="事故恢复考试")
    candidate = create_candidate(db, name="事故考生")
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name or "待注册",
        )
    )
    db.commit()
    create_question_with_options(db, analysis="发布后解析")
    start = exam_service.start_exam(db, exam.id, candidate.id)
    return exam, candidate, start


def test_result_detail_release_api_is_admin_only_audited_and_irreversible() -> None:
    client, db = _build_client()
    exam, candidate, start = _seed_started_attempt(db)
    submit_answers(db, start.attempt_id, start.questions, ["A"])
    candidate_headers = {"X-Candidate-Token": create_candidate_token(candidate.id)}

    hidden = client.get(
        f"/api/attempts/{start.attempt_id}/result", headers=candidate_headers
    )
    unauthenticated = client.post(
        f"/api/admin/exams/{exam.id}/result-details/release",
        json={"confirmation_title": exam.title},
    )
    wrong_title = client.post(
        f"/api/admin/exams/{exam.id}/result-details/release",
        headers=_admin_headers(client),
        json={"confirmation_title": "错误名称"},
    )
    released = client.post(
        f"/api/admin/exams/{exam.id}/result-details/release",
        headers=_admin_headers(client),
        json={"confirmation_title": exam.title},
    )
    visible = client.get(
        f"/api/attempts/{start.attempt_id}/result", headers=candidate_headers
    )
    repeated = client.post(
        f"/api/admin/exams/{exam.id}/result-details/release",
        headers=_admin_headers(client),
        json={"confirmation_title": exam.title},
    )

    assert hidden.status_code == 200
    assert hidden.json()["data"]["questions"] == []
    assert unauthenticated.status_code == 401
    assert wrong_title.status_code == 422
    assert released.status_code == 200
    assert visible.json()["data"]["questions"][0]["correct_answer_snapshot"] == "A"
    assert repeated.status_code == 409
    event = db.query(AdminAuditEvent).filter_by(action="result_details_released").one()
    assert event.target_id == str(exam.id)
    assert "token" not in str(event.metadata_json).lower()


def test_void_and_bulk_retake_apis_preserve_incident_and_row_outcomes() -> None:
    client, db = _build_client()
    exam, first, first_start = _seed_started_attempt(db)
    submit_answers(db, first_start.attempt_id, first_start.questions, ["A"])
    second = create_candidate(db, name="第二考生")
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=second.id,
            roster_email=second.email,
            roster_name=second.name or "待注册",
        )
    )
    db.commit()
    second_start = exam_service.start_exam(db, exam.id, second.id)
    headers = _admin_headers(client)

    voided = client.post(
        f"/api/admin/exams/{exam.id}/attempts/{first_start.attempt_id}/void",
        headers=headers,
        json={"reason": "正式考试期间出现网络事故"},
    )
    incidents = client.get(f"/api/admin/exams/{exam.id}/incidents", headers=headers)
    preview = client.post(
        f"/api/admin/exams/{exam.id}/retakes/preview",
        headers=headers,
        json={"candidate_ids": [first.id, second.id], "void_existing": True},
    )
    preview_data = preview.json()["data"]
    applied = client.post(
        f"/api/admin/exams/{exam.id}/retakes/apply",
        headers=headers,
        json={
            "candidate_ids": [first.id, second.id],
            "void_existing": True,
            "confirmation_title": exam.title,
            "preview_fingerprint": preview_data["fingerprint"],
            "reason": "正式考试期间出现网络事故",
        },
    )

    assert voided.status_code == 200
    assert incidents.status_code == 200
    assert incidents.json()["data"][0]["attempt_id"] == first_start.attempt_id
    assert preview.status_code == 200
    assert preview_data["eligible_count"] == 2
    assert applied.status_code == 200
    assert applied.json()["data"]["granted_count"] == 2
    first_attempt = db.get(ExamAttempt, first_start.attempt_id)
    second_attempt = db.get(ExamAttempt, second_start.attempt_id)
    assert first_attempt is not None
    assert first_attempt.status == "voided"
    assert second_attempt is not None
    assert second_attempt.status == "voided"
    assert db.query(ExamRetakeGrant).filter_by(used_at=None).count() == 2
    assert db.query(AdminAuditEvent).filter_by(action="attempt_voided").count() == 1
    assert (
        db.query(AdminAuditEvent).filter_by(action="bulk_retake_granted").count() == 1
    )


def test_candidate_surface_has_no_ranking_route() -> None:
    client, _db = _build_client()
    response = client.get(
        "/api/rankings",
        headers={"X-Candidate-Token": create_candidate_token(1)},
    )
    assert response.status_code == 404
