from io import BytesIO

from openpyxl import load_workbook

from app.services.template_service import (
    generate_candidate_template,
    generate_question_template,
)


def test_question_template_has_correct_headers() -> None:
    wb = load_workbook(generate_question_template())
    ws = wb.active
    assert ws.title == "题库导入模板"
    headers = [cell.value for cell in ws[1]]
    assert headers == [
        "category_1",
        "category_2",
        "question_type",
        "stem",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "option_e",
        "option_f",
        "correct_answer",
        "analysis",
        "difficulty",
        "score",
        "status",
        "source",
        "source_no",
        "remark",
    ]


def test_question_template_has_two_example_rows() -> None:
    wb = load_workbook(generate_question_template())
    ws = wb.active
    assert ws.max_row == 3  # 1 header + 2 examples
    # first example: single choice
    assert ws.cell(2, 3).value == "single"  # question_type
    assert ws.cell(2, 11).value == "A"  # correct_answer
    # second example: multiple choice
    assert ws.cell(3, 3).value == "multiple"
    assert ws.cell(3, 11).value == "A,B,C,D"


def test_candidate_template_has_correct_headers() -> None:
    wb = load_workbook(generate_candidate_template())
    ws = wb.active
    assert ws.title == "应考名单导入模板"
    headers = [cell.value for cell in ws[1]]
    assert headers == [
        "name",
        "employee_no",
        "department",
        "position",
        "phone_suffix",
        "email",
        "exam_group",
        "should_attend",
        "status",
        "remark",
    ]


def test_candidate_template_has_one_example_row() -> None:
    wb = load_workbook(generate_candidate_template())
    ws = wb.active
    assert ws.max_row == 2  # 1 header + 1 example
    assert ws.cell(2, 1).value == "张三"
    assert ws.cell(2, 2).value == "E1001"


def test_question_template_returns_bytesio() -> None:
    result = generate_question_template()
    assert isinstance(result, BytesIO)
    assert result.tell() == 0  # read position at start


def test_candidate_template_returns_bytesio() -> None:
    result = generate_candidate_template()
    assert isinstance(result, BytesIO)
    assert result.tell() == 0
