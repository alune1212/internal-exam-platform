"""admin 鉴权集成测试。"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, settings
from app.core.database import Base, get_db
from app.core.security import _sign, create_session_token, verify_session_token
from app.main import create_app
from app.models import ExamCandidateScope, ImportBatch
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


def test_admin_login_throttles_repeated_public_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 2, raising=False)
    monkeypatch.setattr(
        settings, "public_token_rate_limit_window_seconds", 60, raising=False
    )
    client, _ = _build_client()

    for _ in range(2):
        resp = client.post(
            "/api/admin/login",
            json={"username": "rate-limit-admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    blocked = client.post(
        "/api/admin/login",
        json={"username": "rate-limit-admin", "password": "wrong"},
    )

    assert blocked.status_code == 429


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
    assert body["data"]["token"] != settings.admin_password


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
    login = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    token = login.json()["data"]["token"]
    resp = client.get(
        "/api/admin/exams",
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_admin_exams_rejects_password_as_token() -> None:
    client, _ = _build_client()
    resp = client.get(
        "/api/admin/exams",
        headers={"X-Admin-Token": settings.admin_password},
    )
    assert resp.status_code == 401


def test_admin_exams_rejects_wrong_token() -> None:
    client, _ = _build_client()
    resp = client.get(
        "/api/admin/exams",
        headers={"X-Admin-Token": "wrong"},
    )
    assert resp.status_code == 401


def test_admin_exams_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _build_client()
    token = create_session_token(settings.admin_username)
    monkeypatch.setattr(settings, "token_ttl_seconds", -1)

    resp = client.get(
        "/api/admin/exams",
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 401


def test_admin_token_rejects_future_issued_at() -> None:
    issued_at = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
    payload = f"{settings.admin_username}.{issued_at}.nonce"
    token = f"{payload}.{_sign(payload, secret=settings.token_secret)}"

    assert (
        verify_session_token(
            token, subject=settings.admin_username, secret=settings.token_secret
        )
        is False
    )


def test_production_rejects_default_admin_password_and_token_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production")

    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            admin_password="strong-password",  # noqa: S106
            token_secret="change-me-in-production",  # noqa: S106
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("admin_password", "local-dev-admin-password"),
        ("token_secret", "local-dev-token-secret-change-before-production"),
    ],
)
def test_production_rejects_repository_sample_secrets(field: str, value: str) -> None:
    kwargs = {
        "environment": "production",
        "admin_password": "strong-password",
        "token_secret": "prod-token-secret",
        "cors_origins": "https://exam.example.com",
    }
    kwargs[field] = value

    with pytest.raises(ValidationError, match=field.upper()):
        Settings(**kwargs)


@pytest.mark.parametrize(
    "cors_origins",
    [
        "",
        "*",
        "https://exam.example.com,*",
        "http://exam.example.com",
        "http://localhost:5173",
        "http://127.0.0.1:8080",
        "http://0.0.0.0:8080",
    ],
)
def test_production_rejects_dangerous_cors_origins(cors_origins: str) -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            environment="production",
            admin_password="strong-password",  # noqa: S106
            token_secret="prod-token-secret",  # noqa: S106
            cors_origins=cors_origins,
        )


def test_production_accepts_explicit_https_cors_origins() -> None:
    configured = Settings(
        environment="production",
        admin_password="strong-password",  # noqa: S106
        token_secret="prod-token-secret",  # noqa: S106
        cors_origins="https://exam.example.com, https://admin.example.com",
    )

    assert configured.cors_origin_list == [
        "https://exam.example.com",
        "https://admin.example.com",
    ]


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
    resp = client.get("/api/admin/imports/templates/questions")
    assert resp.status_code == 401


def test_admin_import_failure_report_download_returns_workbook() -> None:
    client, db = _build_client()
    db.add(
        ImportBatch(
            import_type="questions",
            file_name="questions.xlsx",
            total_count=2,
            success_count=1,
            failed_count=1,
            status="completed",
            error_report=[{"row_number": 3, "reason": "题干不能为空"}],
        )
    )
    db.commit()
    batch = db.query(ImportBatch).one()
    token = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    ).json()["data"]["token"]

    resp = client.get(
        f"/api/admin/imports/{batch.id}/failure-report",
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(resp.content))
    assert workbook.sheetnames == ["导入批次", "失败明细"]
    meta = workbook["导入批次"]
    assert meta.cell(1, 1).value == "字段"
    assert meta.cell(1, 2).value == "值"
    assert meta.cell(2, 1).value == "导入类型"
    assert meta.cell(2, 2).value == "questions"
    assert meta.cell(3, 2).value == "questions.xlsx"
    assert meta.cell(4, 2).value == 2
    assert meta.cell(5, 2).value == 1
    assert meta.cell(6, 2).value == 1
    sheet = workbook["失败明细"]
    assert sheet.cell(1, 1).value == "row_number"
    assert sheet.cell(2, 1).value == 3
    assert sheet.cell(2, 2).value == "题干不能为空"


def test_admin_import_failure_report_returns_empty_detail_sheet_without_failures() -> (
    None
):
    client, db = _build_client()
    db.add(
        ImportBatch(
            import_type="exam_candidates",
            file_name="名单.xlsx",
            total_count=2,
            success_count=2,
            failed_count=0,
            status="completed",
            error_report=[],
        )
    )
    db.commit()
    batch = db.query(ImportBatch).one()
    token = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    ).json()["data"]["token"]

    resp = client.get(
        f"/api/admin/imports/{batch.id}/failure-report",
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 200
    workbook = load_workbook(BytesIO(resp.content))
    assert workbook["导入批次"].cell(2, 2).value == "exam_candidates"
    assert workbook["失败明细"].max_row == 1


def test_admin_import_failure_report_returns_404_for_missing_batch() -> None:
    client, _ = _build_client()
    token = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    ).json()["data"]["token"]

    resp = client.get(
        "/api/admin/imports/999/failure-report",
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 404


def test_admin_candidate_template_download_returns_workbook() -> None:
    client, _ = _build_client()
    login = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    token = login.json()["data"]["token"]

    resp = client.get(
        "/api/admin/imports/templates/candidates",
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(resp.content))
    assert workbook.active.cell(1, 1).value == "name"


def test_admin_report_export_returns_workbook() -> None:
    client, _ = _build_client()
    login = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    token = login.json()["data"]["token"]

    resp = client.get(
        "/api/admin/reports/export",
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(resp.content))
    assert workbook.sheetnames == ["成绩报表", "题目正确率", "错题统计", "参考状态"]


def test_admin_score_report_accepts_exam_filter() -> None:
    client, db = _build_client()
    first_exam = create_exam(db, title="第一场")
    second_exam = create_exam(db, title="第二场")
    candidate = create_candidate(db, employee_no="E001")
    db.add_all(
        [
            ExamCandidateScope(exam_id=first_exam.id, candidate_id=candidate.id),
            ExamCandidateScope(exam_id=second_exam.id, candidate_id=candidate.id),
        ]
    )
    db.commit()
    create_question_with_options(db)
    first_start = exam_service.start_exam(db, first_exam.id, candidate.id)
    submit_answers(db, first_start.attempt_id, first_start.questions, ["A"])
    second_start = exam_service.start_exam(db, second_exam.id, candidate.id)
    submit_answers(db, second_start.attempt_id, second_start.questions, ["B"])
    token = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    ).json()["data"]["token"]

    resp = client.get(
        "/api/admin/reports/scores",
        params={"exam_id": first_exam.id},
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert len(rows) == 1
    assert rows[0]["exam_title"] == "第一场"
