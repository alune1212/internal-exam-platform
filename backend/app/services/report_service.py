from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
    ExamCandidateScope,
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
    latest_submitted = latest_submitted_attempts(db)
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
        .join(
            latest_submitted,
            (latest_submitted.c.exam_id == ExamAttempt.exam_id)
            & (latest_submitted.c.candidate_id == ExamAttempt.candidate_id)
            & (latest_submitted.c.attempt_no == ExamAttempt.attempt_no),
        )
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
    latest_submitted = latest_submitted_attempts(db)

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
        .join(
            latest_submitted,
            latest_submitted.c.attempt_id == ExamAttempt.id,
        )
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
    latest_submitted = latest_submitted_attempts(db)
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
        .join(
            latest_submitted,
            latest_submitted.c.attempt_id == ExamAttempt.id,
        )
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


def get_absent_candidates(
    db: Session, exam_id: int | None = None, status: str = "not_started"
) -> list[AbsentCandidateRow]:
    """缺考人员：应参但在指定考试中无 attempt 记录的考生。

    不传 exam_id 时保留旧行为（全局从未参考过）。
    """
    if exam_id is not None:
        base = (
            db.query(Candidate)
            .join(ExamCandidateScope, ExamCandidateScope.candidate_id == Candidate.id)
            .filter(
                ExamCandidateScope.exam_id == exam_id,
                Candidate.should_attend == True,  # noqa: E712
                Candidate.status == "active",
            )
        )
        if status == "not_started":
            attempted_ids = (
                select(ExamAttempt.candidate_id)
                .where(ExamAttempt.exam_id == exam_id)
                .distinct()
            )
            rows = (
                base.filter(~Candidate.id.in_(attempted_ids))
                .order_by(Candidate.name)
                .all()
            )
        elif status == "in_progress":
            rows = (
                base.join(ExamAttempt, ExamAttempt.candidate_id == Candidate.id)
                .filter(
                    ExamAttempt.exam_id == exam_id,
                    ExamAttempt.status == "in_progress",
                )
                .order_by(Candidate.name)
                .all()
            )
        elif status == "submitted":
            latest_submitted = latest_submitted_attempts(db)
            rows = (
                base.join(ExamAttempt, ExamAttempt.candidate_id == Candidate.id)
                .join(
                    latest_submitted,
                    latest_submitted.c.attempt_id == ExamAttempt.id,
                )
                .order_by(Candidate.name)
                .all()
            )
        else:
            rows = []
    else:
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
            attendance_status=status,
        )
        for c in rows
    ]


def latest_submitted_attempts(db: Session):
    latest_attempt_no = (
        db.query(
            ExamAttempt.exam_id.label("exam_id"),
            ExamAttempt.candidate_id.label("candidate_id"),
            func.max(ExamAttempt.attempt_no).label("attempt_no"),
        )
        .filter(ExamAttempt.status.in_(SUBMITTED_STATUSES))
        .group_by(ExamAttempt.exam_id, ExamAttempt.candidate_id)
        .subquery()
    )
    return (
        db.query(
            ExamAttempt.id.label("attempt_id"),
            ExamAttempt.exam_id.label("exam_id"),
            ExamAttempt.candidate_id.label("candidate_id"),
            ExamAttempt.attempt_no.label("attempt_no"),
        )
        .join(
            latest_attempt_no,
            (latest_attempt_no.c.exam_id == ExamAttempt.exam_id)
            & (latest_attempt_no.c.candidate_id == ExamAttempt.candidate_id)
            & (latest_attempt_no.c.attempt_no == ExamAttempt.attempt_no),
        )
        .subquery()
    )


def generate_report_workbook(db: Session) -> BytesIO:
    workbook = Workbook()
    workbook.remove(workbook.active)

    _append_sheet(
        workbook,
        "成绩报表",
        ["姓名", "员工号", "部门", "考试", "得分", "总分", "提交时间"],
        [
            [
                row.candidate_name,
                row.employee_no,
                row.department,
                row.exam_title,
                row.score,
                row.total_score,
                row.submitted_at.isoformat() if row.submitted_at else None,
            ]
            for row in get_score_report(db)
        ],
    )
    _append_sheet(
        workbook,
        "题目正确率",
        ["题目ID", "题干", "答对次数", "作答次数", "正确率"],
        [
            [
                row.question_id,
                row.stem,
                row.correct_count,
                row.total_count,
                row.accuracy_rate,
            ]
            for row in get_question_accuracy(db)
        ],
    )
    _append_sheet(
        workbook,
        "错题统计",
        ["题目ID", "题干", "错误次数", "一级分类", "二级分类"],
        [
            [row.question_id, row.stem, row.wrong_count, row.category_1, row.category_2]
            for row in get_wrong_questions(db)
        ],
    )
    _append_sheet(
        workbook,
        "缺考人员",
        ["考生ID", "姓名", "员工号", "部门", "考试分组"],
        [
            [
                row.candidate_id,
                row.name,
                row.employee_no,
                row.department,
                row.exam_group,
            ]
            for row in get_absent_candidates(db)
        ],
    )

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def _append_sheet(
    workbook: Workbook, title: str, headers: list[str], rows: list[list[object]]
) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(
            max(max_length + 2, 10), 48
        )
