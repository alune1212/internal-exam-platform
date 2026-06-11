from collections.abc import Iterator
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Candidate, ImportBatch
from app.services.import_service import import_candidates_from_workbook


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_import_candidates_persists_valid_rows_and_import_batch(db: Session) -> None:
    workbook = _build_workbook(
        [
            {
                "name": "张三",
                "employee_no": "E001",
                "department": "研发部",
                "position": "工程师",
                "phone_suffix": "1234",
                "email": "zhangsan@example.com",
                "exam_group": "A组",
                "should_attend": "yes",
                "status": "active",
                "remark": "重点人员",
            },
            {
                "name": "李四",
                "department": "财务部",
                "should_attend": "false",
                "status": "inactive",
            },
        ]
    )

    result = import_candidates_from_workbook(db, workbook, file_name="candidates.xlsx")

    candidates = db.scalars(select(Candidate).order_by(Candidate.id)).all()
    batch = db.scalars(select(ImportBatch)).one()

    assert result.success_count == 2
    assert result.failed_count == 0
    assert [(candidate.name, candidate.employee_no) for candidate in candidates] == [("张三", "E001"), ("李四", None)]
    assert candidates[0].should_attend is True
    assert candidates[1].should_attend is False
    assert candidates[0].department == "研发部"
    assert batch.import_type == "candidates"
    assert batch.file_name == "candidates.xlsx"
    assert batch.total_count == 2
    assert batch.success_count == 2
    assert batch.failed_count == 0
    assert batch.error_report == []


def test_import_candidates_skips_missing_name_and_duplicate_identity(db: Session) -> None:
    existing = Candidate(name="王五", employee_no="E100", should_attend=True, status="active")
    db.add(existing)
    db.commit()

    workbook = _build_workbook(
        [
            {"name": "赵六", "employee_no": "E100", "should_attend": True, "status": "active"},
            {"name": "", "employee_no": "E200", "should_attend": True, "status": "active"},
            {"name": "无号人员", "should_attend": True, "status": "active"},
            {"name": "无号人员", "should_attend": True, "status": "active"},
        ]
    )

    result = import_candidates_from_workbook(db, workbook, file_name="mixed.xlsx")

    candidates = db.scalars(select(Candidate).order_by(Candidate.id)).all()
    batch = db.scalars(select(ImportBatch)).one()

    assert result.success_count == 1
    assert result.failed_count == 3
    assert [failure.row_number for failure in result.failures] == [2, 3, 5]
    assert [failure.reason for failure in result.failures] == ["员工号已存在", "姓名不能为空", "姓名已存在"]
    assert [(candidate.name, candidate.employee_no) for candidate in candidates] == [
        ("王五", "E100"),
        ("无号人员", None),
    ]
    assert batch.error_report == [
        {"row_number": 2, "reason": "员工号已存在"},
        {"row_number": 3, "reason": "姓名不能为空"},
        {"row_number": 5, "reason": "姓名已存在"},
    ]


def _build_workbook(rows: list[dict[str, object]]) -> BytesIO:
    headers = [
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
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    file_obj = BytesIO()
    workbook.save(file_obj)
    file_obj.seek(0)
    return file_obj
