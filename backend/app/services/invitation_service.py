"""Explicit, recoverable invitation delivery for frozen exam rosters.

Invitation mail is notification-only.  Scope rows are claimed in a short
transaction, then each recipient is delivered with an independent session so
one SMTP failure cannot roll back another recipient.  There is intentionally
no durable queue or automatic retry: stale claims are recoverable only when an
administrator invokes send/resend again.
"""

from __future__ import annotations

import hashlib
import logging
import smtplib
import ssl
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import DomainError
from app.core.time import to_utc
from app.models import Exam, ExamCandidateScope
from app.services.email_service import (
    PermanentEmailDeliveryError,
    TransientEmailDeliveryError,
)
from app.services.exam_errors import ExamNotFoundError
from app.services.operational_lock_service import assert_admin_mutation_allowed

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class InvitationMutationError(DomainError):
    status_code = 409


class InvitationBatchLimitError(InvitationMutationError):
    pass


@dataclass(frozen=True)
class InvitationEmail:
    to_email: str
    roster_name: str
    exam_title: str
    exam_url: str
    message_id: str


@dataclass(frozen=True)
class InvitationSchedule:
    exam_id: int
    mode: str
    selected_count: int
    accepted_count: int
    rejected_count: int
    scheduled_count: int
    scope_ids: tuple[int, ...]
    claim_owner: str


INVITATION_EMAIL_OUTBOX_MAXLEN = 256
invitation_email_outbox: deque[InvitationEmail] = deque(
    maxlen=INVITATION_EMAIL_OUTBOX_MAXLEN
)

# Invitation actions are administrator mutations and use a separate bounded
# limiter from public OTP quotas.  The in-memory window is intentionally only
# a burst guard; row claims remain the concurrency authority in the database.
_admin_action_events: dict[tuple[str, int, str], deque[float]] = {}


def clear_invitation_email_outbox() -> None:
    invitation_email_outbox.clear()


def clear_invitation_rate_limiter() -> None:
    _admin_action_events.clear()


def check_invitation_admin_rate_limit(
    *, operator_subject: str, exam_id: int, mode: str, now: float | None = None
) -> None:
    limit = int(_setting("invitation_admin_rate_limit_count", 10))
    window = int(_setting("invitation_admin_rate_limit_window_seconds", 60))
    checked = now if now is not None else time.monotonic()
    key = (operator_subject, exam_id, mode)
    events = _admin_action_events.setdefault(key, deque())
    while events and checked - events[0] >= window:
        events.popleft()
    if len(events) >= max(1, limit):
        raise InvitationMutationError("邀请操作过于频繁，请稍后重试。")
    events.append(checked)


def _setting(name: str, default: object) -> Any:
    return getattr(settings, name, default)


def invitation_batch_size() -> int:
    value = int(_setting("invitation_send_batch_size", 100))
    return max(1, value)


def invitation_claim_ttl_seconds() -> int:
    value = int(_setting("invitation_claim_ttl_seconds", 15 * 60))
    return max(1, value)


def _candidate_public_base_url() -> str:
    raw = str(_setting("candidate_public_base_url", "http://localhost:8080")).strip()
    return raw.rstrip("/") or "http://localhost:8080"


def build_invitation_url(exam_id: int) -> str:
    """Build a same-origin navigation hint with no identity or bearer data."""

    return f"{_candidate_public_base_url()}/exams/{int(exam_id)}/start"


def deterministic_message_id(exam_id: int, scope_id: int) -> str:
    digest = hashlib.sha256(f"{exam_id}:{scope_id}".encode()).hexdigest()[:24]
    return f"<exam-invitation-{digest}@internal-exam-platform>"


def send_invitation_email(
    *,
    to_email: str,
    roster_name: str,
    exam_title: str,
    exam_url: str,
    message_id: str,
) -> None:
    delivery = InvitationEmail(
        to_email=to_email,
        roster_name=roster_name,
        exam_title=exam_title,
        exam_url=exam_url,
        message_id=message_id,
    )
    mode = (
        str(_setting("candidate_login_email_delivery_mode", "memory")).strip().lower()
    )
    if mode == "memory":
        invitation_email_outbox.append(delivery)
        return
    if mode != "smtp":
        raise PermanentEmailDeliveryError()
    _send_invitation_smtp(delivery)


