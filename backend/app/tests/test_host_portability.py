from __future__ import annotations

import hashlib
import io
import json
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from app.ops import host_portability, internal_backup


def _manifest(*, portable: bool = False, cutover: bool = False) -> dict[str, object]:
    manifest: dict[str, object] = {
        "format_version": 1,
        "created_at": "2026-08-07T00:00:00+00:00",
        "migration_head": "202607210001",
        "table_counts": {
            "candidate": 1,
            "question": 1,
            "exam": 1,
            "exam_attempt": 0,
            "learning_video": 0,
        },
        "media_file_count": 0,
    }
    if portable:
        manifest.update(
            {
                "dataset_id": "formal-dataset",
                "writer_generation": 4,
                "source_host_id": "macos-arm64",
            }
        )
    if cutover:
        if not portable:
            raise AssertionError("cutover fixtures must include portability identity")
        manifest["backup_kind"] = internal_backup.CUTOVER_BACKUP_KIND
        manifest["writer_fence_boundary"] = {
            "dataset_id": "formal-dataset",
            "source_host_id": "macos-arm64",
            "writer_generation": 4,
        }
    return manifest


def _backup(directory: Path, *, portable: bool = False, cutover: bool = False) -> None:
    directory.mkdir()
    (directory / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"dump")
    with tarfile.open(
        directory / internal_backup.MEDIA_ARCHIVE_NAME, "w:gz"
    ) as archive:
        content = b"media"
        member = tarfile.TarInfo("sample.txt")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    internal_backup.finalize_backup(
        directory, _manifest(portable=portable, cutover=cutover)
    )


def _artifact_identity(directory: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in (
            internal_backup.DATABASE_DUMP_NAME,
            internal_backup.MEDIA_ARCHIVE_NAME,
            internal_backup.MANIFEST_NAME,
            internal_backup.CHECKSUMS_NAME,
            internal_backup.SUCCESS_MARKER_NAME,
        )
    }


def _stop_proof() -> dict[str, object]:
    return {
        "whole_project_stopped": True,
        "project": host_portability.DEFAULT_PROJECT_NAMES["formal"],
        "observed_at": "2026-08-07T00:00:00+00:00",
        "running_services": [],
        "method": "compose-ps",
    }


def _write_checksummed_json(path: Path, payload: dict[str, object]) -> None:
    content = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.write_bytes(content)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{hashlib.sha256(content).hexdigest()}  {path.name}\n",
        encoding="ascii",
    )


def _release_metadata(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "application_version": "1.2.3",
        "git_commit": "a" * 40,
        "host_os": "darwin",
        "architecture": "arm64",
        "target_platform": "linux/arm64",
        "migration_head": "202607210001",
        "release_file_checksums": {"backend/app/main.py": "0" * 64},
        "base_image_references": {"backend": "sha256:" + "3" * 64},
        "image_references": {
            "arm64": {"backend": "sha256:" + "1" * 64},
            "amd64": {"backend": "sha256:" + "2" * 64},
        },
    }
    payload.update(overrides)
    return payload


def _preflight_evidence(
    *,
    target_writer_generation: int = 5,
    dataset_id: str = "formal-dataset",
    target_host_id: str = "windows-amd64",
    release_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "target-preflight",
        "status": "passed",
        "checked_at": "2026-08-07T00:01:00+00:00",
        "dataset_id": dataset_id,
        "target_host_id": target_host_id,
        "target_writer_generation": target_writer_generation,
        "target_release_metadata": release_metadata or _release_metadata(),
    }


def test_project_names_are_strict_and_isolated() -> None:
    assert host_portability.validate_project_name("internal-exam-dev", "dev") == (
        "internal-exam-dev"
    )
    assert host_portability.validate_project_name(
        "internal-exam-staging-abcdef123456", "staging"
    )
    assert host_portability.validate_project_name(
        "internal-exam-restore-verify-abcdef123456", "restore"
    )
    assert host_portability.validate_project_name("internal-exam-formal", "formal")
    for project, environment in (
        ("internal-exam-development", "development"),
        ("internal-exam-formal-copy", "formal"),
        ("internal-exam-staging", "staging"),
        ("internal-exam-restore-verify", "restore"),
        ("internal_exam_dev", "dev"),
    ):
        with pytest.raises(host_portability.ProjectNameValidationError):
            host_portability.validate_project_name(project, environment)


