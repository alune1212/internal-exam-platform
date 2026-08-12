from collections.abc import Iterator
from io import BytesIO
from typing import cast

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import rate_limit
from app.core.config import settings
from app.core.database import Base
from app.main import app
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamQuestionPool,
    Question,
    QuestionOption,
)
from app.schemas.attempt import AnswerSaveItem, AnswerSaveRequest
from app.services import exam_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_public_token_rate_limit() -> Iterator[None]:
    rate_limit._attempts.clear()
    yield
    rate_limit._attempts.clear()


@pytest.fixture(autouse=True)
def isolate_learning_media(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_media_storage_dir", str(tmp_path / "media"))


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(engine)


def _test_auto_pool_exam_ids(db: Session) -> set[int]:
    return cast(
        "set[int]",
        db.info.setdefault("test_auto_pool_exam_ids", set()),
    )


def create_exam(db: Session, **kwargs) -> Exam:
    """创建考试的测试辅助函数。"""
    defaults = {"title": "默认考试", "duration_minutes": 60, "status": "active"}
    defaults.update(kwargs)
    exam = Exam(**defaults)
    auto_pool = defaults.get("status") == "active"
    db.add(exam)
    db.commit()
    db.refresh(exam)
    if auto_pool:
        _test_auto_pool_exam_ids(db).add(exam.id)
        _repair_missing_active_exam_pools_for_test(db)
    return exam


def create_candidate(db: Session, **kwargs) -> Candidate:
    """创建考生的测试辅助函数。"""
    sequence = int(db.info.get("test_candidate_sequence", 0)) + 1
    db.info["test_candidate_sequence"] = sequence
    defaults = {
        "name": "张三",
        "email": f"candidate-{sequence}@example.com",
        "status": "active",
    }
    defaults.update(kwargs)
    candidate = Candidate(**defaults)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def create_question_with_options(db: Session, **kwargs) -> Question:
    """创建题目及选项的测试辅助函数。"""
    defaults = {
        "question_type": "single",
        "stem": "题目内容",
        "score": 2,
        "status": "active",
    }
    defaults.update(kwargs)
    question = Question(**defaults)
    db.add(question)
    db.flush()
    options = [
        QuestionOption(
            question_id=question.id,
            label="A",
            content="选项A",
            is_correct=True,
            sort_order=0,
        ),
        QuestionOption(
            question_id=question.id,
            label="B",
            content="选项B",
            is_correct=False,
            sort_order=1,
        ),
    ]
    db.add_all(options)
    db.commit()
    db.refresh(question)
    _repair_missing_active_exam_pools_for_test(db)
    return question


def _repair_missing_active_exam_pools_for_test(db: Session) -> None:
    auto_pool_exam_ids = _test_auto_pool_exam_ids(db)
    exam_ids = [
        exam.id
        for exam in db.identity_map.values()
        if isinstance(exam, Exam)
        and exam.id in auto_pool_exam_ids
        and exam.status == "active"
        and db.query(ExamAttempt.id).filter(ExamAttempt.exam_id == exam.id).first()
        is None
    ]
    if not exam_ids:
        return
    questions = (
        db.query(Question)
        .filter(Question.status == "active")
        .order_by(Question.id)
        .all()
    )
    for exam_id in exam_ids:
        db.query(ExamQuestionPool).filter(ExamQuestionPool.exam_id == exam_id).delete()
        for index, active_question in enumerate(questions):
            db.add(
                ExamQuestionPool(
                    exam_id=exam_id,
                    question_id=active_question.id,
                    sort_order=index,
                )
            )
    db.commit()


def submit_answers(
    db: Session, attempt_id: int, questions: list, answers: list[str]
) -> None:
    """快捷提交答案并交卷的测试辅助函数。"""
    exam_service.save_answers(
        db,
        attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(attempt_question_id=q.id, selected_answer=a)
                for q, a in zip(questions, answers, strict=True)
            ]
        ),
    )
    exam_service.submit_attempt(db, attempt_id, "manual")


def build_workbook(headers: list[str], rows: list[dict[str, object]]) -> BytesIO:
    """构建用于导入测试的 Excel 工作簿。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    file_obj = BytesIO()
    workbook.save(file_obj)
    file_obj.seek(0)
    return file_obj
