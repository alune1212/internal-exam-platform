from datetime import datetime

from pydantic import BaseModel, Field


class SessionClosureReadiness(BaseModel):
    ready: bool
    in_progress_attempt_count: int


class RetentionExamPreview(BaseModel):
    exam_id: int
    title: str
    final_activity_at: datetime
    eligible: bool
    reasons: list[str]
    attempt_count: int
    attempt_question_count: int
    answer_count: int
    roster_count: int
    retake_grant_count: int
    frozen_pool_count: int
    protected_candidate_count: int
    audit_evidence_count: int


class RetentionPreviewRead(BaseModel):
    generated_at: datetime
    cutoff_at: datetime
    retention_months: int
    fingerprint: str
    exams: list[RetentionExamPreview]


class RetentionArchiveRequest(BaseModel):
    exam_ids: list[int]
    preview_fingerprint: str


class RetentionArchiveRead(BaseModel):
    artifact_id: str
    created_at: datetime
    exam_ids: list[int]
    preview_fingerprint: str
    archive_sha256: str


class RetentionDeleteRequest(BaseModel):
    exam_ids: list[int]
    preview_fingerprint: str
    archive_id: str
    backup_id: str
    confirmation: str


class RetentionDeleteRead(BaseModel):
    deleted_exam_ids: list[int]
    deleted_attempt_count: int
    protected_candidate_count: int
    archive_id: str
    backup_id: str


class StorageReserveRead(BaseModel):
    free_bytes: int
    database_bytes: int
    media_bytes: int
    proposed_bytes: int
    footprint_after_bytes: int
    free_after_bytes: int
    required_free_bytes: int
    sufficient: bool


class OperationalSignalRead(BaseModel):
    status: str
    summary: str
    checked_at: datetime
    details: dict[str, object] = Field(default_factory=dict)


class OperationsSnapshotRead(BaseModel):
    checked_at: datetime
    version: OperationalSignalRead
    migration: OperationalSignalRead
    service_health: OperationalSignalRead
    worker_health: OperationalSignalRead
    operational_lock: OperationalSignalRead
    writer_fence: OperationalSignalRead
    disk_reserve: OperationalSignalRead
    backup: OperationalSignalRead
    second_copy: OperationalSignalRead
    restore_drill: OperationalSignalRead
    retention: OperationalSignalRead
    security_scan: OperationalSignalRead
