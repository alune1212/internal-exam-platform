from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.schemas.attempt import AnswerSaveRequest, AnswerSaveResponse, AttemptRead, AttemptResultRead
from app.schemas.exam import ExamCreate, ExamRead, ExamStartResponse, ExamUpdate, RankingRow


def list_active_exams(db: Session) -> list[ExamRead]:
    return []


def list_admin_exams(db: Session) -> list[ExamRead]:
    return []


def create_exam(db: Session, payload: ExamCreate) -> ExamRead:
    return ExamRead(id=0, **payload.model_dump())


def update_exam(db: Session, exam_id: int, payload: ExamUpdate) -> ExamRead:
    data = payload.model_dump(exclude_unset=True)
    return ExamRead(
        id=exam_id,
        title=data.get("title", "待配置考试"),
        description=data.get("description"),
        duration_minutes=data.get("duration_minutes", 60),
        question_rule=data.get("question_rule", {}),
        status=data.get("status", "draft"),
        show_answer_after_submit=data.get("show_answer_after_submit", True),
        show_ranking=data.get("show_ranking", True),
    )


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
