from sqlalchemy.orm import Session

from app.models import ExamCandidateScope
from app.services import exam_service, report_service
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
    submit_answers,
)


def _setup_exam_with_candidates(db: Session):
    """创建一场考试、两个考生、两道题，返回 (exam, c1, c2, start1, start2)。"""
    exam = create_exam(db, title="测试考试")
    c1 = create_candidate(db, name="张三", employee_no="E001", department="技术部")
    c2 = create_candidate(db, name="李四", employee_no="E002", department="产品部")
    db.add_all(
        [
            ExamCandidateScope(exam_id=exam.id, candidate_id=c1.id),
            ExamCandidateScope(exam_id=exam.id, candidate_id=c2.id),
        ]
    )
    db.commit()
    create_question_with_options(db, stem="题目A", score=5)
    create_question_with_options(db, stem="题目B", score=5)

    r1 = exam_service.start_exam(db, exam.id, c1.id)
    r2 = exam_service.start_exam(db, exam.id, c2.id)
    return exam, c1, c2, r1, r2


# --- 成绩报表 ---


def test_score_report_returns_submitted_attempts(db: Session) -> None:
    exam, c1, c2, r1, r2 = _setup_exam_with_candidates(db)
    submit_answers(db, r1.attempt_id, r1.questions, ["A", "A"])
    submit_answers(db, r2.attempt_id, r2.questions, ["B", "A"])

    report = report_service.get_score_report(db)

    assert len(report) == 2
    # 按分数降序
    assert report[0].candidate_name == "张三"
    assert report[0].score == 10
    assert report[1].candidate_name == "李四"
    assert report[1].score == 5


def test_score_report_excludes_in_progress(db: Session) -> None:
    exam, c1, c2, r1, r2 = _setup_exam_with_candidates(db)
    submit_answers(db, r1.attempt_id, r1.questions, ["A", "A"])

    report = report_service.get_score_report(db)
    assert len(report) == 1


def test_score_report_uses_latest_submitted_attempt(db: Session) -> None:
    exam, c1, _c2, r1, _r2 = _setup_exam_with_candidates(db)
    submit_answers(db, r1.attempt_id, r1.questions, ["A", "A"])
    exam_service.create_retake_grant(db, exam.id, c1.id)
    retake = exam_service.start_exam(db, exam.id, c1.id)
    submit_answers(db, retake.attempt_id, retake.questions, ["B", "B"])

    report = report_service.get_score_report(db)
    row = next(item for item in report if item.candidate_name == "张三")

    assert row.score == 0


# --- 题目正确率 ---


def test_question_accuracy_calculates_rate(db: Session) -> None:
    exam, c1, c2, r1, r2 = _setup_exam_with_candidates(db)
    # 两人都答对第1题，都答错第2题
    submit_answers(db, r1.attempt_id, r1.questions, ["A", "B"])
    submit_answers(db, r2.attempt_id, r2.questions, ["A", "B"])

    report = report_service.get_question_accuracy(db)

    assert len(report) == 2
    # 按正确率升序
    assert report[0].accuracy_rate == 0.0  # 题目B
    assert report[0].total_count == 2
    assert report[0].correct_count == 0
    assert report[1].accuracy_rate == 1.0  # 题目A
    assert report[1].correct_count == 2


# --- 错题统计 ---


def test_wrong_questions_counts_failures(db: Session) -> None:
    exam, c1, c2, r1, r2 = _setup_exam_with_candidates(db)
    submit_answers(db, r1.attempt_id, r1.questions, ["A", "B"])
    submit_answers(db, r2.attempt_id, r2.questions, ["A", "B"])

    report = report_service.get_wrong_questions(db)

    assert len(report) == 1
    assert report[0].stem == "题目B"
    assert report[0].wrong_count == 2


# --- 缺考人员 ---


def test_absent_candidates_finds_non_attempters(db: Session) -> None:
    exam, c1, c2, r1, r2 = _setup_exam_with_candidates(db)
    submit_answers(db, r1.attempt_id, r1.questions, ["A", "A"])
    # c2 没有 submit，即使有 in_progress attempt 也仍算未提交

    c3 = create_candidate(db, name="王五", employee_no="E003")
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=c3.id))
    db.commit()

    report = report_service.get_absent_candidates(db, exam_id=exam.id)

    names = [r.name for r in report]
    assert "王五" in names
    assert "张三" not in names
    assert "李四" in names


def test_absent_candidates_excludes_non_should_attend(db: Session) -> None:
    create_candidate(db, name="不需要参加", employee_no="E010", should_attend=False)

    report = report_service.get_absent_candidates(db)
    names = [r.name for r in report]
    assert "不需要参加" not in names