def test_formal_paths_reject_worktree_symlinks_and_duplicates(tmp_path: Path) -> None:
    formal_root = tmp_path / "formal-root"
    formal_root.mkdir()
    paths = {
        name: formal_root / name
        for name in host_portability.FORMAL_PATH_FIELDS
        if name != "second_copy"
    }
    paths["second_copy"] = tmp_path / "independent-second-copy"
    validated = host_portability.validate_formal_host_paths(
        paths, development_root=host_portability.REPO_ROOT, formal_root=formal_root
    )
    assert validated["backup"] == paths["backup"]

    symlink = tmp_path / "evidence-link"
    symlink.symlink_to(host_portability.REPO_ROOT, target_is_directory=True)
    with pytest.raises(host_portability.FormalPathValidationError):
        host_portability.validate_formal_host_path(
            symlink / "evidence",
            development_root=host_portability.REPO_ROOT,
            formal_root=tmp_path,
        )

    with pytest.raises(host_portability.FormalPathValidationError):
        host_portability.validate_formal_host_paths(
            dict.fromkeys(host_portability.FORMAL_PATH_FIELDS, paths["backup"]),
            development_root=host_portability.REPO_ROOT,
            formal_root=formal_root,
        )

    overlapping = dict(paths)
    overlapping["second_copy"] = formal_root / "second-copy"
    with pytest.raises(host_portability.FormalPathValidationError, match="独立"):
        host_portability.validate_formal_host_paths(
            overlapping,
            development_root=host_portability.REPO_ROOT,
            formal_root=formal_root,
        )


def test_release_metadata_has_shared_identity_and_rejects_secret_fields() -> None:
    metadata = host_portability.build_release_metadata(
        **_release_metadata(),
    )
    assert metadata["host_os"] == "macos"
    assert metadata["architecture"] == "arm64"
    assert metadata["target_platform"] == "linux/arm64"
    assert metadata["migration_head"] == "202607210001"
    assert metadata["release_file_checksums"]
    assert metadata["image_references"] == {"backend": "sha256:" + "1" * 64}
    assert metadata["base_image_references"] == {"backend": "sha256:" + "3" * 64}
    assert len(metadata["release_input_sha256"]) == 64

    secret_payload = _release_metadata()
    secret_payload["token" + "_secret"] = "do-not-retain"
    with pytest.raises(host_portability.MetadataValidationError):
        host_portability.validate_release_metadata(secret_payload)
    with pytest.raises(host_portability.MetadataValidationError):
        host_portability.validate_evidence_metadata(
            host_portability.build_evidence_metadata(
                release_metadata=metadata,
                kind="preflight",
                status="passed",
                checks={"nested": {"admin_password": "do-not-retain"}},
            )
            | {"checks": {"nested": {"admin_password": "do-not-retain"}}}
        )

    with pytest.raises(host_portability.MetadataValidationError):
        host_portability.validate_release_metadata(
            _release_metadata(target_platform="linux/amd64")
        )

    base_only = _release_metadata()
    base_only.pop("image_references")
    base_only["imageDigests"] = {"backend": "sha256:" + "4" * 64}
    with pytest.raises(host_portability.MetadataValidationError):
        host_portability.validate_release_metadata(base_only)


def test_release_input_identity_is_derived_and_excludes_platform_outputs() -> None:
    raw = _release_metadata(
        release_file_checksums={
            "backend/app/main.py": "0" * 64,
            "ops/release/built-image-identity.json": "1" * 64,
            "ops/release/built-image-identity.json.sha256": "3" * 64,
            "release-evidence/security-scan.json": "2" * 64,
            "release-evidence/security-scan.json.sha256": "4" * 64,
        }
    )
    normalized = host_portability.validate_release_metadata(raw)
    stable_only = host_portability.validate_release_metadata(
        _release_metadata(release_file_checksums={"backend/app/main.py": "0" * 64})
    )
    assert normalized["release_input_sha256"] == stable_only["release_input_sha256"]

    forged = dict(raw)
    forged["release_input_sha256"] = "f" * 64
    with pytest.raises(host_portability.MetadataValidationError):
        host_portability.validate_release_metadata(forged)


def _windows_release_metadata(**overrides: Any) -> dict[str, Any]:
    payload = _release_metadata(
        host_os="windows",
        architecture="amd64",
        target_platform="linux/amd64",
        image_references={"backend": "sha256:" + "9" * 64},
        release_file_checksums={
            "backend/app/main.py": "0" * 64,
            "ops/release/built-image-identity.json": "a" * 64,
            "ops/release/built-image-identity.json.sha256": "d" * 64,
            "release-evidence/security-scan.json": "b" * 64,
            "release-evidence/security-scan.json.sha256": "e" * 64,
        },
    )
    payload.update(overrides)
    return payload


def _prepared_cutover() -> dict[str, Any]:
    return host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=4,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
    )


