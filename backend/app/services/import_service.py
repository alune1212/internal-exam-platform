from dataclasses import dataclass
from typing import Any

from openpyxl import load_workbook

from app.schemas.question import ImportFailure, QuestionImportResult


OPTION_LABELS = ("A", "B", "C", "D", "E", "F")


@dataclass(frozen=True)
class ParsedWorkbook:
    rows: list[dict[str, Any]]
    total_count: int


def parse_workbook(file_obj: Any) -> ParsedWorkbook:
    workbook = load_workbook(file_obj, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        it = sheet.iter_rows(values_only=True)
        headers_row = next(it, None)
        if headers_row is None:
            return ParsedWorkbook(rows=[], total_count=0)

        headers = [str(cell).strip() if cell is not None else "" for cell in headers_row]
        parsed_rows: list[dict[str, Any]] = []
        for row in it:
            parsed_rows.append({headers[i]: v for i, v in enumerate(row) if i < len(headers)})
        return ParsedWorkbook(rows=parsed_rows, total_count=len(parsed_rows))
    finally:
        workbook.close()


def validate_question_import_rows(rows: list[dict[str, Any]]) -> QuestionImportResult:
    failures: list[ImportFailure] = []
    for index, row in enumerate(rows, start=2):
        reason = validate_question_import_row(row)
        if reason:
            failures.append(ImportFailure(row_number=index, reason=reason))
    return QuestionImportResult(
        success_count=len(rows) - len(failures),
        failed_count=len(failures),
        failures=failures,
    )


def validate_question_import_row(row: dict[str, Any]) -> str | None:
    question_type = str(row.get("question_type") or "").strip().lower()
    stem = str(row.get("stem") or "").strip()
    status = str(row.get("status") or "active").strip().lower()
    correct_answer = str(row.get("correct_answer") or "").strip()

    if not question_type:
        return "题型不能为空"
    if question_type not in {"single", "multiple", "judge"}:
        return "题型只能是 single、multiple 或 judge"
    if not stem:
        return "题干不能为空"
    if status not in {"active", "inactive"}:
        return "status 只能是 active 或 inactive"
    if not _is_number(row.get("score")):
        return "分值必须是数字"

    answers = [item.strip().upper() for item in correct_answer.split(",") if item.strip()]
    if question_type == "single" and len(answers) != 1:
        return "单选题只能有一个正确答案"
    if question_type == "multiple" and len(answers) < 2:
        return "多选题至少两个正确答案"
    if question_type == "judge" and correct_answer.lower() not in {"true", "false"}:
        return "判断题答案只能是 true 或 false"

    if question_type in {"single", "multiple"}:
        existing_labels = {
            label
            for label in OPTION_LABELS
            if str(row.get(f"option_{label.lower()}") or "").strip()
        }
        missing = [answer for answer in answers if answer not in existing_labels]
        if missing:
            return "正确答案必须存在于选项中"
    return None


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
