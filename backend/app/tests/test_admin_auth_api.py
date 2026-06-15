"""admin 鉴权集成测试。"""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
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


def test_admin_login_returns_token() -> None:
    client, _ = _build_client()
    resp = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "token" in body["data"]


def test_admin_login_rejects_wrong_password() -> None:
    client, _ = _build_client()
    resp = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_admin_exams_requires_token() -> None:
    client, _ = _build_client()
    resp = client.get("/api/admin/exams")
    assert resp.status_code == 401


def test_admin_exams_accepts_valid_token() -> None:
    client, _ = _build_client()
    resp = client.get(
        "/api/admin/exams",
        headers={"X-Admin-Token": settings.admin_password},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_admin_exams_rejects_wrong_token() -> None:
    client, _ = _build_client()
    resp = client.get(
        "/api/admin/exams",
        headers={"X-Admin-Token": "wrong"},
    )
    assert resp.status_code == 401


def test_admin_questions_requires_token() -> None:
    client, _ = _build_client()
    resp = client.get("/api/admin/questions")
    assert resp.status_code == 401


def test_admin_reports_requires_token() -> None:
    client, _ = _build_client()
    resp = client.get("/api/admin/reports/scores")
    assert resp.status_code == 401


def test_admin_imports_requires_token() -> None:
    client, _ = _build_client()
    resp = client.get("/api/admin/imports/templates")
    assert resp.status_code == 401
