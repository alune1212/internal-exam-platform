import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Candidate, Exam, ExamCandidateScope, ImportBatch
from app.services.import_service import import_exam_roster_from_workbook
from app.tests.conftest import build_workbook

ROSTER_HEADERS = [
    "email",
    "candidate_name",
    "department",
    "position",
    "exam_group",
    "remark",
]


def _draft_exam(db: Session) -> Exam:
    exam = Exam(title="安全考试", duration_minutes=60, status="draft")
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def test_roster_import_creates_pending_account_and_scope(db: Session) -> None:
    exam = _draft_exam(db)
    workbook = build_workbook(
        ROSTER_HEADERS,
        [
            {
                "email": "  USER@Example.COM ",
                "candidate_name": "张三",
                "department": "研发部",
                "position": "工程师",
                "exam_group": "A组",
                "remark": "重点",
            }
        ],
    )

    result = import_exam_roster_from_workbook(
        db, exam.id, workbook, file_name="roster.xlsx"
    )

    candidate = db.scalars(select(Candidate)).one()
    scope = db.scalars(select(ExamCandidateScope)).one()
    batch = db.scalars(select(ImportBatch)).one()
    assert result.success_count == 1
    assert result.failed_count == 0
    assert candidate.email == "user@example.com"
    assert candidate.status == "pending"
    assert candidate.name is None
    assert scope.roster_email == "user@example.com"
    assert scope.roster_name == "张三"
    assert scope.department == "研发部"
    assert scope.roster_remark == "重点"
    assert batch.import_type == "exam_candidates"


def test_roster_import_normalizes_header_case_and_whitespace(db: Session) -> None:
    exam = _draft_exam(db)
    workbook = build_workbook(
        [" Email ", " CANDIDATE_NAME ", " Department "],
        [
            {
                " Email ": "MIXED@example.com",
                " CANDIDATE_NAME ": "名单",
                " Department ": "研发",
            }
        ],
    )

    result = import_exam_roster_from_workbook(
        db, exam.id, workbook, file_name="normalized-headers.xlsx"
    )

    assert result.success_count == 1
    scope = db.query(ExamCandidateScope).one()
    assert scope.roster_email == "mixed@example.com"
    assert scope.roster_name == "名单"
    assert scope.department == "研发"


def test_roster_import_reuses_account_and_rejects_inactive_or_duplicate(
    db: Session,
) -> None:
    exam = _draft_exam(db)
    active = Candidate(name="已注册", email="active@example.com", status="active")
    inactive = Candidate(name="停用", email="inactive@example.com", status="inactive")
    db.add_all([active, inactive])
    db.commit()
    workbook = build_workbook(
        ROSTER_HEADERS,
        [
            {"email": " ACTIVE@example.com ", "candidate_name": "名单名"},
            {"email": "inactive@example.com", "candidate_name": "停用"},
            {"email": "active@example.com", "candidate_name": "重复"},
            {"email": "bad", "candidate_name": "坏邮箱"},
        ],
    )

    result = import_exam_roster_from_workbook(
        db, exam.id, workbook, file_name="mixed.xlsx"
    )

    assert result.success_count == 1
    assert result.failed_count == 3
    assert [failure.reason for failure in result.failures] == [
        "账号已停用，请先恢复账号",
        "邮箱在本批次重复",
        "邮箱格式不正确",
    ]
    scope = db.scalars(select(ExamCandidateScope)).one()
    assert scope.candidate_id == active.id
    assert db.query(Candidate).count() == 2


def test_roster_import_rejects_deprecated_headers_before_write(db: Session) -> None:
    exam = _draft_exam(db)
    workbook = build_workbook(
        ["email", "candidate_name", "legacy_field"],
        [{"email": "u@example.com", "candidate_name": "用户", "legacy_field": "x"}],
    )
    with pytest.raises(Exception, match="不支持"):
        import_exam_roster_from_workbook(db, exam.id, workbook, file_name="legacy.xlsx")
    assert db.query(Candidate).count() == 0
    assert db.query(ExamCandidateScope).count() == 0
    assert db.query(ImportBatch).count() == 0


def test_roster_import_reports_bounds_and_control_characters_per_row(
    db: Session,
) -> None:
    exam = _draft_exam(db)
    workbook = build_workbook(
        ROSTER_HEADERS,
        [
            {
                "email": "too-long@example.com",
                "candidate_name": "n" * 101,
            },
            {
                "email": "control@example.com",
                "candidate_name": "张\n三",
            },
            {
                "email": "ok@example.com",
                "candidate_name": "正常",
                "remark": "r" * 2001,
            },
        ],
    )

    result = import_exam_roster_from_workbook(
        db, exam.id, workbook, file_name="bounds.xlsx"
    )

    assert result.success_count == 0
    assert result.failed_count == 3
    assert [failure.row_number for failure in result.failures] == [2, 3, 4]
    assert db.query(Candidate).count() == 0
    assert db.query(ExamCandidateScope).count() == 0


def test_roster_scope_integrity_error_is_a_row_failure_not_batch_rollback(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    exam = _draft_exam(db)
    workbook = build_workbook(
        ROSTER_HEADERS,
        [{"email": "race@example.com", "candidate_name": "竞争"}],
    )
    original_flush = db.flush
    injected = False

    def flush_with_injected_scope_conflict(*args, **kwargs):
        nonlocal injected
        if not injected and any(
            isinstance(item, ExamCandidateScope) for item in db.new
        ):
            injected = True
            raise IntegrityError("duplicate scope", {}, RuntimeError("duplicate"))
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", flush_with_injected_scope_conflict)
    result = import_exam_roster_from_workbook(
        db, exam.id, workbook, file_name="race.xlsx"
    )

    assert result.success_count == 0
    assert result.failed_count == 1
    assert result.failures[0].reason == "邮箱已在考试名单中"
    assert db.query(ImportBatch).one().failed_count == 1
