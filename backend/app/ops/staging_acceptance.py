"""Fail-closed schema-2 macOS staging evidence assembly and validation.

This module is intentionally runnable from the selected release backend image::

    python -m app.ops.staging_acceptance --help

The host adapter is responsible for starting an isolated Compose project and
for capturing the live image list.  This module owns the evidence contract:

* the release must be the installed, owner-only directory
  ``<protected-root>/releases/<version>``;
* the release manifest, native ``built-image-identity.json`` and sealed
  ``release-evidence/security-scan.json`` are checked against their sidecars;
* one fresh, checksummed ``staging-run`` record binds every check to a run,
  commit, project, host and image-identity digest;
* each of the seven raw check records is a regular, non-symlink, owner-only,
  checksummed strict JSON document with ``status=passed``;
* the live Compose image capture is checked against the exact image IDs from
  the release identity and is fresh for the run; and
* a canonical ``staging-acceptance`` record contains only relative artifact
  paths and their digests.  Validation always re-reads those artifacts, so a
  hand-written top-level ``gates`` object can never satisfy promotion.

Raw records use camelCase names.  A small set of snake_case aliases is
accepted for producers that already emit the repository's operational reports,
but aliases are still allow-listed and unknown fields fail closed.  A
``backupRestore`` record is not a claim that formal data was restored.  It is a
disposable release-bound restore-smoke record and must contain:

``mode``
    ``restore-smoke`` or ``disposable-restore-smoke``.
``restoreProject``
    An isolated ``internal-exam-restore-verify-*`` Compose project.
``sourceBackupSha256``
    The checksum of the portable backup used by the smoke restore.
``restoreMigrationHead``
    The migration head reached by the disposable database.
``cleanupStatus``
    ``passed`` after the disposable project and volumes were removed.

This contract deliberately does not create browser, SMTP, or capacity facts.
Those producers remain external until they can emit the same run identity;
missing records are rejected rather than filled with self-asserted ``passed``
strings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

SCHEMA_VERSION: Final = 2
RAW_KIND: Final = "staging-check"
RUN_KIND: Final = "staging-run"
CANONICAL_KIND: Final = "staging-acceptance"
REQUIRED_CHECKS: Final[tuple[str, ...]] = (
    "healthMigration",
    "browser",
    "smtp",
    "capacity",
    "restart",
    "route",
    "backupRestore",
)
CANONICAL_GATES: Final[tuple[str, ...]] = (*REQUIRED_CHECKS, "security")
IMAGE_NAMES: Final[tuple[str, ...]] = ("db", "backend", "frontend", "gateway")
RESTART_SERVICES: Final[frozenset[str]] = frozenset(
    {"db", "backend", "auto-submit-worker", "frontend", "nginx", "operator-nginx"}
)
COMMIT_RE: Final = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256_RE: Final = re.compile(r"^[0-9a-fA-F]{64}$")
IMAGE_ID_RE: Final = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
RUN_ID_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
PROJECT_RE: Final = re.compile(r"^internal-exam-staging-[0-9a-fA-F]{12}$")
RESTORE_PROJECT_RE: Final = re.compile(
    r"^internal-exam-restore-verify-[a-z0-9][a-z0-9-]{2,62}$"
)
DEFAULT_MAX_AGE_SECONDS: Final = 7 * 24 * 60 * 60
CLOCK_SKEW_SECONDS: Final = 300

# Keep these in lock-step with ``app.ops.capacity_gate.Thresholds``.  The
# staging validator intentionally checks the report emitted by that producer,
# rather than accepting a hand-written flat ``clients/errors`` assertion.
CAPACITY_THRESHOLDS: Final[dict[str, int | float]] = {
    "clients": 100,
    "error_count": 0,
    "start_p95_ms": 5000,
    "save_p95_ms": 2000,
    "submit_p95_ms": 3000,
    "max_database_connections": 40,
    "worker_heartbeat_age_seconds": 90,
}
CAPACITY_PROJECT_RE: Final = re.compile(
    r"^internal-exam-capacity(?:-[a-z0-9][a-z0-9-]{0,62})?$"
)
CAPACITY_METRIC_FIELDS: Final = frozenset(
    {
        "run_id",
        "runId",
        "exam_id",
        "examId",
        "clients",
        "errors",
        "submitted_count",
        "submittedCount",
        "start_p95_ms",
        "startP95Ms",
        "save_p95_ms",
        "saveP95Ms",
        "submit_p95_ms",
        "submitP95Ms",
        "max_database_connections",
        "maxDatabaseConnections",
        "worker_heartbeat_age_seconds",
        "workerHeartbeatAgeSeconds",
        "warmup_performed",
        "warmupPerformed",
        "warmup_errors",
        "warmupErrors",
    }
)
CAPACITY_REQUIRED_MEASURED_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "clients": ("clients",),
    "errors": ("errors",),
    "submitted_count": ("submitted_count", "submittedCount"),
    "start_p95_ms": ("start_p95_ms", "startP95Ms"),
    "save_p95_ms": ("save_p95_ms", "saveP95Ms"),
    "submit_p95_ms": ("submit_p95_ms", "submitP95Ms"),
    "max_database_connections": (
        "max_database_connections",
        "maxDatabaseConnections",
    ),
    "worker_heartbeat_age_seconds": (
        "worker_heartbeat_age_seconds",
        "workerHeartbeatAgeSeconds",
    ),
}
CAPACITY_SOURCE_ALLOWED_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "schema_version",
        "kind",
        "status",
        "generatedAt",
        "generated_at",
        "checkedAt",
        "checked_at",
        "identity",
        "commit",
        "commit_state",
        "host_os",
        "host_arch",
        "run_directory",
        "compose_project",
        "docker_platform",
        "final_images",
        "base_url",
        "warmup",
        "thresholds",
        "metrics",
        "failedChecks",
        "failed_checks",
        "runtime_error",
        "secrets",
    }
)
CAPACITY_SOURCE_IDENTITY_FIELDS: Final = frozenset(
    {
        "runId",
        "run_id",
        "commit",
        "gitCommit",
        "git_commit",
        "commitState",
        "commit_state",
        "hostOS",
        "host_os",
        "architecture",
        "hostArch",
        "host_arch",
        "project",
        "composeProject",
        "compose_project",
        "runDirectory",
        "run_directory",
        "dockerPlatform",
        "docker_platform",
        "finalImages",
        "final_images",
    }
)
CAPACITY_SOURCE_SERVICES: Final = frozenset(
    {
        "db",
        "fake-smtp",
        "backend",
        "frontend",
        "auto-submit-worker",
        "nginx",
        "operator-nginx",
    }
)

BROWSER_REPORT_ALLOWED_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "schema_version",
        "kind",
        "status",
        "runId",
        "run_id",
        "commit",
        "gitCommit",
        "git_commit",
        "project",
        "composeProject",
        "compose_project",
        "hostId",
        "host_id",
        "hostOS",
        "host_os",
        "architecture",
        "platform",
        "builtImageIdentitySha256",
        "built_image_identity_sha256",
        "checkedAt",
        "checked_at",
        "browser",
        "browserName",
        "browser_name",
        "candidateUrl",
        "candidate_url",
        "operatorUrl",
        "operator_url",
        "liveImageIds",
        "live_image_ids",
        "scenarioMarkers",
        "scenario_markers",
        "suiteMarkers",
        "suite_markers",
        "command",
        "commandSha256",
        "command_sha256",
        "secrets",
    }
)
BROWSER_REQUIRED_MARKERS: Final[frozenset[str]] = frozenset(
    {
        "operator-login",
        "exam-publish",
        "candidate-otp-login",
        "exam-start",
        "answer-autosave",
        "offline-draft-recovery",
        "takeover-conflict",
        "submit",
        "answer-release",
        "session-invalidation",
    }
)

# Explicitly allow-list both the canonical producer spelling and the spelling
# emitted by existing capacity/browser operations.  ``unexpected`` (or any
# future field) is rejected until it is deliberately added here.
RAW_ALLOWED_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "schema_version",
        "kind",
        "status",
        "check",
        "gate",
        "runId",
        "run_id",
        "commit",
        "gitCommit",
        "git_commit",
        "project",
        "composeProject",
        "compose_project",
        "hostId",
        "host_id",
        "hostOS",
        "host_os",
        "architecture",
        "hostArch",
        "host_arch",
        "platform",
        "targetPlatform",
        "target_platform",
        "dockerPlatform",
        "docker_platform",
        "builtImageIdentitySha256",
        "built_image_identity_sha256",
        "builtImageIdentityDigest",
        "built_image_identity_digest",
        "startedAt",
        "started_at",
        "checkedAt",
        "checked_at",
        "timestamp",
        "createdAt",
        "created_at",
        "generatedAt",
        "generated_at",
        "migrationHead",
        "migration_head",
        "clients",
        "errors",
        "errorCount",
        "error_count",
        "startP95Ms",
        "saveP95Ms",
        "submitP95Ms",
        "start_p95_ms",
        "save_p95_ms",
        "submit_p95_ms",
        "maxDatabaseConnections",
        "max_database_connections",
        "workerHeartbeatAgeSeconds",
        "worker_heartbeat_age_seconds",
        "submittedCount",
        "submitted_count",
        "browser",
        "browserName",
        "browser_name",
        "url",
        "candidateUrl",
        "candidate_url",
        "operatorUrl",
        "operator_url",
        "browserE2eStatus",
        "browser_e2e_status",
        "browserReportPath",
        "browser_report_path",
        "browserReportSha256",
        "browser_report_sha256",
        "scenarioMarkers",
        "scenario_markers",
        "suiteMarkers",
        "suite_markers",
        "liveImageIds",
        "live_image_ids",
        "sourceMeasurementRunId",
        "source_measurement_run_id",
        "sourceReportPath",
        "source_report_path",
        "sourceReportSha256",
        "source_report_sha256",
        "recipientDomain",
        "recipient_domain",
        "sentAt",
        "sent_at",
        "smtpHost",
        "smtp_host",
        "messageId",
        "message_id",
        "restartedServices",
        "restarted_services",
        "recoveryAt",
        "recovery_at",
        "recoveredAt",
        "recovered_at",
        "healthHttpStatus",
        "health_http_status",
        "readyHttpStatus",
        "ready_http_status",
        "candidatePort",
        "candidate_port",
        "operatorPort",
        "operator_port",
        "candidateAdminHttpStatus",
        "candidate_admin_http_status",
        "operatorAdminHttpStatus",
        "operator_admin_http_status",
        "backendPort",
        "backend_port",
        "frontendPort",
        "frontend_port",
        "routeResults",
        "route_results",
        "mode",
        "restoreSmoke",
        "restore_smoke",
        "restoreProject",
        "restore_project",
        "sourceBackupSha256",
        "source_backup_sha256",
        "sourceBackupPath",
        "source_backup_path",
        "sourceBackupFiles",
        "source_backup_files",
        "sourceBackupDigests",
        "source_backup_digests",
        "secondCopyEvidencePath",
        "second_copy_evidence_path",
        "secondCopyEvidenceSha256",
        "second_copy_evidence_sha256",
        "secondCopyStorageEvidencePath",
        "second_copy_storage_evidence_path",
        "secondCopyStorageEvidenceSha256",
        "second_copy_storage_evidence_sha256",
        "secondCopySha256",
        "second_copy_sha256",
        "restoreMigrationHead",
        "restore_migration_head",
        "cleanupStatus",
        "cleanup_status",
        "tableCounts",
        "table_counts",
        "mediaFileCount",
        "media_file_count",
        "restoreImageIds",
        "restore_image_ids",
        "imageIds",
        "image_ids",
        "imageReferences",
        "image_references",
        "finalImages",
        "final_images",
        "runDirectory",
        "run_directory",
        "identity",
        "probe",
        "observations",
        "metrics",
        "thresholds",
        "failedChecks",
        "failed_checks",
        "commitState",
        "commit_state",
        "baseUrl",
        "base_url",
        "details",
        "evidence",
        "secrets",
        "warmup",
        "runtimeError",
        "runtime_error",
    }
)

RUN_ALLOWED_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "schema_version",
        "kind",
        "status",
        "runId",
        "run_id",
        "commit",
        "gitCommit",
        "git_commit",
        "project",
        "composeProject",
        "compose_project",
        "hostId",
        "host_id",
        "hostOS",
        "host_os",
        "architecture",
        "hostArch",
        "host_arch",
        "platform",
        "targetPlatform",
        "target_platform",
        "builtImageIdentitySha256",
        "built_image_identity_sha256",
        "startedAt",
        "started_at",
        "createdAt",
        "created_at",
        "secrets",
    }
)

LIVE_ALLOWED_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "schema_version",
        "kind",
        "status",
        "runId",
        "run_id",
        "project",
        "composeProject",
        "compose_project",
        "hostId",
        "host_id",
        "hostOS",
        "host_os",
        "architecture",
        "hostArch",
        "host_arch",
        "platform",
        "targetPlatform",
        "target_platform",
        "capturedAt",
        "captured_at",
        "images",
        "imageIds",
        "image_ids",
        "finalImages",
        "final_images",
        "Service",
        "service",
        "ContainerName",
        "container_name",
        "ID",
        "id",
        "Digest",
        "digest",
        "Image",
        "image",
    }
)

CANONICAL_ALLOWED_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "kind",
        "status",
        "runId",
        "commit",
        "project",
        "hostId",
        "hostOS",
        "architecture",
        "platform",
        "startedAt",
        "checkedAt",
        "release",
        "builtImageIdentitySha256",
        "liveImageIds",
        "runIdentity",
        "liveImageEvidence",
        "artifacts",
        "security",
        "gates",
        "secrets",
    }
)


class StagingAcceptanceError(ValueError):
    """A safe, non-sensitive staging evidence contract error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ReleaseIdentity:
    root: Path
    release: Path
    version: str
    commit: str
    host_id: str
    identity_path: Path
    identity_digest: str
    image_ids: dict[str, str]
    security_path: Path
    security_digest: str
    manifest_digest: str
    migration_head: str


