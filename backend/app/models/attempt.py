from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import Base
from app.models.base import TimestampMixin

SUBMITTED_STATUSES = ("submitted", "auto_submitted")
TERMINAL_ATTEMPT_STATUSES = (*SUBMITTED_STATUSES, "voided")


class ExamAttempt(TimestampMixin, Base):
    __tablename__ = "exam_attempt"
    __table_args__ = (
        UniqueConstraint(
            "exam_id", "candidate_id", "attempt_no", name="uq_exam_attempt_no"
        ),
        Index(
            "ux_exam_attempt_one_in_progress",
            "exam_id",
            "candidate_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
            sqlite_where=text("status = 'in_progress'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="in_progress", index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_score_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    show_answer_after_submit_snapshot: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submit_type: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    total_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=0
    )
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    attempt_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, default="initial"
    )
    paper_seed: Mapped[str | None] = mapped_column(String(64))
    attempt_session_hash: Mapped[str | None] = mapped_column(String(128))
    attempt_session_generation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    answer_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by: Mapped[str | None] = mapped_column(String(100))
    void_reason: Mapped[str | None] = mapped_column(Text)

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
    __table_args__ = (
        UniqueConstraint("attempt_id", "sort_order", name="uq_attempt_question_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("exam_attempt.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("question.id", ondelete="SET NULL"), index=True
    )
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stem_snapshot: Mapped[str] = mapped_column(nullable=False)
    options_snapshot: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list
    )
    correct_answer_snapshot: Mapped[str] = mapped_column(nullable=False)
    analysis_snapshot: Mapped[str | None] = mapped_column()
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="questions")
    answer = relationship(
        "ExamAttemptAnswer",
        back_populates="attempt_question",
        uselist=False,
        cascade="all, delete-orphan",
    )


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
    score_awarded: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=0
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    attempt_question = relationship("ExamAttemptQuestion", back_populates="answer")


class PracticeAnswer(Base):
    __tablename__ = "practice_answer"
    __table_args__ = (
        Index(
            "ix_practice_answer_candidate_question_practiced",
            "candidate_id",
            "question_id",
            "practiced_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id"), nullable=False, index=True
    )
    selected_answer: Mapped[str] = mapped_column(nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    practiced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    candidate = relationship("Candidate", back_populates="practice_answers")
    question = relationship("Question", back_populates="practice_answers")


class PracticeAnswerAggregate(Base):
    """All-time mastery counters for one account/question pair.

    ``latest_practice_answer_id`` intentionally is not a foreign key: hot
    detail rows may be archived later while the aggregate retains the
    all-time latest-result evidence.
    """

    __tablename__ = "practice_answer_aggregate"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "question_id",
            name="uq_practice_answer_aggregate_candidate_question",
        ),
        CheckConstraint(
            "total_attempts >= 0",
            name="ck_practice_answer_aggregate_total_attempts_nonnegative",
        ),
        CheckConstraint(
            "incorrect_count >= 0",
            name="ck_practice_answer_aggregate_incorrect_count_nonnegative",
        ),
        CheckConstraint(
            "incorrect_count <= total_attempts",
            name="ck_practice_answer_aggregate_incorrect_count_lte_total",
        ),
        Index(
            "ix_practice_answer_aggregate_candidate_latest",
            "candidate_id",
            "latest_practiced_at",
            "question_id",
        ),
        Index(
            "ix_practice_answer_aggregate_candidate_incorrect_latest",
            "candidate_id",
            "incorrect_count",
            "latest_practiced_at",
            "question_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id", ondelete="CASCADE"), nullable=False
    )
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    latest_is_correct: Mapped[bool] = mapped_column(nullable=False)
    latest_practiced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    latest_practice_answer_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Compatibility aliases make the detail-oriented terminology explicit to
    # retention/read-model callers without adding duplicate storage columns.
    latest_detail_id = synonym("latest_practice_answer_id")
    latest_answer_id = synonym("latest_practice_answer_id")
    latest_answer = synonym("latest_selected_answer")
    latest_correct = synonym("latest_is_correct")

    candidate = relationship("Candidate", back_populates="practice_answer_aggregates")
    question = relationship("Question", back_populates="practice_answer_aggregates")
