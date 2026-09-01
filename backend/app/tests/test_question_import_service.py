from io import BytesIO
from pathlib import Path
from xml.etree.ElementTree import fromstring
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ImportBatch, Question, QuestionOption
from app.services import import_service
from app.services.import_service import (
    generate_failure_report,
    import_questions_from_workbook,
)
from app.services.question_service import list_questions
from app.tests.conftest import build_workbook

QUESTION_HEADERS = [
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


def test_tracked_question_bank_fixture_has_no_local_ooxml_metadata() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[3] / "安全知识竞赛题库_标准化题库.xlsx"
    )
    raw_archive = fixture_path.read_bytes()
    with ZipFile(fixture_path) as archive:
        infos = archive.infolist()
        assert len(infos) == len({info.filename for info in infos})
        assert archive.comment == b""
        assert all(not info.extra and not info.flag_bits & 0x08 for info in infos)

        metadata_values: list[str] = []
        for info in infos:
            if not info.filename.endswith((".xml", ".rels")):
                continue
            root = fromstring(archive.read(info))  # noqa: S314 - tracked test fixture
            for element in root.iter():
                assert element.tag.rsplit("}", 1)[-1] not in {
                    "absPath",
                    "creator",
                    "lastModifiedBy",
                }
                metadata_values.extend(element.attrib.values())
                if element.text:
                    metadata_values.append(element.text)

        end_of_local_files = 0
        for info in sorted(infos, key=lambda item: item.header_offset):
            assert info.header_offset == end_of_local_files
            assert (
                raw_archive[info.header_offset : info.header_offset + 4]
                == b"PK\x03\x04"
            )
            name_length = int.from_bytes(
                raw_archive[info.header_offset + 26 : info.header_offset + 28],
                "little",
            )
            extra_length = int.from_bytes(
                raw_archive[info.header_offset + 28 : info.header_offset + 30],
                "little",
            )
            end_of_local_files = (
                info.header_offset
                + 30
                + name_length
                + extra_length
                + info.compress_size
            )
        end_record = raw_archive.rfind(b"PK\x05\x06")
        assert end_record >= 0
        assert end_record + 22 == len(raw_archive)
        assert end_of_local_files == int.from_bytes(
            raw_archive[end_record + 16 : end_record + 20], "little"
        )

    normalized_metadata = "\n".join(metadata_values).lower()
    for marker in (
        "/users/",
        "\\users\\",
        "xwechat_files",
        "wxid_",
    ):
        assert marker not in normalized_metadata

    workbook = load_workbook(fixture_path, read_only=True, data_only=True)
    try:
        populated_cells = sum(
            cell.value is not None
            for worksheet in workbook.worksheets
            for row in worksheet.iter_rows()
            for cell in row
        )
        assert populated_cells > 0
    finally:
        workbook.close()


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
    options = db.scalars(
        select(QuestionOption).order_by(
            QuestionOption.question_id, QuestionOption.sort_order
        )
    ).all()
    batch = db.scalars(select(ImportBatch)).one()

    assert result.success_count == 2
    assert result.failed_count == 0
    assert result.batch_id == batch.id
    assert [question.stem for question in questions] == [
        "以下哪项是正确做法？",
        "哪些属于安全要求？",
    ]
    assert questions[0].score == 2
    assert [
        option.label for option in options if option.question_id == questions[0].id
    ] == ["A", "B"]
    assert [
        option.label
        for option in options
        if option.question_id == questions[1].id and option.is_correct
    ] == ["A", "B"]
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
    assert batch.error_report == [
        {"row_number": 3, "reason": "正确答案必须存在于选项中"}
    ]


def test_failure_report_escapes_formula_like_file_name(db: Session) -> None:
    from openpyxl import load_workbook

    db.add(
        ImportBatch(
            import_type="questions",
            file_name='=HYPERLINK("http://example.test")',
            total_count=1,
            success_count=0,
            failed_count=1,
            status="completed",
            error_report=[{"row_number": 2, "reason": "题干不能为空"}],
        )
    )
    db.commit()
    batch = db.scalars(select(ImportBatch)).one()

    workbook = load_workbook(generate_failure_report(db, batch.id), data_only=False)

    assert workbook["导入批次"].cell(3, 2).value.startswith("'=")


def test_import_upload_rejects_files_larger_than_limit() -> None:
    file_obj = BytesIO(b"abcd")

    with pytest.raises(import_service.ImportLimitError, match="不能超过 3 字节"):
        import_service.validate_upload_file_size(file_obj, max_bytes=3)

    assert file_obj.tell() == 0


def test_parse_workbook_rejects_too_many_sheets() -> None:
    workbook = Workbook()
    workbook.active.title = "题库"
    workbook.create_sheet("额外 sheet")
    file_obj = BytesIO()
    workbook.save(file_obj)
    file_obj.seek(0)

    with pytest.raises(import_service.ImportLimitError, match="不能超过 1 个工作表"):
        import_service.parse_workbook(file_obj, max_sheets=1)


def test_parse_workbook_rejects_rows_beyond_limit() -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "question_type": "single",
                "stem": "第一题",
                "option_a": "A",
                "correct_answer": "A",
                "score": 1,
            },
            {
                "question_type": "single",
                "stem": "第二题",
                "option_a": "A",
                "correct_answer": "A",
                "score": 1,
            },
        ],
    )

    with pytest.raises(import_service.ImportLimitError, match="不能超过 1 行"):
        import_service.parse_workbook(workbook, max_rows=1)


