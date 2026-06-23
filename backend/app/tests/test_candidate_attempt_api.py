"""候选人 attempt IDOR 防护集成测试。"""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_candidate_token
from app.main import create_app
from app.models import ExamCandidateScope
from app.services import exam_service
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
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


def test_attempt_routes_require_candidate_header() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1")
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_attempt_routes_accept_candidate_token() -> None:
    client, _ = _build_client()
    token = create_candidate_token(1)
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Token": token})
    assert resp.status_code == 404


def test_attempt_routes_reject_invalid_candidate_token() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Token": "not-valid"})
    assert resp.status_code == 401


def test_attempt_routes_reject_forged_candidate_id_header() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Id": "1"})
    assert resp.status_code == 401


def test_save_answers_requires_candidate_header() -> None:
    client, _ = _build_client()
    resp = client.post(
        "/api/attempts/1/answers/save",
        json={"answers": []},
    )
    assert resp.status_code == 401


def test_submit_requires_candidate_header() -> None:
    client, _ = _build_client()
    resp = client.post(
        "/api/attempts/1/submit",
        json={"submit_type": "manual"},
    )
    assert resp.status_code == 401


def test_public_submit_rejects_non_manual_submit_type() -> None:
    client, db = _build_client()
    exam = create_exam(db)
    candidate = create_candidate(db)
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.commit()
    create_question_with_options(db)
    start = exam_service.start_exam(db, exam.id, candidate.id)
    token = create_candidate_token(candidate.id)

    resp = client.post(
        f"/api/attempts/{start.attempt_id}/submit",
        headers={"X-Candidate-Token": token},
        json={"submit_type": "auto"},
    )

    assert resp.status_code == 422


def test_result_requires_candidate_header() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1/result")
    assert resp.status_code == 401


def test_result_rejects_in_progress_attempt_before_submission() -> None:
    client, db = _build_client()
    exam = create_exam(db)
    candidate = create_candidate(db)
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.commit()
    create_question_with_options(db, analysis="答案解析")
    start = exam_service.start_exam(db, exam.id, candidate.id)

    resp = client.get(
        f"/api/attempts/{start.attempt_id}/result",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert resp.status_code == 409
    assert "交卷" in resp.json()["detail"]
