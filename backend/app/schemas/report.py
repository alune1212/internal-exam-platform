from datetime import datetime

from pydantic import BaseModel


class ScoreReportRow(BaseModel):
    candidate_name: str
    employee_no: str | None = None
    department: str | None = None
    exam_title: str
    score: float
    total_score: float
    submitted_at: datetime | None = None


class QuestionAccuracyRow(BaseModel):
    question_id: int
    stem: str
    correct_count: int
    total_count: int
    accuracy_rate: float


class WrongQuestionRow(BaseModel):
    question_id: int
    stem: str
    wrong_count: int
    category_1: str | None = None
    category_2: str | None = None


class AbsentCandidateRow(BaseModel):
    candidate_id: int
    name: str
    employee_no: str | None = None
    department: str | None = None
    exam_group: str | None = None
    attendance_status: str = "not_started"
