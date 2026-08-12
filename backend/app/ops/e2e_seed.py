"""Seed deterministic account and exam fixtures for disposable E2E runs.

The browser gate intentionally exercises the account boundary instead of the
legacy roster-login contract.  All fixtures are keyed by normalized email and
all formal identity is stored on the exam scope snapshot.  This module is
restricted to an explicitly disposable database and never creates a bearer
credential or writes a real-mail address outside that database.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import (
    Candidate,
    Exam,
    ExamCandidateScope,
    ExamQuestionPool,
    Question,
    QuestionOption,
)

E2E_EXAM_TITLE = "E2E 邀请考试（即将开放）"
E2E_INVITATION_STATUS_EXAM_TITLE = "E2E 邀请投递状态"
E2E_QUESTION_SOURCE_NO = "E2E-Q-001"
E2E_STATUS_QUESTION_SOURCE_NO = "E2E-Q-002"

E2E_SCOPED_EMAIL = "e2e.scoped@example.com"
E2E_PENDING_EMAIL = "e2e.pending@example.com"
E2E_UNSCOPED_EMAIL = "e2e.unscoped@example.com"
E2E_INACTIVE_EMAIL = "e2e.inactive@example.com"
E2E_SENT_EMAIL = "e2e.invited.sent@example.com"
E2E_FAILED_EMAIL = "e2e.invited.failed@example.com"


@dataclass(frozen=True)
class SeededE2EData:
    """Stable identifiers needed by the browser gate and local diagnostics."""

    upcoming_exam_id: int
    invitation_status_exam_id: int
    scoped_account_id: int
    pending_account_id: int
    unscoped_account_id: int
    inactive_account_id: int
    sent_scope_account_id: int
    failed_scope_account_id: int

    def as_public_dict(self) -> dict[str, int]:
        return {
            "upcoming_exam_id": self.upcoming_exam_id,
            "invitation_status_exam_id": self.invitation_status_exam_id,
            "scoped_account_id": self.scoped_account_id,
            "pending_account_id": self.pending_account_id,
            "unscoped_account_id": self.unscoped_account_id,
            "inactive_account_id": self.inactive_account_id,
            "sent_scope_account_id": self.sent_scope_account_id,
            "failed_scope_account_id": self.failed_scope_account_id,
        }


def assert_disposable_database() -> None:
    """Fail closed unless the caller explicitly selected the E2E database."""

    database_name = urlparse(settings.database_url).path.removeprefix("/").casefold()
    if (
        settings.environment != "development"
        or os.getenv("E2E_DISPOSABLE_DATABASE") != "true"
        or "e2e" not in database_name
    ):
        raise RuntimeError(
            "E2E seed is restricted to an explicitly disposable database"
        )


def _ensure_account(
    db, *, email: str, display_name: str | None, status: str
) -> Candidate:
    account = db.query(Candidate).filter(Candidate.email == email).one_or_none()
    if account is None:
        account = Candidate(email=email, name=display_name, status=status)
        db.add(account)
        db.flush()
    else:
        # Every invocation starts from the same disposable fixture state.  A
        # prior browser run may have completed registration or deactivated an
        # account; restoring only these fixture-owned fields keeps reruns
        # deterministic without touching histories or attempts.
        account.name = display_name
        account.status = status
    return account


def _ensure_question(db, *, source_no: str, stem: str, analysis: str) -> Question:
    question = db.query(Question).filter(Question.source_no == source_no).one_or_none()
    if question is None:
        question = Question(
            question_type="single",
            stem=stem,
            analysis=analysis,
            category_1="E2E",
            score=Decimal("2"),
            status="active",
            source="browser-gate",
            source_no=source_no,
        )
        db.add(question)
        db.flush()
    else:
        # Keep reruns deterministic while preserving any unrelated question
        # edits in the disposable database.
        question.status = "active"

    if (
        not db.query(QuestionOption.id)
        .filter(QuestionOption.question_id == question.id)
        .first()
    ):
        db.add_all(
            [
                QuestionOption(
                    question_id=question.id,
                    label="A",
                    content="主操作员",
                    is_correct=True,
                    sort_order=0,
                ),
                QuestionOption(
                    question_id=question.id,
                    label="B",
                    content="任意用户",
                    is_correct=False,
                    sort_order=1,
                ),
            ]
        )
    return question


def _ensure_exam(
    db,
    *,
    title: str,
    question: Question,
    available_from: datetime,
    available_until: datetime,
) -> Exam:
    exam = db.query(Exam).filter(Exam.title == title).one_or_none()
    if exam is None:
        exam = Exam(
            title=title,
            description="Disposable browser gate fixture",
            duration_minutes=30,
            question_rule={
                "question_count": 1,
                "total_score": 2,
                "pass_score": 1,
                "mode": "fixed_paper",
                "type_counts": {"single": 1},
            },
            status="active",
            show_answer_after_submit=False,
            show_ranking=False,
            available_from=available_from,
            available_until=available_until,
        )
        db.add(exam)
        db.flush()
    else:
        # The fixture is disposable; ensure an interrupted run cannot leave a
        # draft or stale opening window for the next browser invocation.
        exam.status = "active"
        exam.available_from = available_from
        exam.available_until = available_until
        exam.question_rule = {
            "question_count": 1,
            "total_score": 2,
            "pass_score": 1,
            "mode": "fixed_paper",
            "type_counts": {"single": 1},
        }
    pool = (
        db.query(ExamQuestionPool)
        .filter(
            ExamQuestionPool.exam_id == exam.id,
            ExamQuestionPool.question_id == question.id,
        )
        .one_or_none()
    )
    if pool is None:
        db.add(ExamQuestionPool(exam_id=exam.id, question_id=question.id, sort_order=0))
    return exam


def _ensure_scope(
    db,
    *,
    exam: Exam,
    account: Candidate,
    roster_name: str,
    invitation_status: str = "not_sent",
    department: str | None = None,
    exam_group: str | None = None,
) -> ExamCandidateScope:
    scope = (
        db.query(ExamCandidateScope)
        .filter(
            ExamCandidateScope.exam_id == exam.id,
            ExamCandidateScope.candidate_id == account.id,
        )
        .one_or_none()
    )
    if scope is None:
        scope = ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=account.id,
            roster_email=account.email,
            roster_name=roster_name,
            department=department,
            exam_group=exam_group,
            invitation_status=invitation_status,
        )
        db.add(scope)
    else:
        scope.roster_email = account.email
        scope.roster_name = roster_name
        scope.department = department
        scope.exam_group = exam_group
        scope.invitation_status = invitation_status
        scope.last_invitation_attempt_at = None
        scope.invitation_sent_at = None
        scope.invitation_error_class = None
        scope.invitation_claimed_at = None
        scope.invitation_claim_owner = None
    return scope


def seed_operational_data() -> SeededE2EData:
    """Create the account, roster, invitation, practice, and report fixtures."""

    assert_disposable_database()
    now = datetime.now(UTC)
    with SessionLocal() as db:
        scoped = _ensure_account(
            db,
            email=E2E_SCOPED_EMAIL,
            display_name="平台显示名（可编辑）",
            status="active",
        )
        pending = _ensure_account(
            db, email=E2E_PENDING_EMAIL, display_name=None, status="pending"
        )
        unscoped = _ensure_account(
            db, email=E2E_UNSCOPED_EMAIL, display_name="未受邀用户", status="active"
        )
        inactive = _ensure_account(
            db, email=E2E_INACTIVE_EMAIL, display_name="已停用用户", status="inactive"
        )
        sent_account = _ensure_account(
            db, email=E2E_SENT_EMAIL, display_name="已发送邀请用户", status="active"
        )
        failed_account = _ensure_account(
            db, email=E2E_FAILED_EMAIL, display_name=None, status="pending"
        )

        question = _ensure_question(
            db,
            source_no=E2E_QUESTION_SOURCE_NO,
            stem="E2E：受控局域网正式考试应由谁确认开考？",
            analysis="正式考试必须由主操作员完成预检后人工确认开考。",
        )
        status_question = _ensure_question(
            db,
            source_no=E2E_STATUS_QUESTION_SOURCE_NO,
            stem="E2E：邀请邮件是否授予正式考试权限？",
            analysis="邀请邮件只提供导航提示，正式权限仍由冻结名单范围决定。",
        )

        upcoming = _ensure_exam(
            db,
            title=E2E_EXAM_TITLE,
            question=question,
            available_from=now + timedelta(hours=1),
            available_until=now + timedelta(hours=3),
        )
        invitation_status_exam = _ensure_exam(
            db,
            title=E2E_INVITATION_STATUS_EXAM_TITLE,
            question=status_question,
            available_from=now - timedelta(minutes=5),
            available_until=now + timedelta(hours=2),
        )

        _ensure_scope(
            db,
            exam=upcoming,
            account=scoped,
            roster_name="冻结名单姓名",
            department="质量保障",
            exam_group="E2E-SCOPED",
        )
        _ensure_scope(
            db,
            exam=upcoming,
            account=pending,
            roster_name="待注册应考人员",
            department="质量保障",
            exam_group="E2E-PENDING",
        )
        # Keeping the inactive scope lets report and authorization gates prove
        # that a frozen row survives deactivation without granting access.
        _ensure_scope(
            db,
            exam=upcoming,
            account=inactive,
            roster_name="冻结停用人员",
            invitation_status="not_sent",
            department="质量保障",
            exam_group="E2E-INACTIVE",
        )
        _ensure_scope(
            db,
            exam=invitation_status_exam,
            account=sent_account,
            roster_name="已发送冻结姓名",
            invitation_status="sent",
            department="运营",
            exam_group="E2E-SENT",
        )
        _ensure_scope(
            db,
            exam=invitation_status_exam,
            account=failed_account,
            roster_name="失败待重发姓名",
            invitation_status="failed",
            department="运营",
            exam_group="E2E-FAILED",
        )
        db.commit()
        return SeededE2EData(
            upcoming_exam_id=upcoming.id,
            invitation_status_exam_id=invitation_status_exam.id,
            scoped_account_id=scoped.id,
            pending_account_id=pending.id,
            unscoped_account_id=unscoped.id,
            inactive_account_id=inactive.id,
            sent_scope_account_id=sent_account.id,
            failed_scope_account_id=failed_account.id,
        )


def seed() -> tuple[int, int]:
    """Compatibility wrapper used by local operators: exam ID, scoped account ID."""

    data = seed_operational_data()
    return data.upcoming_exam_id, data.scoped_account_id


if __name__ == "__main__":
    seeded = seed_operational_data()
    sys.stdout.write(
        "e2e_seeded "
        + json.dumps(seeded.as_public_dict(), ensure_ascii=False, sort_keys=True)
        + "\n"
    )
