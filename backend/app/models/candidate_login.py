from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class CandidateLoginChallenge(TimestampMixin, Base):
    __tablename__ = "candidate_login_challenge"
    __table_args__ = (
        Index("ix_candidate_login_challenge_candidate_id", "candidate_id"),
        Index("ix_candidate_login_challenge_expires_at", "expires_at"),
        Index(
            "ix_candidate_login_challenge_candidate_consumed",
            "candidate_id",
            "consumed_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    delivery_channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="email"
    )
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_ip_hash: Mapped[str | None] = mapped_column(String(128))

    candidate = relationship("Candidate", back_populates="login_challenges")
