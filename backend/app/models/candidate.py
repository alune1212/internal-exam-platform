import enum

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class CandidateStatus(enum.StrEnum):
    active = "active"
    inactive = "inactive"


class Candidate(TimestampMixin, Base):
    __tablename__ = "candidate"
    __table_args__ = (
        Index("ix_candidate_name", "name"),
        Index("ix_candidate_exam_group", "exam_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    employee_no: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True
    )
    department: Mapped[str | None] = mapped_column(String(100))
    position: Mapped[str | None] = mapped_column(String(100))
    phone_suffix: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    exam_group: Mapped[str | None] = mapped_column(String(100))
    should_attend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CandidateStatus.active.value, index=True
    )
    remark: Mapped[str | None] = mapped_column(Text)

    attempts = relationship("ExamAttempt", back_populates="candidate")
    practice_answers = relationship("PracticeAnswer", back_populates="candidate")
