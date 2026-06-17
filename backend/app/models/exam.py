import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ExamStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    archived = "archived"


class Exam(TimestampMixin, Base):
    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    question_rule: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ExamStatus.draft.value, index=True
    )
    show_answer_after_submit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    show_ranking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    attempts = relationship("ExamAttempt", back_populates="exam")
    candidate_scopes = relationship(
        "ExamCandidateScope", back_populates="exam", cascade="all, delete-orphan"
    )
    retake_grants = relationship(
        "ExamRetakeGrant", back_populates="exam", cascade="all, delete-orphan"
    )
    question_pool = relationship(
        "ExamQuestionPool", back_populates="exam", cascade="all, delete-orphan"
    )


class ExamQuestionPool(TimestampMixin, Base):
    __tablename__ = "exam_question_pool"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question_pool"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    exam = relationship("Exam", back_populates="question_pool")
    question = relationship("Question")


class ExamCandidateScope(TimestampMixin, Base):
    __tablename__ = "exam_candidate_scope"
    __table_args__ = (
        UniqueConstraint("exam_id", "candidate_id", name="uq_exam_candidate_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False, index=True
    )

    exam = relationship("Exam", back_populates="candidate_scopes")
    candidate = relationship("Candidate")


class ExamRetakeGrant(TimestampMixin, Base):
    __tablename__ = "exam_retake_grant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False, index=True
    )
    used_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_attempt.id", ondelete="SET NULL"), nullable=True, index=True
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    exam = relationship("Exam", back_populates="retake_grants")
    candidate = relationship("Candidate")
