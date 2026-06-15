"""候选人 attempt IDOR 防护集成测试。"""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app


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


def test_attempt_routes_accept_candidate_header() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Id": "1"})
    assert resp.status_code == 404


def test_attempt_routes_reject_invalid_candidate_id() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Id": "not-int"})
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


def test_result_requires_candidate_header() -> None:
    client, _ = _build_client()
    resp = client.get("/api/attempts/1/result")
    assert resp.status_code == 401
