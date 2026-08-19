from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.exceptions import DomainError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[3]

DATABASE_DUMP_NAME = "database.dump"
MEDIA_ARCHIVE_NAME = "learning_media.tar.gz"
MANIFEST_NAME = "manifest.json"
CHECKSUMS_NAME = "SHA256SUMS"
SUCCESS_MARKER_NAME = "SUCCESS"
BACKUP_ARTIFACT_NAMES = frozenset(
    {
        DATABASE_DUMP_NAME,
        MEDIA_ARCHIVE_NAME,
        MANIFEST_NAME,
        CHECKSUMS_NAME,
        SUCCESS_MARKER_NAME,
    }
)
SECOND_COPY_MARKER_NAME = ".internal-exam-encrypted-storage"
SECOND_COPY_EVIDENCE_SUFFIX = ".second-copy.json"
CUTOVER_BACKUP_KIND = "cutover"
BACKUP_KINDS = ("daily", "pre-exam", "post-exam", "pre-upgrade", CUTOVER_BACKUP_KIND)
RESTORE_MEDIA_IMAGE = (
    "nginx:1.27-alpine@sha256:"
    "65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10"
)

TABLE_NAMES = (
    "candidate",
    "question",
    "exam",
    "exam_attempt",
    "learning_video",
)
OPTIONAL_PORTABILITY_FIELDS = ("dataset_id", "writer_generation", "source_host_id")
PORTABILITY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
CHECKSUM_ROW_PATTERN = re.compile(r"^([0-9a-f]{64})  ([^/\\\r\n]+)$")
DISPOSABLE_PROJECT_PATTERN = re.compile(
    r"^internal-exam-restore-verify-[a-z0-9][a-z0-9-]{2,62}$"
)
# The media archive is restored by a host-side tar invocation.  Keep the
# accepted shape bounded even when the compressed input itself is small, and
# reject archive entries that could escape the disposable media root.
MAX_MEDIA_ARCHIVE_MEMBERS = 100_000
MAX_MEDIA_ARCHIVE_BYTES = 512 * 1024 * 1024

IN_PROGRESS_SQL = "SELECT count(*) FROM exam_attempt WHERE status = 'in_progress'"
MIGRATION_HEAD_SQL = "SELECT version_num FROM alembic_version"
TABLE_COUNTS_SQL = " UNION ALL ".join(
    f"SELECT '{table_name}=' || count(*) FROM {table_name}"  # noqa: S608
    for table_name in TABLE_NAMES
)


class BackupError(RuntimeError):
    """Base error for safe operational backup failures."""


class BackupCommandError(BackupError):
    """An external backup or restore command failed."""


class BackupValidationError(BackupError):
    """A backup artifact or restore target failed validation."""


def _run_capture(command: list[str]) -> str:
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupCommandError("运维命令执行失败，未输出命令参数或凭据。") from exc
    return completed.stdout


