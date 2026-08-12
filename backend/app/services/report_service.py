from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.models import (
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
    RankingRow,
    ScoreReportRow,
    WrongQuestionRow,
)
from app.services.excel_security import escape_excel_cell

ATTENDANCE_STATUS_LABELS = {
    "not_started": "未开始",
    "in_progress": "进行中",
    "submitted": "已交卷",
}


def get_score_report(db: Session, exam_id: int | None = None) -> list[ScoreReportRow]:
    """个人成绩：按考试冻结的 roster identity 汇总已交卷结果。

    The candidate row is deliberately not joined here.  A platform account's
    display name/status may change after publication; formal reports must keep
    the snapshot stored on the matching ``exam_candidate_scope`` row instead.
    """

    latest_submitted = latest_submitted_attempts(db, exam_id=exam_id)
    query = (
        db.query(
            ExamCandidateScope.candidate_id,
            ExamCandidateScope.roster_name,
            ExamCandidateScope.roster_email,
            ExamCandidateScope.department,
            ExamCandidateScope.position,
            ExamCandidateScope.exam_group,
            ExamCandidateScope.roster_remark,
            Exam.id,
            Exam.title,
            ExamAttempt.score,
            ExamAttempt.total_score,
            ExamAttempt.submitted_at,
        )
        .select_from(ExamAttempt)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .join(
            latest_submitted,
            (latest_submitted.c.exam_id == ExamAttempt.exam_id)
            & (latest_submitted.c.candidate_id == ExamAttempt.candidate_id)
            & (latest_submitted.c.attempt_no == ExamAttempt.attempt_no),
        )
        .join(
            ExamCandidateScope,
            and_(
                ExamCandidateScope.exam_id == ExamAttempt.exam_id,
                ExamCandidateScope.candidate_id == ExamAttempt.candidate_id,
            ),
        )
        .filter(ExamAttempt.status.in_(SUBMITTED_STATUSES))
    )
    if exam_id is not None:
        query = query.filter(ExamAttempt.exam_id == exam_id)
    rows = query.order_by(ExamAttempt.score.desc()).all()

    return [
        ScoreReportRow(
            candidate_id=candidate_id,
            roster_name=roster_name,
            roster_email=roster_email,
            department=department,
            position=position,
            exam_group=exam_group,
            roster_remark=roster_remark,
            exam_id=exam_id_value,
            exam_title=exam_title,
            score=float(score),
            total_score=float(total_score),
            submitted_at=submitted_at,
        )
        for (
            candidate_id,
            roster_name,
            roster_email,
            department,
            position,
            exam_group,
            roster_remark,
            exam_id_value,
            exam_title,
            score,
            total_score,
            submitted_at,
        ) in rows
    ]


def get_ranking(db: Session, exam_id: int) -> list[RankingRow]:
    """Return the administrator ranking for one exam.

    Only the latest non-voided submitted/auto-submitted attempt per scoped
    account participates.  Rows are ordered by score descending, submission
    time ascending, and candidate id ascending.  Ties use conventional
    competition ranking (``1, 1, 3``), making the ordering deterministic even
    when scores and submission times match.
    """

    latest_attempt_no = (
        db.query(
            ExamAttempt.exam_id.label("exam_id"),
            ExamAttempt.candidate_id.label("candidate_id"),
            func.max(ExamAttempt.attempt_no).label("attempt_no"),
        )
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(SUBMITTED_STATUSES),
            ExamAttempt.voided_at.is_(None),
        )
        .group_by(ExamAttempt.exam_id, ExamAttempt.candidate_id)
        .subquery()
    )
    rows = (
        db.query(
            ExamCandidateScope.candidate_id,
            ExamCandidateScope.roster_name,
            ExamCandidateScope.roster_email,
            ExamCandidateScope.department,
            ExamCandidateScope.position,
            ExamCandidateScope.exam_group,
            ExamCandidateScope.roster_remark,
            Exam.id,
            Exam.title,
            ExamAttempt.score,
            ExamAttempt.total_score,
            ExamAttempt.submitted_at,
        )
        .select_from(ExamAttempt)
        .join(
            latest_attempt_no,
            (latest_attempt_no.c.exam_id == ExamAttempt.exam_id)
            & (latest_attempt_no.c.candidate_id == ExamAttempt.candidate_id)
            & (latest_attempt_no.c.attempt_no == ExamAttempt.attempt_no),
        )
        .join(
            ExamCandidateScope,
            and_(
                ExamCandidateScope.exam_id == ExamAttempt.exam_id,
                ExamCandidateScope.candidate_id == ExamAttempt.candidate_id,
            ),
        )
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .filter(
            ExamAttempt.status.in_(SUBMITTED_STATUSES),
            ExamAttempt.voided_at.is_(None),
        )
        .order_by(
            ExamAttempt.score.desc(),
            ExamAttempt.submitted_at.asc().nulls_last(),
            ExamAttempt.candidate_id.asc(),
        )
        .all()
    )

    ranked: list[RankingRow] = []
    previous_score = None
    current_rank = 0
    for position, row in enumerate(rows, start=1):
        (
            candidate_id,
            roster_name,
            roster_email,
            department,
            scope_position,
            exam_group,
            roster_remark,
            row_exam_id,
            exam_title,
            score,
            total_score,
            submitted_at,
        ) = row
        if previous_score is None or score != previous_score:
            current_rank = position
            previous_score = score
        ranked.append(
            RankingRow(
                rank=current_rank,
                candidate_id=candidate_id,
                roster_name=roster_name,
                roster_email=roster_email,
                department=department,
                position=scope_position,
                exam_group=exam_group,
                roster_remark=roster_remark,
                exam_id=row_exam_id,
                exam_title=exam_title,
                score=float(score),
                total_score=float(total_score),
                submitted_at=submitted_at,
            )
        )
    return ranked


