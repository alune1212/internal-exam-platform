from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
    Question,
)
from app.models.attempt import SUBMITTED_STATUSES
from app.schemas.report import (
    AbsentCandidateRow,
    QuestionAccuracyRow,
    ScoreReportRow,
    WrongQuestionRow,
)


def get_score_report(db: Session) -> list[ScoreReportRow]:
    """成绩报表：所有已提交 attempt 的成绩汇总。"""
    rows = (
        db.query(
            Candidate.name,
            Candidate.employee_no,
            Candidate.department,
            Exam.title,
            ExamAttempt.score,
            ExamAttempt.total_score,
            ExamAttempt.submitted_at,
        )
        .join(ExamAttempt, ExamAttempt.candidate_id == Candidate.id)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .filter(ExamAttempt.status.in_(SUBMITTED_STATUSES))
        .order_by(ExamAttempt.score.desc())
        .all()
    )

    return [
        ScoreReportRow(
            candidate_name=name,
            employee_no=employee_no,
            department=department,
            exam_title=exam_title,
            score=float(score),
            total_score=float(total_score),
            submitted_at=submitted_at,
        )
        for name, employee_no, department, exam_title, score, total_score, submitted_at in rows
    ]


def get_question_accuracy(db: Session) -> list[QuestionAccuracyRow]:
    """题目正确率：基于快照统计每道原始题目的答对率。"""
    correct_expr = case((ExamAttemptAnswer.is_correct == True, 1), else_=0)  # noqa: E712

    stats = (
        db.query(
            ExamAttemptQuestion.original_question_id,
            ExamAttemptQuestion.stem_snapshot,
            func.count(ExamAttemptAnswer.id).label("total_count"),
            func.sum(correct_expr).label("correct_count"),
        )
        .join(
            ExamAttemptAnswer,
            ExamAttemptAnswer.attempt_question_id == ExamAttemptQuestion.id,
        )
        .join(ExamAttempt, ExamAttempt.id == ExamAttemptQuestion.attempt_id)
        .filter(ExamAttempt.status.in_(SUBMITTED_STATUSES))
        .group_by(
            ExamAttemptQuestion.original_question_id, ExamAttemptQuestion.stem_snapshot
        )
        .all()
    )

    result = [
        QuestionAccuracyRow(
            question_id=original_id or 0,
            stem=stem,
            correct_count=correct_count_val or 0,
            total_count=total_count_val,
            accuracy_rate=round((correct_count_val or 0) / total_count_val, 4)
            if total_count_val > 0
            else 0.0,
        )
        for original_id, stem, total_count_val, correct_count_val in stats
    ]

    return sorted(result, key=lambda r: r.accuracy_rate)


def get_wrong_questions(db: Session) -> list[WrongQuestionRow]:
    """错题统计：答错次数最多的题目。"""
    rows = (
        db.query(
            ExamAttemptQuestion.original_question_id,
            ExamAttemptQuestion.stem_snapshot,
            func.count(ExamAttemptAnswer.id).label("wrong_count"),
            Question.category_1,
            Question.category_2,
        )
        .join(
            ExamAttemptAnswer,
            ExamAttemptAnswer.attempt_question_id == ExamAttemptQuestion.id,
        )
        .join(ExamAttempt, ExamAttempt.id == ExamAttemptQuestion.attempt_id)
        .outerjoin(Question, Question.id == ExamAttemptQuestion.original_question_id)
        .filter(
            ExamAttempt.status.in_(SUBMITTED_STATUSES),
            ExamAttemptAnswer.is_correct == False,  # noqa: E712
        )
        .group_by(
            ExamAttemptQuestion.original_question_id,
            ExamAttemptQuestion.stem_snapshot,
            Question.category_1,
            Question.category_2,
        )
        .order_by(func.count(ExamAttemptAnswer.id).desc())
        .all()
    )

    return [
        WrongQuestionRow(
            question_id=original_id or 0,
            stem=stem,
            wrong_count=wrong_count,
            category_1=cat1,
            category_2=cat2,
        )
        for original_id, stem, wrong_count, cat1, cat2 in rows
    ]


def get_absent_candidates(db: Session) -> list[AbsentCandidateRow]:
    """缺考人员：应参但无任何 attempt 记录的考生。"""
    attempted_ids = select(ExamAttempt.candidate_id).distinct()

    rows = (
        db.query(Candidate)
        .filter(
            Candidate.should_attend == True,  # noqa: E712
            Candidate.status == "active",
            ~Candidate.id.in_(attempted_ids),
        )
        .order_by(Candidate.name)
        .all()
    )

    return [
        AbsentCandidateRow(
            candidate_id=c.id,
            name=c.name,
            employee_no=c.employee_no,
            department=c.department,
            exam_group=c.exam_group,
        )
        for c in rows
    ]