def _run_command(command: list[str]) -> None:
    try:
        subprocess.run(  # noqa: S603
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupCommandError("运维命令执行失败，未输出命令参数或凭据。") from exc


def _run_to_file(command: list[str], destination: Path) -> None:
    try:
        with destination.open("wb") as output:
            subprocess.run(  # noqa: S603
                command,
                cwd=REPO_ROOT,
                check=True,
                stdout=output,
                stderr=subprocess.PIPE,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupCommandError("备份产物创建失败，未输出命令参数或凭据。") from exc


def _run_to_file_env(
    command: list[str], destination: Path, environment: dict[str, str]
) -> None:
    try:
        with destination.open("wb") as output:
            subprocess.run(  # noqa: S603
                command,
                cwd=REPO_ROOT,
                check=True,
                stdout=output,
                stderr=subprocess.PIPE,
                env=environment,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupCommandError(
            "容器内数据库备份失败，未输出命令参数或凭据。"
        ) from exc


def _run_from_file(command: list[str], source: Path) -> None:
    try:
        with source.open("rb") as input_file:
            subprocess.run(  # noqa: S603
                command,
                cwd=REPO_ROOT,
                check=True,
                stdin=input_file,
                capture_output=True,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupCommandError("备份产物恢复失败，未输出命令参数或凭据。") from exc


def _compose_command(env_file: Path, project_name: str | None = None) -> list[str]:
    command = ["docker", "compose", "--env-file", str(env_file)]
    if project_name is not None:
        command.extend(["--project-name", project_name])
    return command


def _database_capture_command(
    compose: list[str], sql: str, *, database: str = "internal_exam"
) -> list[str]:
    return [
        *compose,
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "exam",
        "-d",
        database,
        "-Atc",
        sql,
    ]


def _parse_non_negative_integer(value: str, field_name: str) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise BackupValidationError(f"{field_name} 不是有效整数。") from exc
    if parsed < 0:
        raise BackupValidationError(f"{field_name} 不能为负数。")
    return parsed


def _parse_table_counts(output: str) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for row in output.splitlines():
        if "=" not in row:
            continue
        table_name, count = row.split("=", 1)
        if table_name in TABLE_NAMES:
            parsed[table_name] = _parse_non_negative_integer(
                count, f"{table_name} count"
            )
    if set(parsed) != set(TABLE_NAMES):
        raise BackupValidationError("数据库表计数结果不完整。")
    return parsed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_regular_artifact(path: Path, name: str) -> None:
    """Require an artifact to be a direct, non-link regular file."""

    try:
        mode = os.lstat(path).st_mode
    except OSError as exc:
        raise BackupValidationError(f"备份产物无法读取：{name}") from exc
    if not stat.S_ISREG(mode):
        raise BackupValidationError(f"备份产物必须是普通文件：{name}")


def _validate_backup_directory(directory: Path, required_names: set[str]) -> None:
    """Reject symlinked artifacts and any unmanifested directory entries."""

    try:
        if directory.is_symlink() or not directory.is_dir():
            raise BackupValidationError("备份目录必须是非链接目录。")
        entries = list(directory.iterdir())
    except OSError as exc:
        raise BackupValidationError("备份目录无法读取。") from exc
    names = {entry.name for entry in entries}
    if names != required_names:
        raise BackupValidationError("备份不完整：目录包含额外或缺失的产物。")
    for entry in entries:
        _require_regular_artifact(entry, entry.name)


def _validate_media_archive(path: Path) -> None:
    """Validate media tar members before any restore-side extraction."""

    try:
        with tarfile.open(path, mode="r:*") as archive:
            members = archive.getmembers()
    except (OSError, EOFError, tarfile.TarError) as exc:
        raise BackupValidationError("媒体归档不是可读取的 tar 文件。") from exc

    if len(members) > MAX_MEDIA_ARCHIVE_MEMBERS:
        raise BackupValidationError("媒体归档条目数量超出限制。")
    total_bytes = 0
    seen: set[str] = set()
    for member in members:
        name = member.name
        if (
            not isinstance(name, str)
            or not name
            or "\x00" in name
            or "\\" in name
            or name.startswith("/")
            or re.match(r"^[A-Za-z]:", name) is not None
        ):
            raise BackupValidationError("媒体归档包含不安全路径。")
        parts = name.split("/")
        if any(part == ".." for part in parts):
            raise BackupValidationError("媒体归档包含路径穿越。")
        normalized = posixpath.normpath(name)
        if normalized == ".." or normalized.startswith("../"):
            raise BackupValidationError("媒体归档包含路径穿越。")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        # Duplicate names make extraction order-dependent and are not part of
        # the portable media contract.  A root ``.`` entry is harmless but
        # may only occur once.
        if normalized in seen:
            raise BackupValidationError("媒体归档包含重复路径。")
        seen.add(normalized)
        if not (member.isdir() or member.isreg()):
            # This also rejects symlink, hardlink, FIFO, block, and character
            # device entries, regardless of how tarfile classifies them.
            raise BackupValidationError("媒体归档包含非普通文件条目。")
        if member.isdir():
            continue
        if member.size < 0:
            raise BackupValidationError("媒体归档包含无效文件大小。")
        total_bytes += member.size
        if total_bytes > MAX_MEDIA_ARCHIVE_BYTES:
            raise BackupValidationError("媒体归档解压大小超出限制。")


def _validate_portability_fields(
    manifest: dict[str, object], *, require_cross_host_identity: bool = False
) -> None:
    missing = [field for field in OPTIONAL_PORTABILITY_FIELDS if field not in manifest]
    if require_cross_host_identity and missing:
        raise BackupValidationError(
            "跨主机配对备份缺少 dataset_id、writer_generation 或 source_host_id。"
        )

    dataset_id = manifest.get("dataset_id")
    if dataset_id is not None and (
        not isinstance(dataset_id, str)
        or PORTABILITY_ID_PATTERN.fullmatch(dataset_id) is None
    ):
        raise BackupValidationError("备份 manifest 的 dataset_id 无效。")

    writer_generation = manifest.get("writer_generation")
    if writer_generation is not None and (
        isinstance(writer_generation, bool)
        or not isinstance(writer_generation, int)
        or writer_generation < 1
    ):
        raise BackupValidationError("备份 manifest 的 writer_generation 无效。")

    source_host_id = manifest.get("source_host_id")
    if source_host_id is not None and (
        not isinstance(source_host_id, str)
        or PORTABILITY_ID_PATTERN.fullmatch(source_host_id) is None
    ):
        raise BackupValidationError("备份 manifest 的 source_host_id 无效。")


def _validate_backup_kind(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in BACKUP_KINDS:
        raise BackupValidationError("备份 manifest 的 backup_kind 无效。")
    return value


def _validate_writer_fence_boundary(value: object) -> dict[str, object] | None:
    """Validate the optional self-contained cutover provenance payload."""

    if value is None:
        return None
    if not isinstance(value, dict):
        raise BackupValidationError("备份 manifest 的 writer_fence_boundary 无效。")
    boundary = cast("dict[str, object]", value)
    required = {"dataset_id", "source_host_id", "writer_generation"}
    if set(boundary) != required:
        raise BackupValidationError("备份 manifest 的 writer_fence_boundary 不完整。")
    dataset_id = boundary["dataset_id"]
    source_host_id = boundary["source_host_id"]
    writer_generation = boundary["writer_generation"]
    if (
        not isinstance(dataset_id, str)
        or PORTABILITY_ID_PATTERN.fullmatch(dataset_id) is None
    ):
        raise BackupValidationError(
            "备份 manifest 的 writer_fence_boundary dataset_id 无效。"
        )
    if (
        not isinstance(source_host_id, str)
        or PORTABILITY_ID_PATTERN.fullmatch(source_host_id) is None
    ):
        raise BackupValidationError(
            "备份 manifest 的 writer_fence_boundary source_host_id 无效。"
        )
    if (
        isinstance(writer_generation, bool)
        or not isinstance(writer_generation, int)
        or writer_generation < 1
    ):
        raise BackupValidationError(
            "备份 manifest 的 writer_fence_boundary writer_generation 无效。"
        )
    return {
        "dataset_id": dataset_id,
        "source_host_id": source_host_id,
        "writer_generation": writer_generation,
    }


def _validate_manifest(
    manifest: Any, *, require_cross_host_identity: bool = False
) -> dict[str, object]:
    if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
        raise BackupValidationError("备份 manifest 格式不受支持。")
    if not isinstance(manifest.get("created_at"), str) or not isinstance(
        manifest.get("migration_head"), str
    ):
        raise BackupValidationError("备份 manifest 缺少时间或迁移版本。")
    try:
        created_at = datetime.fromisoformat(str(manifest["created_at"]))
    except ValueError as exc:
        raise BackupValidationError("备份 manifest 的创建时间无效。") from exc
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if not str(manifest["migration_head"]).strip():
        raise BackupValidationError("备份 manifest 缺少迁移版本。")

    table_counts = manifest.get("table_counts")
    if not isinstance(table_counts, dict) or set(table_counts) != set(TABLE_NAMES):
        raise BackupValidationError("备份 manifest 的表计数不完整。")
    for count in table_counts.values():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise BackupValidationError("备份 manifest 包含无效表计数。")

    media_file_count = manifest.get("media_file_count")
    if (
        isinstance(media_file_count, bool)
        or not isinstance(media_file_count, int)
        or media_file_count < 0
    ):
        raise BackupValidationError("备份 manifest 包含无效媒体文件数。")
    backup_kind = _validate_backup_kind(manifest.get("backup_kind"))
    fence_boundary = _validate_writer_fence_boundary(
        manifest.get("writer_fence_boundary")
    )
    # A cutover artifact is never a generic portable backup: its identity is
    # the boundary that authorizes target acceptance and must be present even
    # when a caller validates without the explicit cross-host option.
    require_cross_host_identity = require_cross_host_identity or (
        backup_kind == CUTOVER_BACKUP_KIND
    )
    _validate_portability_fields(
        manifest, require_cross_host_identity=require_cross_host_identity
    )
    if backup_kind == CUTOVER_BACKUP_KIND and fence_boundary is None:
        raise BackupValidationError(
            "cutover backup manifest 必须包含 writer_fence_boundary。"
        )
    if backup_kind == CUTOVER_BACKUP_KIND:
        identity = {
            "dataset_id": manifest.get("dataset_id"),
            "source_host_id": manifest.get("source_host_id"),
            "writer_generation": manifest.get("writer_generation"),
        }
        if fence_boundary != identity:
            raise BackupValidationError(
                "备份 manifest 的 writer_fence_boundary 与 cutover identity 不一致。"
            )
    return manifest


def finalize_backup(directory: Path, manifest: dict[str, object]) -> None:
    """Finalize a paired backup, writing SUCCESS only after checksums exist."""

    success_marker = directory / SUCCESS_MARKER_NAME
    success_marker.unlink(missing_ok=True)
    required_artifacts = [
        directory / DATABASE_DUMP_NAME,
        directory / MEDIA_ARCHIVE_NAME,
    ]
    try:
        for path in required_artifacts:
            _require_regular_artifact(path, path.name)
    except BackupValidationError as exc:
        raise BackupValidationError("备份不完整：数据库或媒体产物无效。") from exc

    _validate_manifest(manifest)
    manifest_path = directory / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksummed_paths = [*required_artifacts, manifest_path]
    checksum_content = "".join(
        f"{_sha256(path)}  {path.name}\n" for path in checksummed_paths
    )
    (directory / CHECKSUMS_NAME).write_text(checksum_content, encoding="utf-8")
    success_marker.write_text("ok\n", encoding="utf-8")


def validate_backup(
    directory: str | Path,
    *,
    require_cross_host_identity: bool = False,
    require_cutover_identity: bool | None = None,
    require_cross_host: bool | None = None,
) -> dict[str, object]:
    directory = Path(directory)
    if require_cross_host is not None:
        require_cross_host_identity = require_cross_host_identity or require_cross_host
    if require_cutover_identity is not None:
        require_cross_host_identity = (
            require_cross_host_identity or require_cutover_identity
        )
    required_names = set(BACKUP_ARTIFACT_NAMES)
    _validate_backup_directory(directory, required_names)
    try:
        success_marker = (directory / SUCCESS_MARKER_NAME).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BackupValidationError("备份不完整：成功标记无法读取。") from exc
    if success_marker != "ok\n":
        raise BackupValidationError("备份不完整：成功标记无效。")

    checksum_rows: dict[str, str] = {}
    try:
        rows = (directory / CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines()
        for row in rows:
            match = CHECKSUM_ROW_PATTERN.fullmatch(row)
            if match is None or match.group(2) in checksum_rows:
                raise ValueError("invalid checksum row")
            checksum_rows[match.group(2)] = match.group(1)
    except (OSError, UnicodeError, ValueError) as exc:
        raise BackupValidationError("备份 checksum 文件格式无效。") from exc

    checksummed_names = {DATABASE_DUMP_NAME, MEDIA_ARCHIVE_NAME, MANIFEST_NAME}
    if set(checksum_rows) != checksummed_names:
        raise BackupValidationError("备份 checksum 条目不完整。")
    for filename, expected_digest in checksum_rows.items():
        if (
            not re.fullmatch(r"[0-9a-f]{64}", expected_digest)
            or _sha256(directory / filename) != expected_digest
        ):
            raise BackupValidationError(f"备份 checksum 校验失败：{filename}")

    # Every cross-host paired backup is consumed by a direct tar extraction.
    # Validate recognizable tar inputs even for local callers; retaining the
    # legacy non-tar fixture path keeps diagnostic-only backup checks backward
    # compatible while migration input remains strictly tar-backed below.
    if require_cross_host_identity or tarfile.is_tarfile(
        directory / MEDIA_ARCHIVE_NAME
    ):
        _validate_media_archive(directory / MEDIA_ARCHIVE_NAME)

    try:
        manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupValidationError("备份 manifest 无法读取。") from exc
    return _validate_manifest(
        manifest, require_cross_host_identity=require_cross_host_identity
    )


def validate_cutover_backup(
    directory: str | Path,
    *,
    dataset_id: str | None = None,
    source_host_id: str | None = None,
    writer_generation: int | None = None,
) -> dict[str, object]:
    """Validate the exact completed artifact that authorizes target transfer.

    This is intentionally stricter than ordinary backup inspection: the
    artifact must be a verified ``cutover`` backup and carry both the
    top-level portability identity and the self-contained fence boundary.
    ``validate_backup`` checks the SUCCESS marker and every checksum before
    this identity comparison, so an in-flight or tampered source artifact can
    never be used as a transfer override.
    """

    manifest = validate_backup(directory, require_cross_host_identity=True)
    if manifest.get("backup_kind") != CUTOVER_BACKUP_KIND:
        raise BackupValidationError(
            "restored cutover backup 必须标记 backup_kind=cutover。"
        )
    supplied_identity = (dataset_id, source_host_id, writer_generation)
    if any(value is not None for value in supplied_identity) and not all(
        value is not None for value in supplied_identity
    ):
        raise BackupValidationError(
            "cutover backup identity 必须同时提供 dataset_id、source_host_id、"
            "writer_generation。"
        )
    expected: dict[str, object] | None = None
    if all(value is not None for value in supplied_identity):
        expected = {
            "dataset_id": dataset_id,
            "source_host_id": source_host_id,
            "writer_generation": writer_generation,
        }
        actual = {key: manifest.get(key) for key in expected}
        if actual != expected:
            raise BackupValidationError(
                "restored cutover backup 与活动 writer-fence identity 不匹配。"
            )
    boundary = manifest.get("writer_fence_boundary")
    if boundary is None:
        raise BackupValidationError(
            "restored cutover backup 缺少 writer_fence_boundary。"
        )
    if expected is not None and boundary != expected:
        raise BackupValidationError(
            "restored cutover backup 的 writer_fence_boundary 不匹配。"
        )
    return manifest


def create_backup(
    output_root: Path,
    env_file: Path,
    now: datetime | None = None,
    *,
    dataset_id: str | None = None,
    writer_generation: int | None = None,
    source_host_id: str | None = None,
) -> Path:
    """Create a consistent paired backup during a declared maintenance window."""

    created_at = (now or datetime.now(UTC)).astimezone(UTC)
    backup_dir = output_root.expanduser().resolve() / created_at.strftime(
        "backup-%Y%m%dT%H%M%SZ"
    )
    backup_dir.mkdir(parents=True, exist_ok=False)
    compose = _compose_command(env_file.expanduser().resolve())

    in_progress = _parse_non_negative_integer(
        _run_capture(_database_capture_command(compose, IN_PROGRESS_SQL)),
        "in-progress exam count",
    )
    if in_progress:
        raise BackupValidationError(
            "维护窗口无效：仍有进行中的考试，拒绝创建配对备份。"
        )

    migration_head = _run_capture(
        _database_capture_command(compose, MIGRATION_HEAD_SQL)
    ).strip()
    if not migration_head:
        raise BackupValidationError("无法读取数据库迁移版本。")
    table_counts = _parse_table_counts(
        _run_capture(_database_capture_command(compose, TABLE_COUNTS_SQL))
    )
    media_file_count = _parse_non_negative_integer(
        _run_capture(
            [
                *compose,
                "exec",
                "-T",
                "nginx",
                "sh",
                "-c",
                "find /var/lib/nginx/learning-media -type f | wc -l",
            ]
        ),
        "media file count",
    )

    _run_to_file(
        [
            *compose,
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            "exam",
            "-d",
            "internal_exam",
            "--format=custom",
        ],
        backup_dir / DATABASE_DUMP_NAME,
    )
    _run_to_file(
        [
            *compose,
            "exec",
            "-T",
            "nginx",
            "tar",
            "-C",
            "/var/lib/nginx/learning-media",
            "-czf",
            "-",
            ".",
        ],
        backup_dir / MEDIA_ARCHIVE_NAME,
    )
    manifest: dict[str, object] = {
        "format_version": 1,
        "created_at": created_at.isoformat(),
        "migration_head": migration_head,
        "table_counts": table_counts,
        "media_file_count": media_file_count,
    }
    manifest.update(
        {
            name: value
            for name, value in (
                ("dataset_id", dataset_id),
                ("writer_generation", writer_generation),
                ("source_host_id", source_host_id),
            )
            if value is not None
        }
    )
    finalize_backup(backup_dir, manifest)
    validate_backup(backup_dir)
    return backup_dir


def create_container_backup(
    *,
    db: Session,
    output_root: Path,
    media_root: Path,
    database_url: str,
    now: datetime | None = None,
    backup_kind: str = "daily",
    operator_subject: str = "daily-backup",
    app_version: str = "unknown",
    data_fingerprint: str | None = None,
    dataset_id: str | None = None,
    writer_generation: int | None = None,
    source_host_id: str | None = None,
    under_writer_fence: bool = False,
) -> Path:
    """Create a paired backup inside the versioned backend one-shot container."""

    _validate_backup_kind(backup_kind)
    if backup_kind == CUTOVER_BACKUP_KIND and not all(
        value is not None for value in (dataset_id, writer_generation, source_host_id)
    ):
        raise BackupValidationError(
            "cutover backup 必须绑定 dataset_id、writer_generation、source_host_id。"
        )
    if under_writer_fence != (backup_kind == CUTOVER_BACKUP_KIND):
        raise BackupValidationError(
            "cutover backup 必须同时使用 backup_kind=cutover 与 under_writer_fence。"
        )
    created_at = (now or datetime.now(UTC)).astimezone(UTC)
    backup_dir = output_root.resolve() / created_at.strftime("backup-%Y%m%dT%H%M%SZ")
    backup_dir.mkdir(parents=True, exist_ok=False)
    migration_head = str(db.scalar(text(MIGRATION_HEAD_SQL)) or "").strip()
    if not migration_head:
        raise BackupValidationError("无法读取数据库迁移版本。")
    table_counts = {
        table_name: int(
            db.scalar(text(f'SELECT count(*) FROM "{table_name}"')) or 0  # noqa: S608
        )
        for table_name in TABLE_NAMES
    }
    media_root.mkdir(parents=True, exist_ok=True)
    media_file_count = sum(1 for path in media_root.rglob("*") if path.is_file())

    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        raise BackupValidationError("正式配对备份仅支持 PostgreSQL。")
    command = [
        "pg_dump",
        "--host",
        parsed.host or "db",
        "--port",
        str(parsed.port or 5432),
        "--username",
        unquote(parsed.username or "exam"),
        "--dbname",
        parsed.database or "internal_exam",
        "--format=custom",
    ]
    environment = os.environ.copy()
    environment["PGPASSWORD"] = unquote(parsed.password or "")
    _run_to_file_env(command, backup_dir / DATABASE_DUMP_NAME, environment)
    with tarfile.open(backup_dir / MEDIA_ARCHIVE_NAME, "w:gz") as archive:
        for path in sorted(media_root.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(media_root))
    manifest: dict[str, object] = {
        "format_version": 1,
        "created_at": created_at.isoformat(),
        "verified_at": datetime.now(UTC).isoformat(),
        "migration_head": migration_head,
        "table_counts": table_counts,
        "media_file_count": media_file_count,
        "backup_kind": backup_kind,
        "operator_subject": operator_subject,
        "application_version": app_version,
        "data_fingerprint": data_fingerprint,
        "outcome": "verified",
    }
    manifest.update(
        {
            name: value
            for name, value in (
                ("dataset_id", dataset_id),
                ("writer_generation", writer_generation),
                ("source_host_id", source_host_id),
            )
            if value is not None
        }
    )
    if backup_kind == CUTOVER_BACKUP_KIND:
        manifest["writer_fence_boundary"] = {
            "dataset_id": dataset_id,
            "source_host_id": source_host_id,
            "writer_generation": writer_generation,
        }
    finalize_backup(backup_dir, manifest)
    validate_backup(backup_dir)
    return backup_dir


def list_verified_backups(root: Path) -> list[tuple[Path, dict[str, object]]]:
    rows: list[tuple[Path, dict[str, object]]] = []
    if not root.is_dir():
        return rows
    for directory in root.iterdir():
        if not directory.is_dir() or not directory.name.startswith("backup-"):
            continue
        try:
            rows.append((directory, validate_backup(directory)))
        except BackupValidationError:
            continue
    return sorted(rows, key=lambda row: str(row[1]["created_at"]), reverse=True)


def prune_verified_local_backups(root: Path, *, keep: int = 3) -> list[str]:
    if keep < 1:
        raise ValueError("Local backup retention must keep at least one backup.")
    pruned: list[str] = []
    for directory, _manifest in list_verified_backups(root)[keep:]:
        shutil.rmtree(directory)
        pruned.append(directory.name)
    return pruned


def _write_checksummed_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{_sha256(path)}  {path.name}\n", encoding="ascii"
    )


def sync_verified_second_copy(
    backup_dir: Path,
    second_copy_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    synced_at = (now or datetime.now(UTC)).astimezone(UTC)
    backup_dir = backup_dir.resolve()
    evidence_path = backup_dir.parent / (backup_dir.name + SECOND_COPY_EVIDENCE_SUFFIX)
    evidence: dict[str, object] = {
        "schema_version": 1,
        "kind": "second-copy-sync",
        "backup_id": backup_dir.name,
        "checked_at": synced_at.isoformat(),
        "status": "failed",
        "destination": "configured-encrypted-second-storage",
    }
    try:
        validate_backup(backup_dir)
        if (
            not second_copy_root.is_dir()
            or not (second_copy_root / SECOND_COPY_MARKER_NAME).is_file()
        ):
            raise BackupValidationError("第二存储不可用或无法确认加密保护。")
        destination = second_copy_root / backup_dir.name
        temporary = second_copy_root / f".{backup_dir.name}.partial"
        if temporary.exists():
            shutil.rmtree(temporary)
        shutil.copytree(backup_dir, temporary)
        validate_backup(temporary)
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
        validate_backup(destination)
        evidence["status"] = "passed"
        evidence["artifact_id"] = destination.name
        evidence["pruned_expired"] = prune_expired_second_copies(
            second_copy_root, now=synced_at
        )
    except (OSError, BackupError) as exc:
        evidence["error_type"] = type(exc).__name__
    _write_checksummed_json(evidence_path, evidence)
    return evidence


def prune_expired_second_copies(
    second_copy_root: Path,
    *,
    now: datetime | None = None,
    retention_days: int = 365,
) -> list[str]:
    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    pruned: list[str] = []
    for directory, manifest in list_verified_backups(second_copy_root):
        created_at = datetime.fromisoformat(str(manifest["created_at"]))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if (checked_at - created_at.astimezone(UTC)).days >= retention_days:
            shutil.rmtree(directory)
            pruned.append(directory.name)
    return pruned


def verify_restored_state(
    *, db: Session, backup_dir: Path, media_root: Path
) -> dict[str, object]:
    manifest = validate_backup(backup_dir.resolve())
    restored_head = str(db.scalar(text(MIGRATION_HEAD_SQL)) or "").strip()
    if restored_head != manifest["migration_head"]:
        raise BackupValidationError("恢复后的数据库迁移版本不匹配。")
    restored_counts = {
        table_name: int(
            db.scalar(text(f'SELECT count(*) FROM "{table_name}"')) or 0  # noqa: S608
        )
        for table_name in TABLE_NAMES
    }
    if restored_counts != manifest["table_counts"]:
        raise BackupValidationError("恢复后的代表性数据库计数不匹配。")
    media_files = [path for path in media_root.rglob("*") if path.is_file()]
    if len(media_files) != manifest["media_file_count"]:
        raise BackupValidationError("恢复后的媒体文件数不匹配。")
    if media_files and not any(path.stat().st_size > 0 for path in media_files):
        raise BackupValidationError("恢复后的媒体样本不可读或为空。")
    return {
        "status": "passed",
        "migration_head": restored_head,
        "table_counts": restored_counts,
        "media_file_count": len(media_files),
    }


def assert_disposable_project_name(project_name: str) -> None:
    if DISPOSABLE_PROJECT_PATTERN.fullmatch(project_name) is None:
        raise BackupValidationError(
            "restore target must be a disposable project named "
            "internal-exam-restore-verify-<unique-suffix>."
        )


def _cleanup_resources(commands: list[list[str]]) -> None:
    cleanup_failed = False
    for command in commands:
        try:
            _run_command(command)
        except BackupCommandError:
            cleanup_failed = True
    if cleanup_failed:
        raise BackupCommandError("隔离恢复校验结束，但临时资源清理不完整，请人工检查。")


def verify_restore(backup_dir: Path, env_file: Path, project_name: str) -> None:
    """Restore into disposable resources and verify database/media consistency."""

    backup_dir = backup_dir.expanduser().resolve()
    manifest = validate_backup(backup_dir)
    assert_disposable_project_name(project_name)
    compose = _compose_command(env_file.expanduser().resolve(), project_name)
    media_volume = f"{project_name}_learning_media"
    media_volume_created = False

    try:
        _run_command([*compose, "up", "-d", "--wait", "db"])
        _run_command(["docker", "volume", "create", media_volume])
        media_volume_created = True
        _run_from_file(
            [
                *compose,
                "exec",
                "-T",
                "db",
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "-U",
                "exam",
                "-d",
                "internal_exam",
            ],
            backup_dir / DATABASE_DUMP_NAME,
        )
        _run_from_file(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "-v",
                f"{media_volume}:/restore",
                RESTORE_MEDIA_IMAGE,
                "tar",
                "-C",
                "/restore",
                "-xzf",
                "-",
            ],
            backup_dir / MEDIA_ARCHIVE_NAME,
        )

        restored_head = _run_capture(
            _database_capture_command(compose, MIGRATION_HEAD_SQL)
        ).strip()
        if restored_head != manifest["migration_head"]:
            raise BackupValidationError("恢复后的数据库迁移版本不匹配。")

        restored_counts = _parse_table_counts(
            _run_capture(_database_capture_command(compose, TABLE_COUNTS_SQL))
        )
        if restored_counts != manifest["table_counts"]:
            raise BackupValidationError("恢复后的代表性数据库计数不匹配。")

        restored_media_count = _parse_non_negative_integer(
            _run_capture(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{media_volume}:/restore:ro",
                    RESTORE_MEDIA_IMAGE,
                    "sh",
                    "-c",
                    "find /restore -type f | wc -l",
                ]
            ),
            "restored media file count",
        )
        if restored_media_count != manifest["media_file_count"]:
            raise BackupValidationError("恢复后的媒体文件数不匹配。")
        if (
            restored_media_count
            and not _run_capture(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{media_volume}:/restore:ro",
                    RESTORE_MEDIA_IMAGE,
                    "sh",
                    "-c",
                    "sample=$(find /restore -type f -size +0c -print -quit); "
                    'test -n "$sample" && head -c 1 "$sample" >/dev/null '
                    "&& printf readable",
                ]
            ).strip()
        ):
            raise BackupValidationError("恢复后的媒体样本不可读或为空。")
    finally:
        cleanup_commands = []
        if media_volume_created:
            cleanup_commands.append(["docker", "volume", "rm", media_volume])
        cleanup_commands.append([*compose, "down", "-v", "--remove-orphans"])
        _cleanup_resources(cleanup_commands)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="内部部署配对备份与恢复校验")
    subparsers = parser.add_subparsers(dest="action", required=True)

    backup_parser = subparsers.add_parser("backup", help="创建配对备份")
    backup_parser.add_argument("--output-root", type=Path, default=Path("backups"))
    backup_parser.add_argument("--env-file", type=Path, default=Path(".env"))
    backup_parser.add_argument("--dataset-id")
    backup_parser.add_argument("--writer-generation", type=int)
    backup_parser.add_argument("--source-host-id")

    container_parser = subparsers.add_parser(
        "container-backup", help="在版本化一次性容器中创建配对备份"
    )
    container_parser.add_argument("--output-root", type=Path, default=Path("/backups"))
    container_parser.add_argument("--media-root", type=Path, default=Path("/media"))
    container_parser.add_argument(
        "--kind",
        choices=BACKUP_KINDS,
        default="daily",
    )
    container_parser.add_argument("--operator-subject", default="daily-backup")
    container_parser.add_argument("--app-version", default="unknown")
    container_parser.add_argument("--dataset-id")
    container_parser.add_argument("--writer-generation", type=int)
    container_parser.add_argument("--source-host-id")
    container_parser.add_argument(
        "--under-writer-fence",
        action="store_true",
        help="Use the exact active writer-fence owner path for a cutover final backup",
    )
    container_parser.add_argument("--opportunistic", action="store_true")

    sync_parser = subparsers.add_parser(
        "sync-second-copy", help="校验并同步到已确认加密的第二存储"
    )
    sync_parser.add_argument("backup_dir", type=Path)
    sync_parser.add_argument("second_copy_root", type=Path)

    restored_parser = subparsers.add_parser(
        "verify-restored", help="校验当前一次性容器所连接的隔离恢复状态"
    )
    restored_parser.add_argument("backup_dir", type=Path)
    restored_parser.add_argument(
        "--media-root", type=Path, default=Path("/app/learning-media")
    )

    verify_parser = subparsers.add_parser("verify", help="隔离恢复并校验备份")
    verify_parser.add_argument("backup_dir", type=Path)
    verify_parser.add_argument("--env-file", type=Path, default=Path(".env"))
    verify_parser.add_argument("--project-name")

    inspect_parser = subparsers.add_parser(
        "inspect", help="只读校验配对备份 checksum 与 manifest"
    )
    inspect_parser.add_argument("backup_dir", type=Path)
    return parser


def _validate_container_backup_identity(args: argparse.Namespace) -> None:
    """Validate portability/fence identity combinations before opening DB."""

    values = (args.dataset_id, args.source_host_id, args.writer_generation)
    if any(value is not None for value in values) and not all(
        value is not None for value in values
    ):
        raise BackupValidationError(
            "dataset-id、source-host-id、writer-generation 必须同时提供。"
        )
    if args.under_writer_fence and not all(value is not None for value in values):
        raise BackupValidationError(
            "under-writer-fence 必须绑定 dataset-id、source-host-id、writer-generation。"
        )
    if args.kind == CUTOVER_BACKUP_KIND and not args.under_writer_fence:
        raise BackupValidationError(
            "backup_kind=cutover 必须显式使用 --under-writer-fence。"
        )
    if args.under_writer_fence and args.kind != CUTOVER_BACKUP_KIND:
        raise BackupValidationError("--under-writer-fence 仅允许 backup_kind=cutover。")


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.action == "backup":
            backup_dir = create_backup(
                args.output_root,
                args.env_file,
                dataset_id=args.dataset_id,
                writer_generation=args.writer_generation,
                source_host_id=args.source_host_id,
            )
            sys.stdout.write(f"配对备份已创建并校验：{backup_dir}\n")
        elif args.action == "container-backup":
            _validate_container_backup_identity(args)
            from app.core.config import settings
            from app.core.database import SessionLocal
            from app.services.backup_service import run_paired_backup

            with SessionLocal() as db:
                result = run_paired_backup(
                    db,
                    output_root=args.output_root,
                    media_root=args.media_root,
                    owner=args.operator_subject,
                    opportunistic=args.opportunistic,
                    fence_dataset_id=args.dataset_id,
                    fence_host_id=args.source_host_id,
                    fence_writer_generation=args.writer_generation,
                    under_writer_fence=args.under_writer_fence,
                    backup_kind=args.kind,
                    create_backup=lambda fingerprint: create_container_backup(
                        db=db,
                        output_root=args.output_root,
                        media_root=args.media_root,
                        database_url=settings.database_url,
                        backup_kind=args.kind,
                        operator_subject=args.operator_subject,
                        app_version=args.app_version,
                        data_fingerprint=fingerprint,
                        dataset_id=args.dataset_id,
                        writer_generation=args.writer_generation,
                        source_host_id=args.source_host_id,
                        under_writer_fence=args.under_writer_fence,
                    ),
                )
            sys.stdout.write(
                json.dumps(
                    {
                        "status": result.status,
                        "reason": result.reason,
                        "backup_id": result.backup_id,
                        "evidence": result.evidence_path.name,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        elif args.action == "sync-second-copy":
            evidence = sync_verified_second_copy(args.backup_dir, args.second_copy_root)
            sys.stdout.write(json.dumps(evidence, ensure_ascii=False) + "\n")
            if evidence["status"] != "passed":
                return 1
        elif args.action == "verify-restored":
            from app.core.database import SessionLocal

            with SessionLocal() as db:
                result = verify_restored_state(
                    db=db,
                    backup_dir=args.backup_dir,
                    media_root=args.media_root,
                )
            sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        elif args.action == "verify":
            project_name = (
                args.project_name
                or datetime.now(UTC)
                .strftime("internal-exam-restore-verify-%Y%m%dt%H%M%Sz")
                .lower()
            )
            verify_restore(args.backup_dir, args.env_file, project_name)
            sys.stdout.write("隔离恢复校验通过，临时资源已清理。\n")
        else:
            manifest = validate_backup(args.backup_dir.expanduser().resolve())
            sys.stdout.write(
                "配对备份只读校验通过："
                f"migration={manifest['migration_head']} "
                f"created_at={manifest['created_at']}\n"
            )
    except (BackupError, DomainError, ValueError) as exc:
        sys.stderr.write(f"操作失败：{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
