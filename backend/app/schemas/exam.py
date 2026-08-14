from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    """Frozen roster identity and delivery status for one exam scope.

    ``candidate_id`` remains the compatibility account foreign key, while all
    formal identity fields come from the scope snapshot.  Deliberately do not
    expose the retired personnel/attendance fields here.
    """

    scope_id: int
    candidate_id: int
    roster_email: str
    roster_name: str
    department: str | None = None
    position: str | None = None
    exam_group: str | None = None
    roster_remark: str | None = None
    account_status: str = "pending"
    invitation_status: str = "not_sent"
    last_invitation_attempt_at: datetime | None = None
    invitation_sent_at: datetime | None = None
    invitation_error_class: str | None = None
    invitation_claimed_at: datetime | None = None
    latest_attempt_id: int | None = None
    latest_attempt_status: str | None = None
    latest_score: float | None = None
    latest_total_score: float | None = None
    latest_submitted_at: datetime | None = None
    attempt_no: int | None = None
    attempt_kind: str | None = None
    has_unused_retake_grant: bool = False


class ExamCandidateCreate(BaseModel):
    """Draft roster row contract.

    ``extra='forbid'`` ensures legacy employee/phone/attendance/status
    columns cannot silently re-enter the JSON API.
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=255)
    candidate_name: str = Field(min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    exam_group: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email(cls, value: object) -> object:
        return _validate_roster_email(value)

    @field_validator("candidate_name", mode="before")
    @classmethod
    def _validate_candidate_name(cls, value: object) -> object:
        return _validate_roster_text(value, "姓名", required=True, max_length=100)

    @field_validator("department", "position", "exam_group", mode="before")
    @classmethod
    def _validate_short_roster_text(cls, value: object) -> object:
        return (
            None
            if value is None
            else _validate_roster_text(
                value, "名单字段", required=False, max_length=100
            )
        )

    @field_validator("remark", mode="before")
    @classmethod
    def _validate_roster_remark(cls, value: object) -> object:
        return (
            None
            if value is None
            else _validate_roster_text(value, "备注", required=False, max_length=2000)
        )


class ExamCandidateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = Field(default=None, min_length=1, max_length=255)
    candidate_name: str | None = Field(default=None, min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    exam_group: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email(cls, value: object) -> object:
        return None if value is None else _validate_roster_email(value)

    @field_validator("candidate_name", mode="before")
    @classmethod
    def _validate_candidate_name(cls, value: object) -> object:
        return (
            None
            if value is None
            else _validate_roster_text(value, "姓名", required=True, max_length=100)
        )

    @field_validator("department", "position", "exam_group", mode="before")
    @classmethod
    def _validate_short_roster_text(cls, value: object) -> object:
        return (
            None
            if value is None
            else _validate_roster_text(
                value, "名单字段", required=False, max_length=100
            )
        )

    @field_validator("remark", mode="before")
    @classmethod
    def _validate_roster_remark(cls, value: object) -> object:
        return (
            None
            if value is None
            else _validate_roster_text(value, "备注", required=False, max_length=2000)
        )


def _validate_roster_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("邮箱格式不正确")
    normalized = value.strip().lower()
    if not normalized or len(normalized) > 255:
        raise ValueError("邮箱格式不正确")
    if any(ord(char) < 32 for char in normalized):
        raise ValueError("邮箱包含不支持的控制字符")
    from app.schemas.candidate import normalize_email

    try:
        return normalize_email(normalized)
    except ValueError as exc:
        raise ValueError("邮箱格式不正确") from exc


def _validate_roster_text(
    value: object, label: str, *, required: bool, max_length: int
) -> str | None:
    if not isinstance(value, str):
        raise ValueError(f"{label}格式不正确")
    normalized = value.strip()
    if not normalized:
        if required:
            raise ValueError(f"{label}不能为空")
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{label}长度不能超过{max_length}个字符")
    if any(ord(char) < 32 for char in normalized):
        raise ValueError(f"{label}包含不支持的控制字符")
    return normalized


class InvitationScheduleRead(BaseModel):
    """Accepted/rejected scheduling counts; SMTP outcomes are polled later."""

    exam_id: int
    mode: str
    selected_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    scheduled_count: int = 0


class InvitationStatusRead(BaseModel):
    exam_id: int
    total_count: int = 0
    not_sent_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    rows: list[ExamCandidateRow] = Field(default_factory=list)


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


ExamWorkspaceNextAction = Literal[
    "manage_roster",
    "fix_readiness",
    "publish",
    "wait_invitation_delivery",
    "send_invitations",
    "resend_failed_invitations",
    "wait_for_open",
    "monitor_exam",
    "review_incidents",
    "release_result_details",
    "archive_exam",
    "complete",
]


class ExamWorkspaceRosterSummary(BaseModel):
    """Aggregate roster and account lifecycle counts for one exam.

    The workspace intentionally returns no scope rows or account identity
    fields.  These counts are sufficient for an operator to understand
    publication readiness without exposing roster PII.
    """

    total_count: int = Field(default=0, ge=0)
    active_count: int = Field(default=0, ge=0)
    pending_count: int = Field(default=0, ge=0)
    inactive_count: int = Field(default=0, ge=0)


class ExamWorkspaceInvitationSummary(BaseModel):
    """Delivery state counts; in-flight claims are tracked independently."""

    not_sent_count: int = Field(default=0, ge=0)
    sent_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    in_flight_count: int = Field(default=0, ge=0)


class ExamWorkspaceAttendanceSummary(BaseModel):
    """Latest-attempt attendance counts for the frozen exam roster."""

    not_started_count: int = Field(default=0, ge=0)
    in_progress_count: int = Field(default=0, ge=0)
    submitted_count: int = Field(default=0, ge=0)


class ExamWorkspaceAttemptSummary(BaseModel):
    """Raw attempt history counts, retaining each status separately."""

    in_progress_count: int = Field(default=0, ge=0)
    submitted_count: int = Field(default=0, ge=0)
    auto_submitted_count: int = Field(default=0, ge=0)
    voided_count: int = Field(default=0, ge=0)


class ExamWorkspaceIncidentSummary(BaseModel):
    """Void incidents and still-available retake grants."""

    voided_count: int = Field(default=0, ge=0)
    unused_retake_count: int = Field(default=0, ge=0)


class ExamWorkspaceRead(BaseModel):
    """Privacy-bounded aggregate operational view for one exam."""

    observed_at: datetime
    exam: ExamRead
    readiness: PublicationReadinessRead | None = None
    roster_summary: ExamWorkspaceRosterSummary
    invitation_summary: ExamWorkspaceInvitationSummary
    attendance_summary: ExamWorkspaceAttendanceSummary
    attempt_summary: ExamWorkspaceAttemptSummary
    incident_summary: ExamWorkspaceIncidentSummary
    next_action: ExamWorkspaceNextAction
    next_action_reason: str


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
    roster_email: str | None = None
    roster_name: str | None = None
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
