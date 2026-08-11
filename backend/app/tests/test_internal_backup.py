import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.ops import internal_backup
from app.services import backup_service


def _manifest() -> dict[str, object]:
    return {
        "format_version": 1,
        "created_at": "2026-07-10T00:00:00+00:00",
        "migration_head": "202607210001",
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
    with tarfile.open(
        directory / internal_backup.MEDIA_ARCHIVE_NAME, "w:gz"
    ) as archive:
        content = b"media-archive"
        member = tarfile.TarInfo("learning/video.mp4")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    internal_backup.finalize_backup(directory, _manifest())


def test_finalize_and_validate_complete_backup(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    _create_valid_backup(backup_dir)

    validated = internal_backup.validate_backup(backup_dir)

    assert validated == _manifest()
    assert (backup_dir / internal_backup.SUCCESS_MARKER_NAME).read_text(
        encoding="utf-8"
    ) == "ok\n"


def test_cutover_backup_kind_requires_identity_and_is_retention_safe(
    tmp_path: Path,
) -> None:
    invalid_dir = tmp_path / "backup-invalid-cutover"
    _create_valid_backup(invalid_dir)
    invalid_manifest = _manifest() | {
        "backup_kind": internal_backup.CUTOVER_BACKUP_KIND
    }
    with pytest.raises(internal_backup.BackupValidationError, match="dataset_id"):
        internal_backup.finalize_backup(invalid_dir, invalid_manifest)

    missing_boundary_dir = tmp_path / "backup-missing-boundary"
    _create_valid_backup(missing_boundary_dir)
    missing_boundary_manifest = _manifest() | {
        "backup_kind": internal_backup.CUTOVER_BACKUP_KIND,
        "dataset_id": "formal-dataset",
        "source_host_id": "source-host",
        "writer_generation": 4,
    }
    with pytest.raises(
        internal_backup.BackupValidationError, match="writer_fence_boundary"
    ):
        internal_backup.finalize_backup(missing_boundary_dir, missing_boundary_manifest)

    valid_dir = tmp_path / "backup-valid-cutover"
    valid_dir.mkdir()
    (valid_dir / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"database-dump")
    with tarfile.open(
        valid_dir / internal_backup.MEDIA_ARCHIVE_NAME, "w:gz"
    ) as archive:
        content = b"media-archive"
        member = tarfile.TarInfo("learning/video.mp4")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    manifest = _manifest() | {
        "backup_kind": internal_backup.CUTOVER_BACKUP_KIND,
        "dataset_id": "formal-dataset",
        "source_host_id": "source-host",
        "writer_generation": 4,
        "writer_fence_boundary": {
            "dataset_id": "formal-dataset",
            "source_host_id": "source-host",
            "writer_generation": 4,
        },
    }
    internal_backup.finalize_backup(valid_dir, manifest)
    assert internal_backup.validate_backup(valid_dir)["backup_kind"] == "cutover"
    assert (
        internal_backup.validate_cutover_backup(
            valid_dir,
            dataset_id="formal-dataset",
            source_host_id="source-host",
            writer_generation=4,
        )
        == manifest
    )
    with pytest.raises(internal_backup.BackupValidationError, match="identity"):
        internal_backup.validate_cutover_backup(
            valid_dir,
            dataset_id="formal-dataset",
            source_host_id="source-host",
            writer_generation=5,
        )
    verified = internal_backup.list_verified_backups(tmp_path)
    assert [row[0].name for row in verified] == ["backup-valid-cutover"]


def test_container_backup_cutover_kind_requires_explicit_fence_flag() -> None:
    parser = internal_backup._build_parser()
    missing_flag = parser.parse_args(
        [
            "container-backup",
            "--kind",
            "cutover",
            "--dataset-id",
            "formal-dataset",
            "--source-host-id",
            "source-host",
            "--writer-generation",
            "4",
        ]
    )
    with pytest.raises(
        internal_backup.BackupValidationError, match="under-writer-fence"
    ):
        internal_backup._validate_container_backup_identity(missing_flag)

    wrong_kind = parser.parse_args(
        [
            "container-backup",
            "--kind",
            "daily",
            "--dataset-id",
            "formal-dataset",
            "--source-host-id",
            "source-host",
            "--writer-generation",
            "4",
            "--under-writer-fence",
        ]
    )
    with pytest.raises(internal_backup.BackupValidationError, match="仅允许"):
        internal_backup._validate_container_backup_identity(wrong_kind)


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


def test_validate_backup_rejects_symlink_and_unmanifested_entries(
    tmp_path: Path,
) -> None:
    backup_dir = tmp_path / "backup"
    _create_valid_backup(backup_dir)
    extra = backup_dir / "unexpected.txt"
    extra.write_text("unexpected", encoding="utf-8")
    with pytest.raises(internal_backup.BackupValidationError, match="额外"):
        internal_backup.validate_backup(backup_dir)

    extra.unlink()
    linked = backup_dir / internal_backup.DATABASE_DUMP_NAME
    linked.unlink()
    linked.symlink_to(tmp_path / "outside.dump")
    (tmp_path / "outside.dump").write_bytes(b"dump")
    with pytest.raises(internal_backup.BackupValidationError, match="普通文件"):
        internal_backup.validate_backup(backup_dir)


@pytest.mark.parametrize("member_kind", ["path", "symlink", "hardlink"])
def test_validate_cross_host_backup_rejects_unsafe_media_tar(
    tmp_path: Path, member_kind: str
) -> None:
    backup_dir = tmp_path / f"backup-{member_kind}"
    _create_valid_backup(backup_dir)
    archive_path = backup_dir / internal_backup.MEDIA_ARCHIVE_NAME
    with tarfile.open(archive_path, "w:gz") as archive:
        if member_kind == "path":
            content = b"escape"
            member = tarfile.TarInfo("../escape.txt")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        elif member_kind == "symlink":
            member = tarfile.TarInfo("linked.txt")
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
            archive.addfile(member)
        else:
            member = tarfile.TarInfo("linked.txt")
            member.type = tarfile.LNKTYPE
            member.linkname = "other.txt"
            archive.addfile(member)
    # Rebuild the checksum manifest after changing the media archive.  The
    # paired backup remains structurally complete but its tar policy fails.
    manifest = json.loads(
        (backup_dir / internal_backup.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    internal_backup.finalize_backup(backup_dir, manifest)
    with pytest.raises(internal_backup.BackupValidationError, match="媒体归档"):
        internal_backup.validate_backup(backup_dir, require_cross_host_identity=True)


def test_validate_cross_host_backup_rejects_media_size_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backup-oversize"
    _create_valid_backup(backup_dir)
    archive_path = backup_dir / internal_backup.MEDIA_ARCHIVE_NAME
    with tarfile.open(archive_path, "w:gz") as archive:
        content = b"oversized"
        member = tarfile.TarInfo("oversized.bin")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    monkeypatch.setattr(internal_backup, "MAX_MEDIA_ARCHIVE_BYTES", 1)
    manifest = json.loads(
        (backup_dir / internal_backup.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    internal_backup.finalize_backup(backup_dir, manifest)
    with pytest.raises(internal_backup.BackupValidationError, match="大小"):
        internal_backup.validate_backup(backup_dir, require_cross_host_identity=True)


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
            return "202607210001\n"
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
            return "202607210001\n"
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
            return "202607210001\n"
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
    media_commands = [
        command
        for command, _source in restored_files
        if command[:2] == ["docker", "run"]
    ] + [command for command in commands if command[:2] == ["docker", "run"]]
    assert media_commands
    assert all(
        internal_backup.RESTORE_MEDIA_IMAGE in command for command in media_commands
    )


def test_opportunistic_backup_runs_on_change_then_skips_and_releases_lock(
    db: Session, tmp_path: Path
) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "video.mp4").write_bytes(b"video")
    created: list[Path] = []

    def create(fingerprint: str) -> Path:
        backup_dir = tmp_path / f"backup-20260721T0{len(created)}0000Z"
        backup_dir.mkdir()
        (backup_dir / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"database")
        (backup_dir / internal_backup.MEDIA_ARCHIVE_NAME).write_bytes(b"media")
        manifest = _manifest() | {"data_fingerprint": fingerprint}
        internal_backup.finalize_backup(backup_dir, manifest)
        created.append(backup_dir)
        return backup_dir

    first = backup_service.run_paired_backup(
        db,
        output_root=tmp_path,
        media_root=media_root,
        create_backup=create,
        owner="daily-backup",
        opportunistic=True,
    )
    second = backup_service.run_paired_backup(
        db,
        output_root=tmp_path,
        media_root=media_root,
        create_backup=create,
        owner="daily-backup",
        opportunistic=True,
    )

    assert first.status == "passed"
    assert second.status == "skipped"
    assert second.reason == "no-data-change"
    assert len(created) == 1
    assert first.evidence_path.with_suffix(".json.sha256").is_file()


def test_local_pruning_keeps_latest_three_verified_only(tmp_path: Path) -> None:
    for index in range(5):
        backup_dir = tmp_path / f"backup-202607{10 + index:02d}T000000Z"
        _create_valid_backup(backup_dir)
        manifest_path = backup_dir / internal_backup.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["created_at"] = f"2026-07-{10 + index:02d}T00:00:00+00:00"
        internal_backup.finalize_backup(backup_dir, manifest)
    partial = tmp_path / "backup-partial"
    partial.mkdir()
    (partial / "partial").write_text("keep", encoding="utf-8")

    pruned = internal_backup.prune_verified_local_backups(tmp_path, keep=3)

    assert pruned == ["backup-20260711T000000Z", "backup-20260710T000000Z"]
    assert len(internal_backup.list_verified_backups(tmp_path)) == 3
    assert partial.is_dir()


def test_second_copy_requires_protection_marker_and_verifies_copy(
    tmp_path: Path,
) -> None:
    backup_dir = tmp_path / "local" / "backup-20260721T000000Z"
    backup_dir.parent.mkdir()
    _create_valid_backup(backup_dir)
    second_root = tmp_path / "second"
    second_root.mkdir()

    failed = internal_backup.sync_verified_second_copy(backup_dir, second_root)
    assert failed["status"] == "failed"
    assert not (second_root / backup_dir.name).exists()

    (second_root / internal_backup.SECOND_COPY_MARKER_NAME).write_text(
        "protected\n", encoding="utf-8"
    )
    passed = internal_backup.sync_verified_second_copy(backup_dir, second_root)

    assert passed["status"] == "passed"
    assert internal_backup.validate_backup(second_root / backup_dir.name) == _manifest()
    evidence = backup_dir.parent / (
        backup_dir.name + internal_backup.SECOND_COPY_EVIDENCE_SUFFIX
    )
    assert evidence.is_file()
    assert evidence.with_suffix(".json.sha256").is_file()


def test_second_copy_prunes_only_verified_artifacts_older_than_twelve_months(
    tmp_path: Path,
) -> None:
    root = tmp_path / "second"
    root.mkdir()
    (root / internal_backup.SECOND_COPY_MARKER_NAME).write_text(
        "protected\n", encoding="utf-8"
    )
    old = root / "backup-20250701T000000Z"
    recent = root / "backup-20260701T000000Z"
    _create_valid_backup(old)
    _create_valid_backup(recent)
    for directory, created_at in (
        (old, "2025-07-01T00:00:00+00:00"),
        (recent, "2026-07-01T00:00:00+00:00"),
    ):
        manifest = json.loads(
            (directory / internal_backup.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        manifest["created_at"] = created_at
        internal_backup.finalize_backup(directory, manifest)

    pruned = internal_backup.prune_expired_second_copies(
        root, now=datetime(2026, 7, 21, tzinfo=UTC)
    )

    assert pruned == [old.name]
    assert not old.exists()
    assert recent.exists()
