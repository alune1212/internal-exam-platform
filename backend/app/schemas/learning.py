from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LearningVideoRead(ORMModel):
    id: int
    title: str
    description: str | None = None
    original_filename: str
    storage_key: str
    content_type: str
    file_size_bytes: int
    duration_seconds: int
    completion_threshold_percent: int
    status: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    playback_url: str


class LearningVideoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class LearningVideoProgressRead(BaseModel):
    last_position_seconds: int = 0
    watched_seconds: int = 0
    completion_percent: int = 0
    completed_at: datetime | None = None
    last_heartbeat_at: datetime | None = None


class CandidateLearningVideoRead(LearningVideoRead):
    progress: LearningVideoProgressRead


class LearningProgressUpdate(BaseModel):
    current_position_seconds: int = Field(ge=0)
    watched_start_seconds: int = Field(ge=0)
    watched_end_seconds: int = Field(ge=0)


class LearningReportRow(BaseModel):
    candidate_id: int
    candidate_name: str
    employee_no: str | None = None
    department: str | None = None
    exam_group: str | None = None
    video_id: int
    video_title: str
    video_status: str
    duration_seconds: int
    completion_percent: int
    completion_status: str
    last_heartbeat_at: datetime | None = None
    completed_at: datetime | None = None