def _send_invitation_smtp(delivery: InvitationEmail) -> None:
    message = EmailMessage()
    message["From"] = str(_setting("candidate_login_email_from", ""))
    message["To"] = delivery.to_email
    message["Subject"] = f"{delivery.exam_title}考试邀请"
    message["Message-ID"] = delivery.message_id
    message.set_content(
        "\n".join(
            [
                f"{delivery.roster_name}，您好：",
                "",
                f"您已被邀请参加：{delivery.exam_title}",
                "请在考试平台完成邮箱登录后进入考试。",
                f"考试入口：{delivery.exam_url}",
                "",
                "此邮件仅用于通知，不包含登录凭据或考试授权。",
            ]
        )
    )
    try:
        tls_context = ssl.create_default_context()
        use_ssl = bool(_setting("candidate_login_smtp_use_ssl", False))
        host = str(_setting("candidate_login_smtp_host", ""))
        port = int(_setting("candidate_login_smtp_port", 587))
        if use_ssl:
            smtp_client = smtplib.SMTP_SSL(host, port, timeout=10, context=tls_context)
        else:
            smtp_client = smtplib.SMTP(host, port, timeout=10)
        with smtp_client as smtp:
            if not use_ssl and bool(_setting("candidate_login_smtp_use_tls", True)):
                smtp.starttls(context=tls_context)
            username = str(_setting("candidate_login_smtp_username", ""))
            if username:
                smtp.login(username, str(_setting("candidate_login_smtp_password", "")))
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        if isinstance(exc, smtplib.SMTPResponseException) and not (
            400 <= exc.smtp_code < 500
        ):
            raise PermanentEmailDeliveryError() from exc
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            raise PermanentEmailDeliveryError() from exc
        raise TransientEmailDeliveryError() from exc


def deliver_invitation_email(
    *,
    scope_id: int,
    to_email: str,
    roster_name: str,
    exam_title: str,
    exam_id: int,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    delivered, _error_class = deliver_invitation_email_outcome(
        scope_id=scope_id,
        to_email=to_email,
        roster_name=roster_name,
        exam_title=exam_title,
        exam_id=exam_id,
        sleep=sleep,
    )
    return delivered


def deliver_invitation_email_outcome(
    *,
    scope_id: int,
    to_email: str,
    roster_name: str,
    exam_title: str,
    exam_id: int,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bool, str | None]:
    attempts = int(_setting("candidate_login_email_max_attempts", 3))
    base_seconds = float(_setting("candidate_login_email_retry_base_seconds", 1.0))
    payload = {
        "to_email": to_email,
        "roster_name": roster_name,
        "exam_title": exam_title,
        "exam_url": build_invitation_url(exam_id),
        "message_id": deterministic_message_id(exam_id, scope_id),
    }
    for attempt in range(1, max(1, attempts) + 1):
        try:
            send_invitation_email(**payload)
        except TransientEmailDeliveryError as exc:
            if attempt >= attempts:
                _log_failure(scope_id, attempt, exc)
                return False, "transient"
            sleep(base_seconds * (2 ** (attempt - 1)))
        except Exception as exc:
            _log_failure(scope_id, attempt, exc)
            return False, _sanitize_error_class(exc)
        else:
            logger.info(
                "exam_invitation.email_delivery_succeeded",
                extra={
                    "event": "exam_invitation.email_delivery_succeeded",
                    "scope_id": scope_id,
                    "attempt": attempt,
                },
            )
            return True, None
    return False, "delivery_error"


def _log_failure(scope_id: int, attempt: int, exc: Exception) -> None:
    logger.warning(
        "exam_invitation.email_delivery_failed",
        extra={
            "event": "exam_invitation.email_delivery_failed",
            "scope_id": scope_id,
            "attempt": attempt,
            "error_type": _sanitize_error_class(exc),
        },
    )


def _sanitize_error_class(exc: Exception) -> str:
    if isinstance(exc, TransientEmailDeliveryError):
        return "transient"
    if isinstance(exc, PermanentEmailDeliveryError):
        return "permanent"
    if isinstance(exc, (OSError, smtplib.SMTPException)):
        return "smtp"
    return "delivery_error"


def _scope_claimable(scope: ExamCandidateScope, *, mode: str, now: datetime) -> bool:
    expected = "not_sent" if mode == "initial" else "failed"
    if scope.invitation_status != expected:
        return False
    claimed_at = scope.invitation_claimed_at
    if claimed_at is None:
        return True
    return (now - to_utc(claimed_at)).total_seconds() >= invitation_claim_ttl_seconds()


def claim_invitations(
    db: Session,
    exam_id: int,
    *,
    mode: str,
    claim_owner: str | None = None,
    operator_subject: str | None = None,
    now: datetime | None = None,
    commit: bool = True,
) -> InvitationSchedule:
    """Atomically claim a bounded batch before background scheduling."""

    if mode not in {"initial", "resend"}:
        raise ValueError("invitation mode must be initial or resend")
    assert_admin_mutation_allowed(db)
    if operator_subject:
        check_invitation_admin_rate_limit(
            operator_subject=operator_subject, exam_id=exam_id, mode=mode
        )
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "active":
        raise InvitationMutationError("只有已发布考试可以发送邀请")
    owner = claim_owner or uuid4().hex
    checked_at = now or datetime.now(UTC)
    scopes = (
        db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.exam_id == exam_id)
        .order_by(ExamCandidateScope.id)
        .with_for_update()
        .all()
    )
    eligible = [
        scope for scope in scopes if _scope_claimable(scope, mode=mode, now=checked_at)
    ]
    cap = invitation_batch_size()
    selected = eligible[:cap]
    for scope in selected:
        scope.invitation_claim_owner = owner
        scope.invitation_claimed_at = checked_at
        scope.last_invitation_attempt_at = checked_at
    if operator_subject:
        from app.services.audit_service import record_admin_event

        record_admin_event(
            db,
            operator_subject=operator_subject,
            action="exam_invitation_scheduled",
            target_type="exam",
            target_id=exam_id,
            metadata={
                "exam_id": exam_id,
                "selected_count": len(selected),
                "accepted_count": len(selected),
                "rejected_count": max(0, len(scopes) - len(selected)),
                "mode": mode,
            },
        )
    if commit:
        db.commit()
    else:
        db.flush()
    return InvitationSchedule(
        exam_id=exam_id,
        mode=mode,
        selected_count=len(selected),
        accepted_count=len(selected),
        rejected_count=max(0, len(scopes) - len(selected)),
        scheduled_count=len(selected),
        scope_ids=tuple(scope.id for scope in selected),
        claim_owner=owner,
    )


