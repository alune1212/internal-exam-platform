from datetime import datetime

from pydantic import BaseModel


class ScoreReportRow(BaseModel):
    """A submitted formal result identified by the frozen exam roster.

    ``candidate_id`` is retained as the internal compatibility identifier, but
    all human-facing identity fields come from ``exam_candidate_scope``.  The
    small ``candidate_name`` property below keeps service/test callers that
    used the old Python attribute working without putting the removed legacy
    field back into the JSON contract.
    """

    candidate_id: int
    roster_name: str
    roster_email: str
    department: str | None = None
    position: str | None = None
    exam_group: str | None = None
    roster_remark: str | None = None
    exam_id: int
    exam_title: str
    score: float
    total_score: float
    submitted_at: datetime | None = None

    @property
    def candidate_name(self) -> str:
        """Compatibility alias for callers that still use the old name."""

        return self.roster_name


class RankingRow(BaseModel):
    """An administrator-only ranking row for one frozen exam roster."""

    rank: int
    candidate_id: int
    roster_name: str
    roster_email: str
    department: str | None = None
    position: str | None = None
    exam_group: str | None = None
    roster_remark: str | None = None
    exam_id: int
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
    exam_id: int
    exam_title: str | None = None
    roster_name: str
    roster_email: str
    department: str | None = None
    position: str | None = None
    exam_group: str | None = None
    roster_remark: str | None = None
    attendance_status: str = "not_started"

    @property
    def name(self) -> str:
        """Compatibility alias for the former mutable candidate name."""

        return self.roster_name
