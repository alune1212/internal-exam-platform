from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainError
from app.models import Candidate, ImportBatch, Question, QuestionOption
from app.schemas.question import ImportFailure, QuestionImportResult
from app.services.excel_security import escape_excel_cell
from app.services.operational_lock_service import assert_admin_mutation_allowed
from app.services.scoring_service import normalize_answer_set

OPTION_LABELS = ("A", "B", "C", "D", "E", "F")
VALID_QUESTION_TYPES = {"single", "multiple", "judge"}
VALID_STATUSES = {"active", "inactive"}
DEFAULT_STATUS = "active"
EMAIL_ADAPTER = TypeAdapter(EmailStr)
JUDGE_OPTIONS = [("A", "正确"), ("B", "错误")]
JUDGE_ANSWER_MAP = {"true": "A", "false": "B"}
IMPORT_TYPE_LABELS = {
    "questions": "QUESTION IMPORT · 题库导入",
    "candidates": "ROSTER IMPORT · 应考名单导入",
    "exam_candidates": "ROSTER IMPORT · 应考名单导入",
}


class ImportBatchNotFoundError(DomainError):
    status_code = 404

    def __init__(self, batch_id: int) -> None:
        super().__init__(f"导入批次 #{batch_id} 不存在")


class ImportLimitError(DomainError):
    status_code = 413


@dataclass(frozen=True)
class ParsedWorkbook:
    rows: list[dict[str, Any]]
    total_count: int


def validate_upload_file_size(file_obj: Any, *, max_bytes: int | None = None) -> None:
    limit = max_bytes or settings.import_max_upload_bytes
    try:
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
    except (AttributeError, OSError):
        return

    if size > limit:
        raise ImportLimitError(f"导入文件大小不能超过 {limit} 字节")


def parse_workbook(
    file_obj: Any, *, max_rows: int | None = None, max_sheets: int | None = None
) -> ParsedWorkbook:
    row_limit = max_rows or settings.import_max_rows
    sheet_limit = max_sheets or settings.import_max_sheets
    with suppress(AttributeError, OSError):
        file_obj.seek(0)
    workbook = load_workbook(file_obj, read_only=True, data_only=True)
    try:
        if len(workbook.worksheets) > sheet_limit:
            raise ImportLimitError(f"导入文件不能超过 {sheet_limit} 个工作表")

        sheet = workbook.active
        it = sheet.iter_rows(values_only=True)
        headers_row = next(it, None)
        if headers_row is None:
            return ParsedWorkbook(rows=[], total_count=0)

        headers = [
            str(cell).strip() if cell is not None else "" for cell in headers_row
        ]
        parsed_rows = []
        for row_number, row in enumerate(it, start=1):
            if row_number > row_limit:
                raise ImportLimitError(f"导入数据行数不能超过 {row_limit} 行")
            parsed_rows.append(
                {headers[i]: v for i, v in enumerate(row) if i < len(headers)}
            )
        return ParsedWorkbook(rows=parsed_rows, total_count=len(parsed_rows))
    finally:
        workbook.close()


def import_questions_from_workbook(
    db: Session,
    file_obj: Any,
    file_name: str,
    *,
    commit: bool = True,
) -> QuestionImportResult:
    assert_admin_mutation_allowed(db)
    validate_upload_file_size(file_obj)
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
    batch = ImportBatch(
        import_type="questions",
        file_name=file_name,
        total_count=parsed.total_count,
        success_count=len(imported_questions),
        failed_count=len(failures),
        status="completed",
        error_report=[failure.model_dump() for failure in failures],
    )
    db.add(batch)
    db.flush()
    if commit:
        db.commit()

    return QuestionImportResult(
        batch_id=batch.id,
        success_count=len(imported_questions),
        failed_count=len(failures),
        failures=failures,
    )


def import_candidates_from_workbook(
    db: Session,
    file_obj: Any,
    file_name: str,
    *,
    commit: bool = True,
) -> QuestionImportResult:
    assert_admin_mutation_allowed(db)
    validate_upload_file_size(file_obj)
    parsed = parse_workbook(file_obj)
    failures: list[ImportFailure] = []
    imported_candidates: list[Candidate] = []

    # 预加载已有数据，避免逐行查询 DB
    existing_employee_numbers: set[str] = {
        row[0]
        for row in db.query(Candidate.employee_no)
        .filter(Candidate.employee_no.isnot(None))
        .all()
    }
    existing_names_without_no: set[str] = {
        row[0]
        for row in db.query(Candidate.name)
        .filter(Candidate.employee_no.is_(None))
        .all()
    }

    for row_number, row in enumerate(parsed.rows, start=2):
        reason = _validate_candidate_import_row(
            row=row,
            existing_employee_numbers=existing_employee_numbers,
            existing_names_without_no=existing_names_without_no,
        )
        if reason:
            failures.append(ImportFailure(row_number=row_number, reason=reason))
            continue

        candidate = _build_candidate(row)
        imported_candidates.append(candidate)
        if candidate.employee_no:
            existing_employee_numbers.add(candidate.employee_no)
        else:
            existing_names_without_no.add(candidate.name)

    db.add_all(imported_candidates)
    batch = ImportBatch(
        import_type="candidates",
        file_name=file_name,
        total_count=parsed.total_count,
        success_count=len(imported_candidates),
        failed_count=len(failures),
        status="completed",
        error_report=[failure.model_dump() for failure in failures],
    )
    db.add(batch)
    db.flush()
    if commit:
        db.commit()

    return QuestionImportResult(
        batch_id=batch.id,
        success_count=len(imported_candidates),
        failed_count=len(failures),
        failures=failures,
    )