def test_cutover_accepts_macos_arm64_source_and_windows_amd64_target() -> None:
    prepared = _prepared_cutover()
    target_release = _windows_release_metadata()
    accepted = host_portability.accept_cutover(
        prepared,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(
            target_writer_generation=5,
            release_metadata=target_release,
        ),
    )
    assert accepted["source_release_metadata"]["host_os"] == "macos"
    assert accepted["source_release_metadata"]["architecture"] == "arm64"
    assert accepted["target_release_metadata"]["host_os"] == "windows"
    assert accepted["target_release_metadata"]["architecture"] == "amd64"
    assert (
        accepted["source_release_metadata_sha256"]
        != accepted["target_release_metadata_sha256"]
    )
    assert (
        accepted["source_release_metadata"]["release_input_sha256"]
        == accepted["target_release_metadata"]["release_input_sha256"]
    )
    assert accepted["target_exposed"] is False
    assert accepted["target_write_accepted"] is False
    assert accepted["target_write_authorized"] is True


def test_cutover_accepts_same_architecture_target_with_distinct_outputs() -> None:
    prepared = _prepared_cutover()
    target_release = _release_metadata(
        image_references={"backend": "sha256:" + "9" * 64},
        release_file_checksums={
            "backend/app/main.py": "0" * 64,
            "release-evidence/security-scan.json": "c" * 64,
        },
    )
    accepted = host_portability.accept_cutover(
        prepared,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(
            target_writer_generation=5,
            release_metadata=target_release,
        ),
    )
    assert accepted["target_release_metadata"]["architecture"] == "arm64"
    assert (
        accepted["target_release_metadata"]["image_references"]
        != accepted["source_release_metadata"]["image_references"]
    )
    assert accepted["target_write_authorized"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("application_version", "9.9.9"),
        ("git_commit", "b" * 40),
        ("migration_head", "202608070001"),
        (
            "release_file_checksums",
            {"backend/app/main.py": "e" * 64},
        ),
    ],
)
def test_cutover_rejects_cross_arch_release_input_mismatch(
    field: str, value: Any
) -> None:
    prepared = _prepared_cutover()
    target_release = _windows_release_metadata(**{field: value})
    with pytest.raises(host_portability.HostPortabilityError, match="release input"):
        host_portability.accept_cutover(
            prepared,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(
                target_writer_generation=5,
                release_metadata=target_release,
            ),
        )


@pytest.mark.parametrize("name", ["Docker.raw", "disk.vhdx", "postgres_data"])
def test_migration_rejects_raw_runtime_inputs(tmp_path: Path, name: str) -> None:
    candidate = tmp_path / name
    if "." in name:
        candidate.write_bytes(b"raw")
    else:
        candidate.mkdir()
        (candidate / "PG_VERSION").write_text("16\n", encoding="ascii")
    with pytest.raises(host_portability.MigrationInputError):
        host_portability.validate_migration_input(candidate)


def test_migration_requires_success_complete_pair_and_cutover_identity(
    tmp_path: Path,
) -> None:
    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    (incomplete / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"dump")
    with pytest.raises(host_portability.MigrationInputError):
        host_portability.validate_migration_input(incomplete)

    old_backup = tmp_path / "old-backup"
    _backup(old_backup)
    with pytest.raises(host_portability.MigrationInputError):
        host_portability.validate_migration_input(old_backup)

    portable = tmp_path / "portable-backup"
    _backup(portable, portable=True)
    manifest = host_portability.validate_migration_input(portable)
    assert manifest["writer_generation"] == 4
    with pytest.raises(host_portability.MigrationInputError, match="backup_kind"):
        host_portability.prepare_cutover(
            backup_dir=portable,
            target_host_id="windows-amd64",
        )


def test_prepare_cutover_cli_requires_explicit_checksummed_stop_proof(
    tmp_path: Path,
) -> None:
    backup = tmp_path / "portable-backup"
    _backup(backup, portable=True, cutover=True)
    release_path = tmp_path / "release.json"
    _write_checksummed_json(release_path, _release_metadata())
    common_args = [
        "prepare-cutover",
        "--backup",
        str(backup),
        "--target-host-id",
        "windows-amd64",
        "--release-metadata",
        str(release_path),
        "--source-fully-stopped",
        "--state-path",
        str(tmp_path / "prepared.json"),
    ]
    with pytest.raises(SystemExit):
        host_portability.main(common_args)


def test_prepare_cutover_cli_validates_stop_proof_sidecar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    backup = tmp_path / "portable-backup"
    _backup(backup, portable=True, cutover=True)
    release_path = tmp_path / "release.json"
    _write_checksummed_json(release_path, _release_metadata())
    proof_path = tmp_path / "source-stop-proof.json"
    _write_checksummed_json(proof_path, _stop_proof())
    state_path = tmp_path / "prepared.json"
    args = [
        "prepare-cutover",
        "--backup",
        str(backup),
        "--target-host-id",
        "windows-amd64",
        "--release-metadata",
        str(release_path),
        "--source-stop-proof",
        str(proof_path),
        "--source-fully-stopped",
        "--state-path",
        str(state_path),
    ]
    assert host_portability.main(args) == 0
    assert json.loads(state_path.read_text(encoding="utf-8"))["state"] == ("prepared")
    assert capsys.readouterr().err == ""

    proof_path.write_text(
        proof_path.read_text(encoding="utf-8").replace(
            '"whole_project_stopped": true', '"whole_project_stopped": false'
        ),
        encoding="utf-8",
    )
    assert host_portability.main(args) == 1
    assert "host_portability_failed error=validation" in capsys.readouterr().err


