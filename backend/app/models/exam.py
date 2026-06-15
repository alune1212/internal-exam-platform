import enum

from sqlalchemy import JSON, Boolean, Integer, String, Text
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

    attempts = relationship("ExamAttempt", back_populates="exam")
