"""Focused coverage for the administrator ranking endpoint."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import ExamCandidateScope
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


def test_admin_ranking_endpoint_returns_frozen_identity_and_rank() -> None:
    client, db = _build_client()
    exam = create_exam(db, title="正式考试")
    candidate = create_candidate(db, name="名单姓名", email="roster@example.com")
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_name="冻结姓名",
            roster_email="frozen@example.com",
        )
    )
    db.commit()
    create_question_with_options(db, stem="考试题", score=10)
    started = exam_service.start_exam(db, exam.id, candidate.id)
    submit_answers(db, started.attempt_id, started.questions, ["A"])

    login = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    token = login.json()["data"]["token"]
    response = client.get(
        "/api/admin/reports/rankings",
        params={"exam_id": exam.id},
        headers={"X-Admin-Token": token},
    )

    assert response.status_code == 200
    assert response.json()["data"] == [
        {
            "rank": 1,
            "candidate_id": candidate.id,
            "roster_name": "冻结姓名",
            "roster_email": "frozen@example.com",
            "department": None,
            "position": None,
            "exam_group": None,
            "roster_remark": None,
            "exam_id": exam.id,
            "exam_title": "正式考试",
            "score": 10.0,
            "total_score": 10.0,
            "submitted_at": response.json()["data"][0]["submitted_at"],
        }
    ]


def test_admin_ranking_endpoint_requires_admin_token() -> None:
    client, _db = _build_client()

    response = client.get("/api/admin/reports/rankings", params={"exam_id": 1})

    assert response.status_code == 401
