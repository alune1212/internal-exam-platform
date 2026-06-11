from collections.abc import Iterator
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


def build_workbook(headers: list[str], rows: list[dict[str, object]]) -> BytesIO:
    """构建用于导入测试的 Excel 工作簿。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    file_obj = BytesIO()
    workbook.save(file_obj)
    file_obj.seek(0)
    return file_obj