def test_parse_workbook_accepts_rows_at_limit() -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "question_type": "single",
                "stem": "第一题",
                "option_a": "A",
                "correct_answer": "A",
                "score": 1,
            }
        ],
    )

    parsed = import_service.parse_workbook(workbook, max_rows=1)

    assert parsed.total_count == 1


def test_parse_workbook_rejects_sparse_wide_dimension_before_iteration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbook = build_workbook(QUESTION_HEADERS, [{"stem": "题目"}])
    rebuilt = BytesIO()
    with ZipFile(workbook) as source, ZipFile(rebuilt, "w", ZIP_DEFLATED) as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                assert b'ref="A1:R2"' in content
                content = content.replace(b'ref="A1:R2"', b'ref="A1:XFD1048576"')
            target.writestr(info.filename, content)
    rebuilt.seek(0)

    from openpyxl.worksheet._read_only import ReadOnlyWorksheet

    monkeypatch.setattr(
        ReadOnlyWorksheet,
        "iter_rows",
        lambda *_args, **_kwargs: pytest.fail(
            "wide worksheet must be rejected before row iteration"
        ),
    )

    with pytest.raises(import_service.ImportLimitError, match="不能超过 32 列"):
        import_service.parse_workbook(rebuilt)


def test_question_import_rejects_missing_dimension_without_batch(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    workbook = build_workbook(QUESTION_HEADERS, [{"stem": "题目"}])
    rebuilt = BytesIO()
    with ZipFile(workbook) as source, ZipFile(rebuilt, "w", ZIP_DEFLATED) as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                dimension_start = content.index(b"<dimension")
                dimension_end = content.index(b"/>", dimension_start) + 2
                content = content[:dimension_start] + content[dimension_end:]
            target.writestr(info.filename, content)
    rebuilt.seek(0)

    from openpyxl.worksheet._read_only import ReadOnlyWorksheet

    monkeypatch.setattr(
        ReadOnlyWorksheet,
        "iter_rows",
        lambda *_args, **_kwargs: pytest.fail(
            "missing worksheet dimension must be rejected before row iteration"
        ),
    )

    with pytest.raises(import_service.ImportFormatError, match="尺寸信息"):
        import_questions_from_workbook(db, rebuilt, file_name="missing-dimension.xlsx")

    assert db.query(ImportBatch).count() == 0


def _central_directory_workbook(
    *, extra_members: list[str] | None = None, include_core: bool = True
) -> BytesIO:
    file_obj = BytesIO()
    with ZipFile(file_obj, "w", ZIP_DEFLATED) as archive:
        if include_core:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("xl/workbook.xml", "<workbook/>")
        for name in extra_members or []:
            archive.writestr(name, "x")
    file_obj.seek(0)
    return file_obj


def test_parse_workbook_rejects_unsafe_xlsx_before_openpyxl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_obj = _central_directory_workbook(extra_members=["../escape"])
    monkeypatch.setattr(import_service, "load_workbook", pytest.fail)

    with pytest.raises(import_service.ImportFormatError, match="不安全"):
        import_service.parse_workbook(file_obj)


def test_parse_workbook_rejects_xlsx_member_limit_before_openpyxl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_obj = _central_directory_workbook(
        extra_members=[f"xl/extra-{index}.xml" for index in range(999)]
    )
    monkeypatch.setattr(import_service, "load_workbook", pytest.fail)

    with pytest.raises(import_service.ImportLimitError, match="不能超过 1000"):
        import_service.parse_workbook(file_obj)


def test_parse_workbook_rejects_high_compression_ratio_before_openpyxl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rebuilt = BytesIO()
    with ZipFile(rebuilt, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr("xl/expanded.xml", "x" * 10_000)
    rebuilt.seek(0)
    monkeypatch.setattr(import_service, "load_workbook", pytest.fail)

    with pytest.raises(import_service.ImportLimitError, match="压缩比"):
        import_service.parse_workbook(rebuilt)


def test_question_import_rejects_missing_xlsx_core_without_batch(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(import_service, "load_workbook", pytest.fail)

    with pytest.raises(import_service.ImportFormatError, match="必要"):
        import_questions_from_workbook(
            db,
            _central_directory_workbook(include_core=False),
            file_name="forged.xlsx",
        )

    assert db.query(ImportBatch).count() == 0


def test_import_questions_rejects_blank_required_cells(db: Session) -> None:
    workbook = build_workbook(
        QUESTION_HEADERS,
        [
            {
                "question_type": "single",
                "stem": None,
                "option_a": "正确选项",
                "option_b": "错误选项",
                "correct_answer": "A",
                "score": 1,
                "status": "active",
            },
        ],
    )

    result = import_questions_from_workbook(db, workbook, file_name="blank.xlsx")

    questions = db.scalars(select(Question)).all()
    batch = db.scalars(select(ImportBatch)).one()

    assert result.success_count == 0
    assert result.failed_count == 1
    assert result.failures[0].reason == "题干不能为空"
    assert questions == []
    assert batch.error_report == [{"row_number": 2, "reason": "题干不能为空"}]


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
    options = db.scalars(
        select(QuestionOption).order_by(
            QuestionOption.question_id, QuestionOption.sort_order
        )
    ).all()

    assert result.success_count == 2
    assert result.failed_count == 0
    assert [
        option.label
        for option in options
        if option.question_id == questions[0].id and option.is_correct
    ] == ["A"]
    assert [
        option.label
        for option in options
        if option.question_id == questions[1].id and option.is_correct
    ] == ["B"]


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
    assert [option.label for option in questions[0].options if option.is_correct] == [
        "B"
    ]
