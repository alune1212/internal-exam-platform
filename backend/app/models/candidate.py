import enum

from sqlalchemy import CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import Base
from app.models.base import TimestampMixin


class CandidateStatus(enum.StrEnum):
    pending = "pending"
    active = "active"
    inactive = "inactive"


class Candidate(TimestampMixin, Base):
    __tablename__ = "candidate"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'inactive')",
            name="ck_candidate_status",
        ),
        CheckConstraint(
            "email = lower(trim(email)) AND length(trim(email)) > 3",
            name="ck_candidate_email_normalized",
        ),
        CheckConstraint(
            "name IS NULL OR length(trim(name)) > 0",
            name="ck_candidate_name_nonblank",
        ),
        CheckConstraint(
            "status = 'pending' OR (name IS NOT NULL AND length(trim(name)) > 0)",
            name="ck_candidate_completed_name",
        ),
        Index("ix_candidate_name", "name"),
        Index("ux_candidate_email", "email", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CandidateStatus.pending.value, index=True
    )

    attempts = relationship("ExamAttempt", back_populates="candidate")
    practice_answers = relationship("PracticeAnswer", back_populates="candidate")
    learning_video_progress = relationship(
        "LearningVideoProgress",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    login_challenges = relationship(
        "CandidateLoginChallenge",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    # ``name`` remains the physical compatibility column; a synonym lets new
    # services query or assign the account-facing display-name terminology.
    display_name = synonym("name")
