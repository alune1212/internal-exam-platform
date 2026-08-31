from __future__ import annotations

import posixpath
import re
import stat
import zipfile
from typing import Any
from zipfile import BadZipFile

from app.core.exceptions import DomainError

FORMULA_PREFIXES = ("=", "+", "-", "@")
LEADING_FORMULA_PADDING = "".join(chr(value) for value in range(0x21))

MAX_XLSX_MEMBERS = 1_000
MAX_XLSX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_XLSX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_XLSX_COMPRESSION_RATIO = 100
REQUIRED_XLSX_MEMBERS = frozenset({"[Content_Types].xml", "xl/workbook.xml"})
_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:")


class ExcelSecurityError(DomainError):
    """An XLSX package is malformed or unsafe to expand."""

    status_code = 422


class ExcelSecurityLimitError(ExcelSecurityError):
    """An XLSX package exceeds a bounded resource limit."""

    status_code = 413


def preflight_xlsx(file_obj: Any) -> None:
    """Validate XLSX ZIP metadata without reading any member contents.

    The workbook parser must only see packages whose central directory has
    already passed these bounds.  This keeps ZIP expansion limits independent
    of whichever parser is used by an importer.
    """

    try:
        file_obj.seek(0)
        with zipfile.ZipFile(file_obj) as archive:
            members = archive.infolist()
            if len(members) > MAX_XLSX_MEMBERS:
                raise ExcelSecurityLimitError(
                    f"XLSX 压缩包不能超过 {MAX_XLSX_MEMBERS} 个文件"
                )
            _validate_local_headers(archive, members)
    except (AttributeError, OSError, ValueError, zipfile.BadZipFile) as exc:
        raise ExcelSecurityError("导入文件不是有效的 XLSX 压缩包") from exc

    names: set[str] = set()
    total_size = 0
    for member in members:
        name = member.filename
        if name in names:
            raise ExcelSecurityError("XLSX 压缩包包含重复文件名")
        names.add(name)
        _validate_member_name(name, member)

        compressed_size = member.compress_size
        expanded_size = member.file_size
        if (
            not isinstance(compressed_size, int)
            or not isinstance(expanded_size, int)
            or compressed_size < 0
            or expanded_size < 0
        ):
            raise ExcelSecurityError("XLSX 压缩包文件大小元数据无效")
        if compressed_size == 0 and expanded_size > 0:
            raise ExcelSecurityError("XLSX 压缩包包含无效的零压缩文件")
        if expanded_size > MAX_XLSX_MEMBER_BYTES:
            raise ExcelSecurityLimitError(
                f"XLSX 压缩包单个文件不能超过 {MAX_XLSX_MEMBER_BYTES} 字节"
            )
        total_size += expanded_size
        if total_size > MAX_XLSX_TOTAL_BYTES:
            raise ExcelSecurityLimitError(
                f"XLSX 压缩包展开后不能超过 {MAX_XLSX_TOTAL_BYTES} 字节"
            )
        if (
            compressed_size
            and expanded_size > compressed_size * MAX_XLSX_COMPRESSION_RATIO
        ):
            raise ExcelSecurityLimitError("XLSX 压缩包文件压缩比不能超过 100:1")

    missing = REQUIRED_XLSX_MEMBERS.difference(names)
    if missing:
        raise ExcelSecurityError("XLSX 压缩包缺少必要的 Office 文件")


def _validate_member_name(name: str, member: zipfile.ZipInfo) -> None:
    if not name or "\x00" in name or any(ord(char) < 32 for char in name):
        raise ExcelSecurityError("XLSX 压缩包包含不安全文件名")
    if "\\" in name:
        raise ExcelSecurityError("XLSX 压缩包包含不安全文件路径")
    normalized = posixpath.normpath(name)
    if (
        name.startswith("/")
        or normalized.startswith("../")
        or normalized == ".."
        or any(part == ".." for part in name.split("/"))
        or _WINDOWS_DRIVE_PATH.fullmatch(name.split("/", 1)[0])
    ):
        raise ExcelSecurityError("XLSX 压缩包包含不安全文件路径")
    if stat.S_ISLNK(member.external_attr >> 16):
        raise ExcelSecurityError("XLSX 压缩包包含不安全链接文件")
    if member.flag_bits & 0x1:
        raise ExcelSecurityError("XLSX 压缩包不能加密")


def _validate_local_headers(
    archive: zipfile.ZipFile, members: list[zipfile.ZipInfo]
) -> None:
    """Check each local header without reading or expanding its payload."""

    try:
        for member in members:
            handle = archive.open(member)
            handle.close()
    except (BadZipFile, NotImplementedError, RuntimeError, UnicodeError) as exc:
        raise ExcelSecurityError("XLSX 压缩包本地文件头无效") from exc


def escape_excel_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip(LEADING_FORMULA_PADDING).startswith(
        FORMULA_PREFIXES
    ):
        return f"'{value}"
    return value
