from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.attempt import AttemptQuestionRead
from app.schemas.common import ORMModel


class ExamBase(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int
    question_rule: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    show_answer_after_submit: bool = True
    show_ranking: bool = True


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    question_rule: dict[str, Any] | None = None
    status: str | None = None
    show_answer_after_submit: bool | None = None
    show_ranking: bool | None = None


class ExamRead(ExamBase, ORMModel):
    id: int


class ExamStartRequest(BaseModel):
    candidate_id: int


class ExamStartResponse(BaseModel):
    attempt_id: int
    exam: ExamRead
    questions: list[AttemptQuestionRead]
    started_at: datetime
    ends_at: datetime


class RankingRow(BaseModel):
    rank: int
    candidate_name: str
    department: str | None = None
    score: float
    total_score: float
    submitted_at: datetime | None = None


class ExamCandidateRow(BaseModel):
    candidate_id: int
    candidate_name: str
    employee_no: str | None = None
    department: str | None = None
    exam_group: str | None = None
    should_attend: bool
    candidate_status: str
    latest_attempt_id: int | None = None
    latest_attempt_status: str | None = None
    latest_score: float | None = None
    latest_total_score: float | None = None
    latest_submitted_at: datetime | None = None
    attempt_no: int | None = None
    attempt_kind: str | None = None
    has_unused_retake_grant: bool = False