def generate_failure_report(db: Session, batch_id: int) -> BytesIO:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise ImportBatchNotFoundError(batch_id)

    workbook = Workbook()
    meta_sheet = workbook.active
    meta_sheet.title = "导入批次"
    meta_sheet.append(["字段", "值"])
    meta_sheet.append(
        ["导入类型", IMPORT_TYPE_LABELS.get(batch.import_type, batch.import_type)]
    )
    meta_sheet.append(["文件名", escape_excel_cell(batch.file_name)])
    meta_sheet.append(["总数", batch.total_count])
    meta_sheet.append(["成功数", batch.success_count])
    meta_sheet.append(["失败数", batch.failed_count])
    meta_sheet.append(["生成时间", datetime.now(UTC).isoformat()])

    detail_sheet = workbook.create_sheet("失败明细")
    detail_sheet.append(["ROW · 行号", "REASON · 原因"])
    for failure in batch.error_report or []:
        detail_sheet.append(
            [
                escape_excel_cell(failure.get("row_number")),
                escape_excel_cell(failure.get("reason")),
            ]
        )

    for sheet in workbook.worksheets:
        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(
                max(max_length + 2, 10), 48
            )

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def validate_question_import_row(row: dict[str, Any]) -> str | None:
    question_type = _text(row.get("question_type")).lower()
    stem = _text(row.get("stem"))
    status = _text(row.get("status") or DEFAULT_STATUS).lower()
    correct_answer = _text(row.get("correct_answer"))

    if not question_type:
        return "题型不能为空"
    if question_type not in VALID_QUESTION_TYPES:
        return "题型只能填写单选（single）、多选（multiple）或判断（judge）"
    if not stem:
        return "题干不能为空"
    if status not in VALID_STATUSES:
        return "状态只能填写启用（active）或停用（inactive）"
    if not _is_number(row.get("score")):
        return "分值必须是数字"

    answers = _parse_correct_option_labels(question_type, correct_answer)
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
            if _optional_text(row.get(f"option_{label.lower()}"))
        }
        missing = [answer for answer in answers if answer not in existing_labels]
        if missing:
            return "正确答案必须存在于选项中"
    return None


def _build_question(row: dict[str, Any]) -> Question:
    question_type = _text(row.get("question_type")).lower()
    correct_answers = _parse_correct_option_labels(
        question_type, _text(row.get("correct_answer"))
    )
    question = Question(
        question_type=question_type,
        stem=_text(row.get("stem")),
        analysis=_optional_text(row.get("analysis")),
        category_1=_optional_text(row.get("category_1")),
        category_2=_optional_text(row.get("category_2")),
        difficulty=_optional_text(row.get("difficulty")),
        score=Decimal(_text(row.get("score"))),
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
        for index, (label, content) in enumerate(
            _extract_options(row, question_type), start=1
        )
    ]
    return question


def _validate_candidate_import_row(
    row: dict[str, Any],
    existing_employee_numbers: set[str],
    existing_names_without_no: set[str],
) -> str | None:
    name = _optional_text(row.get("name"))
    employee_no = _optional_text(row.get("employee_no"))
    status = _text(row.get("status") or DEFAULT_STATUS).lower()
    email_error = validate_candidate_email(row)

    if not name:
        return "姓名不能为空"
    if email_error:
        return email_error
    if status not in VALID_STATUSES:
        return "状态只能填写启用（active）或停用（inactive）"
    if employee_no:
        if employee_no in existing_employee_numbers:
            return "员工号已存在"
        return None

    if name in existing_names_without_no:
        return "姓名已存在"
    return None


def _build_candidate(row: dict[str, Any]) -> Candidate:
    return Candidate(
        name=_text(row.get("name")),
        employee_no=_optional_text(row.get("employee_no")),
        department=_optional_text(row.get("department")),
        position=_optional_text(row.get("position")),
        phone_suffix=_optional_text(row.get("phone_suffix")),
        email=normalize_candidate_email(row.get("email")),
        exam_group=_optional_text(row.get("exam_group")),
        should_attend=_parse_bool(row.get("should_attend"), default=True),
        status=_text(row.get("status") or DEFAULT_STATUS).lower(),
        remark=_optional_text(row.get("remark")),
    )


def validate_candidate_email(row: dict[str, Any]) -> str | None:
    raw_email = _optional_text(row.get("email"))
    if raw_email is None:
        return "邮箱不能为空"
    if normalize_candidate_email(raw_email) is None:
        return "邮箱格式不正确"
    return None


def normalize_candidate_email(raw_email: object) -> str | None:
    email = _optional_text(raw_email)
    if email is None:
        return None
    try:
        return str(EMAIL_ADAPTER.validate_python(email)).lower()
    except ValidationError:
        return None


def _parse_correct_option_labels(question_type: str, raw: str) -> set[str]:
    if question_type == "judge":
        label = JUDGE_ANSWER_MAP.get(raw.strip().lower())
        if label is not None:
            return {label}
    return normalize_answer_set(raw)


def _extract_options(row: dict[str, Any], question_type: str) -> list[tuple[str, str]]:
    options = [
        (label, content)
        for label in OPTION_LABELS
        if (content := _optional_text(row.get(f"option_{label.lower()}"))) is not None
    ]
    if question_type == "judge" and not options:
        return list(JUDGE_OPTIONS)
    return options


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
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
