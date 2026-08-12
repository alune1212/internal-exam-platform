"""候选人 attempt IDOR 防护集成测试。"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import _sign, create_candidate_token
from app.main import create_app
from app.models import ExamAttempt, ExamAttemptAnswer, ExamCandidateScope
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
    client, db = _build_client()
    candidate = create_candidate(db)
    token = create_candidate_token(candidate.id)
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
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name or "待注册",
        )
    )
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
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name or "待注册",
        )
    )
    db.commit()
    create_question_with_options(db, analysis="答案解析")
    start = exam_service.start_exam(db, exam.id, candidate.id)

    resp = client.get(
        f"/api/attempts/{start.attempt_id}/result",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert resp.status_code == 409
    assert "交卷" in resp.json()["detail"]


def _started_attempt(db: Session) -> tuple[int, int, str, str]:
    exam = create_exam(db)
    candidate = create_candidate(db)
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name or "待注册",
        )
    )
    db.commit()
    create_question_with_options(db)
    start = exam_service.start_exam(db, exam.id, candidate.id)
    assert start.attempt_session_credential is not None
    return (
        start.attempt_id,
        candidate.id,
        create_candidate_token(candidate.id),
        start.attempt_session_credential,
    )


def test_attempt_read_requires_current_device_session_credential() -> None:
    client, db = _build_client()
    attempt_id, candidate_id, token, credential = _started_attempt(db)
    candidate_headers = {"X-Candidate-Token": token}

    missing = client.get(f"/api/attempts/{attempt_id}", headers=candidate_headers)
    wrong = client.get(
        f"/api/attempts/{attempt_id}",
        headers={**candidate_headers, "X-Attempt-Session": "wrong-device"},
    )
    accepted = client.get(
        f"/api/attempts/{attempt_id}",
        headers={**candidate_headers, "X-Attempt-Session": credential},
    )

    assert missing.status_code == 409
    assert wrong.status_code == 409
    assert accepted.status_code == 200
    assert accepted.json()["data"]["candidate_id"] == candidate_id
    persisted = db.get(ExamAttempt, attempt_id)
    assert persisted is not None
    assert persisted.attempt_session_hash != credential
    assert len(persisted.attempt_session_hash or "") == 64


def test_revisioned_save_rejects_stale_device_without_overwrite() -> None:
    client, db = _build_client()
    attempt_id, _candidate_id, token, credential = _started_attempt(db)
    headers = {"X-Candidate-Token": token, "X-Attempt-Session": credential}
    attempt = db.get(ExamAttempt, attempt_id)
    assert attempt is not None
    question_id = attempt.questions[0].id

    first = client.post(
        f"/api/attempts/{attempt_id}/answers/save",
        headers=headers,
        json={
            "answer_revision": 0,
            "answers": [{"attempt_question_id": question_id, "selected_answer": "A"}],
        },
    )
    stale = client.post(
        f"/api/attempts/{attempt_id}/answers/save",
        headers=headers,
        json={
            "answer_revision": 0,
            "answers": [{"attempt_question_id": question_id, "selected_answer": "B"}],
        },
    )

    assert first.status_code == 200
    assert first.json()["data"]["answer_revision"] == 1
    assert stale.status_code == 409
    db.expire_all()
    answer = db.query(ExamAttemptAnswer).one()
    assert answer.selected_answer == "A"
    refreshed_attempt = db.get(ExamAttempt, attempt_id)
    assert refreshed_attempt is not None
    assert refreshed_attempt.answer_revision == 1


def test_fresh_otp_takeover_rotates_device_session_without_resetting_attempt() -> None:
    client, db = _build_client()
    attempt_id, _candidate_id, token, credential = _started_attempt(db)
    before = db.get(ExamAttempt, attempt_id)
    assert before is not None
    ends_at = before.ends_at
    question_ids = [question.id for question in before.questions]

    takeover = client.post(
        f"/api/attempts/{attempt_id}/takeover",
        headers={"X-Candidate-Token": token},
    )

    assert takeover.status_code == 200
    takeover_data = takeover.json()["data"]
    assert takeover_data["attempt_session_generation"] == 2
    new_credential = takeover_data["attempt_session_credential"]
    assert new_credential != credential
    old_device = client.get(
        f"/api/attempts/{attempt_id}",
        headers={"X-Candidate-Token": token, "X-Attempt-Session": credential},
    )
    new_device = client.get(
        f"/api/attempts/{attempt_id}",
        headers={"X-Candidate-Token": token, "X-Attempt-Session": new_credential},
    )
    assert old_device.status_code == 409
    assert new_device.status_code == 200
    db.expire_all()
    after = db.get(ExamAttempt, attempt_id)
    assert after is not None
    assert after.ends_at == ends_at
    assert [question.id for question in after.questions] == question_ids


def test_takeover_rejects_candidate_token_older_than_fresh_otp_window() -> None:
    client, db = _build_client()
    attempt_id, candidate_id, _token, _credential = _started_attempt(db)
    issued_at = int(
        (
            datetime.now(UTC)
            - timedelta(seconds=settings.candidate_login_otp_ttl_seconds + 1)
        ).timestamp()
    )
    payload = f"candidate:{candidate_id}.{issued_at}.stale-otp-session"
    stale_token = f"{payload}.{_sign(payload, secret=settings.token_secret)}"

    response = client.post(
        f"/api/attempts/{attempt_id}/takeover",
        headers={"X-Candidate-Token": stale_token},
    )

    assert response.status_code == 401
    assert "重新通过邮件验证码" in response.json()["detail"]


def test_stale_attempt_without_roster_scope_is_rejected_across_surfaces() -> None:
    client, db = _build_client()
    attempt_id, _candidate_id, token, credential = _started_attempt(db)
    attempt = db.get(ExamAttempt, attempt_id)
    assert attempt is not None
    question_id = attempt.questions[0].id
    scope = db.query(ExamCandidateScope).one()
    db.delete(scope)
    db.commit()
    headers = {"X-Candidate-Token": token, "X-Attempt-Session": credential}

    read = client.get(f"/api/attempts/{attempt_id}", headers=headers)
    save = client.post(
        f"/api/attempts/{attempt_id}/answers/save",
        headers=headers,
        json={
            "answer_revision": 0,
            "answers": [{"attempt_question_id": question_id, "selected_answer": "A"}],
        },
    )
    submit = client.post(
        f"/api/attempts/{attempt_id}/submit",
        headers=headers,
        json={"submit_type": "manual"},
    )
    takeover = client.post(
        f"/api/attempts/{attempt_id}/takeover",
        headers={"X-Candidate-Token": token},
    )

    assert read.status_code == 403
    assert save.status_code == 403
    assert submit.status_code == 403
    assert takeover.status_code == 403

    result_attempt_id, result_candidate_id, result_token, _ = _started_attempt(db)
    exam_service.submit_attempt(db, result_attempt_id, "manual")
    result_scope = (
        db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.candidate_id == result_candidate_id)
        .one()
    )
    db.delete(result_scope)
    db.commit()
    result = client.get(
        f"/api/attempts/{result_attempt_id}/result",
        headers={"X-Candidate-Token": result_token},
    )
    assert result.status_code == 404
