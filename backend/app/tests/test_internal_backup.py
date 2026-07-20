from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.ops import internal_backup


def _manifest() -> dict[str, object]:
    return {
        "format_version": 1,
        "created_at": "2026-07-10T00:00:00+00:00",
        "migration_head": "202607030002",
        "table_counts": {
            "candidate": 2,
            "question": 50,
            "exam": 1,
            "exam_attempt": 2,
            "learning_video": 1,
        },
        "media_file_count": 1,
    }


def _create_valid_backup(directory: Path) -> None:
    directory.mkdir()
    (directory / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"database-dump")
    (directory / internal_backup.MEDIA_ARCHIVE_NAME).write_bytes(b"media-archive")
    internal_backup.finalize_backup(directory, _manifest())


def test_finalize_and_validate_complete_backup(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    _create_valid_backup(backup_dir)

    validated = internal_backup.validate_backup(backup_dir)

    assert validated == _manifest()
    assert (backup_dir / internal_backup.SUCCESS_MARKER_NAME).read_text(
        encoding="utf-8"
    ) == "ok\n"


def test_validate_backup_rejects_partial_artifacts(tmp_path: Path) -> None:
    backup_dir = tmp_path / "partial"
    backup_dir.mkdir()
    (backup_dir / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"database-dump")

    with pytest.raises(internal_backup.BackupValidationError, match="备份不完整"):
        internal_backup.validate_backup(backup_dir)


def test_validate_backup_rejects_checksum_mismatch(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    _create_valid_backup(backup_dir)
    (backup_dir / internal_backup.MEDIA_ARCHIVE_NAME).write_bytes(b"tampered")

    with pytest.raises(internal_backup.BackupValidationError, match="checksum"):
        internal_backup.validate_backup(backup_dir)


@pytest.mark.parametrize(
    "project_name",
    ["internal-exam-platform", "internal_exam_platform", "production", "restore-test"],
)
def test_restore_project_name_must_be_disposable(project_name: str) -> None:
    with pytest.raises(internal_backup.BackupValidationError, match="disposable"):
        internal_backup.assert_disposable_project_name(project_name)


def test_create_backup_writes_paired_artifacts_and_success_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captures: list[list[str]] = []
    writes: list[list[str]] = []

    def capture(command: list[str]) -> str:
        captures.append(command)
        rendered = " ".join(command)
        if "status = 'in_progress'" in rendered:
            return "0\n"
        if "alembic_version" in rendered:
            return "202607030002\n"
        if "candidate=" in rendered:
            return (
                "candidate=2\nquestion=50\nexam=1\nexam_attempt=2\nlearning_video=1\n"
            )
        if "find /var/lib/nginx/learning-media" in rendered:
            return "1\n"
        raise AssertionError(rendered)

    def write_command(command: list[str], destination: Path) -> None:
        writes.append(command)
        destination.write_bytes(" ".join(command).encode())

    monkeypatch.setattr(internal_backup, "_run_capture", capture)
    monkeypatch.setattr(internal_backup, "_run_to_file", write_command)

    backup_dir = internal_backup.create_backup(
        output_root=tmp_path,
        env_file=tmp_path / ".env",
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    assert backup_dir.name == "backup-20260710T000000Z"
    assert internal_backup.validate_backup(backup_dir)["media_file_count"] == 1
    assert any("pg_dump" in command for command in writes)
    assert any("tar" in command for command in writes)


def test_create_backup_failure_never_writes_success_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def capture(command: list[str]) -> str:
        rendered = " ".join(command)
        if "status = 'in_progress'" in rendered:
            return "0\n"
        if "alembic_version" in rendered:
            return "202607030002\n"
        if "candidate=" in rendered:
            return "candidate=0\nquestion=0\nexam=0\nexam_attempt=0\nlearning_video=0\n"
        if "find /var/lib/nginx/learning-media" in rendered:
            return "0\n"
        raise AssertionError(rendered)

    calls = 0

    def fail_second_artifact(_command: list[str], destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise internal_backup.BackupCommandError("media backup failed")
        destination.write_bytes(b"database")

    monkeypatch.setattr(internal_backup, "_run_capture", capture)
    monkeypatch.setattr(internal_backup, "_run_to_file", fail_second_artifact)

    with pytest.raises(internal_backup.BackupCommandError):
        internal_backup.create_backup(
            output_root=tmp_path,
            env_file=tmp_path / ".env",
            now=datetime(2026, 7, 10, tzinfo=UTC),
        )

    backup_dir = tmp_path / "backup-20260710T000000Z"
    assert not (backup_dir / internal_backup.SUCCESS_MARKER_NAME).exists()


def test_verify_restore_uses_disposable_resources_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backup"
    _create_valid_backup(backup_dir)
    commands: list[list[str]] = []
    restored_files: list[tuple[list[str], Path]] = []

    def run(command: list[str]) -> None:
        commands.append(command)

    def restore(command: list[str], source: Path) -> None:
        restored_files.append((command, source))

    def capture(command: list[str]) -> str:
        commands.append(command)
        rendered = " ".join(command)
        if "alembic_version" in rendered:
            return "202607030002\n"
        if "candidate=" in rendered:
            return (
                "candidate=2\nquestion=50\nexam=1\nexam_attempt=2\nlearning_video=1\n"
            )
        if "find /restore -type f | wc -l" in rendered:
            return "1\n"
        if "find /restore -type f -size +0c" in rendered:
            return "/restore/video.mp4\n"
        return ""

    monkeypatch.setattr(internal_backup, "_run_command", run)
    monkeypatch.setattr(internal_backup, "_run_from_file", restore)
    monkeypatch.setattr(internal_backup, "_run_capture", capture)

    internal_backup.verify_restore(
        backup_dir=backup_dir,
        env_file=tmp_path / ".env",
        project_name="internal-exam-restore-verify-test",
    )

    rendered_commands = [" ".join(command) for command in commands]
    assert any(
        "--project-name internal-exam-restore-verify-test" in row
        for row in rendered_commands
    )
    assert any(
        "docker volume create internal-exam-restore-verify-test_learning_media" in row
        for row in rendered_commands
    )
    assert any("down -v" in row for row in rendered_commands)
    assert any("head -c 1" in row for row in rendered_commands)
    assert [source.name for _, source in restored_files] == [
        internal_backup.DATABASE_DUMP_NAME,
        internal_backup.MEDIA_ARCHIVE_NAME,
    ]
