from collections.abc import Iterator
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Candidate, Exam, Question, QuestionOption
from app.schemas.attempt import AnswerSaveItem, AnswerSaveRequest
from app.services import exam_service


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


def create_exam(db: Session, **kwargs) -> Exam:
    """创建考试的测试辅助函数。"""
    defaults = {"title": "默认考试", "duration_minutes": 60, "status": "active"}
    defaults.update(kwargs)
    exam = Exam(**defaults)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def create_candidate(db: Session, **kwargs) -> Candidate:
    """创建考生的测试辅助函数。"""
    defaults = {"name": "张三"}
    defaults.update(kwargs)
    candidate = Candidate(**defaults)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def create_question_with_options(db: Session, **kwargs) -> Question:
    """创建题目及选项的测试辅助函数。"""
    defaults = {"question_type": "single", "stem": "题目内容", "score": 2, "status": "active"}
    defaults.update(kwargs)
    question = Question(**defaults)
    db.add(question)
    db.flush()
    options = [
        QuestionOption(question_id=question.id, label="A", content="选项A", is_correct=True, sort_order=0),
        QuestionOption(question_id=question.id, label="B", content="选项B", is_correct=False, sort_order=1),
    ]
    db.add_all(options)
    db.commit()
    db.refresh(question)
    return question


def submit_answers(db: Session, attempt_id: int, questions: list, answers: list[str]) -> None:
    """快捷提交答案并交卷的测试辅助函数。"""
    exam_service.save_answers(
        db,
        attempt_id,
        AnswerSaveRequest(answers=[
            AnswerSaveItem(attempt_question_id=q.id, selected_answer=a)
            for q, a in zip(questions, answers)
        ]),
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
