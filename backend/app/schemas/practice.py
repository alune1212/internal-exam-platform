from datetime import datetime

from pydantic import BaseModel


class PracticeAnswerSubmitRequest(BaseModel):
    question_id: int
    selected_answer: str


class PracticeAnswerResult(BaseModel):
    practice_answer_id: int
    question_id: int
    selected_answer: str
    score: float
    is_correct: bool
    correct_answer: str
    analysis: str | None = None
    option_comparison: list["PracticeOptionComparison"]


class PracticeOptionComparison(BaseModel):
    label: str
    content: str
    selected: bool
    correct: bool


class PracticeAnswerHistory(BaseModel):
    practice_answer_id: int
    selected_answer: str
    is_correct: bool
    practiced_at: datetime


class PracticeWrongQuestionRead(BaseModel):
    question_id: int
    question_type: str
    stem: str
    category_1: str | None = None
    category_2: str | None = None
    status: str
    correct_answer: str
    analysis: str | None = None
    incorrect_count: int
    total_attempts: int
    mastered: bool
    latest_practiced_at: datetime
    history: list[PracticeAnswerHistory]
    options: list[PracticeOptionComparison]
