import pytest
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
    ExamCandidateScope,
    Question,
    QuestionOption,
)
from app.schemas.attempt import AnswerSaveItem, AnswerSaveRequest
from app.schemas.exam import ExamCreate, ExamUpdate
from app.services import exam_service
from app.services.exam_service import (
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    CandidateNotEligibleError,
    CandidateNotFoundError,
    ExamFrozenError,
    ExamNotActiveError,
    ExamNotFoundError,
)
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)


def add_exam_candidate_scope(db: Session, exam_id: int, candidate_id: int) -> None:
    db.add(ExamCandidateScope(exam_id=exam_id, candidate_id=candidate_id))
    db.commit()


def create_balanced_question_pool(db: Session, *, per_type: int = 30) -> None:
    for question_type in ("single", "multiple", "judge"):
        for index in range(per_type):
            create_question_with_options(
                db,
                stem=f"{question_type}-{index}",
                question_type=question_type,
                score=1,
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


def test_list_active_exams_for_candidate_hides_submitted_without_retake(
    db: Session,
) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)
    start = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start.attempt_id, "manual")

    active = exam_service.list_active_exams(db, candidate.id)

    assert active == []


def test_list_active_exams_for_candidate_includes_in_progress_attempt(
    db: Session,
) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)
    start = exam_service.start_exam(db, exam.id, candidate.id)

    active = exam_service.list_active_exams(db, candidate.id)

    assert len(active) == 1
    assert active[0].id == exam.id
    assert active[0].latest_attempt_id == start.attempt_id
    assert active[0].latest_attempt_status == "in_progress"


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


def test_update_exam_freezes_structure_after_publish(db: Session) -> None:
    exam = create_exam(db, status="draft", question_rule={})
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)

    published = exam_service.update_exam(db, exam.id, ExamUpdate(status="active"))
    assert published.status == "active"

    with pytest.raises(ExamFrozenError):
        exam_service.update_exam(db, exam.id, ExamUpdate(duration_minutes=90))

    with pytest.raises(ExamFrozenError):
        exam_service.update_exam(
            db, exam.id, ExamUpdate(question_rule={"question_count": 50})
        )


def test_update_exam_validates_new_rule_when_publishing(db: Session) -> None:
    exam = create_exam(db, status="draft", question_rule={})
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db, stem="唯一题目")

    with pytest.raises(exam_service.InsufficientQuestionsError):
        exam_service.update_exam(
            db,
            exam.id,
            ExamUpdate(
                status="active",
                question_rule={
                    "question_count": 2,
                    "total_score": 100,
                    "type_counts": {"single": 2, "multiple": 0, "judge": 0},
                },
            ),
        )


# --- start_exam 测试 ---


def test_start_exam_creates_attempt_and_snapshots(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
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
    add_exam_candidate_scope(db, exam.id, candidate.id)
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


def test_start_exam_rejects_candidate_outside_exam_scope(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db)

    with pytest.raises(CandidateNotEligibleError):
        exam_service.start_exam(db, exam.id, candidate.id)


def test_start_exam_allows_candidate_inside_exam_scope(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)

    result = exam_service.start_exam(db, exam.id, candidate.id)

    assert result.attempt_id > 0


def test_start_exam_returns_existing_in_progress_attempt(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    first = exam_service.start_exam(db, exam.id, candidate.id)
    second = exam_service.start_exam(db, exam.id, candidate.id)

    assert second.attempt_id == first.attempt_id


def test_start_exam_rejects_after_submit_without_retake_grant(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)
    start = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start.attempt_id, "manual")

    with pytest.raises(AttemptAlreadySubmittedError):
        exam_service.start_exam(db, exam.id, candidate.id)


def test_start_exam_consumes_retake_grant_and_creates_retake_attempt(
    db: Session,
) -> None:
    exam = create_exam(db, question_rule={"question_count": 5, "total_score": 100})
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_balanced_question_pool(db, per_type=6)
    first = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, first.attempt_id, "manual")

    grant = exam_service.create_retake_grant(db, exam.id, candidate.id)
    second = exam_service.start_exam(db, exam.id, candidate.id)
    attempts = (
        db.query(ExamAttempt)
        .filter_by(exam_id=exam.id, candidate_id=candidate.id)
        .order_by(ExamAttempt.attempt_no)
        .all()
    )
    db.refresh(grant)

    assert second.attempt_id != first.attempt_id
    assert [attempt.attempt_kind for attempt in attempts] == ["initial", "retake"]
    assert [attempt.attempt_no for attempt in attempts] == [1, 2]
    assert grant.used_at is not None


