from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Exam


class ExamNotFoundError(Exception):
    def __init__(self, exam_id: int) -> None:
        self.exam_id = exam_id
        super().__init__(f"考试 #{exam_id} 不存在")
from app.schemas.attempt import AnswerSaveRequest, AnswerSaveResponse, AttemptRead, AttemptResultRead
from app.schemas.exam import ExamCreate, ExamRead, ExamStartResponse, ExamUpdate, RankingRow


def list_active_exams(db: Session) -> list[ExamRead]:
    exams = db.query(Exam).filter(Exam.status == "active").order_by(Exam.id).all()
    return [ExamRead.model_validate(exam) for exam in exams]


def list_admin_exams(db: Session) -> list[ExamRead]:
    exams = db.query(Exam).order_by(Exam.id).all()
    return [ExamRead.model_validate(exam) for exam in exams]


def create_exam(db: Session, payload: ExamCreate) -> ExamRead:
    exam = Exam(**payload.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return ExamRead.model_validate(exam)


def update_exam(db: Session, exam_id: int, payload: ExamUpdate) -> ExamRead:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exam, field, value)

    db.commit()
    return ExamRead.model_validate(exam)


def start_exam(db: Session, exam_id: int, candidate_id: int) -> ExamStartResponse:
    now = datetime.now(UTC)
    exam = ExamRead(
        id=exam_id,
        title="待配置考试",
        description="第一阶段考试启动接口骨架",
        duration_minutes=60,
        question_rule={},
        status="active",
        show_answer_after_submit=True,
        show_ranking=True,
    )
    return ExamStartResponse(
        attempt_id=0,
        exam=exam,
        questions=[],
        started_at=now,
        ends_at=now + timedelta(minutes=exam.duration_minutes),
    )


def get_attempt(db: Session, attempt_id: int) -> AttemptRead:
    now = datetime.now(UTC)
    return AttemptRead(
        id=attempt_id,
        exam_id=0,
        candidate_id=0,
        status="in_progress",
        started_at=now,
        score=0,
        total_score=0,
        correct_count=0,
        wrong_count=0,
        questions=[],
    )


def save_answers(db: Session, attempt_id: int, payload: AnswerSaveRequest) -> AnswerSaveResponse:
    return AnswerSaveResponse(saved_count=len(payload.answers), saved_at=datetime.now(UTC))


def submit_attempt(db: Session, attempt_id: int, submit_type: str) -> AttemptResultRead:
    return AttemptResultRead(
        attempt_id=attempt_id,
        score=0,
        total_score=0,
        correct_count=0,
        wrong_count=0,
        questions=[],
    )


def get_attempt_result(db: Session, attempt_id: int) -> AttemptResultRead:
    return submit_attempt(db, attempt_id, "view")


def get_ranking(db: Session, exam_id: int) -> list[RankingRow]:
    return []
