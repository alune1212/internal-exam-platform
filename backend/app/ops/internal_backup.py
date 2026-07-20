from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

DATABASE_DUMP_NAME = "database.dump"
MEDIA_ARCHIVE_NAME = "learning_media.tar.gz"
MANIFEST_NAME = "manifest.json"
CHECKSUMS_NAME = "SHA256SUMS"
SUCCESS_MARKER_NAME = "SUCCESS"

TABLE_NAMES = (
    "candidate",
    "question",
    "exam",
    "exam_attempt",
    "learning_video",
)
DISPOSABLE_PROJECT_PATTERN = re.compile(
    r"^internal-exam-restore-verify-[a-z0-9][a-z0-9-]{2,62}$"
)

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


def _validate_manifest(manifest: Any) -> dict[str, object]:
    if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
        raise BackupValidationError("备份 manifest 格式不受支持。")
    if not isinstance(manifest.get("created_at"), str) or not isinstance(
        manifest.get("migration_head"), str
    ):
        raise BackupValidationError("备份 manifest 缺少时间或迁移版本。")

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
    return manifest


def finalize_backup(directory: Path, manifest: dict[str, object]) -> None:
    """Finalize a paired backup, writing SUCCESS only after checksums exist."""

    success_marker = directory / SUCCESS_MARKER_NAME
    success_marker.unlink(missing_ok=True)
    required_artifacts = [
        directory / DATABASE_DUMP_NAME,
        directory / MEDIA_ARCHIVE_NAME,
    ]
    if any(not path.is_file() for path in required_artifacts):
        raise BackupValidationError("备份不完整：数据库或媒体产物缺失。")

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


def validate_backup(directory: Path) -> dict[str, object]:
    required_names = {
        DATABASE_DUMP_NAME,
        MEDIA_ARCHIVE_NAME,
        MANIFEST_NAME,
        CHECKSUMS_NAME,
        SUCCESS_MARKER_NAME,
    }
    if not directory.is_dir() or any(
        not (directory / name).is_file() for name in required_names
    ):
        raise BackupValidationError("备份不完整：缺少必要产物或成功标记。")
    if (directory / SUCCESS_MARKER_NAME).read_text(encoding="utf-8") != "ok\n":
        raise BackupValidationError("备份不完整：成功标记无效。")

    checksum_rows: dict[str, str] = {}
    try:
        for row in (
            (directory / CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines()
        ):
            digest, filename = row.split("  ", 1)
            checksum_rows[filename] = digest
    except (OSError, ValueError) as exc:
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

    try:
        manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupValidationError("备份 manifest 无法读取。") from exc
    return _validate_manifest(manifest)


def create_backup(
    output_root: Path, env_file: Path, now: datetime | None = None
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
    finalize_backup(
        backup_dir,
        {
            "format_version": 1,
            "created_at": created_at.isoformat(),
            "migration_head": migration_head,
            "table_counts": table_counts,
            "media_file_count": media_file_count,
        },
    )
    validate_backup(backup_dir)
    return backup_dir


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
                "nginx:1.27-alpine",
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
                    "nginx:1.27-alpine",
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
                    "nginx:1.27-alpine",
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

    verify_parser = subparsers.add_parser("verify", help="隔离恢复并校验备份")
    verify_parser.add_argument("backup_dir", type=Path)
    verify_parser.add_argument("--env-file", type=Path, default=Path(".env"))
    verify_parser.add_argument("--project-name")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.action == "backup":
            backup_dir = create_backup(args.output_root, args.env_file)
            sys.stdout.write(f"配对备份已创建并校验：{backup_dir}\n")
        else:
            project_name = (
                args.project_name
                or datetime.now(UTC)
                .strftime("internal-exam-restore-verify-%Y%m%dt%H%M%Sz")
                .lower()
            )
            verify_restore(args.backup_dir, args.env_file, project_name)
            sys.stdout.write("隔离恢复校验通过，临时资源已清理。\n")
    except BackupError as exc:
        sys.stderr.write(f"操作失败：{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
