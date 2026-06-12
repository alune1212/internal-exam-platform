from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ImportBatch, Question, QuestionOption
from app.services.import_service import import_questions_from_workbook
from app.services.question_service import list_questions
from app.tests.conftest import build_workbook

QUESTION_HEADERS = [
    "category_1", "category_2", "question_type", "stem",
    "option_a", "option_b", "option_c", "option_d", "option_e", "option_f",
    "correct_answer", "analysis", "difficulty", "score", "status", "source", "source_no", "remark",
]


def test_import_questions_persists_valid_rows_and_import_batch(db: Session) -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "category_1": "制度",
                "category_2": "安全",
                "question_type": "single",
                "stem": "以下哪项是正确做法？",
                "option_a": "保管好账号",
                "option_b": "共享密码",
                "correct_answer": "A",
                "analysis": "账号不可共享。",
                "difficulty": "easy",
                "score": 2,
                "status": "active",
                "source": "handbook",
                "source_no": "Q001",
                "remark": "导入测试",
            },
            {
                "question_type": "multiple",
                "stem": "哪些属于安全要求？",
                "option_a": "定期改密",
                "option_b": "开启 MFA",
                "option_c": "外借账号",
                "correct_answer": "B,A",
                "score": 3,
                "status": "active",
            },
        ],
    )

    result = import_questions_from_workbook(db, workbook, file_name="questions.xlsx")

    questions = db.scalars(select(Question).order_by(Question.id)).all()
    options = db.scalars(select(QuestionOption).order_by(QuestionOption.question_id, QuestionOption.sort_order)).all()
    batch = db.scalars(select(ImportBatch)).one()

    assert result.success_count == 2
    assert result.failed_count == 0
    assert [question.stem for question in questions] == ["以下哪项是正确做法？", "哪些属于安全要求？"]
    assert questions[0].score == 2
    assert [option.label for option in options if option.question_id == questions[0].id] == ["A", "B"]
    assert [option.label for option in options if option.question_id == questions[1].id and option.is_correct] == ["A", "B"]
    assert batch.import_type == "questions"
    assert batch.file_name == "questions.xlsx"
    assert batch.total_count == 2
    assert batch.success_count == 2
    assert batch.failed_count == 0
    assert batch.error_report == []


def test_import_questions_skips_invalid_rows_and_records_failures(db: Session) -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "question_type": "single",
                "stem": "合法题目",
                "option_a": "正确选项",
                "option_b": "错误选项",
                "correct_answer": "A",
                "score": 1,
                "status": "active",
            },
            {
                "question_type": "single",
                "stem": "非法题目",
                "option_a": "只有 A",
                "correct_answer": "B",
                "score": 1,
                "status": "active",
            },
        ],
    )

    result = import_questions_from_workbook(db, workbook, file_name="mixed.xlsx")

    questions = db.scalars(select(Question)).all()
    batch = db.scalars(select(ImportBatch)).one()

    assert result.success_count == 1
    assert result.failed_count == 1
    assert result.failures[0].row_number == 3
    assert result.failures[0].reason == "正确答案必须存在于选项中"
    assert [question.stem for question in questions] == ["合法题目"]
    assert batch.total_count == 2
    assert batch.success_count == 1
    assert batch.failed_count == 1
    assert batch.error_report == [{"row_number": 3, "reason": "正确答案必须存在于选项中"}]


def test_import_questions_marks_judge_answer_from_true_false(db: Session) -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "question_type": "judge",
                "stem": "安全生产月是每年六月。",
                "correct_answer": "true",
                "score": 1,
                "status": "active",
            },
            {
                "question_type": "judge",
                "stem": "应急预案制定后永远不用修改。",
                "correct_answer": "false",
                "score": 1,
                "status": "active",
            },
        ],
    )

    result = import_questions_from_workbook(db, workbook, file_name="judge.xlsx")

    questions = db.scalars(select(Question).order_by(Question.id)).all()
    options = db.scalars(select(QuestionOption).order_by(QuestionOption.question_id, QuestionOption.sort_order)).all()

    assert result.success_count == 2
    assert result.failed_count == 0
    assert [option.label for option in options if option.question_id == questions[0].id and option.is_correct] == ["A"]
    assert [option.label for option in options if option.question_id == questions[1].id and option.is_correct] == ["B"]


def test_list_questions_returns_imported_questions_with_options(db: Session) -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "question_type": "single",
                "stem": "列表可见题目",
                "option_a": "A 选项",
                "option_b": "B 选项",
                "correct_answer": "B",
                "score": 1,
                "status": "active",
            }
        ],
    )
    import_questions_from_workbook(db, workbook, file_name="questions.xlsx")

    questions = list_questions(db)

    assert len(questions) == 1
    assert questions[0].stem == "列表可见题目"
    assert [option.label for option in questions[0].options] == ["A", "B"]
    assert [option.label for option in questions[0].options if option.is_correct] == ["B"]
