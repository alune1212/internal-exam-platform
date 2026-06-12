from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from app.models import Candidate, Question, QuestionOption


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
        json={
            "candidate_id": candidate.id,
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
