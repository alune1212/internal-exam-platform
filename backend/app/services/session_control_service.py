from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExamAttempt
from app.schemas.operations import SessionClosureReadiness


def get_session_closure_readiness(db: Session) -> SessionClosureReadiness:
    in_progress_count = db.scalar(
        select(func.count(ExamAttempt.id)).where(ExamAttempt.status == "in_progress")
    )
    count = int(in_progress_count or 0)
    return SessionClosureReadiness(
        ready=count == 0,
        in_progress_attempt_count=count,
    )
