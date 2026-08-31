from datetime import datetime

from pydantic import BaseModel


class PracticeRetentionAnswerRead(BaseModel):
    practice_answer_id: int
    candidate_id: int
    question_id: int
    selected_answer: str
    is_correct: bool
    practiced_at: datetime


class PracticeRetentionCandidatePreview(BaseModel):
    candidate_id: int
    hot_row_count: int
    expired_row_count: int
    selected_row_count: int
    selected_practice_answer_ids: list[int]
    eligible: bool
    capacity_limited: bool


class PracticeRetentionPreviewRead(BaseModel):
    generated_at: datetime
    cutoff_at: datetime
    retention_days: int
    hot_history_limit: int
    hot_history_low_watermark: int
    fingerprint: str
    candidates: list[PracticeRetentionCandidatePreview]
    limit: int = 100
    offset: int = 0
    total_candidates: int = 0
    has_more: bool = False


class PracticeRetentionArchiveRequest(BaseModel):
    candidate_ids: list[int]
    preview_fingerprint: str


class PracticeRetentionArchiveRead(BaseModel):
    artifact_id: str
    created_at: datetime
    candidate_ids: list[int]
    practice_answer_ids: list[int]
    preview_fingerprint: str
    archive_sha256: str


class PracticeRetentionDeleteRequest(BaseModel):
    candidate_ids: list[int]
    preview_fingerprint: str
    archive_id: str
    backup_id: str
    confirmation: str


class PracticeRetentionDeleteRead(BaseModel):
    deleted_candidate_ids: list[int]
    deleted_practice_answer_ids: list[int]
    deleted_count: int
    archive_id: str
    backup_id: str
