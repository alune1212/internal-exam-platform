from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class CandidateLoginChallenge(TimestampMixin, Base):
    __tablename__ = "candidate_login_challenge"
    __table_args__ = (
        CheckConstraint(
            "email = lower(trim(email)) AND length(trim(email)) > 3",
            name="ck_candidate_login_challenge_email_normalized",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_candidate_login_challenge_attempt_count_nonnegative",
        ),
        Index("ix_candidate_login_challenge_candidate_id", "candidate_id"),
        Index("ix_candidate_login_challenge_email", "email"),
        Index("ix_candidate_login_challenge_expires_at", "expires_at"),
        Index(
            "ix_candidate_login_challenge_candidate_consumed",
            "candidate_id",
            "consumed_at",
        ),
        Index(
            "ix_candidate_login_challenge_email_consumed",
            "email",
            "consumed_at",
        ),
        Index(
            "ix_candidate_login_challenge_registration_credential",
            "registration_credential_hash",
            "registration_credential_consumed_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
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
    registration_credential_hash: Mapped[str | None] = mapped_column(String(128))
    registration_credential_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    registration_credential_consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    candidate = relationship("Candidate", back_populates="login_challenges")

    @property
    def completion_credential_hash(self) -> str | None:
        """Compatibility alias for auth code that calls this a completion token."""

        return self.registration_credential_hash

    @completion_credential_hash.setter
    def completion_credential_hash(self, value: str | None) -> None:
        self.registration_credential_hash = value

    @property
    def completion_credential_expires_at(self) -> datetime | None:
        return self.registration_credential_expires_at

    @completion_credential_expires_at.setter
    def completion_credential_expires_at(self, value: datetime | None) -> None:
        self.registration_credential_expires_at = value

    @property
    def completion_credential_consumed_at(self) -> datetime | None:
        return self.registration_credential_consumed_at

    @completion_credential_consumed_at.setter
    def completion_credential_consumed_at(self, value: datetime | None) -> None:
        self.registration_credential_consumed_at = value
