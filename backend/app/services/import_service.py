from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models import Candidate, ImportBatch, Question, QuestionOption
from app.schemas.question import ImportFailure, QuestionImportResult


OPTION_LABELS = ("A", "B", "C", "D", "E", "F")
VALID_QUESTION_TYPES = {"single", "multiple", "judge"}
VALID_STATUSES = {"active", "inactive"}
DEFAULT_STATUS = "active"


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


def import_questions_from_workbook(
    db: Session,
    file_obj: Any,
    file_name: str,
) -> QuestionImportResult:
    parsed = parse_workbook(file_obj)
    failures: list[ImportFailure] = []
    imported_questions: list[Question] = []

    for row_number, row in enumerate(parsed.rows, start=2):
        reason = validate_question_import_row(row)
        if reason:
            failures.append(ImportFailure(row_number=row_number, reason=reason))
            continue
        imported_questions.append(_build_question(row))

    db.add_all(imported_questions)
    db.add(
        ImportBatch(
            import_type="questions",
            file_name=file_name,
            total_count=parsed.total_count,
            success_count=len(imported_questions),
            failed_count=len(failures),
            status="completed",
            error_report=[failure.model_dump() for failure in failures],
        )
    )
    db.commit()

    return QuestionImportResult(
        success_count=len(imported_questions),
        failed_count=len(failures),
        failures=failures,
    )


def import_candidates_from_workbook(
    db: Session,
    file_obj: Any,
    file_name: str,
) -> QuestionImportResult:
    parsed = parse_workbook(file_obj)
    failures: list[ImportFailure] = []
    imported_candidates: list[Candidate] = []
    seen_employee_numbers: set[str] = set()
    seen_names_without_employee_no: set[str] = set()

    for row_number, row in enumerate(parsed.rows, start=2):
        reason = _validate_candidate_import_row(
            db=db,
            row=row,
            seen_employee_numbers=seen_employee_numbers,
            seen_names_without_employee_no=seen_names_without_employee_no,
        )
        if reason:
            failures.append(ImportFailure(row_number=row_number, reason=reason))
            continue

        candidate = _build_candidate(row)
        imported_candidates.append(candidate)
        if candidate.employee_no:
            seen_employee_numbers.add(candidate.employee_no)
        else:
            seen_names_without_employee_no.add(candidate.name)

    db.add_all(imported_candidates)
    db.add(
        ImportBatch(
            import_type="candidates",
            file_name=file_name,
            total_count=parsed.total_count,
            success_count=len(imported_candidates),
            failed_count=len(failures),
            status="completed",
            error_report=[failure.model_dump() for failure in failures],
        )
    )
    db.commit()

    return QuestionImportResult(
        success_count=len(imported_candidates),
        failed_count=len(failures),
        failures=failures,
    )


def validate_question_import_row(row: dict[str, Any]) -> str | None:
    question_type = _text(row.get("question_type")).lower()
    stem = _text(row.get("stem"))
    status = _text(row.get("status") or DEFAULT_STATUS).lower()
    correct_answer = _text(row.get("correct_answer"))

    if not question_type:
        return "题型不能为空"
    if question_type not in VALID_QUESTION_TYPES:
        return "题型只能是 single、multiple 或 judge"
    if not stem:
        return "题干不能为空"
    if status not in VALID_STATUSES:
        return "status 只能是 active 或 inactive"
    if not _is_number(row.get("score")):
        return "分值必须是数字"

    answers = _parse_correct_answers(correct_answer)
    if question_type == "single" and len(answers) != 1:
        return "单选题只能有一个正确答案"
    if question_type == "multiple" and len(answers) < 2:
        return "多选题至少两个正确答案"
    if question_type == "judge" and correct_answer.lower() not in {"true", "false"}:
        return "判断题答案只能是 true 或 false"

    if question_type in {"single", "multiple"}:
        existing_labels = {label for label in OPTION_LABELS if _optional_text(row.get(f"option_{label.lower()}"))}
        missing = [answer for answer in answers if answer not in existing_labels]
        if missing:
            return "正确答案必须存在于选项中"
    return None


def _build_question(row: dict[str, Any]) -> Question:
    correct_answers = _parse_correct_answers(_text(row.get("correct_answer")))
    question = Question(
        question_type=_text(row.get("question_type")).lower(),
        stem=_text(row.get("stem")),
        analysis=_optional_text(row.get("analysis")),
        category_1=_optional_text(row.get("category_1")),
        category_2=_optional_text(row.get("category_2")),
        difficulty=_optional_text(row.get("difficulty")),
        score=Decimal(str(row.get("score"))),
        status=_text(row.get("status") or DEFAULT_STATUS).lower(),
        source=_optional_text(row.get("source")),
        source_no=_optional_text(row.get("source_no")),
        remark=_optional_text(row.get("remark")),
    )
    question.options = [
        QuestionOption(
            label=label,
            content=content,
            is_correct=label in correct_answers,
            sort_order=index,
        )
        for index, (label, content) in enumerate(_extract_options(row), start=1)
    ]
    return question


def _validate_candidate_import_row(
    db: Session,
    row: dict[str, Any],
    seen_employee_numbers: set[str],
    seen_names_without_employee_no: set[str],
) -> str | None:
    name = _optional_text(row.get("name"))
    employee_no = _optional_text(row.get("employee_no"))
    status = _text(row.get("status") or DEFAULT_STATUS).lower()

    if not name:
        return "姓名不能为空"
    if status not in VALID_STATUSES:
        return "status 只能是 active 或 inactive"
    if employee_no:
        if employee_no in seen_employee_numbers:
            return "员工号已存在"
        if db.query(Candidate.id).filter(Candidate.employee_no == employee_no).first():
            return "员工号已存在"
        return None

    if name in seen_names_without_employee_no:
        return "姓名已存在"
    if db.query(Candidate.id).filter(Candidate.employee_no.is_(None), Candidate.name == name).first():
        return "姓名已存在"
    return None


def _build_candidate(row: dict[str, Any]) -> Candidate:
    return Candidate(
        name=_text(row.get("name")),
        employee_no=_optional_text(row.get("employee_no")),
        department=_optional_text(row.get("department")),
        position=_optional_text(row.get("position")),
        phone_suffix=_optional_text(row.get("phone_suffix")),
        email=_optional_text(row.get("email")),
        exam_group=_optional_text(row.get("exam_group")),
        should_attend=_parse_bool(row.get("should_attend"), default=True),
        status=_text(row.get("status") or DEFAULT_STATUS).lower(),
        remark=_optional_text(row.get("remark")),
    )


def _parse_correct_answers(raw: str) -> set[str]:
    return {item.strip().upper() for item in raw.split(",") if item.strip()}


def _extract_options(row: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (label, content)
        for label in OPTION_LABELS
        if (content := _optional_text(row.get(f"option_{label.lower()}"))) is not None
    ]


def _text(value: Any) -> str:
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "是"}:
        return True
    if text in {"false", "no", "n", "0", "否"}:
        return False
    return default


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