def test_accept_cutover_requires_target_write_and_preflight_identity() -> None:
    prepared = host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=4,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
    )
    with pytest.raises(host_portability.HostPortabilityError, match="写入"):
        host_portability.accept_cutover(
            prepared,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_preflight_evidence=_preflight_evidence(target_writer_generation=5),
        )
    with pytest.raises(host_portability.HostPortabilityError, match="evidence"):
        host_portability.accept_cutover(
            prepared,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
        )
    with pytest.raises(host_portability.HostPortabilityError, match="已暴露"):
        host_portability.accept_cutover(
            prepared,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=True,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(target_writer_generation=5),
        )
    with pytest.raises(host_portability.HostPortabilityError, match="host identity"):
        host_portability.accept_cutover(
            prepared,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(
                target_host_id="other-windows-host"
            ),
        )


def test_accept_cutover_cli_requires_explicit_write_and_preflight_evidence(
    tmp_path: Path,
) -> None:
    backup = tmp_path / "portable-backup"
    _backup(backup, portable=True, cutover=True)
    release_path = tmp_path / "release.json"
    _write_checksummed_json(release_path, _release_metadata())
    source_proof_path = tmp_path / "source-stop-proof.json"
    _write_checksummed_json(source_proof_path, _stop_proof())
    prepared_path = tmp_path / "prepared.json"
    prepared = host_portability.prepare_cutover(
        backup_dir=backup,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        release_metadata=_release_metadata(),
        state_path=prepared_path,
    )
    preflight_path = tmp_path / "target-preflight.json"
    _write_checksummed_json(
        preflight_path,
        _preflight_evidence(
            dataset_id=str(prepared["dataset_id"]),
            target_writer_generation=int(prepared["target_writer_generation"]),
            release_metadata=_windows_release_metadata(),
        ),
    )
    accepted_path = tmp_path / "accepted.json"
    common_args = [
        "accept-cutover",
        str(prepared_path),
        "--target-host-id",
        "windows-amd64",
        "--target-preflight-evidence",
        str(preflight_path),
        "--source-fully-stopped",
        "--state-path",
        str(accepted_path),
    ]
    with pytest.raises(SystemExit):
        host_portability.main(common_args)
    assert (
        host_portability.main(
            [
                *common_args,
                "--target-not-exposed",
                "--target-write-not-accepted",
                "--target-exposed",
            ]
        )
        == 1
    )
    assert (
        host_portability.main(
            [
                *common_args,
                "--target-not-exposed",
                "--target-write-not-accepted",
            ]
        )
        == 0
    )
    accepted_payload = json.loads(accepted_path.read_text(encoding="utf-8"))
    assert accepted_payload["state"] == "accepted"
    assert accepted_payload["target_exposed"] is False
    assert accepted_payload["target_write_accepted"] is False
    assert accepted_payload["target_write_authorized"] is True
    assert accepted_payload["target_release_metadata"]["host_os"] == "windows"


def test_cutover_state_is_checksummed_and_generation_is_monotonic(
    tmp_path: Path,
) -> None:
    backup = tmp_path / "portable-backup"
    _backup(backup, portable=True, cutover=True)
    state_path = tmp_path / "cutover-state.json"
    prepared = host_portability.prepare_cutover(
        backup_dir=backup,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    assert prepared["state"] == "prepared"
    assert prepared["writer_generation"] == 4
    assert prepared["source_writer_generation"] == 4
    assert prepared["target_writer_generation"] == 5
    assert prepared["backup_artifact_sha256"] == _artifact_identity(backup)
    assert state_path.with_suffix(".json.sha256").is_file()
    assert host_portability.validate_checksummed_cutover_state(state_path)["state"] == (
        "prepared"
    )

    with pytest.raises(host_portability.HostPortabilityError):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_writer_generation=8,
            state_path=tmp_path / "bad.json",
        )
    with pytest.raises(host_portability.HostPortabilityError, match="target host"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="other-windows-host",
            source_fully_stopped=True,
            state_path=tmp_path / "wrong-target.json",
        )
    with pytest.raises(host_portability.HostPortabilityError, match="release metadata"):
        host_portability.accept_cutover(
            prepared,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            release_metadata=_release_metadata(application_version="9.9.9"),
        )

    accepted_path = tmp_path / "accepted.json"
    accepted = host_portability.accept_cutover(
        state_path,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_writer_generation=5,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(),
        state_path=accepted_path,
    )
    assert accepted["writer_generation"] == 5
    assert accepted["source_writer_generation"] == 4
    assert accepted["target_writer_generation"] == 5
    assert json.loads(state_path.read_text(encoding="utf-8"))["state"] == "consumed"
    assert host_portability.validate_checksummed_cutover_state(accepted_path)[
        "state"
    ] == ("accepted")

    with pytest.raises(host_portability.HostPortabilityError, match="消费"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_writer_generation=5,
            state_path=tmp_path / "accepted-again.json",
        )

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    raw["writer_generation"] = 99
    state_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(host_portability.HostPortabilityError):
        host_portability.validate_checksummed_cutover_state(state_path)