def get_question_accuracy(
    db: Session, exam_id: int | None = None
) -> list[QuestionAccuracyRow]:
    """题目正确率：基于快照统计每道原始题目的答对率。"""
    correct_expr = case((ExamAttemptAnswer.is_correct == True, 1), else_=0)  # noqa: E712
    latest_submitted = latest_submitted_attempts(db, exam_id=exam_id)

    query = (
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
    )
    if exam_id is not None:
        query = query.filter(ExamAttempt.exam_id == exam_id)
    stats = query.group_by(
        ExamAttemptQuestion.original_question_id, ExamAttemptQuestion.stem_snapshot
    ).all()

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


def get_wrong_questions(
    db: Session, exam_id: int | None = None
) -> list[WrongQuestionRow]:
    """错题排行：答错次数最多的题目。"""
    latest_submitted = latest_submitted_attempts(db, exam_id=exam_id)
    query = (
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
    )
    if exam_id is not None:
        query = query.filter(ExamAttempt.exam_id == exam_id)
    rows = (
        query.group_by(
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
    """参考状态：按未开始、进行中、已交卷拆分冻结 roster。

    Scope rows are the driving table so pending/inactive accounts and scoped
    recipients without an attempt remain visible.  The account row is not
    joined, which makes deactivation/profile edits irrelevant to historical
    formal attendance.
    """
    if status not in {"not_started", "in_progress", "submitted"}:
        return []

    latest_attempt = latest_attempts(db, exam_id=exam_id)
    query = (
        db.query(
            ExamCandidateScope.candidate_id,
            ExamCandidateScope.exam_id,
            Exam.title,
            ExamCandidateScope.roster_name,
            ExamCandidateScope.roster_email,
            ExamCandidateScope.department,
            ExamCandidateScope.position,
            ExamCandidateScope.exam_group,
            ExamCandidateScope.roster_remark,
            latest_attempt.c.attempt_id,
            latest_attempt.c.status,
        )
        .select_from(ExamCandidateScope)
        .join(Exam, Exam.id == ExamCandidateScope.exam_id)
        .outerjoin(
            latest_attempt,
            and_(
                latest_attempt.c.exam_id == ExamCandidateScope.exam_id,
                latest_attempt.c.candidate_id == ExamCandidateScope.candidate_id,
            ),
        )
    )
    if exam_id is not None:
        query = query.filter(ExamCandidateScope.exam_id == exam_id)

    if status == "not_started":
        query = query.filter(
            or_(
                latest_attempt.c.attempt_id.is_(None),
                latest_attempt.c.status == "voided",
            )
        )
    elif status == "in_progress":
        query = query.filter(latest_attempt.c.status == "in_progress")
    else:
        query = query.filter(latest_attempt.c.status.in_(SUBMITTED_STATUSES))

    rows = query.order_by(
        ExamCandidateScope.roster_name, ExamCandidateScope.exam_id
    ).all()
    return [
        AbsentCandidateRow(
            candidate_id=candidate_id,
            exam_id=scope_exam_id,
            exam_title=exam_title,
            roster_name=roster_name,
            roster_email=roster_email,
            department=department,
            position=position,
            exam_group=exam_group,
            roster_remark=roster_remark,
            attendance_status=status,
        )
        for (
            candidate_id,
            scope_exam_id,
            exam_title,
            roster_name,
            roster_email,
            department,
            position,
            exam_group,
            roster_remark,
            _attempt_id,
            _attempt_status,
        ) in rows
    ]


def latest_attempts(db: Session, exam_id: int | None = None):
    latest_attempt_no_query = db.query(
        ExamAttempt.exam_id.label("exam_id"),
        ExamAttempt.candidate_id.label("candidate_id"),
        func.max(ExamAttempt.attempt_no).label("attempt_no"),
    )
    if exam_id is not None:
        latest_attempt_no_query = latest_attempt_no_query.filter(
            ExamAttempt.exam_id == exam_id
        )
    latest_attempt_no = latest_attempt_no_query.group_by(
        ExamAttempt.exam_id, ExamAttempt.candidate_id
    ).subquery()
    return (
        db.query(
            ExamAttempt.id.label("attempt_id"),
            ExamAttempt.exam_id.label("exam_id"),
            ExamAttempt.candidate_id.label("candidate_id"),
            ExamAttempt.attempt_no.label("attempt_no"),
            ExamAttempt.status.label("status"),
        )
        .join(
            latest_attempt_no,
            (latest_attempt_no.c.exam_id == ExamAttempt.exam_id)
            & (latest_attempt_no.c.candidate_id == ExamAttempt.candidate_id)
            & (latest_attempt_no.c.attempt_no == ExamAttempt.attempt_no),
        )
        .subquery()
    )


def latest_submitted_attempts(db: Session, exam_id: int | None = None):
    latest_attempt_no_query = db.query(
        ExamAttempt.exam_id.label("exam_id"),
        ExamAttempt.candidate_id.label("candidate_id"),
        func.max(ExamAttempt.attempt_no).label("attempt_no"),
    ).filter(ExamAttempt.status.in_(SUBMITTED_STATUSES))
    if exam_id is not None:
        latest_attempt_no_query = latest_attempt_no_query.filter(
            ExamAttempt.exam_id == exam_id
        )
    latest_attempt_no = latest_attempt_no_query.group_by(
        ExamAttempt.exam_id, ExamAttempt.candidate_id
    ).subquery()
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
        .filter(ExamAttempt.status.in_(SUBMITTED_STATUSES))
        .subquery()
    )


def generate_report_workbook(db: Session, exam_id: int | None = None) -> BytesIO:
    workbook = Workbook()
    workbook.remove(workbook.active)

    _append_sheet(
        workbook,
        "个人成绩",
        [
            "ROSTER NAME · 名单姓名",
            "ROSTER EMAIL · 名单邮箱",
            "DEPT · 部门",
            "POSITION · 职位",
            "GROUP · 分组",
            "REMARK · 备注",
            "EXAM · 考试",
            "SCORE · 得分",
            "TOTAL · 总分",
            "SUBMITTED AT · 交卷时间",
        ],
        [
            [
                row.roster_name,
                row.roster_email,
                row.department,
                row.position,
                row.exam_group,
                row.roster_remark,
                row.exam_title,
                row.score,
                row.total_score,
                row.submitted_at.isoformat() if row.submitted_at else None,
            ]
            for row in get_score_report(db, exam_id=exam_id)
        ],
    )
    _append_sheet(
        workbook,
        "题目正确率",
        [
            "QID · 题目ID",
            "STEM · 题干",
            "CORRECT · 正确",
            "TOTAL · 总数",
            "RATE · 正确率",
        ],
        [
            [
                row.question_id,
                row.stem,
                row.correct_count,
                row.total_count,
                row.accuracy_rate,
            ]
            for row in get_question_accuracy(db, exam_id=exam_id)
        ],
    )
    _append_sheet(
        workbook,
        "错题排行",
        [
            "QID · 题目ID",
            "STEM · 题干",
            "WRONG · 错误",
            "CAT 1 · 一级分类",
            "CAT 2 · 二级分类",
        ],
        [
            [row.question_id, row.stem, row.wrong_count, row.category_1, row.category_2]
            for row in get_wrong_questions(db, exam_id=exam_id)
        ],
    )
    _append_sheet(
        workbook,
        "参考状态",
        [
            "CID · 人员ID",
            "EXAM ID · 考试ID",
            "EXAM · 考试",
            "ROSTER NAME · 名单姓名",
            "ROSTER EMAIL · 名单邮箱",
            "DEPT · 部门",
            "POSITION · 职位",
            "GROUP · 分组",
            "REMARK · 备注",
            "STATUS · 状态",
        ],
        [
            [
                row.candidate_id,
                row.exam_id,
                row.exam_title,
                row.roster_name,
                row.roster_email,
                row.department,
                row.position,
                row.exam_group,
                row.roster_remark,
                ATTENDANCE_STATUS_LABELS.get(
                    row.attendance_status, row.attendance_status
                ),
            ]
            for status in ("not_started", "in_progress", "submitted")
            for row in get_absent_candidates(db, exam_id=exam_id, status=status)
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
        sheet.append([escape_excel_cell(value) for value in row])
    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(
            max(max_length + 2, 10), 48
        )
