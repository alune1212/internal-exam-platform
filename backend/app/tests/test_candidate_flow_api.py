from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_candidate_token
from app.main import create_app
from app.models import Candidate, Exam, ExamCandidateScope, Question, QuestionOption


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


def test_candidate_login_returns_persisted_candidate_by_employee_no() -> None:
    client, db = _build_client()
    db.add(
        Candidate(
            name="张三", employee_no="YG0001", department="综合管理部", status="active"
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login", json={"name": "张三", "employee_no": "YG0001"}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] > 0
    assert data["name"] == "张三"
    assert data["department"] == "综合管理部"
    assert data["token"]


def test_candidate_login_returns_persisted_candidate_by_name_without_employee_no() -> (
    None
):
    client, db = _build_client()
    db.add(
        Candidate(
            name="王五", employee_no=None, department="安全管理部", status="active"
        )
    )
    db.commit()

    response = client.post("/api/candidates/login", json={"name": "王五"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] > 0
    assert data["name"] == "王五"
    assert data["department"] == "安全管理部"
    assert data["token"]


def test_practice_answer_scores_and_persists_result() -> None:
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
    assert data["score_awarded"] == 2


def test_practice_questions_hide_answers_and_analysis() -> None:
    client, db = _build_client()
    question = Question(
        question_type="single",
        stem="安全题",
        analysis="不要提前泄露解析",
        score=2,
        status="active",
    )
    db.add(question)
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

    response = client.get("/api/practice/questions")

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert "analysis" not in row
    assert "is_correct" not in row["options"][0]


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
    assert response.json()["data"]["correct_answer"] == "A"
    assert response.json()["data"]["analysis"] == "提交后返回"
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