def test_prepare_retry_reuses_exact_prepared_timestamp_and_rejects_mismatch(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "prepared.json"
    artifacts = dict.fromkeys(internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64)
    first = host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=artifacts,
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    original_bytes = state_path.read_bytes()
    checksum_path = state_path.with_suffix(".json.sha256")
    checksum_path.unlink()
    checksum_staging = host_portability._cutover_temp_path(
        checksum_path, host_portability.CUTOVER_WRITE_TEMP_SUFFIX
    )
    checksum_staging.write_bytes(
        f"{hashlib.sha256(original_bytes).hexdigest()}  {state_path.name}\n".encode(
            "ascii"
        )
    )

    retried = host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=artifacts,
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    assert retried == first
    assert state_path.read_bytes() == original_bytes
    assert checksum_path.is_file()

    with pytest.raises(host_portability.MigrationInputError, match="immutable"):
        host_portability.prepare_cutover(
            dataset_id="formal-dataset",
            backup_id="different-backup",
            source_host_id="macos-arm64",
            target_host_id="windows-amd64",
            writer_generation=1,
            source_fully_stopped=True,
            source_stop_proof=_stop_proof(),
            backup_artifact_sha256=artifacts,
            release_metadata=_release_metadata(),
            state_path=state_path,
        )


def test_cutover_library_requires_explicit_whole_source_stop_proof() -> None:
    prepared = host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
    )
    assert prepared["source_stop_proof"]["whole_project_stopped"] is True


def test_cutover_rejects_missing_source_stop_proof() -> None:
    with pytest.raises(host_portability.HostPortabilityError, match="source"):
        host_portability.prepare_cutover(
            dataset_id="formal-dataset",
            backup_id="backup-1",
            source_host_id="macos-arm64",
            target_host_id="windows-amd64",
            writer_generation=1,
            backup_artifact_sha256=dict.fromkeys(
                internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
            ),
            release_metadata=_release_metadata(),
        )


def test_cutover_rejects_tampered_prepared_state_before_consumption(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "prepared.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["writer_generation"] = 9
    state_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(host_portability.HostPortabilityError, match="checksum"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            state_path=tmp_path / "accepted.json",
        )


def test_cutover_path_accept_is_single_use_under_race(tmp_path: Path) -> None:
    state_path = tmp_path / "prepared.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    accepted_paths = [tmp_path / "accepted-a.json", tmp_path / "accepted-b.json"]

    def attempt(path: Path) -> tuple[str, object]:
        try:
            return (
                "passed",
                host_portability.accept_cutover(
                    state_path,
                    target_host_id="windows-amd64",
                    source_fully_stopped=True,
                    target_exposed=False,
                    target_write_accepted=False,
                    target_preflight_evidence=_preflight_evidence(
                        target_writer_generation=2
                    ),
                    state_path=path,
                ),
            )
        except host_portability.HostPortabilityError as exc:
            return ("failed", exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, accepted_paths))

    assert [status for status, _ in results].count("passed") == 1
    assert [status for status, _ in results].count("failed") == 1
    assert sum(path.is_file() for path in accepted_paths) == 1
    assert json.loads(state_path.read_text(encoding="utf-8"))["state"] == "consumed"


