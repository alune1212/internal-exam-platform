from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Question(TimestampMixin, Base):
    __tablename__ = "question"
    __table_args__ = (
        Index("ix_question_category", "category_1", "category_2"),
        Index("ix_question_type_status", "question_type", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    analysis: Mapped[str | None] = mapped_column(Text)
    category_1: Mapped[str | None] = mapped_column(String(100))
    category_2: Mapped[str | None] = mapped_column(String(100))
    difficulty: Mapped[str | None] = mapped_column(String(50))
    score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=1, server_default="1"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    source: Mapped[str | None] = mapped_column(String(200))
    source_no: Mapped[str | None] = mapped_column(String(100))
    remark: Mapped[str | None] = mapped_column(Text)

    options = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan"
    )
    practice_answers = relationship("PracticeAnswer", back_populates="question")


class QuestionOption(TimestampMixin, Base):
    __tablename__ = "question_option"
    __table_args__ = (
        UniqueConstraint("question_id", "label", name="uq_question_option_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    question = relationship("Question", back_populates="options")
