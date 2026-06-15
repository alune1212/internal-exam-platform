from datetime import datetime
from typing import Any

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
    submitted_at: datetime | None = None
    score: float
    total_score: float
    correct_count: int
    wrong_count: int
    questions: list[AttemptQuestionRead] = Field(default_factory=list)


class AnswerSaveItem(BaseModel):
    attempt_question_id: int
    selected_answer: str | None


class AnswerSaveRequest(BaseModel):
    answers: list[AnswerSaveItem]


class AnswerSaveResponse(BaseModel):
    saved_count: int
    saved_at: datetime


class SubmitRequest(BaseModel):
    submit_type: str = "manual"


class AttemptResultQuestion(BaseModel):
    attempt_question_id: int
    stem_snapshot: str
    selected_answer: str | None
    correct_answer_snapshot: str
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
    correct_count: int
    wrong_count: int
    questions: list[AttemptResultQuestion] = Field(default_factory=list)
