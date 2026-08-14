"""Aggregate read model for the administrator exam workspace.

The workspace deliberately uses grouped/windowed queries instead of composing
the row-oriented roster and report endpoints.  It therefore returns one
privacy-bounded snapshot without exposing roster identity fields or creating
an N+1 query path for latest attempts.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.core.time import ensure_aware
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamCandidateScope,
    ExamRetakeGrant,
)
from app.models.attempt import SUBMITTED_STATUSES
from app.schemas.exam import (
    ExamWorkspaceAttemptSummary,
    ExamWorkspaceAttendanceSummary,
    ExamWorkspaceIncidentSummary,
    ExamWorkspaceInvitationSummary,
    ExamWorkspaceNextAction,
    ExamWorkspaceRead,
    ExamWorkspaceRosterSummary,
    PublicationReadinessRead,
)
from app.services.exam_configuration import _build_exam_read, get_publication_readiness
from app.services.exam_errors import ExamNotFoundError


def _as_count(value: object) -> int:
    """Normalize aggregate values returned by PostgreSQL and SQLite."""

    return 0 if value is None else int(str(value))


def _roster_summary(db: Session, exam_id: int) -> ExamWorkspaceRosterSummary:
    rows = (
        db.query(Candidate.status, func.count(ExamCandidateScope.id))
        .select_from(ExamCandidateScope)
        .join(Candidate, Candidate.id == ExamCandidateScope.candidate_id)
        .filter(ExamCandidateScope.exam_id == exam_id)
        .group_by(Candidate.status)
        .all()
    )
    counts = {status: _as_count(count) for status, count in rows}
    return ExamWorkspaceRosterSummary(
        total_count=sum(counts.values()),
        active_count=counts.get("active", 0),
        pending_count=counts.get("pending", 0),
        inactive_count=counts.get("inactive", 0),
    )


def _invitation_summary(db: Session, exam_id: int) -> ExamWorkspaceInvitationSummary:
    row = (
        db.query(
            func.sum(
                case((ExamCandidateScope.invitation_status == "not_sent", 1), else_=0)
            ).label("not_sent_count"),
            func.sum(
                case((ExamCandidateScope.invitation_status == "sent", 1), else_=0)
            ).label("sent_count"),
            func.sum(
                case((ExamCandidateScope.invitation_status == "failed", 1), else_=0)
            ).label("failed_count"),
            func.sum(
                case(
                    (ExamCandidateScope.invitation_claimed_at.is_not(None), 1), else_=0
                )
            ).label("in_flight_count"),
        )
        .filter(ExamCandidateScope.exam_id == exam_id)
        .one()
    )
    return ExamWorkspaceInvitationSummary(
        not_sent_count=_as_count(row.not_sent_count),
        sent_count=_as_count(row.sent_count),
        failed_count=_as_count(row.failed_count),
        in_flight_count=_as_count(row.in_flight_count),
    )


def _attempt_summary(db: Session, exam_id: int) -> ExamWorkspaceAttemptSummary:
    rows = (
        db.query(ExamAttempt.status, func.count(ExamAttempt.id))
        .filter(ExamAttempt.exam_id == exam_id)
        .group_by(ExamAttempt.status)
        .all()
    )
    counts = {status: _as_count(count) for status, count in rows}
    return ExamWorkspaceAttemptSummary(
        in_progress_count=counts.get("in_progress", 0),
        submitted_count=counts.get("submitted", 0),
        auto_submitted_count=counts.get("auto_submitted", 0),
        voided_count=counts.get("voided", 0),
    )


def _latest_attempt_subquery(db: Session, exam_id: int):
    """Return one latest attempt row per scoped account.

    The report contract orders by greatest ``(attempt_no, id)``.  A window
    function preserves that tie-breaker instead of relying on a separate max
    query that could select columns from different attempts.
    """

    ranked = (
        db.query(
            ExamAttempt.id.label("attempt_id"),
            ExamAttempt.exam_id.label("exam_id"),
            ExamAttempt.candidate_id.label("candidate_id"),
            ExamAttempt.status.label("status"),
            func.row_number()
            .over(
                partition_by=(ExamAttempt.exam_id, ExamAttempt.candidate_id),
                order_by=(ExamAttempt.attempt_no.desc(), ExamAttempt.id.desc()),
            )
            .label("row_number"),
        )
        .filter(ExamAttempt.exam_id == exam_id)
        .subquery()
    )
    return (
        db.query(
            ranked.c.attempt_id,
            ranked.c.exam_id,
            ranked.c.candidate_id,
            ranked.c.status,
        )
        .filter(ranked.c.row_number == 1)
        .subquery()
    )


def _attendance_summary(db: Session, exam_id: int) -> ExamWorkspaceAttendanceSummary:
    latest = _latest_attempt_subquery(db, exam_id)
    row = (
        db.query(
            func.sum(
                case(
                    (latest.c.attempt_id.is_(None), 1),
                    (latest.c.status == "voided", 1),
                    else_=0,
                )
            ).label("not_started_count"),
            func.sum(case((latest.c.status == "in_progress", 1), else_=0)).label(
                "in_progress_count"
            ),
            func.sum(case((latest.c.status.in_(SUBMITTED_STATUSES), 1), else_=0)).label(
                "submitted_count"
            ),
        )
        .select_from(ExamCandidateScope)
        .outerjoin(
            latest,
            and_(
                latest.c.exam_id == ExamCandidateScope.exam_id,
                latest.c.candidate_id == ExamCandidateScope.candidate_id,
            ),
        )
        .filter(ExamCandidateScope.exam_id == exam_id)
        .one()
    )
    return ExamWorkspaceAttendanceSummary(
        not_started_count=_as_count(row.not_started_count),
        in_progress_count=_as_count(row.in_progress_count),
        submitted_count=_as_count(row.submitted_count),
    )


def _incident_summary(
    db: Session, exam_id: int, attempt_summary: ExamWorkspaceAttemptSummary
) -> ExamWorkspaceIncidentSummary:
    unused_retake_count = _as_count(
        db.query(func.count(ExamRetakeGrant.id))
        .filter(
            ExamRetakeGrant.exam_id == exam_id,
            ExamRetakeGrant.used_at.is_(None),
        )
        .scalar()
    )
    return ExamWorkspaceIncidentSummary(
        voided_count=attempt_summary.voided_count,
        unused_retake_count=unused_retake_count,
    )


def _derive_next_action(
    exam: Exam,
    *,
    observed_at: datetime,
    readiness: PublicationReadinessRead | None,
    roster: ExamWorkspaceRosterSummary,
    invitations: ExamWorkspaceInvitationSummary,
    attempts: ExamWorkspaceAttemptSummary,
) -> tuple[ExamWorkspaceNextAction, str]:
    """Apply the documented advisory action precedence in one place."""

    # Archived exams are terminal from an operator's point of view even when
    # historical invitations or incidents remain visible in the summaries.
    if exam.status == "archived":
        return "complete", "考试已归档。"

    if exam.status == "draft":
        if roster.total_count == 0:
            return "manage_roster", "请先维护应考名单。"
        if readiness is not None and not readiness.ready:
            return "fix_readiness", "发布预检仍有阻塞项，请先修复。"
        return "publish", "考试已具备发布条件，可以发布。"

    if invitations.in_flight_count:
        return "wait_invitation_delivery", "邀请正在发送，请等待投递结果。"
    if invitations.not_sent_count:
        return "send_invitations", "考试已发布，仍有未发送的邀请。"
    if invitations.failed_count:
        return "resend_failed_invitations", "有邀请发送失败，请重试失败项。"

    available_from = (
        ensure_aware(exam.available_from) if exam.available_from is not None else None
    )
    if available_from is not None and observed_at < available_from:
        return "wait_for_open", "考试尚未到开放时间。"

    if attempts.in_progress_count:
        return "monitor_exam", "考试正在进行，请持续关注现场状态。"

    usable_submissions = attempts.submitted_count + attempts.auto_submitted_count
    if usable_submissions:
        if exam.result_details_released_at is None:
            return "release_result_details", "考试已有可用成绩，可以发布答案解析。"
        return "archive_exam", "答案解析已发布，可以归档考试。"

    available_until = (
        ensure_aware(exam.available_until) if exam.available_until is not None else None
    )
    if available_until is not None and observed_at >= available_until:
        return "review_incidents", "考试窗口已结束，暂无可发布成绩，请先复核异常记录。"

    return "monitor_exam", "考试正在等待应考人员入场。"


def get_exam_workspace(db: Session, exam_id: int) -> ExamWorkspaceRead:
    """Build one privacy-bounded aggregate workspace snapshot for an exam."""

    observed_at = datetime.now(UTC)
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ExamNotFoundError(exam_id)

    readiness = (
        get_publication_readiness(db, exam_id) if exam.status == "draft" else None
    )
    roster = _roster_summary(db, exam_id)
    invitations = _invitation_summary(db, exam_id)
    attendance = _attendance_summary(db, exam_id)
    attempts = _attempt_summary(db, exam_id)
    incidents = _incident_summary(db, exam_id, attempts)
    next_action, next_action_reason = _derive_next_action(
        exam,
        observed_at=observed_at,
        readiness=readiness,
        roster=roster,
        invitations=invitations,
        attempts=attempts,
    )
    return ExamWorkspaceRead(
        observed_at=observed_at,
        exam=_build_exam_read(db, exam, observed_at=observed_at),
        readiness=readiness,
        roster_summary=roster,
        invitation_summary=invitations,
        attendance_summary=attendance,
        attempt_summary=attempts,
        incident_summary=incidents,
        next_action=next_action,
        next_action_reason=next_action_reason,
    )
