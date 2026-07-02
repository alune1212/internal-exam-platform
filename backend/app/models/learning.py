import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class LearningVideoStatus(enum.StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


class LearningVideo(TimestampMixin, Base):
    __tablename__ = "learning_video"
    __table_args__ = (
        Index("ix_learning_video_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_threshold_percent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LearningVideoStatus.draft.value, index=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    progress_records = relationship(
        "LearningVideoProgress",
        back_populates="video",
        cascade="all, delete-orphan",
    )


class LearningVideoProgress(TimestampMixin, Base):
    __tablename__ = "learning_video_progress"
    __table_args__ = (
        UniqueConstraint("video_id", "candidate_id", name="uq_learning_video_progress"),
        Index(
            "ix_learning_progress_candidate_completed", "candidate_id", "completed_at"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("learning_video.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_position_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    watched_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    watched_intervals: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    video = relationship("LearningVideo", back_populates="progress_records")
    candidate = relationship("Candidate", back_populates="learning_video_progress")
