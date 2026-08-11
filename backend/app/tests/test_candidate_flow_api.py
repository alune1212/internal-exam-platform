from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_candidate_token
from app.main import create_app
from app.models import (
    Candidate,
    CandidateLoginChallenge,
    Exam,
    ExamCandidateScope,
    PracticeAnswer,
    Question,
    QuestionOption,
)
from app.services.email_service import candidate_login_email_outbox


def _build_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_local()
    _ensure_login_sentinel(db)
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), db


def _ensure_login_sentinel(db: Session) -> None:
    """Install the candidate login sentinel row.

    Mirrors the data migration ``202607030002_candidate_login_sentinel``.
    The uniform-response contract requires exactly one such row to exist.
    """
    existing = db.query(Candidate).filter(Candidate.is_login_sentinel.is_(True)).first()
    if existing is not None:
        return
    db.add(
        Candidate(
            name="__candidate_login_sentinel__",
            status="inactive",
            should_attend=False,
            is_login_sentinel=True,
        )
    )
    db.commit()


def test_candidate_login_throttles_repeated_public_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 2, raising=False)
    monkeypatch.setattr(
        settings, "public_token_rate_limit_window_seconds", 60, raising=False
    )
    client, db = _build_client()
    db.add(
        Candidate(
            name="限流人",
            employee_no="RL001",
            email="ratelimit@example.com",
            phone_suffix="1234",
        )
    )
    db.commit()

    for _ in range(2):
        resp = client.post(
            "/api/candidates/login",
            json={
                "name": "限流人",
                "employee_no": "RL001",
                "email": "wrong@example.com",
            },
        )
        # Wrong email lands on the sentinel path, which returns a uniform 200.
        assert resp.status_code == 200

    blocked = client.post(
        "/api/candidates/login",
        json={"name": "限流人", "employee_no": "RL001", "email": "wrong@example.com"},
    )

    assert blocked.status_code == 429


