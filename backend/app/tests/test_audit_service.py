from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import AdminAuditEvent
from app.services.audit_service import record_admin_event


def _request() -> Request:
    captured: list[Request] = []
    app = FastAPI()

    @app.get("/")
    def capture(request: Request) -> dict[str, bool]:
        captured.append(request)
        return {"ok": True}

    TestClient(app).get("/", headers={"User-Agent": "audit-test-secret-agent"})
    return captured[0]


@contextmanager
def _session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    with session_local() as db:
        yield db


def test_audit_metadata_allowlist_redacts_sensitive_and_complex_values() -> None:
    with _session() as db:
        record_admin_event(
            db,
            operator_subject="primary",
            action="exam_published",
            target_type="exam",
            target_id=42,
            metadata={
                "exam_id": 42,
                "count": 3,
                "password": "secret-password",
                "token": "secret-token",
                "otp": "123456",
                "uploaded_content": "sensitive workbook content",
                "outcome_artifact": {"nested": "not allowed"},
            },
            request=_request(),
        )
        db.commit()
        event = db.query(AdminAuditEvent).one()

        assert event.metadata_json == {"exam_id": 42, "count": 3}
        assert event.request_source_hash is not None
        serialized = str(event.metadata_json) + event.request_source_hash
        for secret in (
            "secret-password",
            "secret-token",
            "123456",
            "sensitive workbook content",
            "audit-test-secret-agent",
            "testclient",
        ):
            assert secret not in serialized


def test_application_exposes_no_audit_update_or_delete_route() -> None:
    from app.main import create_app

    mutable_routes = [
        (path, method)
        for route in create_app().routes
        if (path := getattr(route, "path", ""))
        for method in getattr(route, "methods", set())
        if "audit" in path and method in {"POST", "PUT", "PATCH", "DELETE"}
    ]

    assert mutable_routes == []
