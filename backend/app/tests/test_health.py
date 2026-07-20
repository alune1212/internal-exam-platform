from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.main import app, create_app


def _build_readiness_client(db: Session) -> TestClient:
    readiness_app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    readiness_app.dependency_overrides[get_db] = override_get_db
    return TestClient(readiness_app)


def test_health_returns_ok_status() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "service": "internal-exam-platform"},
        "message": "ok",
    }


def test_readiness_returns_ready_when_database_and_media_are_available(
    db: Session,
) -> None:
    Path(settings.learning_media_storage_dir).mkdir(parents=True)
    client = _build_readiness_client(db)

    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "status": "ready",
            "database": "ok",
            "learning_media": "ok",
        },
        "message": "ok",
    }


def test_readiness_returns_non_sensitive_503_when_database_is_unavailable(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    Path(settings.learning_media_storage_dir).mkdir(parents=True)
    sensitive_error = "postgresql://exam:secret-password@db/internal_exam"

    def fail_execute(*_args: object, **_kwargs: object) -> None:
        raise SQLAlchemyError(sensitive_error)

    monkeypatch.setattr(db, "execute", fail_execute)
    client = _build_readiness_client(db)

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "服务尚未就绪。"}
    assert sensitive_error not in response.text


def test_readiness_returns_503_when_media_directory_is_unavailable(db: Session) -> None:
    client = _build_readiness_client(db)

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "服务尚未就绪。"}
