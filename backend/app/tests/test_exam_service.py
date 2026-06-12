import pytest
from sqlalchemy.orm import Session

from app.models import ExamAttemptAnswer, Question, QuestionOption
from app.schemas.attempt import AnswerSaveItem, AnswerSaveRequest
from app.schemas.exam import ExamCreate, ExamUpdate
from app.services import exam_service
from app.services.exam_service import (
    AttemptAlreadyExistsError,
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    CandidateNotFoundError,
    ExamNotActiveError,
    ExamNotFoundError,
)
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)

# --- CRUD 测试 ---


def test_create_exam_persists(db: Session) -> None:
    payload = ExamCreate(title="安全考试", duration_minutes=60)
    result = exam_service.create_exam(db, payload)
    assert result.id > 0
    assert result.title == "安全考试"
    assert result.status == "draft"


def test_list_active_exams_filters(db: Session) -> None:
    exam_service.create_exam(
        db, ExamCreate(title="草稿", duration_minutes=60, status="draft")
    )
    exam_service.create_exam(
        db, ExamCreate(title="上线", duration_minutes=60, status="active")
    )
    active = exam_service.list_active_exams(db)
    assert len(active) == 1
    assert active[0].title == "上线"


def test_update_exam_partial(db: Session) -> None:
    exam = exam_service.create_exam(
        db, ExamCreate(title="原始标题", duration_minutes=60)
    )
    updated = exam_service.update_exam(db, exam.id, ExamUpdate(title="新标题"))
    assert updated.title == "新标题"
    assert updated.duration_minutes == 60


def test_update_exam_not_found(db: Session) -> None:
    with pytest.raises(ExamNotFoundError):
        exam_service.update_exam(db, 999, ExamUpdate(title="x"))


# --- start_exam 测试 ---


def test_start_exam_creates_attempt_and_snapshots(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db, stem="题目1", score=2)
    create_question_with_options(db, stem="题目2", score=3)

    result = exam_service.start_exam(db, exam.id, candidate.id)

    assert result.attempt_id > 0
    assert result.exam.id == exam.id
    assert len(result.questions) == 2
    assert result.questions[0].stem_snapshot == "题目1"
    assert result.questions[1].stem_snapshot == "题目2"
    assert result.started_at < result.ends_at


def test_start_exam_snapshot_preserves_options(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db)

    result = exam_service.start_exam(db, exam.id, candidate.id)
    q = result.questions[0]

    assert q.question_type == "single"
    assert len(q.options_snapshot) == 2
    assert q.options_snapshot[0]["label"] == "A"
    assert q.options_snapshot[0]["content"] == "选项A"
    assert q.score == 2


def test_start_exam_exam_not_found(db: Session) -> None:
    candidate = create_candidate(db)
    with pytest.raises(ExamNotFoundError):
        exam_service.start_exam(db, 999, candidate.id)


def test_start_exam_exam_not_active(db: Session) -> None:
    exam = create_exam(db, status="draft")
    candidate = create_candidate(db)
    with pytest.raises(ExamNotActiveError):
        exam_service.start_exam(db, exam.id, candidate.id)


def test_start_exam_candidate_not_found(db: Session) -> None:
    exam = create_exam(db)
    with pytest.raises(CandidateNotFoundError):
        exam_service.start_exam(db, exam.id, 999)


def test_start_exam_prevents_duplicate_attempt(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    exam_service.start_exam(db, exam.id, candidate.id)
    with pytest.raises(AttemptAlreadyExistsError):
        exam_service.start_exam(db, exam.id, candidate.id)


def test_start_exam_total_score_matches_questions(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db, score=2)
    create_question_with_options(db, score=5)

    result = exam_service.start_exam(db, exam.id, candidate.id)
    # total_score 通过 get_attempt 验证
    attempt = exam_service.get_attempt(db, result.attempt_id)
    assert attempt.total_score == 7


# --- get_attempt 测试 ---


def test_get_attempt_returns_snapshot_questions(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db, stem="快照题")
    start_result = exam_service.start_exam(db, exam.id, candidate.id)

    attempt = exam_service.get_attempt(db, start_result.attempt_id)

    assert attempt.id == start_result.attempt_id
    assert attempt.exam_id == exam.id
    assert attempt.status == "in_progress"
    assert len(attempt.questions) == 1
    assert attempt.questions[0].stem_snapshot == "快照题"


def test_get_attempt_not_found(db: Session) -> None:
    with pytest.raises(AttemptNotFoundError):
        exam_service.get_attempt(db, 999)


# --- answer save / submit 测试 ---


def test_save_answers_persists_selected_answer(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    attempt_question_id = start_result.questions[0].id

    result = exam_service.save_answers(
        db,
        start_result.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=attempt_question_id, selected_answer="A"
                )
            ]
        ),
    )

    attempt = exam_service.get_attempt(db, start_result.attempt_id)

    assert result.saved_count == 1
    assert attempt.questions[0].selected_answer == "A"