@dataclass(frozen=True)
class RunIdentity:
    path: Path
    digest: str
    run_id: str
    commit: str
    project: str
    host_id: str
    started_at: datetime
    built_identity_digest: str
    host_os: str
    architecture: str
    platform: str


@dataclass(frozen=True)
class ArtifactIdentity:
    check: str
    path: Path
    digest: str
    checked_at: datetime


def _error(code: str) -> StagingAcceptanceError:
    return StagingAcceptanceError(code)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise _error("json_duplicate_key")
        output[key] = value
    return output


def _reject_constant(_value: str) -> Any:
    raise _error("json_non_finite_number")


def _strict_json_bytes(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _error("json_bom_not_allowed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _error("json_utf8_invalid") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except StagingAcceptanceError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _error("json_invalid") from exc


def _owner_only(path: Path, *, code: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise _error(f"{code}_unreadable") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise _error(f"{code}_symlink")
    if not stat.S_ISREG(metadata.st_mode):
        raise _error(f"{code}_not_regular")
    if metadata.st_uid != os.getuid():
        raise _error(f"{code}_owner_invalid")
    if metadata.st_mode & 0o077:
        raise _error(f"{code}_permissions_invalid")


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor or "/")
    for component in path.parts[1:]:
        current /= component
        try:
            if current.is_symlink():
                raise _error("path_symlink")
        except OSError as exc:
            raise _error("path_unreadable") from exc


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of an owner-only regular file."""

    try:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise _error("artifact_unreadable") from exc
    return digest.hexdigest()


def _read_checksums(path: Path, *, code: str) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    _owner_only(sidecar, code=f"{code}_checksum")
    try:
        text = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise _error(f"{code}_checksum_invalid") from exc
    if not text.endswith("\n"):
        raise _error(f"{code}_checksum_invalid")
    lines = text.splitlines()
    if len(lines) != 1:
        raise _error(f"{code}_checksum_invalid")
    match = re.fullmatch(r"([0-9a-fA-F]{64})  ([^/\\\r\n]+)", lines[0])
    if match is None or match.group(2) != path.name:
        raise _error(f"{code}_checksum_invalid")
    actual = sha256_file(path)
    if match.group(1).lower() != actual:
        raise _error(f"{code}_checksum_mismatch")
    return actual


def _read_json_file(
    path: Path, *, allowed: frozenset[str], code: str
) -> tuple[Any, str]:
    _owner_only(path, code=code)
    digest = _read_checksums(path, code=code)
    try:
        payload = _strict_json_bytes(path.read_bytes())
    except OSError as exc:
        raise _error(f"{code}_unreadable") from exc
    if not isinstance(payload, dict):
        raise _error(f"{code}_object_required")
    unknown = set(payload) - allowed
    if unknown:
        raise _error(f"{code}_unknown_field")
    return payload, digest


def _read_unchecksummed_json_file(
    path: Path, *, allowed: frozenset[str], code: str
) -> tuple[Any, str]:
    """Read release metadata covered by the bundle SHA256SUMS file.

    Release manifests are part of the release's top-level ``SHA256SUMS``
    inventory rather than carrying a sibling checksum.  Raw staging records
    never use this helper; they always require their own ``.sha256`` sidecar.
    """

    _owner_only(path, code=code)
    try:
        payload = _strict_json_bytes(path.read_bytes())
    except OSError as exc:
        raise _error(f"{code}_unreadable") from exc
    if not isinstance(payload, dict):
        raise _error(f"{code}_object_required")
    unknown = set(payload) - allowed
    if unknown:
        raise _error(f"{code}_unknown_field")
    return payload, sha256_file(path)


def _one(payload: Mapping[str, Any], *names: str, required: bool = True) -> Any:
    present = [name for name in names if name in payload]
    if len(present) > 1:
        raise _error("identity_duplicate_alias")
    if not present:
        if required:
            raise _error("identity_field_missing")
        return None
    return payload[present[0]]


def _string(
    payload: Mapping[str, Any], *names: str, required: bool = True
) -> str | None:
    value = _one(payload, *names, required=required)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise _error("identity_field_invalid")
    return value


def _timestamp(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{code}_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _error(f"{code}_invalid") from exc
    if parsed.tzinfo is None:
        raise _error(f"{code}_timezone_missing")
    return parsed.astimezone(UTC)


def _fresh(timestamp: datetime, *, code: str, maximum_age_seconds: int) -> None:
    now = datetime.now(UTC)
    if timestamp > now + timedelta(seconds=CLOCK_SKEW_SECONDS):
        raise _error(f"{code}_future")
    if now - timestamp > timedelta(seconds=maximum_age_seconds):
        raise _error(f"{code}_stale")


def _validate_identity_values(
    payload: Mapping[str, Any], *, code: str, expected: Mapping[str, str] | None = None
) -> dict[str, str]:
    schema = _one(payload, "schemaVersion", "schema_version")
    if isinstance(schema, bool) or schema != SCHEMA_VERSION:
        raise _error(f"{code}_schema_invalid")
    run_id = _string(payload, "runId", "run_id")
    commit = _string(payload, "commit", "gitCommit", "git_commit")
    project = _string(payload, "project", "composeProject", "compose_project")
    host_id = _string(payload, "hostId", "host_id")
    host_os = _string(payload, "hostOS", "host_os")
    architecture = _string(payload, "architecture", "hostArch", "host_arch")
    platform = _string(
        payload,
        "platform",
        "targetPlatform",
        "target_platform",
        "dockerPlatform",
        "docker_platform",
    )
    built_digest = _string(
        payload,
        "builtImageIdentitySha256",
        "built_image_identity_sha256",
        "builtImageIdentityDigest",
        "built_image_identity_digest",
    )
    if run_id is None or RUN_ID_RE.fullmatch(run_id) is None:
        raise _error(f"{code}_run_invalid")
    if commit is None or COMMIT_RE.fullmatch(commit) is None:
        raise _error(f"{code}_commit_invalid")
    if project is None or PROJECT_RE.fullmatch(project) is None:
        raise _error(f"{code}_project_invalid")
    if host_id is None or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:-]{1,127}", host_id
    ):
        raise _error(f"{code}_host_invalid")
    if host_os != "darwin" or architecture != "arm64" or platform != "linux/arm64":
        raise _error(f"{code}_platform_invalid")
    if built_digest is None or SHA256_RE.fullmatch(built_digest) is None:
        raise _error(f"{code}_image_identity_invalid")
    values = {
        "runId": run_id,
        "commit": commit.lower(),
        "project": project,
        "hostId": host_id,
        "hostOS": host_os,
        "architecture": architecture,
        "platform": platform,
        "builtImageIdentitySha256": built_digest.lower(),
    }
    if expected:
        for key, expected_value in expected.items():
            actual = values.get(key)
            if actual != expected_value:
                raise _error(f"{code}_{key[0].lower()}{key[1:]}_mismatch")
    return values


def _path_relative_to(path: Path, base: Path, *, code: str) -> str:
    try:
        relative = path.relative_to(base)
    except ValueError as exc:
        raise _error(f"{code}_outside_root") from exc
    value = relative.as_posix()
    if not value or value == "." or value.startswith("../") or "/../" in value:
        raise _error(f"{code}_path_invalid")
    return value


def _validate_release_path(release: Path, root: Path) -> tuple[Path, str]:
    _reject_symlink_components(root)
    _reject_symlink_components(release)
    try:
        root = root.resolve(strict=True)
        release = release.resolve(strict=True)
    except OSError as exc:
        raise _error("release_path_unreadable") from exc
    if not root.is_dir() or not release.is_dir():
        raise _error("release_path_missing")
    releases_root = root / "releases"
    if release.parent != releases_root:
        raise _error("release_path_not_installed")
    if release.name in {"", ".", ".."} or "/" in release.name:
        raise _error("release_version_invalid")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[.-][0-9A-Za-z.-]+)?", release.name):
        raise _error("release_version_invalid")
    try:
        root.lstat()
        release.lstat()
    except OSError as exc:
        raise _error("release_path_unreadable") from exc
    return release, release.name


def validate_release(release: Path, root: Path) -> ReleaseIdentity:
    """Validate the installed release and its sealed, identity-bound evidence."""

    release, version = _validate_release_path(release, root)
    manifest_path = release / "release-manifest.json"
    manifest, manifest_digest = _read_unchecksummed_json_file(
        manifest_path,
        allowed=frozenset(
            {
                "formatVersion",
                "format_version",
                "applicationVersion",
                "application_version",
                "gitCommit",
                "git_commit",
                "hostOS",
                "architecture",
                "platform",
                "targetPlatform",
                "migrationHead",
                "migration_head",
                "sealState",
                "sealedAt",
                "createdAt",
                "securityEvidence",
                "security_evidence",
                "builtImageIdentity",
                "built_image_identity",
                "imageDigests",
                "image_digests",
                "files",
                "imageTag",
                "baseImageReferences",
                "platformSupport",
            }
        ),
        code="release_manifest",
    )
    checksums_path = release / "SHA256SUMS"
    _owner_only(checksums_path, code="release_checksums")
    try:
        checksum_lines = checksums_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise _error("release_checksums_invalid") from exc
    manifest_rows = [
        line
        for line in checksum_lines
        if re.fullmatch(r"[0-9a-fA-F]{64}  release-manifest\.json", line)
    ]
    if len(manifest_rows) != 1 or not manifest_rows[0].startswith(manifest_digest):
        raise _error("release_manifest_checksum_mismatch")
    if _one(manifest, "formatVersion", "format_version") != 1:
        raise _error("release_manifest_schema_invalid")
    if _one(manifest, "applicationVersion", "application_version") != version:
        raise _error("release_manifest_version_mismatch")
    commit = _string(manifest, "gitCommit", "git_commit")
    if commit is None or COMMIT_RE.fullmatch(commit) is None:
        raise _error("release_manifest_commit_invalid")
    if (
        _one(manifest, "hostOS", required=False) != "darwin"
        or _one(manifest, "architecture", required=False) != "arm64"
        or _one(manifest, "platform", "targetPlatform", required=False) != "linux/arm64"
    ):
        raise _error("release_manifest_platform_invalid")
    if _one(manifest, "sealState", required=False) != "sealed":
        raise _error("release_not_sealed")
    migration_head = _string(manifest, "migrationHead", "migration_head", required=True)
    if migration_head is None:
        raise _error("release_manifest_migration_invalid")

    identity_path = release / "ops" / "release" / "built-image-identity.json"
    identity, identity_digest = _read_json_file(
        identity_path,
        allowed=frozenset(
            {
                "schemaVersion",
                "status",
                "gitCommit",
                "applicationVersion",
                "platform",
                "images",
            }
        ),
        code="built_identity",
    )
    if identity.get("schemaVersion") != 1 or identity.get("status") != "passed":
        raise _error("built_identity_status_invalid")
    if (
        identity.get("gitCommit") != commit.lower()
        or identity.get("platform") != "linux/arm64"
    ):
        raise _error("built_identity_release_mismatch")
    images = identity.get("images")
    if not isinstance(images, dict) or set(images) != set(IMAGE_NAMES):
        raise _error("built_identity_images_invalid")
    image_ids: dict[str, str] = {}
    references: dict[str, str] = {}
    for image_name in IMAGE_NAMES:
        row = images.get(image_name)
        if not isinstance(row, dict):
            raise _error("built_identity_image_invalid")
        reference = row.get("reference")
        image_id = row.get("id")
        if (
            not isinstance(reference, str)
            or not reference
            or not isinstance(image_id, str)
            or IMAGE_ID_RE.fullmatch(image_id) is None
            or row.get("os") != "linux"
            or row.get("architecture") != "arm64"
            or not reference.endswith(f":{commit.lower()}")
        ):
            raise _error("built_identity_image_invalid")
        image_ids[image_name] = image_id.lower()
        references[image_name] = reference
    identity_meta = _one(manifest, "builtImageIdentity", "built_image_identity")
    if not isinstance(identity_meta, dict):
        raise _error("release_manifest_identity_invalid")
    if identity_meta.get("path") != "ops/release/built-image-identity.json":
        raise _error("release_manifest_identity_path_invalid")
    if identity_meta.get("sha256", "").lower() != identity_digest:
        raise _error("release_manifest_identity_digest_mismatch")
    manifest_images = _one(manifest, "imageDigests", "image_digests", required=False)
    if not isinstance(manifest_images, dict):
        raise _error("release_manifest_images_invalid")
    if any(manifest_images.get(name) != references[name] for name in IMAGE_NAMES):
        raise _error("release_manifest_images_mismatch")

    security_path = release / "release-evidence" / "security-scan.json"
    security, security_digest = _read_json_file(
        security_path,
        allowed=frozenset(
            {
                "schemaVersion",
                "schema_version",
                "status",
                "kind",
                "checkedAt",
                "checked_at",
                "sealedAt",
                "sealState",
                "builtImageIdentitySha256",
                "imageIdentitySha256",
                "imagePlatform",
                "finalImagePlatform",
                "targetPlatform",
                "hostOS",
                "architecture",
                "scannerMode",
                "scannerEvidenceSha256",
                "imageRecordSha256",
                "imageIds",
                "imageReferences",
                "binding_errors",
                "security_errors",
                "blocking_keys",
                "findings",
                "finding_count",
                "policy",
                "finalImageRecord",
                "secrets",
            }
        ),
        code="security_evidence",
    )
    if security.get("status") != "passed" or security.get("sealState") != "sealed":
        raise _error("security_evidence_not_sealed")
    if security.get("scannerMode") != "identity-bound":
        raise _error("security_evidence_binding_invalid")
    if security.get("builtImageIdentitySha256") != identity_digest:
        raise _error("security_evidence_identity_mismatch")
    if security.get("imagePlatform", security.get("targetPlatform")) != "linux/arm64":
        raise _error("security_evidence_platform_invalid")
    if security.get("binding_errors") != [] or security.get("security_errors") != []:
        raise _error("security_evidence_errors_present")
    security_meta = _one(manifest, "securityEvidence", "security_evidence")
    if (
        not isinstance(security_meta, dict)
        or security_meta.get("sha256", "").lower() != security_digest
    ):
        raise _error("release_manifest_security_digest_mismatch")
    return ReleaseIdentity(
        root=root.resolve(),
        release=release,
        version=version,
        commit=commit.lower(),
        host_id=str(_one(manifest, "hostId", required=False) or ""),
        identity_path=identity_path,
        identity_digest=identity_digest,
        image_ids=image_ids,
        security_path=security_path,
        security_digest=security_digest,
        manifest_digest=manifest_digest,
        migration_head=migration_head,
    )


def validate_run_identity(
    path: Path,
    *,
    release: ReleaseIdentity,
    project: str | None = None,
    expected_host_id: str | None = None,
    maximum_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> RunIdentity:
    payload, digest = _read_json_file(
        path, allowed=RUN_ALLOWED_FIELDS, code="run_identity"
    )
    if payload.get("kind") != RUN_KIND or payload.get("status") not in {
        "started",
        "running",
        "active",
    }:
        raise _error("run_identity_status_invalid")
    values = _validate_identity_values(payload, code="run_identity")
    if (
        values["commit"] != release.commit
        or values["builtImageIdentitySha256"] != release.identity_digest
    ):
        raise _error("run_identity_release_mismatch")
    if project is not None and values["project"] != project:
        raise _error("run_identity_project_mismatch")
    if expected_host_id is not None and values["hostId"] != expected_host_id:
        raise _error("run_identity_host_mismatch")
    started_value = _one(payload, "startedAt", "started_at", "createdAt", "created_at")
    started_at = _timestamp(started_value, code="run_identity_started_at")
    _fresh(started_at, code="run_identity", maximum_age_seconds=maximum_age_seconds)
    return RunIdentity(
        path=path,
        digest=digest,
        run_id=values["runId"],
        commit=values["commit"],
        project=values["project"],
        host_id=values["hostId"],
        started_at=started_at,
        built_identity_digest=values["builtImageIdentitySha256"],
        host_os=values["hostOS"],
        architecture=values["architecture"],
        platform=values["platform"],
    )


def _expected_fields(run: RunIdentity) -> dict[str, str]:
    return {
        "runId": run.run_id,
        "commit": run.commit,
        "project": run.project,
        "hostId": run.host_id,
        "hostOS": run.host_os,
        "architecture": run.architecture,
        "platform": run.platform,
        "builtImageIdentitySha256": run.built_identity_digest,
    }


BACKUP_REQUIRED_FILES: Final[frozenset[str]] = frozenset(
    {"database.dump", "learning_media.tar.gz", "manifest.json", "SHA256SUMS", "SUCCESS"}
)
BACKUP_CHECKSUM_FILES: Final[frozenset[str]] = frozenset(
    {"database.dump", "learning_media.tar.gz", "manifest.json"}
)
SECOND_COPY_ALLOWED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "schemaVersion",
        "kind",
        "backup_id",
        "backupId",
        "checked_at",
        "checkedAt",
        "status",
        "artifact_id",
        "artifactId",
        "destination",
        "pruned_expired",
        "prunedExpired",
        "error_type",
        "errorType",
        "secrets",
    }
)
SECOND_COPY_STORAGE_ALLOWED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schemaVersion",
        "schema_version",
        "kind",
        "hostId",
        "host_id",
        "status",
        "path",
        "mountPoint",
        "mount_point",
        "mounted",
        "encrypted",
        "writable",
        "deviceId",
        "device_id",
        "wholeDeviceId",
        "whole_device_id",
        "formalWholeDeviceId",
        "formal_whole_device_id",
        "liveDevice",
        "live_device",
        "distinctPhysicalDevice",
        "distinct_physical_device",
        "markerPresent",
        "marker_present",
        "checkedAt",
        "checked_at",
        "secrets",
    }
)


def _validate_backup_bundle(
    bundle: Path,
    *,
    source_digest: str,
    source_files: list[Any],
    source_digests: Mapping[str, Any],
    expected_migration_head: str | None,
    expected_table_counts: Mapping[str, Any] | None,
    expected_media_file_count: int | None,
) -> None:
    _reject_symlink_components(bundle)
    try:
        metadata = bundle.lstat()
    except OSError as exc:
        raise _error("backup_restore_source_unreadable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise _error("backup_restore_source_not_directory")
    try:
        names = {entry.name for entry in bundle.iterdir()}
    except OSError as exc:
        raise _error("backup_restore_source_unreadable") from exc
    if names != BACKUP_REQUIRED_FILES:
        raise _error("backup_restore_source_files_invalid")
    if (
        any(not isinstance(value, str) for value in source_files)
        or set(source_files) != BACKUP_REQUIRED_FILES
    ):
        raise _error("backup_restore_source_files_invalid")
    if (
        any(not isinstance(key, str) for key in source_digests)
        or set(source_digests) != BACKUP_CHECKSUM_FILES
        or any(
            not isinstance(value, str) or SHA256_RE.fullmatch(value) is None
            for value in source_digests.values()
        )
    ):
        raise _error("backup_restore_source_digests_invalid")
    for filename in BACKUP_REQUIRED_FILES:
        path = bundle / filename
        try:
            item = path.lstat()
        except OSError as exc:
            raise _error("backup_restore_source_unreadable") from exc
        if stat.S_ISLNK(item.st_mode) or not stat.S_ISREG(item.st_mode):
            raise _error("backup_restore_source_files_invalid")
    try:
        checksum_text = (bundle / "SHA256SUMS").read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise _error("backup_restore_source_checksums_invalid") from exc
    if sha256_file(bundle / "SHA256SUMS") != source_digest.lower():
        raise _error("backup_restore_source_digest_mismatch")
    if not checksum_text.endswith("\n"):
        raise _error("backup_restore_source_checksums_invalid")
    checksum_rows: dict[str, str] = {}
    for line in checksum_text.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})  ([^/\\\r\n]+)", line)
        if match is None or match.group(2) in checksum_rows:
            raise _error("backup_restore_source_checksums_invalid")
        checksum_rows[match.group(2)] = match.group(1).lower()
    if set(checksum_rows) != BACKUP_CHECKSUM_FILES:
        raise _error("backup_restore_source_checksums_invalid")
    for filename, digest in checksum_rows.items():
        actual = sha256_file(bundle / filename)
        if actual != digest or source_digests.get(filename, "").lower() != actual:
            raise _error("backup_restore_source_digest_mismatch")
    try:
        if (bundle / "SUCCESS").read_text(encoding="utf-8") != "ok\n":
            raise _error("backup_restore_source_success_invalid")
        manifest_payload = _strict_json_bytes((bundle / "manifest.json").read_bytes())
    except OSError as exc:
        raise _error("backup_restore_source_manifest_invalid") from exc
    if not isinstance(manifest_payload, dict):
        raise _error("backup_restore_source_manifest_invalid")
    manifest_migration = _string(
        manifest_payload, "migration_head", "migrationHead", required=True
    )
    if (
        expected_migration_head is not None
        and manifest_migration != expected_migration_head
    ):
        raise _error("backup_restore_migration_mismatch")
    manifest_counts = _one(
        manifest_payload, "table_counts", "tableCounts", required=True
    )
    manifest_media = _one(
        manifest_payload, "media_file_count", "mediaFileCount", required=True
    )
    if expected_table_counts is not None and manifest_counts != expected_table_counts:
        raise _error("backup_restore_table_counts_mismatch")
    if (
        expected_media_file_count is not None
        and manifest_media != expected_media_file_count
    ):
        raise _error("backup_restore_media_count_mismatch")


def _validate_second_copy_evidence(
    path: Path,
    *,
    backup_id: str,
    expected_digest: str,
) -> None:
    payload, digest = _read_json_file(
        path, allowed=SECOND_COPY_ALLOWED_FIELDS, code="backup_restore_second_copy"
    )
    if digest != expected_digest.lower():
        raise _error("backup_restore_second_copy_digest_mismatch")
    if payload.get("status") != "passed" or payload.get("kind") != "second-copy-sync":
        raise _error("backup_restore_second_copy_status_invalid")
    artifact_id = _string(payload, "artifact_id", "artifactId", required=True)
    declared_backup_id = _string(payload, "backup_id", "backupId", required=True)
    if artifact_id != backup_id or declared_backup_id != backup_id:
        raise _error("backup_restore_second_copy_identity_mismatch")
    if payload.get("error_type") is not None or payload.get("errorType") is not None:
        raise _error("backup_restore_second_copy_status_invalid")


def _validate_second_copy_storage_evidence(path: Path, *, expected_digest: str) -> None:
    payload, digest = _read_json_file(
        path,
        allowed=SECOND_COPY_STORAGE_ALLOWED_FIELDS,
        code="backup_restore_second_copy_storage",
    )
    if digest != expected_digest.lower():
        raise _error("backup_restore_second_copy_storage_digest_mismatch")
    if payload.get("status") != "passed":
        raise _error("backup_restore_second_copy_storage_status_invalid")
    for name in ("mounted", "encrypted", "writable"):
        if payload.get(name) is not True:
            raise _error("backup_restore_second_copy_storage_status_invalid")
    distinct = payload.get(
        "distinctPhysicalDevice", payload.get("distinct_physical_device")
    )
    if distinct is not True:
        raise _error("backup_restore_second_copy_storage_status_invalid")
    device = _string(payload, "deviceId", "device_id", required=True)
    whole = _string(payload, "wholeDeviceId", "whole_device_id", required=True)
    formal_whole = _string(
        payload, "formalWholeDeviceId", "formal_whole_device_id", required=True
    )
    if not device or not whole or not formal_whole or whole == formal_whole:
        raise _error("backup_restore_second_copy_storage_status_invalid")


def _validate_backup_restore(
    payload: Mapping[str, Any],
    *,
    path: Path,
    run: RunIdentity,
    root: Path | None,
    expected_migration_head: str | None,
    expected_image_ids: Mapping[str, str] | None,
) -> None:
    mode = _string(payload, "mode", required=False)
    restore_project = _string(
        payload, "restoreProject", "restore_project", required=False
    )
    backup_digest = _string(
        payload, "sourceBackupSha256", "source_backup_sha256", required=False
    )
    backup_path_value = _string(
        payload, "sourceBackupPath", "source_backup_path", required=False
    )
    backup_files = _one(
        payload, "sourceBackupFiles", "source_backup_files", required=False
    )
    backup_digests = _one(
        payload, "sourceBackupDigests", "source_backup_digests", required=False
    )
    second_copy_evidence_path = _string(
        payload,
        "secondCopyEvidencePath",
        "second_copy_evidence_path",
        required=False,
    )
    second_copy_evidence_digest = _string(
        payload,
        "secondCopyEvidenceSha256",
        "second_copy_evidence_sha256",
        required=False,
    )
    second_copy_storage_path = _string(
        payload,
        "secondCopyStorageEvidencePath",
        "second_copy_storage_evidence_path",
        required=False,
    )
    second_copy_storage_digest = _string(
        payload,
        "secondCopyStorageEvidenceSha256",
        "second_copy_storage_evidence_sha256",
        required=False,
    )
    second_copy_digest = _string(
        payload, "secondCopySha256", "second_copy_sha256", required=False
    )
    migration_head = _string(
        payload, "restoreMigrationHead", "restore_migration_head", required=False
    )
    cleanup_status = _string(payload, "cleanupStatus", "cleanup_status", required=False)
    table_counts = _one(payload, "tableCounts", "table_counts", required=False)
    media_file_count = _one(
        payload, "mediaFileCount", "media_file_count", required=False
    )
    restore_image_ids = _one(
        payload, "restoreImageIds", "restore_image_ids", required=False
    )
    nested = _one(payload, "restoreSmoke", "restore_smoke", required=False)
    if isinstance(nested, dict):
        mode = mode or _string(nested, "mode", required=False)
        restore_project = restore_project or _string(
            nested, "restoreProject", "restore_project", required=False
        )
        backup_digest = backup_digest or _string(
            nested, "sourceBackupSha256", "source_backup_sha256", required=False
        )
        backup_path_value = backup_path_value or _string(
            nested, "sourceBackupPath", "source_backup_path", required=False
        )
        backup_files = backup_files or _one(
            nested, "sourceBackupFiles", "source_backup_files", required=False
        )
        backup_digests = backup_digests or _one(
            nested, "sourceBackupDigests", "source_backup_digests", required=False
        )
        second_copy_evidence_path = second_copy_evidence_path or _string(
            nested,
            "secondCopyEvidencePath",
            "second_copy_evidence_path",
            required=False,
        )
        second_copy_evidence_digest = second_copy_evidence_digest or _string(
            nested,
            "secondCopyEvidenceSha256",
            "second_copy_evidence_sha256",
            required=False,
        )
        second_copy_storage_path = second_copy_storage_path or _string(
            nested,
            "secondCopyStorageEvidencePath",
            "second_copy_storage_evidence_path",
            required=False,
        )
        second_copy_storage_digest = second_copy_storage_digest or _string(
            nested,
            "secondCopyStorageEvidenceSha256",
            "second_copy_storage_evidence_sha256",
            required=False,
        )
        second_copy_digest = second_copy_digest or _string(
            nested, "secondCopySha256", "second_copy_sha256", required=False
        )
        migration_head = migration_head or _string(
            nested, "restoreMigrationHead", "restore_migration_head", required=False
        )
        cleanup_status = cleanup_status or _string(
            nested, "cleanupStatus", "cleanup_status", required=False
        )
    if mode not in {"restore-smoke", "disposable-restore-smoke"}:
        raise _error("backup_restore_mode_invalid")
    if restore_project is None or RESTORE_PROJECT_RE.fullmatch(restore_project) is None:
        raise _error("backup_restore_project_invalid")
    if backup_digest is None or SHA256_RE.fullmatch(backup_digest) is None:
        raise _error("backup_restore_backup_digest_invalid")
    if (
        second_copy_evidence_path is None
        or second_copy_evidence_digest is None
        or SHA256_RE.fullmatch(second_copy_evidence_digest) is None
        or second_copy_storage_path is None
        or second_copy_storage_digest is None
        or SHA256_RE.fullmatch(second_copy_storage_digest) is None
        or second_copy_digest is None
        or SHA256_RE.fullmatch(second_copy_digest) is None
        or second_copy_digest.lower() != backup_digest.lower()
    ):
        raise _error("backup_restore_second_copy_binding_invalid")
    if (
        not migration_head
        or (
            expected_migration_head is not None
            and migration_head != expected_migration_head
        )
        or cleanup_status != "passed"
    ):
        raise _error("backup_restore_contract_invalid")
    if root is None or backup_path_value is None:
        raise _error("backup_restore_source_path_invalid")
    if (
        backup_path_value.startswith("/")
        or ".." in Path(backup_path_value).parts
        or not isinstance(backup_files, list)
        or not isinstance(backup_digests, dict)
    ):
        raise _error("backup_restore_source_path_invalid")
    source_path = root / backup_path_value
    _reject_symlink_components(source_path)
    try:
        source_path.resolve().relative_to(root.resolve())
        # The accepted bundle may be moved from the live run directory to a
        # durable evidence directory during ``Down``.  Bind the source to the
        # protected staging subtree and its run-scoped restore-smoke prefix,
        # rather than deriving a now-stale path from ``run.path``.
        staging_root = root / "staging"
        source_path.resolve().relative_to(staging_root.resolve())
    except ValueError as exc:
        raise _error("backup_restore_source_path_invalid") from exc
    run_backup_prefix = f"restore-smoke-{run.run_id}"
    try:
        staging_relative = source_path.resolve().relative_to(staging_root.resolve())
    except ValueError as exc:
        raise _error("backup_restore_source_path_invalid") from exc
    if run_backup_prefix not in staging_relative.parts:
        raise _error("backup_restore_source_path_invalid")
    _validate_backup_bundle(
        source_path,
        source_digest=backup_digest,
        source_files=backup_files,
        source_digests=backup_digests,
        expected_migration_head=expected_migration_head,
        expected_table_counts=table_counts if isinstance(table_counts, dict) else None,
        expected_media_file_count=media_file_count
        if isinstance(media_file_count, int) and not isinstance(media_file_count, bool)
        else None,
    )
    for relative, expected_code in (
        (second_copy_evidence_path, "backup_restore_second_copy_path_invalid"),
        (second_copy_storage_path, "backup_restore_second_copy_storage_path_invalid"),
    ):
        if relative.startswith("/") or ".." in Path(relative).parts or not relative:
            raise _error(expected_code)
    second_copy_evidence = root / second_copy_evidence_path
    second_copy_storage = root / second_copy_storage_path
    _reject_symlink_components(second_copy_evidence)
    _reject_symlink_components(second_copy_storage)
    try:
        second_copy_evidence.resolve().relative_to(root.resolve())
        second_copy_storage.resolve().relative_to(root.resolve())
        source_parent = source_path.resolve().parent
        if second_copy_evidence.resolve() != source_parent / (
            source_path.name + ".second-copy.json"
        ):
            raise _error("backup_restore_second_copy_path_invalid")
        if (
            second_copy_storage.resolve()
            != (root / "evidence" / "second-copy-storage.json").resolve()
        ):
            raise _error("backup_restore_second_copy_storage_path_invalid")
    except ValueError as exc:
        raise _error("backup_restore_second_copy_path_invalid") from exc
    _validate_second_copy_evidence(
        second_copy_evidence,
        backup_id=source_path.name,
        expected_digest=second_copy_evidence_digest,
    )
    _validate_second_copy_storage_evidence(
        second_copy_storage, expected_digest=second_copy_storage_digest
    )
    if (
        not isinstance(table_counts, dict)
        or not table_counts
        or any(
            not isinstance(key, str)
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for key, value in table_counts.items()
        )
    ):
        raise _error("backup_restore_table_counts_invalid")
    if (
        isinstance(media_file_count, bool)
        or not isinstance(media_file_count, int)
        or media_file_count < 0
    ):
        raise _error("backup_restore_media_count_invalid")
    if not isinstance(restore_image_ids, dict) or set(restore_image_ids) != {
        "db",
        "backend",
        "frontend",
        "gateway",
    }:
        raise _error("backup_restore_images_invalid")
    if any(
        not isinstance(value, str) or IMAGE_ID_RE.fullmatch(value) is None
        for value in restore_image_ids.values()
    ):
        raise _error("backup_restore_images_invalid")
    if expected_image_ids is not None and {
        key: str(value).lower() for key, value in restore_image_ids.items()
    } != {key: value.lower() for key, value in expected_image_ids.items()}:
        raise _error("backup_restore_images_mismatch")


def _validate_capacity_report(payload: Mapping[str, Any]) -> None:
    """Validate the real nested report emitted by ``capacity_gate``.

    A capacity pass is meaningful only when the producer recorded every
    measured metric and its threshold evaluation.  Do not accept a flat
    ``clients=100, errors=[]`` object: that shape is trivial to hand-write
    and omits submission, latency, database, and worker observations.
    """

    failed_checks = _one(payload, "failed_checks", "failedChecks")
    if failed_checks != []:
        raise _error("capacity_gate_not_passed")
    source_run_id = _string(
        payload, "sourceMeasurementRunId", "source_measurement_run_id"
    )
    source_digest = _string(payload, "sourceReportSha256", "source_report_sha256")
    if source_run_id is None or RUN_ID_RE.fullmatch(source_run_id) is None:
        raise _error("capacity_source_run_invalid")
    if source_digest is None or SHA256_RE.fullmatch(source_digest) is None:
        raise _error("capacity_source_report_invalid")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise _error("capacity_metrics_missing")
    unknown_metrics = set(metrics) - CAPACITY_METRIC_FIELDS
    if unknown_metrics:
        raise _error("capacity_metrics_unknown_field")
    nested_run_id = _one(metrics, "run_id", "runId", required=False)
    if nested_run_id is not None and nested_run_id != source_run_id:
        raise _error("capacity_metric_run_mismatch")

    def metric(*names: str) -> int | float:
        value = _one(metrics, *names)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise _error("capacity_metric_invalid")
        return value

    clients = metric("clients")
    submitted_count = metric("submitted_count", "submittedCount")
    errors = _one(metrics, "errors")
    if (
        not isinstance(clients, int)
        or clients != int(CAPACITY_THRESHOLDS["clients"])
        or not isinstance(submitted_count, int)
        or submitted_count != int(CAPACITY_THRESHOLDS["clients"])
        or not isinstance(errors, list)
        or errors != []
    ):
        raise _error("capacity_gate_not_passed")

    measured_thresholds = {
        "start_p95_ms": (
            ("start_p95_ms", "startP95Ms"),
            CAPACITY_THRESHOLDS["start_p95_ms"],
        ),
        "save_p95_ms": (
            ("save_p95_ms", "saveP95Ms"),
            CAPACITY_THRESHOLDS["save_p95_ms"],
        ),
        "submit_p95_ms": (
            ("submit_p95_ms", "submitP95Ms"),
            CAPACITY_THRESHOLDS["submit_p95_ms"],
        ),
        "max_database_connections": (
            ("max_database_connections", "maxDatabaseConnections"),
            CAPACITY_THRESHOLDS["max_database_connections"],
        ),
        "worker_heartbeat_age_seconds": (
            ("worker_heartbeat_age_seconds", "workerHeartbeatAgeSeconds"),
            CAPACITY_THRESHOLDS["worker_heartbeat_age_seconds"],
        ),
    }
    for names, threshold in measured_thresholds.values():
        if metric(*names) > threshold:
            raise _error("capacity_gate_not_passed")

    threshold_report = payload.get("thresholds")
    if not isinstance(threshold_report, dict):
        raise _error("capacity_thresholds_missing")
    threshold_aliases = {
        "clients": ("clients",),
        "error_count": ("error_count", "errorCount"),
        "start_p95_ms": ("start_p95_ms", "startP95Ms"),
        "save_p95_ms": ("save_p95_ms", "saveP95Ms"),
        "submit_p95_ms": ("submit_p95_ms", "submitP95Ms"),
        "max_database_connections": (
            "max_database_connections",
            "maxDatabaseConnections",
        ),
        "worker_heartbeat_age_seconds": (
            "worker_heartbeat_age_seconds",
            "workerHeartbeatAgeSeconds",
        ),
    }
    allowed_thresholds = {
        alias for aliases in threshold_aliases.values() for alias in aliases
    }
    if set(threshold_report) - allowed_thresholds:
        raise _error("capacity_thresholds_unknown_field")
    for name, aliases in threshold_aliases.items():
        value = _one(threshold_report, *aliases)
        expected = CAPACITY_THRESHOLDS[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value != expected
        ):
            raise _error("capacity_thresholds_invalid")


def _validate_browser_report(
    payload: Mapping[str, Any], *, path: Path, run: RunIdentity
) -> None:
    """Require a checksummed, identity-bound full business E2E report.

    A two-page HTTP smoke is intentionally insufficient.  The report must be
    a separate artifact, carry the same run/image identity, and enumerate the
    complete formal-exam scenario markers before browser evidence can pass.
    """

    report_relative = _string(payload, "browserReportPath", "browser_report_path")
    report_digest = _string(payload, "browserReportSha256", "browser_report_sha256")
    if (
        report_relative is None
        or report_digest is None
        or SHA256_RE.fullmatch(report_digest) is None
    ):
        raise _error("browser_report_reference_invalid")
    report_path = path.parent / report_relative
    if report_relative.startswith("/") or ".." in Path(report_relative).parts:
        raise _error("browser_report_path_invalid")
    _reject_symlink_components(report_path)
    try:
        if report_path.resolve() == path.resolve():
            raise _error("browser_report_path_invalid")
        if report_path.resolve().relative_to(path.parent.resolve()) == Path("."):
            raise _error("browser_report_path_invalid")
    except ValueError as exc:
        raise _error("browser_report_path_invalid") from exc
    report, actual_digest = _read_json_file(
        report_path,
        allowed=BROWSER_REPORT_ALLOWED_FIELDS,
        code="browser_report",
    )
    if actual_digest != report_digest.lower():
        raise _error("browser_report_digest_mismatch")
    if report.get("kind") != "browser-e2e-report" or report.get("status") != "passed":
        raise _error("browser_report_status_invalid")
    if _one(report, "schemaVersion", "schema_version") != SCHEMA_VERSION:
        raise _error("browser_report_schema_invalid")
    _validate_identity_values(
        report,
        code="browser_report",
        expected=_expected_fields(run),
    )
    browser_status = _string(
        payload, "browserE2eStatus", "browser_e2e_status", required=True
    )
    if browser_status != "passed":
        raise _error("browser_report_status_invalid")
    candidate_url = _string(payload, "candidateUrl", "candidate_url", required=True)
    operator_url = _string(payload, "operatorUrl", "operator_url", required=True)
    report_candidate = _string(report, "candidateUrl", "candidate_url", required=True)
    report_operator = _string(report, "operatorUrl", "operator_url", required=True)
    if candidate_url != report_candidate or operator_url != report_operator:
        raise _error("browser_report_url_mismatch")
    if (
        candidate_url != "http://127.0.0.1:18080"
        or operator_url != "http://127.0.0.1:18081"
    ):
        raise _error("browser_report_url_invalid")
    markers = _one(
        report, "scenarioMarkers", "scenario_markers", "suiteMarkers", "suite_markers"
    )
    if (
        not isinstance(markers, list)
        or any(not isinstance(value, str) for value in markers)
        or set(markers) != BROWSER_REQUIRED_MARKERS
    ):
        raise _error("browser_report_markers_invalid")
    raw_markers = _one(
        payload, "scenarioMarkers", "scenario_markers", "suiteMarkers", "suite_markers"
    )
    if raw_markers != markers:
        raise _error("browser_report_markers_mismatch")
    report_live = _one(report, "liveImageIds", "live_image_ids", required=True)
    raw_live = _one(payload, "liveImageIds", "live_image_ids", required=True)
    if (
        not isinstance(report_live, dict)
        or not isinstance(raw_live, dict)
        or report_live != raw_live
    ):
        raise _error("browser_report_images_mismatch")
    checked_value = _one(report, "checkedAt", "checked_at")
    checked_at = _timestamp(checked_value, code="browser_report_checked_at")
    if checked_at < run.started_at:
        raise _error("browser_report_stale_run")
    _fresh(
        checked_at, code="browser_report", maximum_age_seconds=DEFAULT_MAX_AGE_SECONDS
    )


def _validate_capacity_source(
    payload: Mapping[str, Any], *, path: Path, run: RunIdentity
) -> None:
    """Bind the raw capacity envelope to a complete source report.

    A checksum alone proves only that a report was copied unchanged.  The
    source must also be a passed schema-2 producer report whose run, release,
    project, host, measured metrics, and live image IDs agree with the raw
    envelope that references it.
    """

    report_relative = _string(payload, "sourceReportPath", "source_report_path")
    report_digest = _string(payload, "sourceReportSha256", "source_report_sha256")
    if report_relative is None or report_digest is None:
        raise _error("capacity_source_report_invalid")
    if report_relative.startswith("/") or ".." in Path(report_relative).parts:
        raise _error("capacity_source_report_path_invalid")
    report_path = path.parent / report_relative
    _reject_symlink_components(report_path)
    try:
        if report_path.resolve() == path.resolve():
            raise _error("capacity_source_report_path_invalid")
        report_path.resolve().relative_to(path.parent.resolve())
    except ValueError as exc:
        raise _error("capacity_source_report_path_invalid") from exc
    report, actual = _read_json_file(
        report_path,
        allowed=CAPACITY_SOURCE_ALLOWED_FIELDS,
        code="capacity_source_report",
    )
    if actual != report_digest.lower():
        raise _error("capacity_source_report_digest_mismatch")
    report_kind = report.get("kind")
    if (
        report.get("schemaVersion", report.get("schema_version")) != SCHEMA_VERSION
        or (report_kind is not None and report_kind != "capacity-gate-report")
        or report.get("status") != "passed"
        or report.get("runtime_error") is not None
    ):
        raise _error("capacity_source_report_status_invalid")
    failed_checks = _one(report, "failed_checks", "failedChecks")
    if failed_checks != []:
        raise _error("capacity_source_report_status_invalid")
    generated_at = _one(
        report,
        "generatedAt",
        "generated_at",
        "checkedAt",
        "checked_at",
        required=True,
    )
    generated_timestamp = _timestamp(
        generated_at, code="capacity_source_report_timestamp"
    )
    if generated_timestamp < run.started_at:
        raise _error("capacity_source_report_stale_run")
    _fresh(
        generated_timestamp,
        code="capacity_source_report",
        maximum_age_seconds=DEFAULT_MAX_AGE_SECONDS,
    )
    identity = report.get("identity")
    metrics = report.get("metrics")
    if not isinstance(identity, dict) or not isinstance(metrics, dict):
        raise _error("capacity_source_report_shape_invalid")
    unknown_identity = set(identity) - CAPACITY_SOURCE_IDENTITY_FIELDS
    if unknown_identity:
        raise _error("capacity_source_report_identity_unknown_field")
    unknown_metrics = set(metrics) - CAPACITY_METRIC_FIELDS
    if unknown_metrics:
        raise _error("capacity_source_report_metrics_unknown_field")

    source_run_id = _string(identity, "run_id", "runId", required=True)
    raw_source_run_id = _string(
        payload, "sourceMeasurementRunId", "source_measurement_run_id", required=True
    )
    if source_run_id != raw_source_run_id:
        raise _error("capacity_source_report_run_mismatch")
    source_commit = _string(
        identity, "commit", "gitCommit", "git_commit", required=True
    )
    source_project = _string(
        identity,
        "project",
        "composeProject",
        "compose_project",
        required=True,
    )
    source_host_os = _string(identity, "hostOS", "host_os", required=True)
    source_architecture = _string(
        identity, "architecture", "hostArch", "host_arch", required=True
    )
    source_commit_state = _string(
        identity, "commitState", "commit_state", required=True
    )
    source_run_directory = _string(
        identity, "runDirectory", "run_directory", required=True
    )
    source_docker_platform = _string(
        identity, "dockerPlatform", "docker_platform", required=True
    )
    raw_commit = _string(payload, "commit", "gitCommit", "git_commit", required=True)
    raw_project = _string(
        payload, "project", "composeProject", "compose_project", required=True
    )
    raw_host_os = _string(payload, "hostOS", "host_os", required=True)
    raw_architecture = _string(
        payload, "architecture", "hostArch", "host_arch", required=True
    )
    details = payload.get("details")
    if not isinstance(details, dict) or set(details) - {
        "capacityProject",
        "capacity_project",
    }:
        raise _error("capacity_source_report_project_invalid")
    capacity_project = _string(
        details, "capacityProject", "capacity_project", required=True
    )
    if (
        source_commit != raw_commit
        or source_host_os != raw_host_os
        or source_architecture != raw_architecture
        or source_commit != run.commit
        or raw_project != run.project
        or source_host_os != run.host_os
        or source_architecture != run.architecture
        or source_commit_state != "clean"
        or source_run_directory != source_run_id
        or source_docker_platform != run.platform
        or capacity_project != source_project
        or capacity_project is None
        or CAPACITY_PROJECT_RE.fullmatch(capacity_project) is None
    ):
        raise _error("capacity_source_report_identity_mismatch")

    duplicated_identity_fields = {
        "commit": source_commit,
        "commit_state": source_commit_state,
        "host_os": source_host_os,
        "host_arch": source_architecture,
        "run_directory": source_run_directory,
        "compose_project": source_project,
        "docker_platform": source_docker_platform,
    }
    for field, expected_value in duplicated_identity_fields.items():
        if report.get(field) != expected_value:
            raise _error("capacity_source_report_identity_mismatch")
    if report.get("base_url") != "http://nginx":
        raise _error("capacity_source_report_identity_mismatch")

    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, dict):
        raise _error("capacity_metrics_missing")
    source_metrics_run_id = _string(metrics, "run_id", "runId", required=True)
    if source_metrics_run_id != source_run_id:
        raise _error("capacity_source_report_run_mismatch")
    raw_metrics_run_id = _string(raw_metrics, "run_id", "runId", required=True)
    if raw_metrics_run_id != source_run_id:
        raise _error("capacity_source_report_run_mismatch")
    exam_id = _one(metrics, "exam_id", "examId", required=False)
    if exam_id is None or isinstance(exam_id, bool) or not isinstance(exam_id, int):
        raise _error("capacity_source_report_metrics_invalid")
    for names in CAPACITY_REQUIRED_MEASURED_FIELDS.values():
        source_value = _one(metrics, *names, required=False)
        raw_value = _one(raw_metrics, *names, required=False)
        if source_value is None or raw_value is None or source_value != raw_value:
            raise _error("capacity_source_report_metrics_mismatch")

    warmup = report.get("warmup")
    if not isinstance(warmup, dict) or set(warmup) != {
        "performed",
        "measured",
        "errors",
        "cold_start_recovery",
    }:
        raise _error("capacity_source_report_metrics_invalid")
    warmup_performed = _one(
        metrics, "warmup_performed", "warmupPerformed", required=True
    )
    warmup_errors = _one(metrics, "warmup_errors", "warmupErrors", required=True)
    if (
        not isinstance(warmup_performed, bool)
        or not isinstance(warmup_errors, list)
        or any(not isinstance(value, str) for value in warmup_errors)
        or warmup.get("performed") is not warmup_performed
        or warmup.get("measured") is not False
        or warmup.get("errors") != warmup_errors
        or warmup.get("cold_start_recovery") != "separate-gate"
    ):
        raise _error("capacity_source_report_metrics_invalid")
    source_thresholds = report.get("thresholds")
    raw_thresholds = payload.get("thresholds")
    if source_thresholds != raw_thresholds:
        raise _error("capacity_source_report_metrics_mismatch")

    source_images = _one(identity, "final_images", "finalImages", required=True)
    if not isinstance(source_images, list):
        raise _error("capacity_source_report_images_invalid")
    if report.get("final_images") != source_images:
        raise _error("capacity_source_report_images_mismatch")
    normalized_source_images: dict[str, str] = {}
    source_services: set[str] = set()
    aliases = {
        "db": "db",
        "backend": "backend",
        "auto-submit-worker": "backend",
        "frontend": "frontend",
        "nginx": "gateway",
        "operator-nginx": "gateway",
        "gateway": "gateway",
        "fake-smtp": None,
    }
    for row in source_images:
        if not isinstance(row, dict) or set(row) - {
            "service",
            "Service",
            "image_id",
            "imageId",
            "id",
            "ID",
            "digest",
            "Digest",
        }:
            raise _error("capacity_source_report_images_invalid")
        service = row.get("service", row.get("Service"))
        image_id = row.get(
            "image_id",
            row.get("imageId", row.get("id", row.get("ID"))),
        )
        service_name = str(service or "")
        if (
            service_name not in CAPACITY_SOURCE_SERVICES
            or service_name in source_services
        ):
            raise _error("capacity_source_report_images_invalid")
        source_services.add(service_name)
        canonical = aliases.get(service_name)
        if not isinstance(image_id, str):
            raise _error("capacity_source_report_images_invalid")
        if IMAGE_ID_RE.fullmatch(image_id) is None:
            raise _error("capacity_source_report_images_invalid")
        digest = row.get("digest", row.get("Digest"))
        if not isinstance(digest, str) or IMAGE_ID_RE.fullmatch(digest) is None:
            raise _error("capacity_source_report_images_invalid")
        if canonical is None:
            continue
        previous = normalized_source_images.get(canonical)
        if previous is not None and previous != image_id.lower():
            raise _error("capacity_source_report_images_invalid")
        normalized_source_images[canonical] = image_id.lower()
    if source_services != CAPACITY_SOURCE_SERVICES:
        raise _error("capacity_source_report_images_invalid")
    raw_images = _one(payload, "liveImageIds", "live_image_ids", required=True)
    if (
        not isinstance(raw_images, dict)
        or set(raw_images) != set(IMAGE_NAMES)
        or any(
            not isinstance(value, str) or IMAGE_ID_RE.fullmatch(value) is None
            for value in raw_images.values()
        )
        or normalized_source_images
        != {key: str(value).lower() for key, value in raw_images.items()}
    ):
        raise _error("capacity_source_report_images_mismatch")


def _validate_probe_facts(payload: Mapping[str, Any], *, check: str) -> None:
    """Require one or more observable facts for each non-capacity gate."""

    if check == "healthMigration":
        migration_head = _string(
            payload, "migrationHead", "migration_head", required=True
        )
        if not migration_head:
            raise _error("health_migration_probe_missing")
        health_status = _one(
            payload, "healthHttpStatus", "health_http_status", required=True
        )
        if isinstance(health_status, bool) or health_status != 200:
            raise _error("health_migration_probe_missing")
        ready_status = _one(
            payload, "readyHttpStatus", "ready_http_status", required=True
        )
        if isinstance(ready_status, bool) or ready_status != 200:
            raise _error("health_migration_probe_missing")
    elif check == "browser":
        browser_name = _string(
            payload, "browser", "browserName", "browser_name", required=False
        )
        url = _string(payload, "url", "candidateUrl", "candidate_url", required=False)
        if not browser_name or not url:
            raise _error("browser_probe_missing")
    elif check == "smtp":
        recipient_domain = _string(
            payload, "recipientDomain", "recipient_domain", required=False
        )
        sent_at = _one(payload, "sentAt", "sent_at", required=False)
        if not recipient_domain or sent_at is None:
            raise _error("smtp_probe_missing")
        _timestamp(sent_at, code="smtp_sent_at")
    elif check == "restart":
        restarted = _one(
            payload, "restartedServices", "restarted_services", required=False
        )
        recovered = _one(
            payload,
            "recoveredAt",
            "recovered_at",
            "recoveryAt",
            "recovery_at",
            required=False,
        )
        if not isinstance(restarted, list) or not restarted or recovered is None:
            raise _error("restart_probe_missing")
        if (
            len(restarted) != len(RESTART_SERVICES)
            or any(not isinstance(service, str) for service in restarted)
            or set(restarted) != RESTART_SERVICES
        ):
            raise _error("restart_probe_missing")
        _timestamp(recovered, code="restart_recovery_at")
        ready_status = _one(
            payload, "readyHttpStatus", "ready_http_status", required=True
        )
        if isinstance(ready_status, bool) or ready_status != 200:
            raise _error("restart_probe_missing")
        health_status = _one(
            payload, "healthHttpStatus", "health_http_status", required=True
        )
        if isinstance(health_status, bool) or health_status != 200:
            raise _error("restart_probe_missing")
        migration_head = _string(
            payload, "migrationHead", "migration_head", required=True
        )
        if not migration_head:
            raise _error("restart_probe_missing")
        heartbeat_age = _one(
            payload,
            "workerHeartbeatAgeSeconds",
            "worker_heartbeat_age_seconds",
            required=True,
        )
        if (
            isinstance(heartbeat_age, bool)
            or not isinstance(heartbeat_age, (int, float))
            or heartbeat_age < 0
            or heartbeat_age > CAPACITY_THRESHOLDS["worker_heartbeat_age_seconds"]
        ):
            raise _error("restart_probe_missing")
    elif check == "route":
        candidate_port = _one(
            payload, "candidatePort", "candidate_port", required=False
        )
        operator_port = _one(payload, "operatorPort", "operator_port", required=False)
        if (
            not isinstance(candidate_port, int)
            or isinstance(candidate_port, bool)
            or not isinstance(operator_port, int)
            or isinstance(operator_port, bool)
            or candidate_port != 18080
            or operator_port != 18081
        ):
            raise _error("route_probe_missing")
        candidate_status = _one(
            payload,
            "candidateAdminHttpStatus",
            "candidate_admin_http_status",
            required=True,
        )
        operator_status = _one(
            payload,
            "operatorAdminHttpStatus",
            "operator_admin_http_status",
            required=True,
        )
        if isinstance(candidate_status, bool) or candidate_status != 404:
            raise _error("route_probe_missing")
        if isinstance(operator_status, bool) or operator_status != 200:
            raise _error("route_probe_missing")


def validate_raw_artifact(
    path: Path,
    *,
    check: str,
    run: RunIdentity,
    root: Path | None = None,
    expected_migration_head: str | None = None,
    expected_image_ids: Mapping[str, str] | None = None,
    maximum_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> ArtifactIdentity:
    if check not in REQUIRED_CHECKS:
        raise _error("check_name_invalid")
    payload, digest = _read_json_file(
        path, allowed=RAW_ALLOWED_FIELDS, code="raw_artifact"
    )
    if payload.get("kind") not in {
        RAW_KIND,
        "staging-evidence",
        "staging-runtime-check",
    }:
        raise _error("raw_artifact_kind_invalid")
    if payload.get("status") != "passed":
        raise _error("raw_artifact_status_invalid")
    declared_check = _string(payload, "check", "gate", required=False)
    if declared_check is not None and declared_check != check:
        raise _error("raw_artifact_check_mismatch")
    _validate_identity_values(
        payload, code="raw_artifact", expected=_expected_fields(run)
    )
    if "secrets" in payload and payload["secrets"] not in {"redacted", "excluded"}:
        raise _error("raw_artifact_secret_field_invalid")
    started_value = _one(payload, "startedAt", "started_at", required=False)
    if (
        started_value is not None
        and _timestamp(started_value, code="raw_artifact_started_at") < run.started_at
    ):
        raise _error("raw_artifact_started_before_run")
    checked_value = _one(
        payload,
        "checkedAt",
        "checked_at",
        "timestamp",
        "createdAt",
        "created_at",
    )
    checked_at = _timestamp(checked_value, code="raw_artifact_checked_at")
    if checked_at < run.started_at:
        raise _error("raw_artifact_stale_run")
    _fresh(checked_at, code="raw_artifact", maximum_age_seconds=maximum_age_seconds)
    if check == "capacity":
        _validate_capacity_report(payload)
    _validate_probe_facts(payload, check=check)
    if check == "browser":
        _validate_browser_report(payload, path=path, run=run)
    if check == "capacity":
        _validate_capacity_source(payload, path=path, run=run)
    if check == "backupRestore":
        _validate_backup_restore(
            payload,
            path=path,
            run=run,
            root=root,
            expected_migration_head=expected_migration_head,
            expected_image_ids=expected_image_ids,
        )
    return ArtifactIdentity(
        check=check, path=path, digest=digest, checked_at=checked_at
    )


def _live_image_rows(
    payload: Any, *, expected_project: str | None = None
) -> tuple[dict[str, str], str | None]:
    project: str | None = None
    rows: Any = payload
    if isinstance(payload, dict):
        project_value = _one(
            payload, "project", "composeProject", "compose_project", required=False
        )
        if project_value is not None:
            if not isinstance(project_value, str):
                raise _error("live_images_project_invalid")
            project = project_value
        rows = _one(
            payload,
            "images",
            "imageIds",
            "image_ids",
            "finalImages",
            "final_images",
            required=False,
        )
        if rows is None and any(
            key in payload for key in ("id", "ID", "service", "Service")
        ):
            rows = [payload]
    if isinstance(rows, dict):
        output: dict[str, str] = {}
        for name, value in rows.items():
            if (
                name in IMAGE_NAMES
                and isinstance(value, str)
                and IMAGE_ID_RE.fullmatch(value)
            ):
                output[name] = value.lower()
        if output:
            return output, project
        # A map keyed by service names is also accepted.
        rows = [{"service": name, "id": value} for name, value in rows.items()]
    if not isinstance(rows, list):
        raise _error("live_images_shape_invalid")
    output = {}
    service_aliases = {
        "db": "db",
        "backend": "backend",
        "auto-submit-worker": "backend",
        "frontend": "frontend",
        "nginx": "gateway",
        "operator-nginx": "gateway",
        "gateway": "gateway",
    }
    for row in rows:
        if not isinstance(row, dict):
            raise _error("live_images_row_invalid")
        service_value = row.get("service", row.get("Service"))
        service = str(service_value or "")
        if not service:
            container_name = row.get("container_name", row.get("ContainerName"))
            if isinstance(container_name, str):
                for candidate in sorted(service_aliases, key=len, reverse=True):
                    if re.search(rf"-{re.escape(candidate)}-\d+$", container_name):
                        service = candidate
                        break
        canonical = service_aliases.get(service)
        image_id = row.get("id", row.get("ID"))
        image_id = str(image_id or "")
        if canonical is None or IMAGE_ID_RE.fullmatch(image_id) is None:
            raise _error("live_images_row_invalid")
        container = row.get("container_name", row.get("ContainerName"))
        if isinstance(container, str):
            project_for_container = project or expected_project
            if project_for_container is not None and not container.startswith(
                f"{project_for_container}-"
            ):
                raise _error("live_images_project_mismatch")
        previous = output.get(canonical)
        if previous is not None and previous != image_id.lower():
            raise _error("live_images_id_mismatch")
        output[canonical] = image_id.lower()
    return output, project


def validate_live_image_ids(
    path: Path,
    *,
    run: RunIdentity,
    expected_image_ids: Mapping[str, str],
    maximum_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, str]:
    _owner_only(path, code="live_images")
    _digest = _read_checksums(path, code="live_images")
    try:
        captured_from_file = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError as exc:
        raise _error("live_images_unreadable") from exc
    if captured_from_file < run.started_at:
        raise _error("live_images_stale_run")
    _fresh(
        captured_from_file,
        code="live_images",
        maximum_age_seconds=maximum_age_seconds,
    )
    try:
        payload = _strict_json_bytes(path.read_bytes())
    except OSError as exc:
        raise _error("live_images_unreadable") from exc
    metadata: Mapping[str, Any]
    if isinstance(payload, dict):
        unknown = set(payload) - LIVE_ALLOWED_FIELDS
        if unknown:
            raise _error("live_images_unknown_field")
        metadata = payload
    elif not isinstance(payload, list):
        raise _error("live_images_shape_invalid")
    else:
        # Docker Compose v5 emits ``images --format json`` as a bare list of
        # rows (ContainerName/ID).  There is no wrapper metadata in that
        # shape; freshness is therefore anchored to the checksummed file
        # mtime and the project is derived from each container name.
        metadata = {}
    if _one(metadata, "schemaVersion", "schema_version", required=False) not in {
        SCHEMA_VERSION,
        1,
        None,
    }:
        raise _error("live_images_schema_invalid")
    captured = _one(metadata, "capturedAt", "captured_at", required=False)
    if captured is not None:
        captured_at = _timestamp(captured, code="live_images_captured_at")
        if captured_at < run.started_at:
            raise _error("live_images_stale_run")
        _fresh(captured_at, code="live_images", maximum_age_seconds=maximum_age_seconds)
    declared_run = _one(metadata, "runId", "run_id", required=False)
    if declared_run is not None and declared_run != run.run_id:
        raise _error("live_images_run_mismatch")
    declared_project = _one(
        metadata, "project", "composeProject", "compose_project", required=False
    )
    if declared_project is not None and declared_project != run.project:
        raise _error("live_images_project_mismatch")
    images, row_project = _live_image_rows(payload, expected_project=run.project)
    if row_project is not None and row_project != run.project:
        raise _error("live_images_project_mismatch")
    if set(images) != set(IMAGE_NAMES):
        raise _error("live_images_missing")
    normalized_expected = {
        name: value.lower() for name, value in expected_image_ids.items()
    }
    if images != normalized_expected:
        raise _error("live_images_id_mismatch")
    return images


def _artifact_reference(path: Path, base: Path, digest: str) -> dict[str, str]:
    return {
        "path": _path_relative_to(path, base, code="canonical_artifact"),
        "sha256": digest,
    }


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _write_checksumming_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_json(payload)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_bytes(data)
        os.chmod(temporary, 0o600)
        temporary.replace(path)
        os.chmod(path, 0o600)
        digest = hashlib.sha256(data).hexdigest()
        sidecar = path.with_name(path.name + ".sha256")
        sidecar_data = f"{digest}  {path.name}\n".encode("ascii")
        sidecar.write_bytes(sidecar_data)
        os.chmod(sidecar, 0o600)
    except OSError as exc:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise _error("canonical_write_failed") from exc
    return digest


def assemble_acceptance(
    *,
    release: Path,
    root: Path,
    run_identity: Path,
    live_image_ids: Path,
    evidence: Mapping[str, Path],
    output: Path,
    project: str | None = None,
    expected_host_id: str | None = None,
    maximum_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    write_output: bool = True,
) -> dict[str, Any]:
    """Validate raw evidence and write a checksummed canonical acceptance."""

    identity = validate_release(release, root)
    run = validate_run_identity(
        run_identity,
        release=identity,
        project=project,
        expected_host_id=expected_host_id,
        maximum_age_seconds=maximum_age_seconds,
    )
    if set(evidence) != set(REQUIRED_CHECKS):
        raise _error("raw_artifacts_incomplete")
    output = output.resolve()
    _reject_symlink_components(output.parent)
    if output.parent != run_identity.resolve().parent:
        # Keeping canonical and raw artifacts together makes relative paths
        # portable and prevents an external path from being silently bound.
        raise _error("canonical_output_directory_invalid")
    artifact_rows: dict[str, ArtifactIdentity] = {}
    for check in REQUIRED_CHECKS:
        artifact_rows[check] = validate_raw_artifact(
            evidence[check],
            check=check,
            run=run,
            root=identity.root,
            expected_migration_head=identity.migration_head,
            expected_image_ids=identity.image_ids,
            maximum_age_seconds=maximum_age_seconds,
        )
        if artifact_rows[check].path.resolve().parent != output.parent:
            raise _error("raw_artifact_directory_invalid")
    live_digest = _read_checksums(live_image_ids, code="live_images")
    live = validate_live_image_ids(
        live_image_ids,
        run=run,
        expected_image_ids=identity.image_ids,
        maximum_age_seconds=maximum_age_seconds,
    )
    if live_image_ids.resolve().parent != output.parent:
        raise _error("live_images_directory_invalid")
    checked_at = max(row.checked_at for row in artifact_rows.values())
    now = datetime.now(UTC)
    if now > checked_at:
        checked_at = now
    canonical: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": CANONICAL_KIND,
        "status": "passed",
        "runId": run.run_id,
        "commit": run.commit,
        "project": run.project,
        "hostId": run.host_id,
        "hostOS": run.host_os,
        "architecture": run.architecture,
        "platform": run.platform,
        "startedAt": run.started_at.isoformat().replace("+00:00", "Z"),
        "checkedAt": checked_at.isoformat().replace("+00:00", "Z"),
        "release": {
            "version": identity.version,
            "path": _path_relative_to(
                identity.release, identity.root, code="canonical_release"
            ),
            "manifestSha256": identity.manifest_digest,
            "securityEvidenceSha256": identity.security_digest,
        },
        "builtImageIdentitySha256": identity.identity_digest,
        "liveImageIds": live,
        "runIdentity": _artifact_reference(run.path, output.parent, run.digest),
        "liveImageEvidence": _artifact_reference(
            live_image_ids, output.parent, live_digest
        ),
        "artifacts": {
            check: _artifact_reference(row.path, output.parent, row.digest)
            for check, row in artifact_rows.items()
        },
        "security": {
            "status": "passed",
            "path": _path_relative_to(
                identity.security_path, identity.root, code="canonical_security"
            ),
            "sha256": identity.security_digest,
            "source": "sealed-release-evidence",
        },
        "gates": dict.fromkeys(CANONICAL_GATES, "passed"),
        "secrets": "redacted",
    }
    if write_output:
        _write_checksumming_json(output, canonical)
    return canonical


def _read_reference(base: Path, reference: Any, *, code: str) -> tuple[Path, str]:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise _error(f"{code}_reference_invalid")
    relative = reference.get("path")
    digest = reference.get("sha256")
    if (
        not isinstance(relative, str)
        or not relative
        or relative.startswith("/")
        or ".." in Path(relative).parts
    ):
        raise _error(f"{code}_path_invalid")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        raise _error(f"{code}_digest_invalid")
    path = base / relative
    _reject_symlink_components(path)
    if path.resolve().parent != base.resolve():
        raise _error(f"{code}_path_invalid")
    actual = _read_checksums(path, code=code)
    if actual != digest.lower():
        raise _error(f"{code}_digest_mismatch")
    return path, actual


def validate_canonical(
    canonical: Path,
    *,
    release: Path,
    root: Path,
    live_image_ids: Path | None = None,
    expected_host_id: str | None = None,
    maximum_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    """Revalidate a canonical acceptance and every referenced raw artifact."""

    payload, canonical_digest = _read_json_file(
        canonical, allowed=CANONICAL_ALLOWED_FIELDS, code="canonical"
    )
    if (
        payload.get("schemaVersion") != SCHEMA_VERSION
        or payload.get("kind") != CANONICAL_KIND
    ):
        raise _error("canonical_schema_invalid")
    if payload.get("status") != "passed":
        raise _error("canonical_status_invalid")
    identity = validate_release(release, root)
    if (
        payload.get("commit") != identity.commit
        or payload.get("builtImageIdentitySha256") != identity.identity_digest
    ):
        raise _error("canonical_release_mismatch")
    release_ref = payload.get("release")
    if (
        not isinstance(release_ref, dict)
        or release_ref.get("version") != identity.version
        or release_ref.get("path")
        != _path_relative_to(identity.release, identity.root, code="canonical_release")
        or release_ref.get("manifestSha256") != identity.manifest_digest
        or release_ref.get("securityEvidenceSha256") != identity.security_digest
    ):
        raise _error("canonical_release_reference_invalid")
    run_ref_path, _ = _read_reference(
        canonical.parent, payload.get("runIdentity"), code="canonical_run"
    )
    run = validate_run_identity(
        run_ref_path,
        release=identity,
        project=payload.get("project"),
        expected_host_id=expected_host_id,
        maximum_age_seconds=maximum_age_seconds,
    )
    if payload.get("runId") != run.run_id or payload.get("hostId") != run.host_id:
        raise _error("canonical_run_mismatch")
    if payload.get("startedAt") != run.started_at.isoformat().replace("+00:00", "Z"):
        raise _error("canonical_started_at_mismatch")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(REQUIRED_CHECKS):
        raise _error("canonical_artifacts_incomplete")
    for check in REQUIRED_CHECKS:
        artifact_path, _digest = _read_reference(
            canonical.parent, artifacts[check], code=f"canonical_{check}"
        )
        validate_raw_artifact(
            artifact_path,
            check=check,
            run=run,
            root=identity.root,
            expected_migration_head=identity.migration_head,
            expected_image_ids=identity.image_ids,
            maximum_age_seconds=maximum_age_seconds,
        )
    live_ref_path, _ = _read_reference(
        canonical.parent, payload.get("liveImageEvidence"), code="canonical_live_images"
    )
    # Revalidation uses a fresh host capture, not merely the old canonical map.
    # The fresh capture may live outside the canonical directory but remains
    # owner-only/checksummed and must have the same run binding.
    live_path = live_image_ids if live_image_ids is not None else live_ref_path
    live = validate_live_image_ids(
        live_path,
        run=run,
        expected_image_ids=identity.image_ids,
        maximum_age_seconds=maximum_age_seconds,
    )
    if payload.get("liveImageIds") != live:
        raise _error("canonical_live_images_mismatch")
    security = payload.get("security")
    if (
        not isinstance(security, dict)
        or security.get("status") != "passed"
        or security.get("source") != "sealed-release-evidence"
        or security.get("path")
        != _path_relative_to(
            identity.security_path, identity.root, code="canonical_security"
        )
        or security.get("sha256") != identity.security_digest
    ):
        raise _error("canonical_security_invalid")
    if payload.get("gates") != dict.fromkeys(CANONICAL_GATES, "passed"):
        raise _error("canonical_gates_invalid")
    for identity_key, expected_value in (
        ("hostOS", run.host_os),
        ("architecture", run.architecture),
        ("platform", run.platform),
    ):
        if payload.get(identity_key) != expected_value:
            raise _error("canonical_identity_mismatch")
    checked_at = _timestamp(payload.get("checkedAt"), code="canonical_checked_at")
    if checked_at < run.started_at:
        raise _error("canonical_stale_run")
    _fresh(checked_at, code="canonical", maximum_age_seconds=maximum_age_seconds)
    # The digest is intentionally computed/read above so tampering with the
    # canonical bytes is covered by its sidecar as well.
    if canonical_digest != sha256_file(canonical):
        raise _error("canonical_digest_mismatch")
    return payload


# Descriptive aliases keep the module convenient for host wrappers and tests
# that call the contract directly rather than going through argparse.
assemble_canonical_evidence = assemble_acceptance
validate_staging_acceptance = validate_canonical
validate_raw_evidence = validate_raw_artifact


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble or revalidate schema-2 macOS staging evidence. "
            "Raw checks must be fresh, owner-only, checksummed JSON tied to "
            "one staging run; backupRestore is a disposable release-bound "
            "restore-smoke, never a formal restore claim."
        )
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--release", "--release-path", required=True, type=Path)
        subparser.add_argument("--root", "--protected-root", required=True, type=Path)
        subparser.add_argument(
            "--max-age-seconds", type=int, default=DEFAULT_MAX_AGE_SECONDS
        )
        subparser.add_argument("--project")
        subparser.add_argument(
            "--expected-host-id",
            help="Bind acceptance to the commissioning host identity supplied by the host wrapper",
        )

    assemble = subparsers.add_parser(
        "assemble", help="validate raw records and write canonical evidence"
    )
    common(assemble)
    assemble.add_argument("--run-identity", "--run-evidence", required=True, type=Path)
    assemble.add_argument("--live-image-ids", "--live-images", required=True, type=Path)
    assemble.add_argument("--output", "--canonical-output", required=True, type=Path)
    assemble.add_argument(
        "--stdout",
        action="store_true",
        help="validate and print canonical JSON without writing the output path",
    )
    for check in REQUIRED_CHECKS:
        option = "--" + re.sub(r"(?<!^)([A-Z])", r"-\1", check).lower() + "-evidence"
        assemble.add_argument(option, required=True, type=Path)

    validate = subparsers.add_parser(
        "validate", help="revalidate canonical and referenced raw evidence"
    )
    common(validate)
    validate.add_argument("--canonical", "--staging-evidence", required=True, type=Path)
    validate.add_argument("--live-image-ids", "--live-images", type=Path)
    return parser


def _main(args: argparse.Namespace) -> int:
    if args.max_age_seconds <= 0:
        raise _error("max_age_invalid")
    if args.action == "assemble":
        # argparse destination names are generated from the option spelling;
        # using the explicit mapping keeps healthMigration/backupRestore
        # readable and avoids accepting arbitrary evidence names.
        evidence = {
            "healthMigration": args.health_migration_evidence,
            "browser": args.browser_evidence,
            "smtp": args.smtp_evidence,
            "capacity": args.capacity_evidence,
            "restart": args.restart_evidence,
            "route": args.route_evidence,
            "backupRestore": args.backup_restore_evidence,
        }
        result = assemble_acceptance(
            release=args.release,
            root=args.root,
            run_identity=args.run_identity,
            live_image_ids=args.live_image_ids,
            evidence=evidence,
            output=args.output,
            project=args.project,
            expected_host_id=args.expected_host_id,
            maximum_age_seconds=args.max_age_seconds,
            write_output=not args.stdout,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    else:
        validate_canonical(
            args.canonical,
            release=args.release,
            root=args.root,
            live_image_ids=args.live_image_ids,
            expected_host_id=args.expected_host_id,
            maximum_age_seconds=args.max_age_seconds,
        )
    sys.stdout.write(json.dumps({"status": "passed", "action": args.action}) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        return _main(parser.parse_args(argv))
    except StagingAcceptanceError as exc:
        sys.stderr.write(f"staging_acceptance_failed code={exc.code}\n")
        return 1
    except (OSError, TypeError, ValueError) as exc:
        # Keep CLI diagnostics non-sensitive even when an unexpected producer
        # value reaches the boundary.
        _ = exc
        sys.stderr.write("staging_acceptance_failed code=invalid_input\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
