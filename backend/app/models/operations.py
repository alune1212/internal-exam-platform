from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperationalLock(Base):
    __tablename__ = "operational_lock"
    __table_args__ = (Index("ix_operational_lock_expires_at", "expires_at"),)

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Formal cutover writer-fence metadata lives with the existing operational
    # lock row so backend and worker containers observe the same DB-backed
    # state.  These fields remain nullable for the pre-fence backup lock.
    dataset_id: Mapped[str | None] = mapped_column(String(200))
    host_id: Mapped[str | None] = mapped_column(String(200))
    writer_generation: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(500))


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_event"
    __table_args__ = (
        Index("ix_admin_audit_event_created_at", "created_at"),
        Index("ix_admin_audit_event_action", "action"),
        Index("ix_admin_audit_event_operator_subject", "operator_subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_subject: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(200))
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    request_source_hash: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