def test_save_answers_updates_existing_answer(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    attempt_question_id = start_result.questions[0].id

    exam_service.save_answers(
        db,
        start_result.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=attempt_question_id, selected_answer="B"
                )
            ]
        ),
    )
    exam_service.save_answers(
        db,
        start_result.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=attempt_question_id, selected_answer="A"
                )
            ]
        ),
    )

    answers = db.query(ExamAttemptAnswer).all()
    attempt = exam_service.get_attempt(db, start_result.attempt_id)

    assert len(answers) == 1
    assert attempt.questions[0].selected_answer == "A"


def test_submit_attempt_scores_from_snapshots(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db, stem="单选题", score=2)
    create_question_with_options(db, stem="错题", score=3)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)

    exam_service.save_answers(
        db,
        start_result.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=start_result.questions[0].id,
                    selected_answer="A",
                ),
                AnswerSaveItem(
                    attempt_question_id=start_result.questions[1].id,
                    selected_answer="B",
                ),
            ]
        ),
    )

    result = exam_service.submit_attempt(db, start_result.attempt_id, "manual")
    attempt = exam_service.get_attempt(db, start_result.attempt_id)

    assert result.score == 2
    assert result.total_score == 5
    assert result.correct_count == 1
    assert result.wrong_count == 1
    assert result.questions[0].is_correct is True
    assert result.questions[0].score_awarded == 2
    assert result.questions[1].is_correct is False
    assert result.questions[1].score_awarded == 0
    assert attempt.status == "submitted"
    assert attempt.submitted_at is not None


def test_submit_attempt_scores_multiple_choice_by_set(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    question = Question(
        question_type="multiple", stem="多选题", score=4, status="active"
    )
    db.add(question)
    db.flush()
    db.add_all(
        [
            QuestionOption(
                question_id=question.id,
                label="A",
                content="选项A",
                is_correct=True,
                sort_order=0,
            ),
            QuestionOption(
                question_id=question.id,
                label="B",
                content="选项B",
                is_correct=False,
                sort_order=1,
            ),
            QuestionOption(
                question_id=question.id,
                label="C",
                content="选项C",
                is_correct=True,
                sort_order=2,
            ),
        ]
    )
    db.commit()
    start_result = exam_service.start_exam(db, exam.id, candidate.id)

    exam_service.save_answers(
        db,
        start_result.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=start_result.questions[0].id,
                    selected_answer="C,A",
                )
            ]
        ),
    )
    result = exam_service.submit_attempt(db, start_result.attempt_id, "manual")

    assert result.score == 4
    assert result.correct_count == 1
    assert result.wrong_count == 0


def test_get_attempt_result_reads_submitted_result_without_mutating_submit_type(
    db: Session,
) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start_result.attempt_id, "auto")

    result = exam_service.get_attempt_result(db, start_result.attempt_id)
    attempt = exam_service.get_attempt(db, start_result.attempt_id)

    assert result.attempt_id == start_result.attempt_id
    assert attempt.status == "auto_submitted"


# --- ranking 测试 ---


def test_get_ranking_orders_by_score_desc(db: Session) -> None:
    exam = create_exam(db)
    c1 = create_candidate(db, name="甲", employee_no="E001")
    c2 = create_candidate(db, name="乙", employee_no="E002")
    create_question_with_options(db, score=10)

    # 考生1答对
    r1 = exam_service.start_exam(db, exam.id, c1.id)
    exam_service.save_answers(
        db,
        r1.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=r1.questions[0].id, selected_answer="A"
                )
            ]
        ),
    )
    exam_service.submit_attempt(db, r1.attempt_id, "manual")

    # 考生2答错
    r2 = exam_service.start_exam(db, exam.id, c2.id)
    exam_service.save_answers(
        db,
        r2.attempt_id,
        AnswerSaveRequest(
            answers=[
                AnswerSaveItem(
                    attempt_question_id=r2.questions[0].id, selected_answer="B"
                )
            ]
        ),
    )
    exam_service.submit_attempt(db, r2.attempt_id, "manual")

    ranking = exam_service.get_ranking(db, exam.id)

    assert len(ranking) == 2
    assert ranking[0].rank == 1
    assert ranking[0].candidate_name == "甲"
    assert ranking[0].score == 10
    assert ranking[1].rank == 2
    assert ranking[1].candidate_name == "乙"
    assert ranking[1].score == 0


def test_get_ranking_excludes_in_progress(db: Session) -> None:
    exam = create_exam(db)
    c1 = create_candidate(db, name="进行中", employee_no="E001")
    create_question_with_options(db)
    exam_service.start_exam(db, exam.id, c1.id)

    ranking = exam_service.get_ranking(db, exam.id)
    assert len(ranking) == 0


def test_get_ranking_empty_for_no_attempts(db: Session) -> None:
    exam = create_exam(db)
    assert exam_service.get_ranking(db, exam.id) == []


def test_submit_attempt_rejects_already_submitted(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start_result.attempt_id, "manual")

    with pytest.raises(AttemptAlreadySubmittedError):
        exam_service.submit_attempt(db, start_result.attempt_id, "manual")