def deliver_claimed_invitations(
    scope_ids: Iterable[int],
    claim_owner: str,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    operator_subject: str | None = None,
) -> dict[str, int]:
    """Deliver each claimed scope in an independent database session."""

    counts = {"sent": 0, "failed": 0}
    exam_id: int | None = None
    for scope_id in scope_ids:
        with session_factory() as db:
            scope = db.get(ExamCandidateScope, scope_id)
            if scope is None or scope.invitation_claim_owner != claim_owner:
                continue
            exam = db.get(Exam, scope.exam_id)
            if exam is None:
                continue
            exam_id = exam.id
            try:
                sent, error_class = deliver_invitation_email_outcome(
                    scope_id=scope.id,
                    to_email=scope.roster_email,
                    roster_name=scope.roster_name,
                    exam_title=exam.title,
                    exam_id=exam.id,
                )
            except Exception:
                # Leave the claim in place for explicit stale-claim recovery.
                db.rollback()
                continue
            scope.invitation_status = "sent" if sent else "failed"
            scope.invitation_error_class = None if sent else error_class
            scope.invitation_sent_at = datetime.now(UTC) if sent else None
            scope.invitation_claim_owner = None
            scope.invitation_claimed_at = None
            counts["sent" if sent else "failed"] += 1
            db.commit()

    if operator_subject is not None and exam_id is not None:
        try:
            from app.services.audit_service import record_admin_event

            with session_factory() as audit_db:
                record_admin_event(
                    audit_db,
                    operator_subject=operator_subject,
                    action=(
                        "exam_invitation_sent"
                        if counts["sent"] or counts["failed"]
                        else "exam_invitation_scheduled"
                    ),
                    target_type="exam",
                    target_id=exam_id,
                    metadata={
                        "exam_id": exam_id,
                        "sent_count": counts["sent"],
                        "failed_count": counts["failed"],
                        "outcome_classes": [
                            key for key, value in counts.items() if value
                        ],
                    },
                )
                audit_db.commit()
        except Exception:
            logger.warning(
                "exam_invitation.audit_failed",
                extra={"event": "exam_invitation.audit_failed", "exam_id": exam_id},
            )
    return counts


def invitation_status(db: Session, exam_id: int) -> dict[str, object]:
    from app.services.exam_service import list_exam_candidates

    rows = list_exam_candidates(db, exam_id)
    counts = {
        "not_sent": sum(row.invitation_status == "not_sent" for row in rows),
        "sent": sum(row.invitation_status == "sent" for row in rows),
        "failed": sum(row.invitation_status == "failed" for row in rows),
    }
    return {
        "exam_id": exam_id,
        "total_count": len(rows),
        "not_sent_count": counts["not_sent"],
        "sent_count": counts["sent"],
        "failed_count": counts["failed"],
        "rows": rows,
    }