def test_cutover_reservation_binds_same_basename_to_resolved_destination(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "prepared.json"
    prepared = host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    first_directory = tmp_path / "first-destination"
    second_directory = tmp_path / "second-destination"
    first_directory.mkdir()
    second_directory.mkdir()
    first = first_directory / "accepted.json"
    second = second_directory / "accepted.json"

    assert host_portability._reserve_cutover_state(state_path, first)["state"] == (
        "reserved"
    )
    with pytest.raises(host_portability.HostPortabilityError, match="identity"):
        host_portability._claim_cutover_state(
            state_path,
            source_digest=hashlib.sha256(state_path.read_bytes()).hexdigest(),
            accepted_digest="a" * 64,
            accepted_state_name=second.name,
            accepted_state_identity=host_portability._cutover_destination_identity(
                second
            ),
            prepared_state=prepared,
        )
    with pytest.raises(host_portability.HostPortabilityError, match="占用"):
        host_portability._reserve_cutover_state(state_path, second)

    marker = host_portability._cutover_consumed_marker_path(state_path)
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    assert marker_payload["accepted_state_name"] == first.name
    assert marker_payload["accepted_state_identity"] == (
        host_portability._cutover_destination_identity(first)
    )
    marker_text = marker.read_text(encoding="utf-8")
    assert str(first.resolve()) not in marker_text
    assert str(second.resolve()) not in marker_text


def test_validate_cutover_bindings_checks_backup_identity_and_target_release(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    backup = tmp_path / "backup-1"
    _backup(backup, portable=True, cutover=True)
    prepared_path = tmp_path / "prepared.json"
    host_portability.prepare_cutover(
        backup_dir=backup,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        release_metadata=_release_metadata(),
        state_path=prepared_path,
    )

    prepared_result = host_portability.validate_cutover_bindings(prepared_path, backup)
    assert prepared_result["status"] == "passed"
    assert prepared_result["backup_id"] == "backup-1"
    assert prepared_result["writer_generation"] == 4
    assert prepared_result["backup_artifact_sha256"] == _artifact_identity(backup)

    target_release = _windows_release_metadata()
    target_evidence = _preflight_evidence(
        target_writer_generation=5,
        release_metadata=target_release,
    )
    accepted_path = tmp_path / "accepted.json"
    host_portability.accept_cutover(
        prepared_path,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=target_evidence,
        state_path=accepted_path,
    )
    target_release_path = tmp_path / "target-release.json"
    _write_checksummed_json(target_release_path, target_release)

    with pytest.raises(host_portability.HostPortabilityError, match="checksummed"):
        host_portability.validate_cutover_bindings(accepted_path, backup)
    accepted_result = host_portability.validate_cutover_bindings(
        accepted_path,
        backup,
        target_release_metadata=target_release_path,
    )
    assert accepted_result["state"] == "accepted"
    assert accepted_result["writer_generation"] == 4
    assert accepted_result["target_release_metadata_sha256"] == (
        host_portability._canonical_json_sha256(
            host_portability._normalize_cutover_release_metadata(target_release)
        )
    )

    assert (
        host_portability.main(
            [
                "validate-cutover-bindings",
                str(accepted_path),
                "--backup",
                str(backup),
                "--target-release-metadata",
                str(target_release_path),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "passed"

    wrong_target_release_path = tmp_path / "wrong-target-release.json"
    _write_checksummed_json(
        wrong_target_release_path,
        _windows_release_metadata(image_references={"backend": "sha256:" + "8" * 64}),
    )
    with pytest.raises(host_portability.HostPortabilityError, match="不匹配"):
        host_portability.validate_cutover_bindings(
            accepted_path,
            backup,
            target_release_metadata=wrong_target_release_path,
        )

    wrong_name = tmp_path / "different-backup-name"
    wrong_name.mkdir()
    for artifact in backup.iterdir():
        (wrong_name / artifact.name).write_bytes(artifact.read_bytes())
    with pytest.raises(host_portability.MigrationInputError, match="目录名"):
        host_portability.validate_cutover_bindings(
            accepted_path,
            wrong_name,
            target_release_metadata=target_release_path,
        )

    (backup / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"tampered")
    with pytest.raises(host_portability.MigrationInputError, match="backup"):
        host_portability.validate_cutover_bindings(
            accepted_path,
            backup,
            target_release_metadata=target_release_path,
        )


def test_cutover_retry_repairs_reservation_marker_without_sidecar(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    host_portability._reserve_cutover_state(state_path, accepted_path)
    with pytest.raises(host_portability.HostPortabilityError):
        host_portability.recover_cutover_state(
            state_path, tmp_path / "different-accepted.json"
        )
    marker = host_portability._cutover_consumed_marker_path(state_path)
    marker_checksum = marker.with_suffix(marker.suffix + ".sha256")
    marker_checksum.unlink()

    accepted = host_portability.accept_cutover(
        state_path,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
        state_path=accepted_path,
    )
    assert accepted["state"] == "accepted"
    assert json.loads(state_path.read_text(encoding="utf-8"))["state"] == ("consumed")
    assert marker_checksum.is_file()


def test_recover_cutover_cli_repairs_only_existing_reservation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    host_portability._reserve_cutover_state(state_path, accepted_path)
    marker = host_portability._cutover_consumed_marker_path(state_path)
    marker.with_suffix(marker.suffix + ".sha256").unlink()

    assert (
        host_portability.main(
            [
                "recover-cutover-state",
                str(state_path),
                "--accepted-state",
                str(accepted_path),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "reserved"
    assert marker.with_suffix(marker.suffix + ".sha256").is_file()


def test_recover_cutover_rejects_substituted_accepted_payload(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=4,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    prepared = host_portability.validate_checksummed_cutover_state(state_path)
    accepted = host_portability.accept_cutover(
        prepared,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(target_writer_generation=5),
    )
    host_portability._reserve_cutover_state(
        state_path,
        accepted_path,
        accepted_digest="f" * 64,
    )
    accepted_path.write_bytes(host_portability._canonical_cutover_json(accepted))

    with pytest.raises(host_portability.HostPortabilityError, match="digest"):
        host_portability.recover_cutover_state(state_path, accepted_path)


def test_cutover_retry_repairs_accepted_json_without_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    real_writer = host_portability.write_checksummed_cutover_state

    def interrupted_writer(path: str | Path, state: dict[str, Any]) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            host_portability._canonical_cutover_json(
                host_portability.validate_cutover_state(state)
            )
        )
        raise host_portability.HostPortabilityError("simulated accepted write crash")

    monkeypatch.setattr(
        host_portability, "write_checksummed_cutover_state", interrupted_writer
    )
    with pytest.raises(host_portability.HostPortabilityError, match="simulated"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
            state_path=accepted_path,
        )
    assert accepted_path.is_file()
    assert not accepted_path.with_suffix(".json.sha256").exists()

    monkeypatch.setattr(
        host_portability, "write_checksummed_cutover_state", real_writer
    )
    accepted = host_portability.accept_cutover(
        state_path,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
        state_path=accepted_path,
    )
    assert accepted["state"] == "accepted"
    assert accepted_path.with_suffix(".json.sha256").is_file()


def test_cutover_retry_repairs_accepted_staging_without_canonical_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    real_writer = host_portability.write_checksummed_cutover_state

    def interrupted_writer(path: str | Path, state: dict[str, Any]) -> Path:
        destination = Path(path)
        staged = host_portability._cutover_temp_path(
            destination, host_portability.CUTOVER_WRITE_TEMP_SUFFIX
        )
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(
            host_portability._canonical_cutover_json(
                host_portability.validate_cutover_state(state)
            )
        )
        raise host_portability.HostPortabilityError("simulated accepted staging crash")

    monkeypatch.setattr(
        host_portability, "write_checksummed_cutover_state", interrupted_writer
    )
    with pytest.raises(host_portability.HostPortabilityError, match="staging"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
            state_path=accepted_path,
        )
    assert not accepted_path.exists()
    assert host_portability._cutover_temp_path(
        accepted_path, host_portability.CUTOVER_WRITE_TEMP_SUFFIX
    ).is_file()

    monkeypatch.setattr(
        host_portability, "write_checksummed_cutover_state", real_writer
    )
    accepted = host_portability.accept_cutover(
        state_path,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
        state_path=accepted_path,
    )
    assert accepted["state"] == "accepted"
    assert accepted_path.with_suffix(".json.sha256").is_file()


def test_recover_cutover_from_accepted_json_staging_before_checksum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    real_stage = host_portability._stage_cutover_bytes

    def interrupted_stage(path: Path, payload: bytes, *, label: str) -> None:
        real_stage(path, payload, label=label)
        if label == "cutover state":
            raise host_portability.HostPortabilityError(
                "simulated accepted JSON staging crash"
            )

    monkeypatch.setattr(host_portability, "_stage_cutover_bytes", interrupted_stage)
    with pytest.raises(host_portability.HostPortabilityError, match="JSON staging"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
            state_path=accepted_path,
        )
    accepted_staging = host_portability._cutover_temp_path(
        accepted_path, host_portability.CUTOVER_WRITE_TEMP_SUFFIX
    )
    accepted_checksum_staging = host_portability._cutover_temp_path(
        accepted_path.with_suffix(".json.sha256"),
        host_portability.CUTOVER_WRITE_TEMP_SUFFIX,
    )
    assert accepted_staging.is_file()
    assert not accepted_checksum_staging.exists()
    marker_path = host_portability._cutover_consumed_marker_path(state_path)
    assert not marker_path.exists()

    original_staging = accepted_staging.read_bytes()
    tampered = json.loads(original_staging)
    tampered["backup_id"] = "substituted-backup"
    accepted_staging.write_bytes(host_portability._canonical_cutover_json(tampered))
    monkeypatch.setattr(host_portability, "_stage_cutover_bytes", real_stage)
    with pytest.raises(host_portability.HostPortabilityError, match="identity"):
        host_portability.recover_cutover_state(state_path, accepted_path)
    accepted_staging.write_bytes(original_staging)

    recovered = host_portability.recover_cutover_state(state_path, accepted_path)
    assert recovered["state"] == "consumed"
    assert json.loads(state_path.read_text(encoding="utf-8"))["state"] == "consumed"
    assert (
        host_portability.validate_checksummed_cutover_state(accepted_path)["state"]
        == "accepted"
    )


def test_prepare_retry_reuses_prepared_json_staging_before_checksum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "prepared.json"
    artifacts = dict.fromkeys(internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64)
    real_stage = host_portability._stage_cutover_bytes

    def interrupted_stage(path: Path, payload: bytes, *, label: str) -> None:
        real_stage(path, payload, label=label)
        if label == "cutover state":
            raise host_portability.HostPortabilityError(
                "simulated prepared JSON staging crash"
            )

    monkeypatch.setattr(host_portability, "_stage_cutover_bytes", interrupted_stage)
    with pytest.raises(host_portability.HostPortabilityError, match="prepared JSON"):
        host_portability.prepare_cutover(
            dataset_id="formal-dataset",
            backup_id="backup-1",
            source_host_id="macos-arm64",
            target_host_id="windows-amd64",
            writer_generation=1,
            source_fully_stopped=True,
            source_stop_proof=_stop_proof(),
            backup_artifact_sha256=artifacts,
            release_metadata=_release_metadata(),
            state_path=state_path,
        )
    prepared_staging = host_portability._cutover_temp_path(
        state_path, host_portability.CUTOVER_WRITE_TEMP_SUFFIX
    )
    checksum_staging = host_portability._cutover_temp_path(
        state_path.with_suffix(".json.sha256"),
        host_portability.CUTOVER_WRITE_TEMP_SUFFIX,
    )
    assert prepared_staging.is_file()
    assert not checksum_staging.exists()

    original_staging = prepared_staging.read_bytes()
    tampered = json.loads(original_staging)
    tampered["backup_id"] = "substituted-backup"
    prepared_staging.write_bytes(host_portability._canonical_cutover_json(tampered))
    monkeypatch.setattr(host_portability, "_stage_cutover_bytes", real_stage)
    with pytest.raises(host_portability.MigrationInputError, match="immutable"):
        host_portability.prepare_cutover(
            dataset_id="formal-dataset",
            backup_id="backup-1",
            source_host_id="macos-arm64",
            target_host_id="windows-amd64",
            writer_generation=1,
            source_fully_stopped=True,
            source_stop_proof=_stop_proof(),
            backup_artifact_sha256=artifacts,
            release_metadata=_release_metadata(),
            state_path=state_path,
        )

    prepared_staging.write_bytes(original_staging)
    retried = host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=artifacts,
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    assert retried["state"] == "prepared"
    assert (
        host_portability.validate_checksummed_cutover_state(state_path)["state"]
        == "prepared"
    )


@pytest.mark.parametrize(
    "failure_label",
    ["consumed source", "consumed source checksum", "consumed marker"],
)
def test_cutover_retry_finishes_claim_after_each_claim_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_label: str,
) -> None:
    state_path = tmp_path / "prepared.json"
    accepted_path = tmp_path / "accepted.json"
    host_portability.prepare_cutover(
        dataset_id="formal-dataset",
        backup_id="backup-1",
        source_host_id="macos-arm64",
        target_host_id="windows-amd64",
        writer_generation=1,
        source_fully_stopped=True,
        source_stop_proof=_stop_proof(),
        backup_artifact_sha256=dict.fromkeys(
            internal_backup.BACKUP_ARTIFACT_NAMES, "a" * 64
        ),
        release_metadata=_release_metadata(),
        state_path=state_path,
    )
    real_replace = host_portability._replace_cutover_staging
    interrupted = False

    def interrupted_claim(staging: Path, destination: Path, *, label: str) -> None:
        nonlocal interrupted
        real_replace(staging, destination, label=label)
        if label == failure_label and not interrupted:
            interrupted = True
            raise host_portability.HostPortabilityError("simulated claim crash")

    monkeypatch.setattr(host_portability, "_replace_cutover_staging", interrupted_claim)
    with pytest.raises(host_portability.HostPortabilityError, match="simulated"):
        host_portability.accept_cutover(
            state_path,
            target_host_id="windows-amd64",
            source_fully_stopped=True,
            target_exposed=False,
            target_write_accepted=False,
            target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
            state_path=accepted_path,
        )
    assert json.loads(state_path.read_text(encoding="utf-8"))["state"] == ("consumed")
    expected_marker_state = (
        "consumed" if failure_label == "consumed marker" else "reserved"
    )
    assert (
        json.loads(
            host_portability._cutover_consumed_marker_path(state_path).read_text(
                encoding="utf-8"
            )
        )["state"]
        == expected_marker_state
    )
    assert accepted_path.is_file()

    monkeypatch.setattr(host_portability, "_replace_cutover_staging", real_replace)
    accepted = host_portability.accept_cutover(
        state_path,
        target_host_id="windows-amd64",
        source_fully_stopped=True,
        target_exposed=False,
        target_write_accepted=False,
        target_preflight_evidence=_preflight_evidence(target_writer_generation=2),
        state_path=accepted_path,
    )
    assert accepted["state"] == "accepted"
    assert (
        json.loads(
            host_portability._cutover_consumed_marker_path(state_path).read_text(
                encoding="utf-8"
            )
        )["state"]
        == "consumed"
    )
