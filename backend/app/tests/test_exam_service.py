from sqlalchemy.orm import Session

from app.schemas.exam import ExamCreate, ExamUpdate
from app.services.exam_service import create_exam, list_active_exams, list_admin_exams, update_exam


def test_create_exam_persists_configuration(db: Session) -> None:
    exam = create_exam(
        db,
        ExamCreate(
            title="安全考试",
            description="六月安全制度考试",
            duration_minutes=45,
            question_rule={"mode": "all_active"},
            status="active",
            show_answer_after_submit=True,
            show_ranking=False,
        ),
    )

    exams = list_admin_exams(db)

    assert exam.id > 0
    assert exam.title == "安全考试"
    assert exam.question_rule == {"mode": "all_active"}
    assert len(exams) == 1
    assert exams[0].id == exam.id
    assert exams[0].show_ranking is False


def test_list_active_exams_filters_non_active_status(db: Session) -> None:
    create_exam(db, ExamCreate(title="草稿考试", duration_minutes=30, status="draft"))
    active = create_exam(db, ExamCreate(title="正式考试", duration_minutes=60, status="active"))
    create_exam(db, ExamCreate(title="已关闭考试", duration_minutes=45, status="inactive"))

    active_exams = list_active_exams(db)

    assert [(exam.id, exam.title) for exam in active_exams] == [(active.id, "正式考试")]


def test_update_exam_persists_only_provided_fields(db: Session) -> None:
    exam = create_exam(
        db,
        ExamCreate(
            title="原考试",
            description="原说明",
            duration_minutes=30,
            question_rule={"mode": "all_active"},
            status="draft",
            show_answer_after_submit=True,
            show_ranking=True,
        ),
    )

    updated = update_exam(
        db,
        exam.id,
        ExamUpdate(
            title="更新后的考试",
            status="active",
            show_ranking=False,
        ),
    )

    exams = list_admin_exams(db)

    assert updated.title == "更新后的考试"
    assert updated.description == "原说明"
    assert updated.duration_minutes == 30
    assert updated.question_rule == {"mode": "all_active"}
    assert updated.status == "active"
    assert updated.show_answer_after_submit is True
    assert updated.show_ranking is False
    assert exams[0].title == "更新后的考试"
