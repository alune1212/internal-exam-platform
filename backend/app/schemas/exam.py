from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.attempt import AttemptQuestionRead
from app.schemas.common import ORMModel


class ExamBase(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int
    question_rule: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    show_answer_after_submit: bool = True
    available_from: datetime | None = None
    available_until: datetime | None = None


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    question_rule: dict[str, Any] | None = None
    status: str | None = None
    show_answer_after_submit: bool | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    confirmation_title: str | None = None


class ExamRead(ExamBase, ORMModel):
    id: int
    result_details_released_at: datetime | None = None
    result_details_released_by: str | None = None
    latest_attempt_id: int | None = None
    latest_attempt_status: str | None = None
    has_unused_retake_grant: bool = False
    question_pool_count: int = 0
    availability_status: str = "open"


class ExamStartRequest(BaseModel):
    candidate_id: int


class ExamStartResponse(BaseModel):
    attempt_id: int
    exam: ExamRead
    questions: list[AttemptQuestionRead]
    started_at: datetime
    ends_at: datetime
    attempt_session_credential: str | None = None
    attempt_session_generation: int = 0
    answer_revision: int = 0


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


class PublicationReadinessIssue(BaseModel):
    code: str
    message: str


class PublicationReadinessRead(BaseModel):
    exam_id: int
    ready: bool
    prospective_pool_count: int
    roster_count: int
    blockers: list[PublicationReadinessIssue] = Field(default_factory=list)
    warnings: list[PublicationReadinessIssue] = Field(default_factory=list)
    fingerprint: str


class ExamPublishRequest(BaseModel):
    confirmation_title: str


class ResultDetailsReleaseRequest(BaseModel):
    confirmation_title: str


class ResultDetailsReleaseRead(BaseModel):
    exam_id: int
    released_at: datetime
    released_by: str


class BulkRetakePreviewRequest(BaseModel):
    candidate_ids: list[int] = Field(min_length=1, max_length=500)
    void_existing: bool = False


class BulkRetakeApplyRequest(BulkRetakePreviewRequest):
    confirmation_title: str
    preview_fingerprint: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=5, max_length=1000)


class BulkRetakeRow(BaseModel):
    candidate_id: int
    candidate_name: str | None = None
    attempt_id: int | None = None
    prior_status: str | None = None
    outcome: str
    reason: str


class BulkRetakePreviewRead(BaseModel):
    exam_id: int
    void_existing: bool
    eligible_count: int
    skipped_count: int
    rows: list[BulkRetakeRow] = Field(default_factory=list)
    fingerprint: str


class BulkRetakeApplyRead(BulkRetakePreviewRead):
    granted_count: int
    voided_count: int
    applied_at: datetime


class FormalExamEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_manifest_ref: str | None = Field(default=None, max_length=200)
    preflight_ref: str | None = Field(default=None, max_length=200)
    smtp_ref: str | None = Field(default=None, max_length=200)
    backup_ref: str | None = Field(default=None, max_length=200)
    close_exam_ref: str | None = Field(default=None, max_length=200)


class FormalExamEvidenceRead(BaseModel):
    exam_id: int
    generated_at: datetime
    manifest: dict[str, Any]
    checksum_sha256: str
