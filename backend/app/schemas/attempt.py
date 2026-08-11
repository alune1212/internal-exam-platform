from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AttemptQuestionRead(ORMModel):
    id: int
    question_type: str
    stem_snapshot: str
    options_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    score: float
    sort_order: int
    selected_answer: str | None = None


class AttemptRead(ORMModel):
    id: int
    exam_id: int
    candidate_id: int
    status: str
    started_at: datetime
    duration_minutes: int
    ends_at: datetime
    server_now: datetime
    submitted_at: datetime | None = None
    score: float
    total_score: float
    correct_count: int
    wrong_count: int
    attempt_session_generation: int = 0
    answer_revision: int = 0
    voided_at: datetime | None = None
    voided_by: str | None = None
    void_reason: str | None = None
    questions: list[AttemptQuestionRead] = Field(default_factory=list)


class AnswerSaveItem(BaseModel):
    attempt_question_id: int
    selected_answer: str | None


class AnswerSaveRequest(BaseModel):
    answers: list[AnswerSaveItem]
    answer_revision: int = 0


class AnswerSaveResponse(BaseModel):
    saved_count: int
    saved_at: datetime
    answer_revision: int = 0


class SubmitRequest(BaseModel):
    submit_type: Literal["manual"] = "manual"


class AttemptSessionTakeoverResponse(BaseModel):
    attempt_id: int
    attempt_session_credential: str
    attempt_session_generation: int
    answer_revision: int
    ends_at: datetime


class AttemptResultQuestion(BaseModel):
    attempt_question_id: int
    stem_snapshot: str
    selected_answer: str | None
    correct_answer_snapshot: str | None
    analysis_snapshot: str | None = None
    is_correct: bool
    score_awarded: float
    score: float


class AttemptResultRead(BaseModel):
    attempt_id: int
    score: float
    total_score: float
    pass_score: float | None = None
    is_passed: bool | None = None
    show_answer_after_submit: bool
    correct_count: int
    wrong_count: int
    questions: list[AttemptResultQuestion] = Field(default_factory=list)


class AttemptVoidRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class AttemptIncidentRead(BaseModel):
    attempt_id: int
    exam_id: int
    candidate_id: int
    prior_status: str
    status: Literal["voided"] = "voided"
    voided_at: datetime
    voided_by: str
    reason: str
    attempt_no: int
    retake_granted: bool = False
