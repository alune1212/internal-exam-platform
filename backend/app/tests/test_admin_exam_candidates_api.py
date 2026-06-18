"""考试应考名单与补考授权 API 测试。"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import Candidate, Exam, ExamAttempt, ExamCandidateScope, ImportBatch
from app.services import import_service
from app.tests.conftest import build_workbook, create_question_with_options


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
    resp = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": settings.admin_password},
    )
    return {"X-Admin-Token": resp.json()["data"]["token"]}


def _create_exam(db: Session, *, status: str = "draft") -> Exam:
    exam = Exam(title="安全考试", duration_minutes=60, status=status)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def test_import_exam_candidates_adds_scope_rows() -> None:
    client, db = _build_client()
    exam = _create_exam(db)
    workbook = build_workbook(
        [
            "name",
            "employee_no",
            "department",
            "position",
            "phone_suffix",
            "email",
            "exam_group",
            "should_attend",
            "status",
            "remark",
        ],
        [
            {
                "name": "张三",
                "employee_no": "E001",
                "department": "安全部",
                "should_attend": True,
                "status": "active",
            }
        ],
    )

    resp = client.post(
        f"/api/admin/exams/{exam.id}/candidates/import",
        headers=_admin_headers(client),
        files={
            "file": (
                "candidates.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    batch = db.query(ImportBatch).one()
    assert data["batch_id"] == batch.id
    assert batch.import_type == "exam_candidates"
    assert db.query(Candidate).count() == 1
    assert db.query(ExamCandidateScope).filter_by(exam_id=exam.id).count() == 1


def test_import_exam_candidates_rejects_oversized_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = _build_client()
    exam = _create_exam(db)
    workbook = build_workbook(
        [
            "name",
            "employee_no",
            "department",
            "position",
            "phone_suffix",
            "email",
            "exam_group",
            "should_attend",
            "status",
            "remark",
        ],
        [{"name": "张三", "should_attend": True, "status": "active"}],
    )
    monkeypatch.setattr(import_service.settings, "import_max_upload_bytes", 1)

    resp = client.post(
        f"/api/admin/exams/{exam.id}/candidates/import",
        headers=_admin_headers(client),
        files={
            "file": (
                "candidates.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert resp.status_code == 413
    assert "导入文件大小不能超过 1 字节" in resp.json()["detail"]
    assert db.query(ImportBatch).count() == 0


def test_import_exam_candidates_reuses_existing_name_without_employee_no() -> None:
    client, db = _build_client()
    first_exam = _create_exam(db)
    second_exam = _create_exam(db)
    candidate = Candidate(name="人员1", status="active")
    db.add(candidate)
    db.flush()
    db.add(ExamCandidateScope(exam_id=first_exam.id, candidate_id=candidate.id))
    db.commit()
    workbook = build_workbook(
        [
            "name",
            "employee_no",
            "department",
            "position",
            "phone_suffix",
            "email",
            "exam_group",
            "should_attend",
            "status",
            "remark",
        ],
        [
            {
                "name": "人员1",
                "should_attend": True,
                "status": "active",
            },
            {
                "name": "人员2",
                "should_attend": True,
                "status": "active",
            },
        ],
    )

    resp = client.post(
        f"/api/admin/exams/{second_exam.id}/candidates/import",
        headers=_admin_headers(client),
        files={
            "file": (
                "candidates.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["success_count"] == 2
    assert data["failed_count"] == 0
    assert db.query(Candidate).count() == 2
    assert db.query(ExamCandidateScope).filter_by(exam_id=second_exam.id).count() == 2


def test_list_exam_candidates_returns_attempt_and_retake_state() -> None:
    client, db = _build_client()
    exam = _create_exam(db)
    candidate = Candidate(name="李四", employee_no="E002", status="active")
    db.add(candidate)
    db.flush()
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    attempt = ExamAttempt(
        exam_id=exam.id,
        candidate_id=candidate.id,
        status="submitted",
        started_at=create_question_with_options(db).created_at,
        submitted_at=create_question_with_options(db, stem="x").created_at,
        total_score=100,
        score=88,
        attempt_no=1,
        attempt_kind="initial",
    )
    db.add(attempt)
    db.commit()

    resp = client.get(
        f"/api/admin/exams/{exam.id}/candidates", headers=_admin_headers(client)
    )

    assert resp.status_code == 200
    row = resp.json()["data"][0]
    assert row["candidate_name"] == "李四"
    assert row["latest_attempt_status"] == "submitted"
    assert row["latest_score"] == 88
    assert row["has_unused_retake_grant"] is False


def test_remove_exam_candidate_only_allowed_for_draft_exam() -> None:
    client, db = _build_client()
    draft_exam = _create_exam(db, status="draft")
    active_exam = _create_exam(db, status="active")
    candidate = Candidate(name="王五", employee_no="E003", status="active")
    db.add(candidate)
    db.flush()
    db.add_all(
        [
            ExamCandidateScope(exam_id=draft_exam.id, candidate_id=candidate.id),
            ExamCandidateScope(exam_id=active_exam.id, candidate_id=candidate.id),
        ]
    )
    db.commit()

    ok = client.delete(
        f"/api/admin/exams/{draft_exam.id}/candidates/{candidate.id}",
        headers=_admin_headers(client),
    )
    blocked = client.delete(
        f"/api/admin/exams/{active_exam.id}/candidates/{candidate.id}",
        headers=_admin_headers(client),
    )

    assert ok.status_code == 200
    assert blocked.status_code == 409


def test_create_retake_grant_endpoint() -> None:
    client, db = _build_client()
    exam = _create_exam(db, status="active")
    candidate = Candidate(name="赵六", employee_no="E004", status="active")
    db.add(candidate)
    db.flush()
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.add(
        ExamAttempt(
            exam_id=exam.id,
            candidate_id=candidate.id,
            status="submitted",
            started_at=create_question_with_options(db).created_at,
            submitted_at=create_question_with_options(db, stem="y").created_at,
            total_score=100,
            score=72,
            attempt_no=1,
            attempt_kind="initial",
        )
    )
    db.commit()

    resp = client.post(
        f"/api/admin/exams/{exam.id}/candidates/{candidate.id}/retake-grants",
        headers=_admin_headers(client),
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["has_unused_retake_grant"] is True