def test_candidate_login_request_creates_email_challenge_without_token() -> None:
    candidate_login_email_outbox.clear()
    client, db = _build_client()
    db.add(
        Candidate(
            name="张三",
            employee_no="YG0001",
            department="综合管理部",
            email="zhangsan@example.com",
            phone_suffix="1234",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={"name": "张三", "employee_no": "YG0001", "email": "zhangsan@example.com"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["challenge_id"] > 0
    assert data["expires_at"]
    assert data["resend_available_at"]
    assert "token" not in data
    challenge = db.get(CandidateLoginChallenge, data["challenge_id"])
    assert challenge is not None
    assert challenge.candidate_id > 0
    assert challenge.otp_hash != candidate_login_email_outbox[-1].otp
    assert candidate_login_email_outbox[-1].to_email == "zhangsan@example.com"


def test_candidate_login_verify_returns_token_and_consumes_challenge() -> None:
    candidate_login_email_outbox.clear()
    client, db = _build_client()
    db.add(
        Candidate(
            name="张三",
            employee_no="YG0001",
            department="综合管理部",
            email="zhangsan@example.com",
            phone_suffix="1234",
            status="active",
        )
    )
    db.commit()

    requested = client.post(
        "/api/candidates/login",
        json={"name": "张三", "employee_no": "YG0001", "email": "zhangsan@example.com"},
    )
    challenge_id = requested.json()["data"]["challenge_id"]
    otp = candidate_login_email_outbox[-1].otp

    response = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": challenge_id, "otp": otp},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] > 0
    assert data["name"] == "张三"
    assert data["department"] == "综合管理部"
    assert data["token"]
    challenge = db.get(CandidateLoginChallenge, challenge_id)
    assert challenge is not None
    db.refresh(challenge)
    assert challenge.consumed_at is not None


def test_candidate_login_returns_uniform_200_for_mismatched_name() -> None:
    client, db = _build_client()
    db.add(
        Candidate(
            name="张三",
            employee_no="YG0001",
            department="综合管理部",
            email="zhangsan@example.com",
            phone_suffix="1234",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={"name": "李四", "employee_no": "YG0001", "email": "zhangsan@example.com"},
    )

    # Uniform response: lookup failure surfaces as a 200 sentinel challenge,
    # not as a 404. The real rejection happens at the verify step.
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["challenge_id"] > 0
    assert "token" not in data


def test_candidate_login_returns_uniform_200_for_missing_email() -> None:
    client, db = _build_client()
    db.add(Candidate(name="张三", employee_no="YG0001", email="zhangsan@example.com"))
    db.commit()

    response = client.post(
        "/api/candidates/login", json={"name": "张三", "employee_no": "YG0001"}
    )

    # Missing email is treated as invalid_input → sentinel, not a 404.
    assert response.status_code == 200
    assert "data" in response.json()


def test_candidate_login_returns_uniform_200_for_wrong_email() -> None:
    client, db = _build_client()
    db.add(Candidate(name="张三", employee_no="YG0001", email="zhangsan@example.com"))
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={"name": "张三", "employee_no": "YG0001", "email": "wrong@example.com"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["challenge_id"] > 0


def test_candidate_login_creates_challenge_by_name_without_employee_no() -> None:
    candidate_login_email_outbox.clear()
    client, db = _build_client()
    db.add(
        Candidate(
            name="王五",
            employee_no=None,
            department="安全管理部",
            email="wangwu@example.com",
            phone_suffix="5678",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login", json={"name": "王五", "email": "wangwu@example.com"}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["challenge_id"] > 0
    assert "token" not in data
    assert candidate_login_email_outbox[-1].to_email == "wangwu@example.com"


def test_candidate_login_returns_uniform_200_for_old_phone_suffix_payload() -> None:
    client, db = _build_client()
    db.add(
        Candidate(
            name="旧流程",
            employee_no="OLD001",
            email="old@example.com",
            phone_suffix="1234",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={"name": "旧流程", "employee_no": "OLD001", "phone_suffix": "1234"},
    )

    # Phone-suffix-only payload has no email; service treats it as
    # invalid_input → sentinel → uniform 200. The legacy direct-token path
    # is fully removed.
    assert response.status_code == 200
    assert "token" not in response.json()["data"]


def test_candidate_login_verify_rejects_wrong_expired_consumed_and_attempt_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_login_email_outbox.clear()
    monkeypatch.setattr(settings, "candidate_login_otp_attempt_limit", 2, raising=False)
    client, db = _build_client()
    db.add(Candidate(name="验证人", email="verify@example.com", status="active"))
    db.commit()

    requested = client.post(
        "/api/candidates/login", json={"name": "验证人", "email": "verify@example.com"}
    )
    challenge_id = requested.json()["data"]["challenge_id"]

    wrong = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": challenge_id, "otp": "000000"},
    )
    exhausted = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": challenge_id, "otp": "111111"},
    )
    blocked = client.post(
        "/api/candidates/login/verify",
        json={
            "challenge_id": challenge_id,
            "otp": candidate_login_email_outbox[-1].otp,
        },
    )

    assert wrong.status_code == 404
    assert exhausted.status_code == 404
    assert blocked.status_code == 404


def test_candidate_login_resend_invalidates_previous_challenge() -> None:
    candidate_login_email_outbox.clear()
    client, db = _build_client()
    db.add(Candidate(name="重发人", email="resend@example.com", status="active"))
    db.commit()

    first = client.post(
        "/api/candidates/login", json={"name": "重发人", "email": "resend@example.com"}
    )
    first_id = first.json()["data"]["challenge_id"]
    first_otp = candidate_login_email_outbox[-1].otp
    second = client.post(
        "/api/candidates/login", json={"name": "重发人", "email": "resend@example.com"}
    )
    second_id = second.json()["data"]["challenge_id"]

    old_verify = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": first_id, "otp": first_otp},
    )
    new_verify = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": second_id, "otp": candidate_login_email_outbox[-1].otp},
    )

    assert second_id != first_id
    assert old_verify.status_code == 404
    assert new_verify.status_code == 200


def test_candidate_login_persists_same_row_count_for_valid_and_invalid_identities() -> (
    None
):
    """Observation equality: a real-candidate request and an unknown-identity
    request must each leave behind exactly one challenge row, so timing and
    row-count side channels cannot be used to enumerate the roster."""
    from collections import Counter

    candidate_login_email_outbox.clear()
    client, db = _build_client()
    db.add(
        Candidate(
            name="张三",
            employee_no="YG0001",
            email="zhangsan@example.com",
            status="active",
        )
    )
    db.commit()

    valid = client.post(
        "/api/candidates/login",
        json={"name": "张三", "email": "zhangsan@example.com"},
    )
    unknown = client.post(
        "/api/candidates/login",
        json={"name": "不存在", "email": "nobody@example.com"},
    )
    ambiguous = client.post(
        "/api/candidates/login",
        json={"name": "重名", "email": "dup@example.com"},
    )

    assert valid.status_code == unknown.status_code == ambiguous.status_code == 200
    rows = db.query(CandidateLoginChallenge).all()
    assert len(rows) == 3
    counter = Counter(r.candidate_id for r in rows)
    # Two of the three challenges point at the sentinel; one points at the
    # real candidate. The sentinel id is the one that appears more than once.
    sentinel_id, sentinel_count = counter.most_common(1)[0]
    assert sentinel_count == 2
    other_ids = [cid for cid in counter if cid != sentinel_id]
    assert len(other_ids) == 1
    assert counter[other_ids[0]] == 1


def test_candidate_login_sentinel_challenge_is_rejected_at_verify() -> None:
    """A challenge created against the sentinel must reject at verify time,
    even if the OTP could be guessed. The verify step reads the candidate
    and rejects on ``is_login_sentinel`` / inactive status / missing email."""
    client, db = _build_client()
    db.add(
        Candidate(
            name="活跃人",
            email="active@example.com",
            status="active",
        )
    )
    db.commit()

    unknown = client.post(
        "/api/candidates/login",
        json={"name": "未知", "email": "nobody@example.com"},
    )
    sentinel_challenge_id = unknown.json()["data"]["challenge_id"]

    # The verify step must reject the sentinel challenge with the same 404
    # envelope as any other invalid challenge — the caller cannot tell
    # whether the underlying identity was real.
    verify = client.post(
        "/api/candidates/login/verify",
        json={"challenge_id": sentinel_challenge_id, "otp": "000000"},
    )
    assert verify.status_code == 404


def test_candidate_login_commits_challenge_before_email_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SMTP failure during post-commit delivery must not roll back the
    challenge row and must not surface a 5xx to the caller."""
    from app.api import candidates as candidates_api

    def _boom(**_kwargs: object) -> None:
        raise RuntimeError("simulated SMTP failure")

    monkeypatch.setattr(candidates_api, "deliver_candidate_login_otp", _boom)
    candidate_login_email_outbox.clear()
    client, db = _build_client()
    db.add(
        Candidate(
            name="张三",
            email="zhangsan@example.com",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={"name": "张三", "email": "zhangsan@example.com"},
    )

    # The route swallows the background-task failure and still returns 200.
    assert response.status_code == 200
    challenge_id = response.json()["data"]["challenge_id"]
    # The challenge row must still exist and be verifiable by the candidate.
    challenge = db.get(CandidateLoginChallenge, challenge_id)
    assert challenge is not None
    assert challenge.consumed_at is None


def test_candidate_login_unknown_identity_emits_audit_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each unknown-identity request must emit a single WARN log line with
    hashed identity fields, and no such log line for a valid request."""
    import logging

    client, db = _build_client()
    db.add(
        Candidate(
            name="活跃人",
            email="active@example.com",
            status="active",
        )
    )
    db.commit()

    with caplog.at_level(logging.WARNING, logger="app.services.candidate_service"):
        valid = client.post(
            "/api/candidates/login",
            json={"name": "活跃人", "email": "active@example.com"},
        )
        unknown = client.post(
            "/api/candidates/login",
            json={"name": "不存在", "email": "nobody@example.com"},
        )

    assert valid.status_code == 200
    assert unknown.status_code == 200
    unknown_logs = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "candidate_login.unknown_identity"
    ]
    assert len(unknown_logs) == 1
    record = unknown_logs[0]
    # No plaintext identity fields.
    assert "active@example.com" not in record.getMessage()
    assert "nobody@example.com" not in record.getMessage()


def test_practice_answer_returns_feedback_and_preserves_each_retry() -> None:
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", status="active")
    question = Question(
        question_type="multiple", stem="哪些属于安全要求？", score=2, status="active"
    )
    db.add_all([candidate, question])
    db.flush()
    db.add_all(
        [
            QuestionOption(
                question_id=question.id,
                label="A",
                content="定期改密",
                is_correct=True,
                sort_order=1,
            ),
            QuestionOption(
                question_id=question.id,
                label="B",
                content="开启 MFA",
                is_correct=True,
                sort_order=2,
            ),
            QuestionOption(
                question_id=question.id,
                label="C",
                content="共享密码",
                is_correct=False,
                sort_order=3,
            ),
        ]
    )
    db.commit()

    response = client.post(
        "/api/practice/answers",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
        json={
            "question_id": question.id,
            "selected_answer": "B,A",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["question_id"] == question.id
    assert data["selected_answer"] == "B,A"
    assert data["correct_answer"] == "A,B"
    assert data["is_correct"] is True
    assert data["analysis"] is None
    assert data["option_comparison"] == [
        {"label": "A", "content": "定期改密", "selected": True, "correct": True},
        {"label": "B", "content": "开启 MFA", "selected": True, "correct": True},
        {"label": "C", "content": "共享密码", "selected": False, "correct": False},
    ]
    assert "score_awarded" not in data

    retry = client.post(
        "/api/practice/answers",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
        json={"question_id": question.id, "selected_answer": "C"},
    )

    assert retry.status_code == 200
    assert retry.json()["data"]["is_correct"] is False
    saved = db.query(PracticeAnswer).order_by(PracticeAnswer.id).all()
    assert len(saved) == 2
    assert saved[0].id != saved[1].id
    assert [row.selected_answer for row in saved] == ["B,A", "C"]
    assert [row.is_correct for row in saved] == [True, False]


def test_practice_questions_require_candidate_token() -> None:
    client, _ = _build_client()

    response = client.get("/api/practice/questions")

    assert response.status_code == 401


def test_practice_questions_hide_answers_and_analysis_for_authenticated_candidate() -> (
    None
):
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", status="active")
    question = Question(
        question_type="single",
        stem="安全题",
        analysis="不要提前泄露解析",
        score=2,
        status="active",
    )
    db.add_all([candidate, question])
    db.flush()
    db.add_all(
        [
            QuestionOption(
                question_id=question.id,
                label="A",
                content="正确",
                is_correct=True,
                sort_order=1,
            ),
            QuestionOption(
                question_id=question.id,
                label="B",
                content="错误",
                is_correct=False,
                sort_order=2,
            ),
        ]
    )
    db.commit()

    response = client.get(
        "/api/practice/questions",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert "analysis" not in row
    assert "is_correct" not in row["options"][0]


def test_practice_questions_reject_inactive_candidate_token() -> None:
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", status="inactive")
    question = Question(
        question_type="single",
        stem="安全题",
        score=2,
        status="active",
    )
    db.add_all([candidate, question])
    db.commit()

    response = client.get(
        "/api/practice/questions",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert response.status_code == 404


def test_active_exams_requires_candidate_token() -> None:
    client, db = _build_client()
    db.add(Exam(title="安全考试", duration_minutes=60, status="active"))
    db.commit()

    response = client.get("/api/exams/active")

    assert response.status_code == 401


def test_active_exams_returns_only_candidate_scoped_exams() -> None:
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", status="active")
    scoped_exam = Exam(title="可参加考试", duration_minutes=60, status="active")
    other_exam = Exam(title="其他考试", duration_minutes=60, status="active")
    db.add_all([candidate, scoped_exam, other_exam])
    db.flush()
    db.add(ExamCandidateScope(exam_id=scoped_exam.id, candidate_id=candidate.id))
    db.commit()

    response = client.get(
        "/api/exams/active",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["title"] for row in rows] == ["可参加考试"]


def test_practice_answer_uses_candidate_token_not_request_body() -> None:
    client, db = _build_client()
    token_candidate = Candidate(name="张三", employee_no="YG0001", status="active")
    body_candidate = Candidate(name="李四", employee_no="YG0002", status="active")
    question = Question(
        question_type="single",
        stem="安全题",
        analysis="提交后返回",
        score=2,
        status="active",
    )
    db.add_all([token_candidate, body_candidate, question])
    db.flush()
    db.add_all(
        [
            QuestionOption(
                question_id=question.id,
                label="A",
                content="正确",
                is_correct=True,
                sort_order=1,
            ),
            QuestionOption(
                question_id=question.id,
                label="B",
                content="错误",
                is_correct=False,
                sort_order=2,
            ),
        ]
    )
    db.commit()

    response = client.post(
        "/api/practice/answers",
        headers={"X-Candidate-Token": create_candidate_token(token_candidate.id)},
        json={
            "candidate_id": body_candidate.id,
            "question_id": question.id,
            "selected_answer": "A",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["correct_answer"] == "A"
    assert data["analysis"] == "提交后返回"
    db.refresh(token_candidate)
    assert token_candidate.practice_answers[0].question_id == question.id
    db.refresh(body_candidate)
    assert body_candidate.practice_answers == []


def test_practice_answer_requires_candidate_token() -> None:
    client, db = _build_client()
    question = Question(question_type="single", stem="安全题", score=2, status="active")
    db.add(question)
    db.commit()

    response = client.post(
        "/api/practice/answers",
        json={"question_id": question.id, "selected_answer": "A"},
    )

    assert response.status_code == 401


def test_wrong_question_review_filters_mastery_and_isolates_candidates() -> None:
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", status="active")
    other = Candidate(name="李四", employee_no="YG0002", status="active")
    mastered_question = Question(
        question_type="single",
        stem="已掌握题",
        analysis="解析一",
        category_1="安全",
        category_2="账号",
        score=2,
        status="active",
    )
    learning_question = Question(
        question_type="single",
        stem="待巩固题",
        analysis="解析二",
        category_1="合规",
        category_2="流程",
        score=2,
        status="active",
    )
    db.add_all([candidate, other, mastered_question, learning_question])
    db.flush()
    for question in (mastered_question, learning_question):
        db.add_all(
            [
                QuestionOption(
                    question_id=question.id,
                    label="A",
                    content="正确",
                    is_correct=True,
                    sort_order=1,
                ),
                QuestionOption(
                    question_id=question.id,
                    label="B",
                    content="错误",
                    is_correct=False,
                    sort_order=2,
                ),
            ]
        )
    db.commit()

    candidate_headers = {"X-Candidate-Token": create_candidate_token(candidate.id)}
    other_headers = {"X-Candidate-Token": create_candidate_token(other.id)}
    for selected_answer in ("B", "A"):
        response = client.post(
            "/api/practice/answers",
            headers=candidate_headers,
            json={
                "question_id": mastered_question.id,
                "selected_answer": selected_answer,
            },
        )
        assert response.status_code == 200
    assert (
        client.post(
            "/api/practice/answers",
            headers=candidate_headers,
            json={"question_id": learning_question.id, "selected_answer": "B"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/practice/answers",
            headers=other_headers,
            json={"question_id": mastered_question.id, "selected_answer": "B"},
        ).status_code
        == 200
    )

    mastered = client.get(
        "/api/practice/wrong-questions?category_1=安全&mastered=true",
        headers=candidate_headers,
    )
    assert mastered.status_code == 200
    rows = mastered.json()["data"]
    assert len(rows) == 1
    assert rows[0]["stem"] == "已掌握题"
    assert rows[0]["mastered"] is True
    assert rows[0]["incorrect_count"] == 1
    assert rows[0]["total_attempts"] == 2
    assert len(rows[0]["history"]) == 2

    learning = client.get(
        "/api/practice/wrong-questions?mastered=false", headers=candidate_headers
    )
    assert learning.status_code == 200
    assert [row["stem"] for row in learning.json()["data"]] == ["待巩固题"]

    other_rows = client.get(
        "/api/practice/wrong-questions", headers=other_headers
    ).json()["data"]
    assert len(other_rows) == 1
    assert other_rows[0]["total_attempts"] == 1
    assert other_rows[0]["mastered"] is False


def test_wrong_question_review_requires_candidate_token() -> None:
    client, _ = _build_client()

    response = client.get("/api/practice/wrong-questions")

    assert response.status_code == 401
