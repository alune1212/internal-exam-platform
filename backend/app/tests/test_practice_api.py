from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_candidate_token
from app.main import create_app
from app.tests.conftest import create_candidate, create_question_with_options


@pytest.fixture
def practice_client(db: Session) -> Iterator[TestClient]:
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client


def test_practice_questions_paginate_and_rate_limit(
    practice_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = create_candidate(db)
    questions = [
        create_question_with_options(db, stem=f"练习题 {index}") for index in range(3)
    ]
    headers = {"X-Candidate-Token": create_candidate_token(candidate.id)}
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)

    response = practice_client.get(
        "/api/practice/questions",
        params={"limit": 1, "offset": 1},
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [questions[1].id]
    assert response.json()["data"][0]["options"][0]["label"] == "A"

    limited = practice_client.get(
        "/api/practice/questions",
        params={"limit": 1, "offset": 1},
        headers=headers,
    )

    assert limited.status_code == 429


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 2**31}],
)
def test_practice_questions_reject_invalid_pagination(
    practice_client: TestClient,
    db: Session,
    params: dict[str, int],
) -> None:
    candidate = create_candidate(db)
    response = practice_client.get(
        "/api/practice/questions",
        params=params,
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert response.status_code == 422


def test_wrong_questions_paginate_and_rate_limit(
    practice_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = create_candidate(db)
    headers = {"X-Candidate-Token": create_candidate_token(candidate.id)}
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)

    response = practice_client.get("/api/practice/wrong-questions", headers=headers)
    limited = practice_client.get("/api/practice/wrong-questions", headers=headers)

    assert response.status_code == 200
    assert limited.status_code == 429


def test_wrong_questions_reject_offset_above_signed_integer(
    practice_client: TestClient, db: Session
) -> None:
    candidate = create_candidate(db)
    response = practice_client.get(
        "/api/practice/wrong-questions",
        params={"offset": 2**31},
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert response.status_code == 422