def test_retake_uses_new_equivalent_random_paper(db: Session) -> None:
    exam = create_exam(
        db,
        question_rule={
            "question_count": 5,
            "total_score": 100,
            "type_counts": {"single": 3, "multiple": 1, "judge": 1},
        },
    )
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_balanced_question_pool(db, per_type=12)
    first = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, first.attempt_id, "manual")
    exam_service.create_retake_grant(db, exam.id, candidate.id)

    second = exam_service.start_exam(db, exam.id, candidate.id)
    first_ids = {
        row.original_question_id
        for row in db.query(ExamAttemptQuestion).filter_by(attempt_id=first.attempt_id)
    }
    second_snapshots = (
        db.query(ExamAttemptQuestion).filter_by(attempt_id=second.attempt_id).all()
    )
    second_ids = {row.original_question_id for row in second_snapshots}
    type_counts = {
        question_type: sum(
            1 for row in second_snapshots if row.question_type == question_type
        )
        for question_type in ("single", "multiple", "judge")
    }

    assert first_ids != second_ids
    assert len(second_snapshots) == 5
    assert sum(float(row.score) for row in second_snapshots) == 100
    assert type_counts == {"single": 3, "multiple": 1, "judge": 1}


def test_start_exam_total_score_matches_questions(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db, stem="题目1", score=2)
    create_question_with_options(db, stem="题目2", score=5)

    result = exam_service.start_exam(db, exam.id, candidate.id)
    # total_score 通过 get_attempt 验证
    attempt = exam_service.get_attempt(db, result.attempt_id)
    assert attempt.total_score == 7


def test_start_exam_distributes_fixed_paper_scores_evenly(db: Session) -> None:
    """固定试卷按总分和题量均分，不按题库原始分值加权。"""
    exam = create_exam(
        db,
        question_rule={"question_count": 5, "total_score": 100, "pass_score": 60},
    )
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    for index in range(3):
        create_question_with_options(
            db, stem=f"单选题{index + 1}", question_type="single", score=index + 1
        )
    create_question_with_options(db, stem="多选题1", question_type="multiple", score=8)
    create_question_with_options(db, stem="判断题1", question_type="judge", score=13)

    result = exam_service.start_exam(db, exam.id, candidate.id)
    attempt = exam_service.get_attempt(db, result.attempt_id)
    snapshots = (
        db.query(ExamAttemptQuestion).filter_by(attempt_id=result.attempt_id).all()
    )

    assert attempt.total_score == 100
    assert sum(float(s.score) for s in snapshots) == 100
    assert all(float(s.score) == 20 for s in snapshots)


def test_start_exam_rescales_scores_to_integer_points(db: Session) -> None:
    exam = create_exam(
        db,
        question_rule={
            "question_count": 3,
            "total_score": 100,
            "type_counts": {"single": 3, "multiple": 0, "judge": 0},
        },
    )
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    for index in range(3):
        create_question_with_options(db, stem=f"题目{index + 1}", score=1)

    result = exam_service.start_exam(db, exam.id, candidate.id)
    snapshots = (
        db.query(ExamAttemptQuestion).filter_by(attempt_id=result.attempt_id).all()
    )

    assert sum(snapshot.score for snapshot in snapshots) == 100
    assert {snapshot.score for snapshot in snapshots} == {33, 34}


def test_select_questions_by_type_uses_unique_stems() -> None:
    rule = exam_service.FixedPaperRule(
        question_count=3,
        total_score=100,
        type_counts={"single": 3, "multiple": 0, "judge": 0},
    )
    questions = [
        Question(id=1, question_type="single", stem="题目1", score=1),
        Question(id=2, question_type="single", stem="题目1", score=1),
        Question(id=3, question_type="single", stem="题目1 ", score=1),
        Question(id=4, question_type="single", stem="题目2", score=1),
        Question(id=5, question_type="single", stem="题目3", score=1),
    ]

    selected = exam_service._select_questions_by_type(questions, rule)

    assert len(selected) == 3
    assert len({question.stem.strip() for question in selected}) == 3


