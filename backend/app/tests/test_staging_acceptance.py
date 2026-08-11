import hashlib
import json
import os
import shutil
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.ops import staging_acceptance as acceptance

COMMIT = "0123456789abcdef0123456789abcdef01234567"
HOST_ID = "host-macos-commissioning"


def _write_json(path: Path, payload: object, *, checksum: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    if checksum:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sidecar = path.with_name(path.name + ".sha256")
        sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
        os.chmod(sidecar, 0o600)


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    os.chmod(path, 0o600)


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, Path], Path, Path]:
    root = tmp_path / "protected"
    release = root / "releases" / "1.2.3"
    evidence_dir = root / "staging" / "run"
    release.mkdir(parents=True)
    (release / "ops" / "release").mkdir(parents=True)
    (release / "release-evidence").mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    for directory in (root, root / "releases", release, evidence_dir):
        os.chmod(directory, 0o700)

    images = {
        name: {
            "reference": f"internal-exam-platform-{name}:" + COMMIT,
            "id": f"sha256:{index:064x}",
            "os": "linux",
            "architecture": "arm64",
        }
        for index, name in enumerate(acceptance.IMAGE_NAMES, start=1)
    }
    identity = {
        "schemaVersion": 1,
        "status": "passed",
        "gitCommit": COMMIT,
        "applicationVersion": "1.2.3",
        "platform": "linux/arm64",
        "images": images,
    }
    identity_path = release / "ops" / "release" / "built-image-identity.json"
    _write_json(identity_path, identity)
    identity_digest = hashlib.sha256(identity_path.read_bytes()).hexdigest()

    security = {
        "schemaVersion": 1,
        "status": "passed",
        "kind": "release-security-scan",
        "sealState": "sealed",
        "scannerMode": "identity-bound",
        "builtImageIdentitySha256": identity_digest,
        "imagePlatform": "linux/arm64",
        "scannerEvidenceSha256": "a" * 64,
        "imageRecordSha256": "b" * 64,
        "binding_errors": [],
        "security_errors": [],
    }
    security_path = release / "release-evidence" / "security-scan.json"
    _write_json(security_path, security)
    security_digest = hashlib.sha256(security_path.read_bytes()).hexdigest()

    manifest = {
        "formatVersion": 1,
        "applicationVersion": "1.2.3",
        "gitCommit": COMMIT,
        "hostOS": "darwin",
        "architecture": "arm64",
        "platform": "linux/arm64",
        "migrationHead": "202607210001",
        "sealState": "sealed",
        "builtImageIdentity": {
            "path": "ops/release/built-image-identity.json",
            "sha256": identity_digest,
        },
        "imageDigests": {name: row["reference"] for name, row in images.items()},
        "securityEvidence": {
            "sha256": security_digest,
            "status": "passed",
        },
    }
    manifest_path = release / "release-manifest.json"
    _write_json(manifest_path, manifest, checksum=False)
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    _write_bytes(
        release / "SHA256SUMS", f"{manifest_digest}  release-manifest.json\n".encode()
    )

    started_at = datetime.now(UTC) - timedelta(seconds=2)
    started_text = started_at.isoformat().replace("+00:00", "Z")
    project = "internal-exam-staging-0123456789ab"
    run = {
        "schemaVersion": 2,
        "kind": "staging-run",
        "status": "started",
        "runId": "run-20260811T010203Z-123456",
        "commit": COMMIT,
        "project": project,
        "hostId": HOST_ID,
        "hostOS": "darwin",
        "architecture": "arm64",
        "platform": "linux/arm64",
        "builtImageIdentitySha256": identity_digest,
        "startedAt": started_text,
    }
    run_path = evidence_dir / "run.json"
    _write_json(run_path, run)
    live = {
        "schemaVersion": 2,
        "kind": "staging-live-images",
        "status": "passed",
        "runId": run["runId"],
        "project": project,
        "capturedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "images": {name: row["id"] for name, row in images.items()},
    }
    live_path = evidence_dir / "live-images.json"
    _write_json(live_path, live)

    # A backupRestore raw record is a disposable restore-smoke, not a free-form
    # ``status=passed`` assertion.  Keep the fixture's five-artifact portable
    # bundle under the run-scoped staging backup root so the validator can
    # re-read every byte and bind it to the sealed release migration head.
    backup_dir = (
        root
        / "staging"
        / "backups"
        / f"restore-smoke-{run['runId']}"
        / "backup-20260811T010204Z"
    )
    _write_bytes(backup_dir / "database.dump", b"portable database dump\n")
    _write_bytes(backup_dir / "learning_media.tar.gz", b"portable media archive\n")
    backup_manifest = {
        "format_version": 1,
        "migration_head": "202607210001",
        "table_counts": {"candidates": 0, "exams": 0},
        "media_file_count": 0,
    }
    _write_json(backup_dir / "manifest.json", backup_manifest, checksum=False)
    backup_digests = {
        name: hashlib.sha256((backup_dir / name).read_bytes()).hexdigest()
        for name in ("database.dump", "learning_media.tar.gz", "manifest.json")
    }
    _write_bytes(
        backup_dir / "SHA256SUMS",
        "".join(
            f"{backup_digests[name]}  {name}\n" for name in sorted(backup_digests)
        ).encode("ascii"),
    )
    _write_bytes(backup_dir / "SUCCESS", b"ok\n")
    backup_digest = hashlib.sha256((backup_dir / "SHA256SUMS").read_bytes()).hexdigest()
    backup_relative = backup_dir.relative_to(root).as_posix()
    second_copy_evidence = backup_dir.parent / f"{backup_dir.name}.second-copy.json"
    _write_json(
        second_copy_evidence,
        {
            "schema_version": 1,
            "kind": "second-copy-sync",
            "backup_id": backup_dir.name,
            "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "status": "passed",
            "artifact_id": backup_dir.name,
            "destination": "configured-encrypted-second-storage",
        },
    )
    storage_evidence = root / "evidence" / "second-copy-storage.json"
    _write_json(
        storage_evidence,
        {
            "schemaVersion": 1,
            "kind": "second-copy-storage",
            "status": "passed",
            "path": "/Volumes/EncryptedSecondCopy",
            "mountPoint": "/Volumes/EncryptedSecondCopy",
            "mounted": True,
            "encrypted": True,
            "writable": True,
            "deviceId": "/dev/disk9s1",
            "wholeDeviceId": "/dev/disk9",
            "formalWholeDeviceId": "/dev/disk8",
            "liveDevice": "/dev/disk9s1",
            "distinctPhysicalDevice": True,
            "markerPresent": True,
            "checkedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "secrets": "excluded",
        },
    )
    second_copy_evidence_relative = second_copy_evidence.relative_to(root).as_posix()
    second_copy_evidence_digest = hashlib.sha256(
        second_copy_evidence.read_bytes()
    ).hexdigest()
    storage_evidence_relative = storage_evidence.relative_to(root).as_posix()
    storage_evidence_digest = hashlib.sha256(storage_evidence.read_bytes()).hexdigest()
    browser_report_path = evidence_dir / "browser-report.json"
    browser_markers = sorted(acceptance.BROWSER_REQUIRED_MARKERS)
    _write_json(
        browser_report_path,
        {
            "schemaVersion": 2,
            "kind": "browser-e2e-report",
            "status": "passed",
            "runId": run["runId"],
            "commit": COMMIT,
            "project": project,
            "hostId": HOST_ID,
            "hostOS": "darwin",
            "architecture": "arm64",
            "platform": "linux/arm64",
            "builtImageIdentitySha256": identity_digest,
            "checkedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "browser": "Playwright Chromium desktop",
            "browserName": "chromium",
            "candidateUrl": "http://127.0.0.1:18080",
            "operatorUrl": "http://127.0.0.1:18081",
            "liveImageIds": live["images"],
            "scenarioMarkers": browser_markers,
        },
    )
    browser_report_digest = hashlib.sha256(browser_report_path.read_bytes()).hexdigest()
    capacity_source_path = evidence_dir / "capacity-source.json"
    capacity_images = [
        {
            "service": "db",
            "image_id": images["db"]["id"],
            "digest": images["db"]["id"],
        },
        {
            "service": "fake-smtp",
            "image_id": "sha256:" + "9" * 64,
            "digest": "sha256:" + "9" * 64,
        },
        {
            "service": "backend",
            "image_id": images["backend"]["id"],
            "digest": images["backend"]["id"],
        },
        {
            "service": "frontend",
            "image_id": images["frontend"]["id"],
            "digest": images["frontend"]["id"],
        },
        {
            "service": "auto-submit-worker",
            "image_id": images["backend"]["id"],
            "digest": images["backend"]["id"],
        },
        {
            "service": "nginx",
            "image_id": images["gateway"]["id"],
            "digest": images["gateway"]["id"],
        },
        {
            "service": "operator-nginx",
            "image_id": images["gateway"]["id"],
            "digest": images["gateway"]["id"],
        },
    ]
    capacity_identity = {
        "run_id": "run-capacity-20260811",
        "commit": COMMIT,
        "commit_state": "clean",
        "host_os": "darwin",
        "host_arch": "arm64",
        "run_directory": "run-capacity-20260811",
        "compose_project": "internal-exam-capacity",
        "docker_platform": "linux/arm64",
        "final_images": capacity_images,
    }
    capacity_thresholds = {
        "clients": 100,
        "error_count": 0,
        "start_p95_ms": 5000,
        "save_p95_ms": 2000,
        "submit_p95_ms": 3000,
        "max_database_connections": 40,
        "worker_heartbeat_age_seconds": 90,
    }
    capacity_metrics = {
        "run_id": "run-capacity-20260811",
        "exam_id": 1,
        "clients": 100,
        "errors": [],
        "submitted_count": 100,
        "start_p95_ms": 617,
        "save_p95_ms": 572,
        "submit_p95_ms": 524,
        "max_database_connections": 17,
        "worker_heartbeat_age_seconds": 6.062,
        "warmup_performed": False,
        "warmup_errors": [],
    }
    _write_json(
        capacity_source_path,
        {
            "schema_version": 2,
            "status": "passed",
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "identity": capacity_identity,
            "commit": COMMIT,
            "commit_state": "clean",
            "host_os": "darwin",
            "host_arch": "arm64",
            "run_directory": "run-capacity-20260811",
            "compose_project": "internal-exam-capacity",
            "docker_platform": "linux/arm64",
            "final_images": capacity_images,
            "base_url": "http://nginx",
            "warmup": {
                "performed": False,
                "measured": False,
                "errors": [],
                "cold_start_recovery": "separate-gate",
            },
            "thresholds": capacity_thresholds,
            "metrics": capacity_metrics,
            "failed_checks": [],
        },
    )
    capacity_source_digest = hashlib.sha256(
        capacity_source_path.read_bytes()
    ).hexdigest()
    evidence: dict[str, Path] = {}
    for check in acceptance.REQUIRED_CHECKS:
        payload: dict[str, object] = {
            "schemaVersion": 2,
            "kind": "staging-check",
            "status": "passed",
            "check": check,
            "runId": run["runId"],
            "commit": COMMIT,
            "project": project,
            "hostId": HOST_ID,
            "hostOS": "darwin",
            "architecture": "arm64",
            "platform": "linux/arm64",
            "builtImageIdentitySha256": identity_digest,
            "startedAt": started_text,
            "checkedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        if check == "capacity":
            payload["failed_checks"] = []
            payload["thresholds"] = {
                "clients": 100,
                "error_count": 0,
                "start_p95_ms": 5000,
                "save_p95_ms": 2000,
                "submit_p95_ms": 3000,
                "max_database_connections": 40,
                "worker_heartbeat_age_seconds": 90,
            }
            payload["metrics"] = {
                "run_id": "run-capacity-20260811",
                "clients": 100,
                "errors": [],
                "submitted_count": 100,
                "start_p95_ms": 617,
                "save_p95_ms": 572,
                "submit_p95_ms": 524,
                "max_database_connections": 17,
                "worker_heartbeat_age_seconds": 6.062,
                "warmup_performed": False,
                "warmup_errors": [],
            }
            payload["sourceMeasurementRunId"] = "run-capacity-20260811"
            payload["sourceReportPath"] = capacity_source_path.name
            payload["sourceReportSha256"] = capacity_source_digest
            payload["liveImageIds"] = live["images"]
            payload["details"] = {"capacityProject": "internal-exam-capacity"}
        if check == "healthMigration":
            payload["migrationHead"] = "202607210001"
            payload["healthHttpStatus"] = 200
            payload["readyHttpStatus"] = 200
        if check == "browser":
            payload["browser"] = "Chrome"
            payload["candidateUrl"] = "http://127.0.0.1:18080"
            payload["operatorUrl"] = "http://127.0.0.1:18081"
            payload["browserE2eStatus"] = "passed"
            payload["browserReportPath"] = browser_report_path.name
            payload["browserReportSha256"] = browser_report_digest
            payload["scenarioMarkers"] = browser_markers
            payload["liveImageIds"] = live["images"]
        if check == "smtp":
            payload["recipientDomain"] = "example.test"
            payload["sentAt"] = payload["checkedAt"]
        if check == "restart":
            payload["restartedServices"] = [
                "db",
                "backend",
                "auto-submit-worker",
                "frontend",
                "nginx",
                "operator-nginx",
            ]
            payload["recoveredAt"] = payload["checkedAt"]
            payload["healthHttpStatus"] = 200
            payload["readyHttpStatus"] = 200
            payload["migrationHead"] = "202607210001"
            payload["workerHeartbeatAgeSeconds"] = 6.062
        if check == "route":
            payload["candidatePort"] = 18080
            payload["operatorPort"] = 18081
            payload["candidateAdminHttpStatus"] = 404
            payload["operatorAdminHttpStatus"] = 200
        if check == "backupRestore":
            payload.update(
                {
                    "mode": "restore-smoke",
                    "restoreProject": "internal-exam-restore-verify-run123",
                    "sourceBackupPath": backup_relative,
                    "sourceBackupFiles": sorted(acceptance.BACKUP_REQUIRED_FILES),
                    "sourceBackupDigests": backup_digests,
                    "sourceBackupSha256": backup_digest,
                    "secondCopyEvidencePath": second_copy_evidence_relative,
                    "secondCopyEvidenceSha256": second_copy_evidence_digest,
                    "secondCopyStorageEvidencePath": storage_evidence_relative,
                    "secondCopyStorageEvidenceSha256": storage_evidence_digest,
                    "secondCopySha256": backup_digest,
                    "restoreMigrationHead": "202607210001",
                    "cleanupStatus": "passed",
                    "tableCounts": backup_manifest["table_counts"],
                    "mediaFileCount": backup_manifest["media_file_count"],
                    "restoreImageIds": {
                        name: row["id"] for name, row in images.items()
                    },
                }
            )
        artifact_path = evidence_dir / f"{check}.json"
        _write_json(artifact_path, payload)
        evidence[check] = artifact_path
    return root, release, evidence, run_path, live_path


def test_schema_two_assembly_and_revalidation(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    output = run_path.parent / "staging-acceptance.json"

    result = acceptance.assemble_acceptance(
        release=release,
        root=root,
        run_identity=run_path,
        live_image_ids=live_path,
        evidence=evidence,
        output=output,
    )

    assert result["schemaVersion"] == 2
    assert result["gates"]["security"] == "passed"
    assert (
        acceptance.validate_canonical(
            output, release=release, root=root, live_image_ids=live_path
        )["status"]
        == "passed"
    )


def test_compose_v5_live_image_list_shape(tmp_path: Path) -> None:
    root, release, _evidence, run_path, live_path = _fixture(tmp_path)
    run = acceptance.validate_run_identity(
        run_path, release=acceptance.validate_release(release, root)
    )
    expected = acceptance.validate_release(release, root).image_ids
    rows = [
        {
            "ContainerName": f"{run.project}-{service}-1",
            "ID": expected[name],
            "Repository": f"internal-exam-platform-{name}",
            "Tag": run.commit,
        }
        for service, name in (
            ("db", "db"),
            ("backend", "backend"),
            ("frontend", "frontend"),
            ("nginx", "gateway"),
        )
    ]
    _write_json(live_path, rows)

    assert (
        acceptance.validate_live_image_ids(
            live_path, run=run, expected_image_ids=expected
        )
        == expected
    )


def test_capacity_requires_nested_real_report_shape(tmp_path: Path) -> None:
    root, release, evidence, run_path, _live_path = _fixture(tmp_path)
    run = acceptance.validate_run_identity(
        run_path, release=acceptance.validate_release(release, root)
    )
    payload = json.loads(evidence["capacity"].read_text(encoding="utf-8"))
    payload.pop("metrics")
    payload.pop("thresholds")
    payload["clients"] = 100
    payload["errors"] = []
    payload["failed_checks"] = []
    _write_json(evidence["capacity"], payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_raw_artifact(
            evidence["capacity"], check="capacity", run=run
        )
    assert error.value.code == "capacity_metrics_missing"


@pytest.mark.parametrize(
    ("mutate_source", "expected_code"),
    [
        (
            lambda source: source.update({"status": "failed"}),
            "capacity_source_report_status_invalid",
        ),
        (
            lambda source: source["metrics"].update({"clients": 99}),
            "capacity_source_report_metrics_mismatch",
        ),
        (
            lambda source: source["identity"]["final_images"][0].update(
                {"image_id": "sha256:" + "f" * 64}
            ),
            "capacity_source_report_images_mismatch",
        ),
        (
            lambda source: source["identity"].update(
                {"compose_project": "internal-exam-staging-0123456789ab"}
            ),
            "capacity_source_report_identity_mismatch",
        ),
        (
            lambda source: source["metrics"].update({"run_id": "run-other-20260811"}),
            "capacity_source_report_run_mismatch",
        ),
    ],
)
def test_capacity_source_report_is_revalidated_against_raw(
    tmp_path: Path,
    mutate_source: Callable[[dict[str, object]], object],
    expected_code: str,
) -> None:
    root, release, evidence, run_path, _live_path = _fixture(tmp_path)
    source_path = run_path.parent / "capacity-source.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    mutate_source(source)
    _write_json(source_path, source)
    payload = json.loads(evidence["capacity"].read_text(encoding="utf-8"))
    payload["sourceReportSha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    _write_json(evidence["capacity"], payload)
    run = acceptance.validate_run_identity(
        run_path, release=acceptance.validate_release(release, root)
    )
    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_raw_artifact(
            evidence["capacity"], check="capacity", run=run
        )
    assert error.value.code == expected_code


@pytest.mark.parametrize(
    ("check", "mutate", "error_code"),
    [
        (
            "healthMigration",
            lambda payload: payload.pop("healthHttpStatus"),
            "identity_field_missing",
        ),
        (
            "restart",
            lambda payload: payload.update({"restartedServices": ["backend"]}),
            "restart_probe_missing",
        ),
        (
            "route",
            lambda payload: payload.pop("candidateAdminHttpStatus"),
            "identity_field_missing",
        ),
    ],
)
def test_runtime_probe_facts_are_required(
    tmp_path: Path,
    check: str,
    mutate: Callable[[dict[str, object]], object],
    error_code: str,
) -> None:
    root, release, evidence, run_path, _live_path = _fixture(tmp_path)
    run = acceptance.validate_run_identity(
        run_path, release=acceptance.validate_release(release, root)
    )
    payload = json.loads(evidence[check].read_text(encoding="utf-8"))
    mutate(payload)
    _write_json(evidence[check], payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_raw_artifact(evidence[check], check=check, run=run)
    assert error.value.code == error_code


def test_manual_schema_one_canonical_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    output = run_path.parent / "staging-acceptance.json"
    acceptance.assemble_acceptance(
        release=release,
        root=root,
        run_identity=run_path,
        live_image_ids=live_path,
        evidence=evidence,
        output=output,
    )
    payload = json.loads(output.read_text())
    payload["schemaVersion"] = 1
    _write_json(output, payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_canonical(output, release=release, root=root)
    assert error.value.code == "canonical_schema_invalid"


def test_tampered_raw_artifact_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    output = run_path.parent / "staging-acceptance.json"
    acceptance.assemble_acceptance(
        release=release,
        root=root,
        run_identity=run_path,
        live_image_ids=live_path,
        evidence=evidence,
        output=output,
    )
    evidence["browser"].write_text(
        evidence["browser"]
        .read_text()
        .replace('"status": "passed"', '"status": "failed"'),
        encoding="utf-8",
    )

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_canonical(output, release=release, root=root)
    assert error.value.code == "canonical_browser_checksum_mismatch"


def test_mismatched_raw_run_identity_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    payload = json.loads(evidence["smtp"].read_text())
    payload["runId"] = "run-other-20260811"
    _write_json(evidence["smtp"], payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.assemble_acceptance(
            release=release,
            root=root,
            run_identity=run_path,
            live_image_ids=live_path,
            evidence=evidence,
            output=run_path.parent / "staging-acceptance.json",
        )
    assert error.value.code == "raw_artifact_runId_mismatch"


def test_reused_stale_run_identity_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    payload = json.loads(run_path.read_text())
    payload["startedAt"] = (
        (datetime.now(UTC) - timedelta(days=8)).isoformat().replace("+00:00", "Z")
    )
    _write_json(run_path, payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.assemble_acceptance(
            release=release,
            root=root,
            run_identity=run_path,
            live_image_ids=live_path,
            evidence=evidence,
            output=run_path.parent / "staging-acceptance.json",
        )
    assert error.value.code == "run_identity_stale"


def test_symlink_raw_artifact_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    original = evidence["route"]
    replacement = original.with_name("route-real.json")
    original.rename(replacement)
    original.symlink_to(replacement)
    evidence["route"] = original

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.assemble_acceptance(
            release=release,
            root=root,
            run_identity=run_path,
            live_image_ids=live_path,
            evidence=evidence,
            output=run_path.parent / "staging-acceptance.json",
        )
    assert error.value.code == "raw_artifact_symlink"


def test_unknown_raw_field_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    payload = json.loads(evidence["healthMigration"].read_text())
    payload["unexpected"] = "manual pass"
    _write_json(evidence["healthMigration"], payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.assemble_acceptance(
            release=release,
            root=root,
            run_identity=run_path,
            live_image_ids=live_path,
            evidence=evidence,
            output=run_path.parent / "staging-acceptance.json",
        )
    assert error.value.code == "raw_artifact_unknown_field"


def test_raw_digest_mutation_breaks_canonical_bundle(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    output = run_path.parent / "staging-acceptance.json"
    acceptance.assemble_acceptance(
        release=release,
        root=root,
        run_identity=run_path,
        live_image_ids=live_path,
        evidence=evidence,
        output=output,
    )
    payload = json.loads(evidence["restart"].read_text())
    payload["checkedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _write_json(evidence["restart"], payload)

    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_canonical(output, release=release, root=root)
    assert error.value.code == "canonical_restart_digest_mismatch"


def test_macos_staging_captures_live_checksum_and_preserves_accepted_bundle() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    invoke = (repo_root / "ops" / "macos" / "Invoke-Staging.zsh").read_text(
        encoding="utf-8"
    )
    promote = (repo_root / "ops" / "macos" / "Promote-Release.zsh").read_text(
        encoding="utf-8"
    )
    runtime = (
        repo_root / "ops" / "macos" / "Invoke-StagingRuntimeChecks.zsh"
    ).read_text(encoding="utf-8")

    assert 'macos_write_checksum "$destination"' in invoke
    assert "staging_evidence_preserved" in invoke
    assert 'rm -R -- "$staging_host_root"' not in invoke
    assert "staging-acceptance (schemaVersion 2)" in promote
    assert "durable checksummed" in promote
    assert "--live-image-ids" in promote
    assert "never emits browser, SMTP, or capacity passed evidence" in runtime
    assert "assert_protected_output" in runtime
    assert "runtime evidence output must remain under the protected root" in runtime
    assert "runtime evidence output must not be a symlink" in runtime
    assert "up -d --no-build --wait" in runtime
    assert "auto-submit-worker" in runtime
    assert "staging_up_failed cleanup=project" in invoke


def test_canonical_bundle_survives_staging_down_relocation(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    output = run_path.parent / "staging-acceptance.json"
    acceptance.assemble_acceptance(
        release=release,
        root=root,
        run_identity=run_path,
        live_image_ids=live_path,
        evidence=evidence,
        output=output,
    )
    durable = root / "evidence" / "staging-run-bundle"
    durable.parent.mkdir(exist_ok=True)
    shutil.move(str(run_path.parent), durable)

    relocated_output = durable / output.name
    relocated_live = durable / live_path.name
    assert (
        acceptance.validate_canonical(
            relocated_output,
            release=release,
            root=root,
            live_image_ids=relocated_live,
        )["status"]
        == "passed"
    )


def test_backup_restore_raw_record_rechecks_portable_bundle_and_image_binding(
    tmp_path: Path,
) -> None:
    root, release, evidence, run_path, _live_path = _fixture(tmp_path)
    run = acceptance.validate_run_identity(
        run_path, release=acceptance.validate_release(release, root)
    )

    acceptance.validate_raw_artifact(
        evidence["backupRestore"],
        check="backupRestore",
        run=run,
        root=root,
        expected_migration_head="202607210001",
        expected_image_ids=acceptance.validate_release(release, root).image_ids,
    )
    payload = json.loads(evidence["backupRestore"].read_text(encoding="utf-8"))
    payload["restoreImageIds"]["backend"] = "sha256:" + "f" * 64
    _write_json(evidence["backupRestore"], payload)
    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_raw_artifact(
            evidence["backupRestore"],
            check="backupRestore",
            run=run,
            root=root,
            expected_migration_head="202607210001",
            expected_image_ids=acceptance.validate_release(release, root).image_ids,
        )
    assert error.value.code == "backup_restore_images_mismatch"


def test_backup_restore_tampered_source_bundle_is_rejected(tmp_path: Path) -> None:
    root, release, evidence, run_path, _live_path = _fixture(tmp_path)
    payload = json.loads(evidence["backupRestore"].read_text(encoding="utf-8"))
    source = root / payload["sourceBackupPath"]
    source.joinpath("database.dump").write_bytes(b"tampered\n")
    os.chmod(source / "database.dump", 0o600)
    run = acceptance.validate_run_identity(
        run_path, release=acceptance.validate_release(release, root)
    )
    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.validate_raw_artifact(
            evidence["backupRestore"],
            check="backupRestore",
            run=run,
            root=root,
            expected_migration_head="202607210001",
            expected_image_ids=acceptance.validate_release(release, root).image_ids,
        )
    assert error.value.code == "backup_restore_source_digest_mismatch"


def test_acceptance_binds_to_expected_commissioning_host(tmp_path: Path) -> None:
    root, release, evidence, run_path, live_path = _fixture(tmp_path)
    with pytest.raises(acceptance.StagingAcceptanceError) as error:
        acceptance.assemble_acceptance(
            release=release,
            root=root,
            run_identity=run_path,
            live_image_ids=live_path,
            evidence=evidence,
            output=run_path.parent / "staging-acceptance.json",
            expected_host_id="host-another-mac",
        )
    assert error.value.code == "run_identity_host_mismatch"


def test_backup_restore_producer_contract_is_disposable_and_real() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    producer = (
        repo_root / "ops" / "macos" / "Invoke-StagingBackupRestoreCheck.zsh"
    ).read_text(encoding="utf-8")
    for marker in (
        "container-backup",
        "sync-second-copy",
        "verify-restored",
        "database.dump",
        "learning_media.tar.gz",
        "SHA256SUMS",
        "SUCCESS",
        "sourceBackupSha256",
        "restoreMigrationHead",
        "cleanupStatus",
        "down -v --remove-orphans",
        "restore_compose_override",
        "restore_compose_base",
        "ports: !reset []",
        "backup_run_root_created",
        "second_copy_created",
    ):
        assert marker in producer
    assert producer.count("ports: !reset []") == 4
    assert "restore_compose up -d --no-build --wait db" in producer
    assert "restore_compose_capture ps --status running --services" in producer
    assert '"$second_copy_destination/database.dump"' in producer
    assert 'restore_compose cp \\\n  "$backup_path/database.dump"' not in producer
    assert '"$second_copy_destination:/backup:ro"' in producer
    assert 'rm -R -- "$backup_run_root"' in producer
    assert 'rm -R -- "$second_copy_destination"' in producer
    override_start = producer.index("restore_override_body=")
    override_end = producer.index(
        'macos_write_atomic "$restore_compose_override"', override_start
    )
    override = producer[override_start:override_end]
    for staging_port in ("15432", "18080", "18081", "15173"):
        assert staging_port not in override
    assert '"$MACOS_FORMAL_ENV"' not in producer
    assert '"$MACOS_FORMAL_PROJECT"' not in producer

    promote = (repo_root / "ops" / "macos" / "Promote-Release.zsh").read_text(
        encoding="utf-8"
    )
    assert '[[ "$paired_backup_path:h" == "$MACOS_LAYOUT_BACKUPS" ]]' in promote
    assert '[[ "$second_copy_backup_path:h" == "$second_copy_root" ]]' in promote
    assert '[[ "$paired_backup_path:t" == backup-* ]]' in promote
