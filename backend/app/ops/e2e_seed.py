"""Seed the disposable PostgreSQL database used by browser and capacity gates."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Candidate, Exam, ExamCandidateScope, Question, QuestionOption

EXAM_TITLE = "E2E 正式考试"
CANDIDATE_EMAIL = "e2e.candidate@example.com"


def assert_disposable_database() -> None:
    database_name = urlparse(settings.database_url).path.casefold()
    if (
        settings.environment != "development"
        or os.getenv("E2E_DISPOSABLE_DATABASE") != "true"
        or "e2e" not in database_name
    ):
        raise RuntimeError(
            "E2E seed is restricted to an explicitly disposable database"
        )


def seed() -> tuple[int, int]:
    assert_disposable_database()
    now = datetime.now(UTC)
    with SessionLocal() as db:
        candidate = (
            db.query(Candidate).filter(Candidate.email == CANDIDATE_EMAIL).one_or_none()
        )
        if candidate is None:
            candidate = Candidate(
                name="端到端考生",
                employee_no="E2E-001",
                email=CANDIDATE_EMAIL,
                department="质量保障",
                status="active",
                should_attend=True,
            )
            db.add(candidate)
            db.flush()

        question = (
            db.query(Question).filter(Question.source_no == "E2E-Q-001").one_or_none()
        )
        if question is None:
            question = Question(
                question_type="single",
                stem="E2E：受控局域网正式考试应由谁确认开考？",
                analysis="正式考试必须由主操作员完成预检后人工确认开考。",
                category_1="E2E",
                score=Decimal("2"),
                status="active",
                source="browser-gate",
                source_no="E2E-Q-001",
            )
            db.add(question)
            db.flush()
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
                        content="任意考生",
                        is_correct=False,
                        sort_order=1,
                    ),
                ]
            )

        exam = db.query(Exam).filter(Exam.title == EXAM_TITLE).one_or_none()
        if exam is None:
            exam = Exam(
                title=EXAM_TITLE,
                description="Disposable Playwright release gate",
                duration_minutes=30,
                question_rule={
                    "question_count": 1,
                    "total_score": 2,
                    "pass_score": 1,
                    "mode": "fixed_paper",
                    "type_counts": {"single": 1},
                },
                status="draft",
                show_answer_after_submit=False,
                show_ranking=False,
                available_from=now - timedelta(minutes=5),
                available_until=now + timedelta(hours=2),
            )
            db.add(exam)
            db.flush()
        scope = (
            db.query(ExamCandidateScope)
            .filter(
                ExamCandidateScope.exam_id == exam.id,
                ExamCandidateScope.candidate_id == candidate.id,
            )
            .one_or_none()
        )
        if scope is None:
            db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
        db.commit()
        return exam.id, candidate.id


if __name__ == "__main__":
    seeded_exam_id, seeded_candidate_id = seed()
    sys.stdout.write(
        f"e2e_seeded exam_id={seeded_exam_id} candidate_id={seeded_candidate_id}\n"
    )