def test_start_exam_applies_question_rule_sampling_coverage_and_total_score(
    db: Session,
) -> None:
    exam = create_exam(
        db,
        question_rule={"question_count": 50, "total_score": 100, "pass_score": 60},
    )
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    categories = ["交通", "安全", "工伤", "廉政"]
    question_types = ["single", "multiple", "judge"]

    for category in categories:
        for question_type in question_types:
            create_question_with_options(
                db,
                stem=f"{category}-{question_type}-must-cover",
                category_1=category,
                question_type=question_type,
                score=2,
            )
    for index in range(120):
        create_question_with_options(
            db,
            stem=f"补充题-{index}",
            category_1=categories[index % len(categories)],
            question_type=question_types[index % len(question_types)],
            score=2,
        )

    result = exam_service.start_exam(db, exam.id, candidate.id)
    attempt = exam_service.get_attempt(db, result.attempt_id)
    snapshots = (
        db.query(ExamAttemptQuestion).filter_by(attempt_id=result.attempt_id).all()
    )
    original_ids = [snapshot.original_question_id for snapshot in snapshots]
    selected_questions = db.query(Question).filter(Question.id.in_(original_ids)).all()
    selected_combos = {
        (question.category_1, question.question_type) for question in selected_questions
    }

    assert len(result.questions) == 50
    assert attempt.total_score == 100
    assert sum(float(snapshot.score) for snapshot in snapshots) == 100
    assert result.exam.question_rule["pass_score"] == 60
    assert {question.category_1 for question in selected_questions} == set(categories)
    assert {question.question_type for question in selected_questions} == set(
        question_types
    )
    assert selected_combos.issuperset(
        {
            (category, question_type)
            for category in categories
            for question_type in question_types
        }
    )


def test_start_exam_generates_independent_equivalent_papers_for_same_exam(
    db: Session,
) -> None:
    exam = create_exam(
        db,
        question_rule={"question_count": 50, "total_score": 100, "pass_score": 60},
    )
    first_candidate = create_candidate(db, name="甲", employee_no="E001")
    second_candidate = create_candidate(db, name="乙", employee_no="E002")
    add_exam_candidate_scope(db, exam.id, first_candidate.id)
    add_exam_candidate_scope(db, exam.id, second_candidate.id)
    categories = ["交通", "安全", "工伤", "廉政"]
    question_types = ["single", "multiple", "judge"]

    for category in categories:
        for question_type in question_types:
            for index in range(10):
                create_question_with_options(
                    db,
                    stem=f"{category}-{question_type}-{index}",
                    category_1=category,
                    question_type=question_type,
                    score=2,
                )

    first = exam_service.start_exam(db, exam.id, first_candidate.id)
    second = exam_service.start_exam(db, exam.id, second_candidate.id)

    first_ids = [
        row.original_question_id
        for row in db.query(ExamAttemptQuestion)
        .filter_by(attempt_id=first.attempt_id)
        .order_by(ExamAttemptQuestion.sort_order)
        .all()
    ]
    second_ids = [
        row.original_question_id
        for row in db.query(ExamAttemptQuestion)
        .filter_by(attempt_id=second.attempt_id)
        .order_by(ExamAttemptQuestion.sort_order)
        .all()
    ]

    assert first_ids != second_ids
    assert len(first_ids) == 50


def test_start_exam_rejects_question_rule_when_pool_is_too_small(
    db: Session,
) -> None:
    exam = create_exam(db, question_rule={"question_count": 50, "total_score": 100})
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)

    with pytest.raises(exam_service.InsufficientQuestionsError):
        exam_service.start_exam(db, exam.id, candidate.id)


def test_update_exam_rejects_type_count_smaller_than_category_coverage(
    db: Session,
) -> None:
    exam = create_exam(
        db,
        status="draft",
        question_rule={
            "question_count": 2,
            "total_score": 100,
            "type_counts": {"single": 1, "multiple": 1, "judge": 0},
        },
    )
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(
        db, question_type="single", stem="A-单选", category_1="A"
    )
    create_question_with_options(
        db, question_type="single", stem="B-单选", category_1="B"
    )
    create_question_with_options(
        db, question_type="multiple", stem="A-多选", category_1="A"
    )

    with pytest.raises(exam_service.InsufficientQuestionsError) as exc:
        exam_service.update_exam(db, exam.id, ExamUpdate(status="active"))

    assert "single" in str(exc.value)
    assert "需要覆盖 2 个分类组合，当前配置 1 题" in str(exc.value)


