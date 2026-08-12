import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
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
    result_details_released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    result_details_released_by: Mapped[str | None] = mapped_column(String(100))

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
        CheckConstraint(
            "roster_email = lower(trim(roster_email)) "
            "AND length(trim(roster_email)) > 3",
            name="ck_exam_candidate_scope_roster_email_normalized",
        ),
        CheckConstraint(
            "length(trim(roster_name)) > 0",
            name="ck_exam_candidate_scope_roster_name_nonblank",
        ),
        CheckConstraint(
            "invitation_status IN ('not_sent', 'sent', 'failed')",
            name="ck_exam_candidate_scope_invitation_status",
        ),
        UniqueConstraint("exam_id", "candidate_id", name="uq_exam_candidate_scope"),
        Index(
            "ux_exam_candidate_scope_exam_roster_email",
            "exam_id",
            "roster_email",
            unique=True,
        ),
        Index(
            "ix_exam_candidate_scope_invitation_claim",
            "invitation_status",
            "invitation_claimed_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False, index=True
    )
    roster_email: Mapped[str] = mapped_column(String(255), nullable=False)
    roster_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))
    position: Mapped[str | None] = mapped_column(String(100))
    exam_group: Mapped[str | None] = mapped_column(String(100))
    roster_remark: Mapped[str | None] = mapped_column(Text)
    invitation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_sent", index=True
    )
    last_invitation_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    invitation_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invitation_error_class: Mapped[str | None] = mapped_column(String(100))
    invitation_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    invitation_claim_owner: Mapped[str | None] = mapped_column(String(200))

    exam = relationship("Exam", back_populates="candidate_scopes")
    candidate = relationship("Candidate")

    @property
    def invitation_state(self) -> str:
        """Alias used by delivery code while the database column stays explicit."""

        return self.invitation_status

    @invitation_state.setter
    def invitation_state(self, value: str) -> None:
        self.invitation_status = value

    @property
    def remark(self) -> str | None:
        """Scope-owned replacement for the old global candidate remark."""

        return self.roster_remark

    @remark.setter
    def remark(self, value: str | None) -> None:
        self.roster_remark = value


class ExamRetakeGrant(TimestampMixin, Base):
    __tablename__ = "exam_retake_grant"
    __table_args__ = (
        Index(
            "ux_exam_retake_grant_one_unused",
            "exam_id",
            "candidate_id",
            unique=True,
            postgresql_where=text("used_at IS NULL"),
            sqlite_where=text("used_at IS NULL"),
        ),
    )

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
