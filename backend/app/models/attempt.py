from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ExamAttempt(TimestampMixin, Base):
    __tablename__ = "exam_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submit_type: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    total_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    exam = relationship("Exam", back_populates="attempts")
    candidate = relationship("Candidate", back_populates="attempts")
    questions = relationship(
        "ExamAttemptQuestion",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ExamAttemptQuestion.sort_order",
    )


class ExamAttemptQuestion(TimestampMixin, Base):
    __tablename__ = "exam_attempt_question"
    __table_args__ = (UniqueConstraint("attempt_id", "sort_order", name="uq_attempt_question_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempt.id", ondelete="CASCADE"), nullable=False, index=True)
    original_question_id: Mapped[int | None] = mapped_column(ForeignKey("question.id"), index=True)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stem_snapshot: Mapped[str] = mapped_column(nullable=False)
    options_snapshot: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    correct_answer_snapshot: Mapped[str] = mapped_column(nullable=False)
    analysis_snapshot: Mapped[str | None] = mapped_column()
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="questions")
    answer = relationship("ExamAttemptAnswer", back_populates="attempt_question", uselist=False, cascade="all, delete-orphan")


class ExamAttemptAnswer(TimestampMixin, Base):
    __tablename__ = "exam_attempt_answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_question_id: Mapped[int] = mapped_column(
        ForeignKey("exam_attempt_question.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    selected_answer: Mapped[str | None] = mapped_column()
    is_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    score_awarded: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    attempt_question = relationship("ExamAttemptQuestion", back_populates="answer")


class PracticeAnswer(Base):
    __tablename__ = "practice_answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False, index=True)
    selected_answer: Mapped[str] = mapped_column(nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    practiced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    candidate = relationship("Candidate", back_populates="practice_answers")
    question = relationship("Question", back_populates="practice_answers")