def test_start_exam_keeps_legacy_empty_question_rule_behavior(db: Session) -> None:
    exam = create_exam(db, question_rule={})
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db, stem="题目1", score=2)
    create_question_with_options(db, stem="题目2", score=3)

    result = exam_service.start_exam(db, exam.id, candidate.id)
    attempt = exam_service.get_attempt(db, result.attempt_id)

    assert len(result.questions) == 2
    assert attempt.total_score == 5


# --- get_attempt 测试 ---


def test_get_attempt_returns_snapshot_questions(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
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
    add_exam_candidate_scope(db, exam.id, candidate.id)
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
    add_exam_candidate_scope(db, exam.id, candidate.id)
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
    add_exam_candidate_scope(db, exam.id, candidate.id)
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


def test_submit_attempt_includes_pass_status_from_question_rule(db: Session) -> None:
    exam = create_exam(db, question_rule={"pass_score": 6})
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db, stem="题目1", score=5)
    create_question_with_options(db, stem="题目2", score=5)
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

    assert result.score == 5
    assert result.pass_score == 6
    assert result.is_passed is False


def test_submit_attempt_scores_multiple_choice_by_set(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
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
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start_result.attempt_id, "auto")

    result = exam_service.get_attempt_result(db, start_result.attempt_id)
    attempt = exam_service.get_attempt(db, start_result.attempt_id)

    assert result.attempt_id == start_result.attempt_id
    assert attempt.status == "auto_submitted"


def test_submit_attempt_is_idempotent_after_submitted(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)
    start_result = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start_result.attempt_id, "manual")

    again = exam_service.submit_attempt(db, start_result.attempt_id, "manual")

    assert again.attempt_id == start_result.attempt_id
    assert again.score == 0


def test_get_attempt_includes_timer_fields_from_attempt_exam(db: Session) -> None:
    exam = create_exam(db, duration_minutes=45)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)

    start = exam_service.start_exam(db, exam.id, candidate.id)
    exam.status = "archived"
    db.commit()

    attempt = exam_service.get_attempt(db, start.attempt_id)

    assert attempt.duration_minutes == 45
    assert attempt.ends_at == start.ends_at
    assert attempt.server_now >= attempt.started_at


def test_result_hides_answer_snapshots_when_exam_disables_review(db: Session) -> None:
    exam = create_exam(db, show_answer_after_submit=False)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)

    start = exam_service.start_exam(db, exam.id, candidate.id)
    result = exam_service.submit_attempt(db, start.attempt_id, "manual")

    assert result.show_answer_after_submit is False
    assert result.questions[0].correct_answer_snapshot is None
    assert result.questions[0].analysis_snapshot is None


def test_save_answers_rejects_after_submit(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db, stem="题目", score=5)
    start = exam_service.start_exam(db, exam.id, candidate.id)
    exam_service.submit_attempt(db, start.attempt_id, "manual")

    with pytest.raises(AttemptAlreadySubmittedError):
        exam_service.save_answers(
            db,
            start.attempt_id,
            AnswerSaveRequest(
                answers=[
                    AnswerSaveItem(
                        attempt_question_id=start.questions[0].id,
                        selected_answer="A",
                    )
                ]
            ),
        )


def test_submit_attempt_with_no_answers_zeros_score(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db, stem="题目1", score=2)
    create_question_with_options(db, stem="题目2", score=3)
    start = exam_service.start_exam(db, exam.id, candidate.id)

    result = exam_service.submit_attempt(db, start.attempt_id, "manual")

    assert result.score == 0
    assert result.total_score == 5
    assert result.correct_count == 0
    assert result.wrong_count == 2


def test_start_exam_rejects_inactive_candidate(db: Session) -> None:
    exam = create_exam(db)
    candidate = Candidate(
        name="禁用人", employee_no="E999", status="inactive", should_attend=True
    )
    db.add(candidate)
    db.commit()
    create_question_with_options(db)

    with pytest.raises(CandidateNotEligibleError):
        exam_service.start_exam(db, exam.id, candidate.id)
