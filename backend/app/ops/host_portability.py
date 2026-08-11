"""Host-neutral contracts for release identity and portable formal data.

The host adapters (PowerShell on Windows and zsh on macOS) deliberately keep
their policy surface small.  This module is the shared, fail-closed contract
they can invoke from the versioned backend image.  It only emits metadata that
is safe to retain in release or evidence bundles; credentials and runtime
internals are never accepted as migration inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from app.ops.internal_backup import (
    BACKUP_ARTIFACT_NAMES,
    CHECKSUMS_NAME,
    DATABASE_DUMP_NAME,
    MANIFEST_NAME,
    MEDIA_ARCHIVE_NAME,
    SUCCESS_MARKER_NAME,
    BackupError,
    BackupValidationError,
    validate_backup,
    validate_cutover_backup,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

SUPPORTED_ENVIRONMENTS: Final = frozenset(
    {"development", "dev", "staging", "formal", "restore"}
)
CANONICAL_ENVIRONMENTS: Final = frozenset(
    {"development", "staging", "formal", "restore"}
)
DEFAULT_PROJECT_NAMES: Final[dict[str, str]] = {
    "development": "internal-exam-dev",
    "staging": "internal-exam-staging-local",
    "formal": "internal-exam-formal",
}

# Docker Compose project names are intentionally narrower than Compose's
# permissive grammar: no underscores, dots, path separators, interpolation,
# or names that could be confused with the repository/development stack.
SAFE_PROJECT_NAME_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
PROJECT_NAME_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "development": re.compile(r"^internal-exam-dev$"),
    # A short commit or an explicit local suffix keeps staging isolated from
    # formal.  The Windows adapter uses a 12-character commit prefix.
    "staging": re.compile(r"^internal-exam-staging-[a-z0-9][a-z0-9-]{2,31}$"),
    "formal": re.compile(r"^internal-exam-formal$"),
    "restore": re.compile(r"^internal-exam-restore-verify-[a-z0-9][a-z0-9-]{2,31}$"),
}

FORMAL_PATH_FIELDS: Final[tuple[str, ...]] = (
    "lifecycle",
    "backup",
    "evidence",
    "second_copy",
)
FORMAL_PATH_ALIASES: Final[dict[str, str]] = {
    "lifecycle": "lifecycle",
    "lifecycle_dir": "lifecycle",
    "lifecycle_archive": "lifecycle",
    "lifecycle_archive_dir": "lifecycle",
    "internal_exam_lifecycle_host_dir": "lifecycle",
    "backup": "backup",
    "backups": "backup",
    "backup_dir": "backup",
    "backup_storage": "backup",
    "backup_storage_dir": "backup",
    "internal_exam_backup_host_dir": "backup",
    "evidence": "evidence",
    "evidence_dir": "evidence",
    "operations_evidence": "evidence",
    "operations_evidence_dir": "evidence",
    "internal_exam_evidence_host_dir": "evidence",
    "second_copy": "second_copy",
    "second_copy_dir": "second_copy",
    "second_copy_root": "second_copy",
    "second_copy_path": "second_copy",
}

SUPPORTED_HOST_OS: Final[frozenset[str]] = frozenset(
    {"macos", "darwin", "windows", "linux"}
)
SUPPORTED_ARCHITECTURES: Final[frozenset[str]] = frozenset({"arm64", "amd64"})
ARCHITECTURE_ALIASES: Final[dict[str, str]] = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "arm64e": "arm64",
    "amd64": "amd64",
    "x86_64": "amd64",
    "x86-64": "amd64",
    "x64": "amd64",
}
HOST_OS_ALIASES: Final[dict[str, str]] = {
    "darwin": "macos",
    "mac": "macos",
    "macos": "macos",
    "osx": "macos",
    "windows": "windows",
    "win32": "windows",
    "linux": "linux",
}

SEMVER_PATTERN: Final = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[.-][0-9A-Za-z.-]+)?$")
GIT_COMMIT_PATTERN: Final = re.compile(r"^[0-9a-fA-F]{40}$")
MIGRATION_HEAD_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
IMAGE_NAME_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,254}$")
IMAGE_DIGEST_PATTERN: Final = re.compile(
    r"^[a-z0-9][a-z0-9._/-]{0,254}@sha256:[0-9a-f]{64}$"
)
IMAGE_ID_PATTERN: Final = re.compile(r"^sha256:[0-9a-f]{64}$")

# Metadata is intentionally an allow-list in addition to this recursive
# secret-key guard.  The guard protects optional ``checks``/``details`` data
# supplied by host wrappers from accidentally carrying credentials.
SECRET_KEY_PATTERN: Final = re.compile(
    r"(?:password|passwd|secret|token|otp|credential|private[_.-]?key|"
    r"api[_.-]?key|authorization|cookie|session|smtp|database[_.-]?url|dsn|"
    r"access[_.-]?key)",
    re.IGNORECASE,
)

RELEASE_KEY_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "schema_version": (
        "schema_version",
        "schemaVersion",
        "format_version",
        "formatVersion",
    ),
    "application_version": ("application_version", "applicationVersion"),
    "git_commit": ("git_commit", "gitCommit"),
    "build_host": ("build_host", "buildHost"),
    "target_platform": (
        "target_platform",
        "targetPlatform",
        "target_linux_platform",
        "targetLinuxPlatform",
    ),
    "host_os": (
        "host_os",
        "hostOs",
        "hostOS",
        "host_operating_system",
        "hostOperatingSystem",
    ),
    "architecture": (
        "architecture",
        "cpu_architecture",
        "cpuArchitecture",
        "arch",
    ),
    "migration_head": ("migration_head", "migrationHead"),
    "release_file_checksums": (
        "release_file_checksums",
        "releaseFileChecksums",
        "checksums",
    ),
    "release_input_sha256": (
        "release_input_sha256",
        "releaseInputSha256",
        "source_input_sha256",
        "sourceInputSha256",
        "release_input_identity",
        "releaseInputIdentity",
        "source_input_identity",
        "sourceInputIdentity",
    ),
    "image_references": (
        "image_references",
        "imageReferences",
        "final_image_references",
        "finalImageReferences",
        "final_images",
        "finalImages",
        "image_ids",
        "imageIds",
        "final_image_ids",
        "finalImageIds",
    ),
    "base_image_references": (
        "base_image_references",
        "baseImageReferences",
        "base_image_digests",
        "baseImageDigests",
        # Older host bundles called these image digests.  Keep the alias in
        # the base-input namespace so it cannot be mistaken for app images.
        "image_digests",
        "imageDigests",
    ),
    "created_at": ("created_at", "createdAt", "generated_at", "generatedAt"),
}

CUTOVER_SCHEMA_VERSION: Final = 1
CUTOVER_KIND: Final = "formal-cutover"
CUTOVER_STATES: Final[frozenset[str]] = frozenset({"prepared", "accepted"})
CUTOVER_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
CHECKSUM_LINE_PATTERN: Final = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)$")
CONSUMED_MARKER_SUFFIX: Final = ".consumed.json"
CONSUMED_MARKER_CHECKSUM_SUFFIX: Final = ".sha256"
# A pair of canonical files cannot be replaced in one filesystem operation.
# These deterministic, hidden staging names let a later invocation recognize
# and finish an interrupted write without deleting either canonical file.
CUTOVER_WRITE_TEMP_SUFFIX: Final = ".cutover-write.tmp"
CUTOVER_CLAIM_TEMP_SUFFIX: Final = ".cutover-claim.tmp"
BACKUP_ARTIFACT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    DATABASE_DUMP_NAME: (DATABASE_DUMP_NAME, "database_dump", "databaseDump"),
    MEDIA_ARCHIVE_NAME: (
        MEDIA_ARCHIVE_NAME,
        "learning_media",
        "learningMedia",
    ),
    MANIFEST_NAME: (
        MANIFEST_NAME,
        "manifest",
        "backup_manifest",
        "backupManifest",
    ),
    CHECKSUMS_NAME: (CHECKSUMS_NAME, "checksums", "sha256sums"),
    SUCCESS_MARKER_NAME: (SUCCESS_MARKER_NAME, "success", "success_marker"),
}

# These are generated only after a host-specific image build or security
# evaluation.  They are intentionally excluded from the stable source/input
# identity so ARM64 and AMD64 release metadata can bind the same source tree
# while retaining their own final-image and security evidence checksums.
RELEASE_INPUT_EXCLUDED_PATHS: Final[frozenset[str]] = frozenset(
    {
        "ops/release/built-image-identity.json",
        "ops/release/built-image-identity.json.sha256",
        "release-evidence/security-scan.json",
        "release-evidence/security-scan.json.sha256",
    }
)


class HostPortabilityError(ValueError):
    """Base error for host-portability contract violations."""


class ProjectNameValidationError(HostPortabilityError):
    """A Compose project name is unsafe for its requested environment."""


class FormalPathValidationError(HostPortabilityError):
    """A formal mutable host path is unsafe or ambiguous."""


class MetadataValidationError(HostPortabilityError):
    """Release/evidence metadata is invalid or contains a secret field."""


class MigrationInputError(BackupValidationError, HostPortabilityError):
    """The supplied artifact is not a verified portable paired backup."""


def _canonical_environment(environment: str) -> str:
    if not isinstance(environment, str):
        raise ProjectNameValidationError("Compose 环境标识无效。")
    normalized = environment.strip().lower()
    if normalized == "dev":
        normalized = "development"
    if normalized not in CANONICAL_ENVIRONMENTS:
        raise ProjectNameValidationError("Compose 环境标识无效。")
    return normalized


def validate_project_name(project_name: str, environment: str) -> str:
    """Validate and return a project name scoped to one deployment environment.

    ``environment`` may be supplied first by wrappers written against an
    earlier draft of this contract; the small swap below keeps that call shape
    compatible without weakening the actual name checks.
    """

    if (
        isinstance(project_name, str)
        and project_name.strip().lower() in SUPPORTED_ENVIRONMENTS
        and isinstance(environment, str)
        and environment.strip().lower() not in SUPPORTED_ENVIRONMENTS
    ):
        project_name, environment = environment, project_name
    canonical_environment = _canonical_environment(environment)
    if not isinstance(project_name, str) or project_name != project_name.strip():
        raise ProjectNameValidationError("Compose project name 必须是无空白安全标识。")
    if SAFE_PROJECT_NAME_PATTERN.fullmatch(project_name) is None:
        raise ProjectNameValidationError("Compose project name 格式不安全。")
    pattern = PROJECT_NAME_PATTERNS[canonical_environment]
    if pattern.fullmatch(project_name) is None:
        raise ProjectNameValidationError("Compose project name 与环境不匹配。")
    return project_name


def assert_safe_project_name(project_name: str, environment: str) -> None:
    """Raise when ``project_name`` is not safe for ``environment``."""

    validate_project_name(project_name, environment)


def assert_project_name(project_name: str, environment: str) -> None:
    """Compatibility alias used by host adapters."""

    assert_safe_project_name(project_name, environment)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_absolute_path(value: str | Path, *, error: str) -> Path:
    if isinstance(value, Path):
        raw = value
    elif isinstance(value, str):
        raw = Path(value)
    else:
        raise FormalPathValidationError(error)
    # Do not silently turn a development-relative path into a formal root.
    if not raw.is_absolute() or str(raw).strip() != str(raw):
        raise FormalPathValidationError(error)
    resolved = raw.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise FormalPathValidationError(error)
    return resolved


def validate_formal_host_path(
    path: str | Path,
    *,
    development_root: str | Path | None = None,
    formal_root: str | Path | None = None,
) -> Path:
    """Validate one absolute mutable path used by the formal host.

    The check resolves existing symlinks and therefore cannot be bypassed by a
    path that syntactically sits outside the checkout but points into it.
    """

    resolved = _resolve_absolute_path(path, error="正式宿主路径必须是安全绝对路径。")
    dev_root = (
        REPO_ROOT
        if development_root is None
        else _resolve_absolute_path(
            development_root, error="开发工作树必须是安全绝对路径。"
        )
    )
    if _is_relative_to(resolved, dev_root):
        raise FormalPathValidationError("正式宿主路径不得位于开发工作树内。")
    if formal_root is not None:
        root = _resolve_absolute_path(
            formal_root, error="正式宿主根目录必须是安全绝对路径。"
        )
        if _is_relative_to(root, dev_root):
            raise FormalPathValidationError("正式宿主根目录不得位于开发工作树内。")
        if not _is_relative_to(resolved, root) or resolved == root:
            raise FormalPathValidationError("正式宿主路径必须位于正式宿主根目录内。")
    return resolved


def validate_formal_host_paths(
    paths: Mapping[str, str | Path] | None = None,
    *,
    development_root: str | Path | None = None,
    formal_root: str | Path | None = None,
    lifecycle: str | Path | None = None,
    backup: str | Path | None = None,
    evidence: str | Path | None = None,
    second_copy: str | Path | None = None,
) -> dict[str, Path]:
    """Validate all formal lifecycle/backup/evidence/second-copy paths.

    ``paths`` accepts either canonical field names or the environment-variable
    spellings (for example ``BACKUP_STORAGE_DIR`` after lower-casing).  Every
    required field must be present; development defaults are intentionally not
    passed through this function.
    """

    collected: dict[str, str | Path] = dict(paths or {})
    collected.update(
        {
            key: value
            for key, value in {
                "lifecycle": lifecycle,
                "backup": backup,
                "evidence": evidence,
                "second_copy": second_copy,
            }.items()
            if value is not None
        }
    )

    root_value: str | Path | None = formal_root
    for key in tuple(collected):
        normalized_key = key.strip().lower() if isinstance(key, str) else ""
        if normalized_key in {"root", "formal_root", "formal_host_root"}:
            if root_value is None:
                root_value = collected[key]
            del collected[key]
            continue
        canonical_key = FORMAL_PATH_ALIASES.get(normalized_key)
        if canonical_key is None:
            raise FormalPathValidationError("正式宿主路径字段不受支持。")
        if canonical_key != key:
            collected[canonical_key] = collected.pop(key)

    missing = [field for field in FORMAL_PATH_FIELDS if field not in collected]
    if missing:
        raise FormalPathValidationError("正式宿主路径字段不完整。")
    if root_value is None:
        raise FormalPathValidationError("正式宿主根目录必须提供。")
    # Validate the root itself even when no path points at it directly.
    root_value = _resolve_absolute_path(
        root_value, error="正式宿主根目录必须是安全绝对路径。"
    )
    resolved: dict[str, Path] = {}
    for field in ("lifecycle", "backup", "evidence"):
        resolved[field] = validate_formal_host_path(
            collected[field],
            development_root=development_root,
            formal_root=root_value,
        )
    # The second copy is intentionally independent storage.  It must remain
    # outside the formal root and cannot be an ancestor of it (or a child of
    # it), otherwise a local disk failure could take out both copies.
    resolved["second_copy"] = validate_formal_host_path(
        collected["second_copy"],
        development_root=development_root,
        formal_root=None,
    )
    if _is_relative_to(resolved["second_copy"], root_value) or _is_relative_to(
        root_value, resolved["second_copy"]
    ):
        raise FormalPathValidationError("第二副本必须位于独立存储路径。")
    values = list(resolved.items())
    for index, (left_name, left_path) in enumerate(values):
        for right_name, right_path in values[index + 1 :]:
            if _is_relative_to(left_path, right_path) or _is_relative_to(
                right_path, left_path
            ):
                raise FormalPathValidationError(
                    f"正式宿主路径不得互相重叠：{left_name}/{right_name}。"
                )
    return resolved


def validate_formal_paths(
    paths: Mapping[str, str | Path],
    *,
    development_root: str | Path | None = None,
    formal_root: str | Path | None = None,
) -> dict[str, Path]:
    """Short compatibility alias for :func:`validate_formal_host_paths`."""

    return validate_formal_host_paths(
        paths, development_root=development_root, formal_root=formal_root
    )


def assert_formal_host_paths(
    paths: Mapping[str, str | Path],
    *,
    development_root: str | Path | None = None,
    formal_root: str | Path | None = None,
) -> None:
    """Raise when formal host paths violate the deployment boundary."""

    validate_formal_host_paths(
        paths, development_root=development_root, formal_root=formal_root
    )


def _normalize_host_os(value: str | None) -> str:
    normalized = (value or platform.system()).strip().lower()
    canonical = HOST_OS_ALIASES.get(normalized)
    if canonical is None or canonical not in SUPPORTED_HOST_OS:
        raise MetadataValidationError("宿主操作系统不受支持。")
    return canonical


def _normalize_architecture(value: str | None) -> str:
    normalized = (value or platform.machine()).strip().lower()
    canonical = ARCHITECTURE_ALIASES.get(normalized)
    if canonical is None or canonical not in SUPPORTED_ARCHITECTURES:
        raise MetadataValidationError("CPU 架构不受支持。")
    return canonical


def _default_target_platform(architecture: str) -> str:
    return f"linux/{architecture}"


def _normalize_build_host(value: Any) -> dict[str, str]:
    if value is None:
        return {
            "os": _normalize_host_os(None),
            "architecture": _normalize_architecture(None),
        }
    if not isinstance(value, Mapping):
        raise MetadataValidationError("buildHost 字段无效。")
    host_os = value.get("os", value.get("host_os", value.get("hostOs")))
    architecture = value.get(
        "architecture",
        value.get("cpu_architecture", value.get("cpuArchitecture")),
    )
    return {
        "os": _normalize_host_os(host_os),
        "architecture": _normalize_architecture(architecture),
    }


def _normalize_target_platform(value: Any, *, architecture: str) -> str:
    if value is None:
        return _default_target_platform(architecture)
    if isinstance(value, Mapping):
        target_os = value.get("os", value.get("target_os", value.get("targetOs")))
        if target_os is not None and str(target_os).strip().lower() not in {
            "linux",
        }:
            raise MetadataValidationError("targetPlatform 必须是 Linux。")
        target_architecture = value.get(
            "architecture",
            value.get("cpu_architecture", value.get("cpuArchitecture")),
        )
        if (
            target_architecture is not None
            and _normalize_architecture(str(target_architecture)) != architecture
        ):
            raise MetadataValidationError("targetPlatform 与 CPU 架构不匹配。")
        value = value.get(
            "platform",
            value.get(
                "containerPlatform",
                value.get("container_platform", value.get("target")),
            ),
        )
    if not isinstance(value, str):
        raise MetadataValidationError("targetPlatform 字段无效。")
    normalized = value.strip().lower()
    expected = _default_target_platform(architecture)
    if normalized != expected:
        raise MetadataValidationError("targetPlatform 必须是匹配架构的 Linux 平台。")
    return normalized


def _ensure_no_secret_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or SECRET_KEY_PATTERN.search(key):
                raise MetadataValidationError("元数据包含禁止的敏感字段。")
            _ensure_no_secret_fields(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _ensure_no_secret_fields(nested)


def _value_for_key(payload: Mapping[str, Any], canonical_key: str) -> Any:
    for key in RELEASE_KEY_ALIASES[canonical_key]:
        if key in payload:
            return payload[key]
    return None


def _validate_timestamp(value: Any, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise MetadataValidationError("元数据时间字段无效。")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise MetadataValidationError("元数据时间字段无效。") from exc
    if parsed.tzinfo is None:
        raise MetadataValidationError("元数据时间字段必须包含时区。")
    return parsed.astimezone(UTC).isoformat()


def _normalize_release_file_checksums(value: Any) -> dict[str, str]:
    if isinstance(value, Mapping):
        rows = value.items()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        converted: list[tuple[str, Any]] = []
        for row in value:
            if not isinstance(row, Mapping):
                raise MetadataValidationError("release 文件 checksum 字段无效。")
            path = row.get("path", row.get("name"))
            converted.append((path, row.get("sha256")))
        rows = converted
    else:
        raise MetadataValidationError("release 文件 checksum 字段无效。")

    normalized: dict[str, str] = {}
    for path_value, digest_value in rows:
        if not isinstance(path_value, str) or not path_value:
            raise MetadataValidationError("release 文件 checksum 字段无效。")
        path = path_value.replace("\\", "/")
        path_obj = Path(path)
        if (
            path_obj.is_absolute()
            or path.startswith("/")
            or path in {"", "."}
            or path.startswith("./")
            or ".." in path_obj.parts
            or "\x00" in path
        ):
            raise MetadataValidationError("release 文件路径必须是安全相对路径。")
        if (
            not isinstance(digest_value, str)
            or SHA256_PATTERN.fullmatch(digest_value) is None
        ):
            raise MetadataValidationError("release 文件 checksum 字段无效。")
        if path in normalized:
            raise MetadataValidationError("release 文件 checksum 字段重复。")
        normalized[path] = digest_value
    if not normalized:
        raise MetadataValidationError("release 文件 checksum 字段不能为空。")
    return dict(sorted(normalized.items()))


def _derive_release_input_sha256(checksums: Mapping[str, str]) -> str:
    """Derive the cross-host source identity from release file checksums.

    Platform-generated image and security evidence files are deliberately
    omitted.  The resulting digest is computed by this contract rather than
    trusted from caller input, so a supplied identity can only corroborate the
    derived value, never replace it.
    """

    stable_checksums = {
        path: digest
        for path, digest in checksums.items()
        if path not in RELEASE_INPUT_EXCLUDED_PATHS
    }
    return _canonical_json_sha256(stable_checksums)


def _normalize_image_references(value: Any, architecture: str) -> dict[str, str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        converted: dict[str, Any] = {}
        for row in value:
            if not isinstance(row, Mapping):
                raise MetadataValidationError("架构专用镜像引用格式无效。")
            image_name = row.get("name", row.get("image"))
            if not isinstance(image_name, str):
                raise MetadataValidationError("架构专用镜像名称无效。")
            converted[image_name] = row.get("reference", row.get("ref", row.get("id")))
        value = converted
    if not isinstance(value, Mapping) or not value:
        raise MetadataValidationError("架构专用镜像引用不能为空。")

    selected: Mapping[str, Any] = value
    # Accept a multi-architecture manifest while selecting only the host's
    # references.  This prevents a darwin/arm64 evidence record from silently
    # carrying the Windows/amd64 image set.
    for alias in (
        architecture,
        "linux/arm64" if architecture == "arm64" else "linux/amd64",
    ):
        nested = value.get(alias)
        if isinstance(nested, Mapping):
            selected = nested
            break
    normalized: dict[str, str] = {}
    for image_name, reference in selected.items():
        if isinstance(reference, Mapping):
            reference = reference.get(
                "reference", reference.get("ref", reference.get("id"))
            )
        if (
            not isinstance(image_name, str)
            or IMAGE_NAME_PATTERN.fullmatch(image_name) is None
            or not isinstance(reference, str)
            or (
                IMAGE_DIGEST_PATTERN.fullmatch(reference) is None
                and IMAGE_ID_PATTERN.fullmatch(reference) is None
            )
        ):
            raise MetadataValidationError("架构专用镜像引用必须使用 immutable digest。")
        normalized[image_name] = reference
    if not normalized:
        raise MetadataValidationError("架构专用镜像引用不能为空。")
    return dict(sorted(normalized.items()))


def _normalize_release_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    _ensure_no_secret_fields(payload)
    version = _value_for_key(payload, "application_version")
    git_commit = _value_for_key(payload, "git_commit")
    migration_head = _value_for_key(payload, "migration_head")
    if (
        not isinstance(version, str)
        or SEMVER_PATTERN.fullmatch(version) is None
        or not isinstance(git_commit, str)
        or GIT_COMMIT_PATTERN.fullmatch(git_commit) is None
        or not isinstance(migration_head, str)
        or MIGRATION_HEAD_PATTERN.fullmatch(migration_head) is None
    ):
        raise MetadataValidationError("release 身份字段无效。")
    architecture = _normalize_architecture(_value_for_key(payload, "architecture"))
    host_os = _normalize_host_os(_value_for_key(payload, "host_os"))
    target_platform = _normalize_target_platform(
        _value_for_key(payload, "target_platform"), architecture=architecture
    )
    checksums = _normalize_release_file_checksums(
        _value_for_key(payload, "release_file_checksums")
    )
    derived_input_sha256 = _derive_release_input_sha256(checksums)
    supplied_input_values = [
        payload[key]
        for key in RELEASE_KEY_ALIASES["release_input_sha256"]
        if key in payload
    ]
    if supplied_input_values and any(
        value != supplied_input_values[0] for value in supplied_input_values[1:]
    ):
        raise MetadataValidationError("release source/input identity 别名不一致。")
    supplied_input_sha256 = supplied_input_values[0] if supplied_input_values else None
    if supplied_input_sha256 is not None and (
        not isinstance(supplied_input_sha256, str)
        or SHA256_PATTERN.fullmatch(supplied_input_sha256) is None
        or supplied_input_sha256 != derived_input_sha256
    ):
        raise MetadataValidationError("release source/input identity checksum 无效。")
    images = _normalize_image_references(
        _value_for_key(payload, "image_references"), architecture
    )
    base_images_value = _value_for_key(payload, "base_image_references")
    base_images = (
        _normalize_image_references(base_images_value, architecture)
        if base_images_value is not None
        else None
    )
    schema_version = _value_for_key(payload, "schema_version")
    if schema_version is not None and schema_version not in {1, "1"}:
        raise MetadataValidationError("release metadata 版本不受支持。")
    created_at = _validate_timestamp(
        _value_for_key(payload, "created_at"), required=False
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "application_version": version,
        "git_commit": git_commit.lower(),
        "host_os": host_os,
        "architecture": architecture,
        "target_platform": target_platform,
        "migration_head": migration_head,
        "release_file_checksums": checksums,
        "release_input_sha256": derived_input_sha256,
        "image_references": images,
    }
    if base_images is not None:
        result["base_image_references"] = base_images
    if created_at is not None:
        result["created_at"] = created_at
    return result


def validate_release_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize non-secret architecture-aware release metadata."""

    if not isinstance(metadata, Mapping):
        raise MetadataValidationError("release metadata 必须是 JSON object。")
    return _normalize_release_metadata(metadata)


def build_release_metadata(
    *,
    application_version: str,
    git_commit: str,
    migration_head: str,
    image_references: Mapping[str, Any],
    release_file_checksums: Mapping[str, str] | Sequence[Mapping[str, Any]],
    base_image_references: Mapping[str, Any] | None = None,
    host_os: str | None = None,
    architecture: str | None = None,
    target_platform: str | Mapping[str, Any] | None = None,
    release_input_sha256: str | None = None,
    created_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Build the shared release identity from explicitly non-secret fields."""

    if created_at is None:
        created_value = datetime.now(UTC).isoformat()
    elif isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            raise MetadataValidationError("release metadata 时间必须包含时区。")
        created_value = created_at.astimezone(UTC).isoformat()
    else:
        created_value = created_at
    payload: dict[str, Any] = {
        "schema_version": 1,
        "application_version": application_version,
        "git_commit": git_commit,
        "host_os": _normalize_host_os(host_os),
        "architecture": _normalize_architecture(architecture),
        "target_platform": target_platform,
        "migration_head": migration_head,
        "release_file_checksums": release_file_checksums,
        "image_references": image_references,
        "created_at": created_value,
    }
    if release_input_sha256 is not None:
        payload["release_input_sha256"] = release_input_sha256
    if base_image_references is not None:
        payload["base_image_references"] = base_image_references
    return validate_release_metadata(payload)


generate_release_metadata = build_release_metadata


def build_evidence_metadata(
    *,
    release_metadata: Mapping[str, Any],
    kind: str,
    status: str,
    checks: Mapping[str, Any] | None = None,
    checked_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Build a checksummed-evidence identity without copying secrets."""

    if (
        not isinstance(kind, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", kind) is None
    ):
        raise MetadataValidationError("evidence 类型无效。")
    if status not in {"passed", "failed", "degraded", "skipped"}:
        raise MetadataValidationError("evidence 状态无效。")
    identity = validate_release_metadata(release_metadata)
    if checked_at is None:
        checked_value = datetime.now(UTC).isoformat()
    elif isinstance(checked_at, datetime):
        if checked_at.tzinfo is None:
            raise MetadataValidationError("evidence 时间必须包含时区。")
        checked_value = checked_at.astimezone(UTC).isoformat()
    else:
        checked_value = checked_at
    _validate_timestamp(checked_value, required=True)
    if checks is not None:
        _ensure_no_secret_fields(checks)
    result = {
        "schema_version": 1,
        "kind": kind,
        "status": status,
        "checked_at": checked_value,
        **identity,
    }
    if checks is not None:
        result["checks"] = dict(checks)
    return result


generate_evidence_metadata = build_evidence_metadata
build_release_identity = build_release_metadata
validate_release_identity = validate_release_metadata


def validate_evidence_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a non-secret host/release evidence record."""

    if not isinstance(metadata, Mapping):
        raise MetadataValidationError("evidence metadata 必须是 JSON object。")
    _ensure_no_secret_fields(metadata)
    kind = metadata.get("kind")
    status = metadata.get("status")
    if (
        not isinstance(kind, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", kind) is None
    ):
        raise MetadataValidationError("evidence 类型无效。")
    if status not in {"passed", "failed", "degraded", "skipped"}:
        raise MetadataValidationError("evidence 状态无效。")
    checked_at = _validate_timestamp(
        metadata.get("checked_at", metadata.get("checkedAt")), required=True
    )
    identity = validate_release_metadata(metadata)
    result = {
        "schema_version": 1,
        "kind": kind,
        "status": status,
        "checked_at": checked_at,
        **identity,
    }
    checks = metadata.get("checks")
    if checks is not None:
        if not isinstance(checks, Mapping):
            raise MetadataValidationError("evidence checks 字段无效。")
        _ensure_no_secret_fields(checks)
        result["checks"] = dict(checks)
    return result


def _normalize_cutover_identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or CUTOVER_ID_PATTERN.fullmatch(value) is None:
        raise HostPortabilityError(f"cutover {field_name} 无效。")
    return value


def _normalize_writer_generation(
    value: Any, field_name: str = "writer_generation"
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise HostPortabilityError(f"cutover {field_name} 无效。")
    return value


def _normalize_cutover_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise HostPortabilityError(f"cutover {field_name} 必须是布尔值。")
    return value


def _canonical_json_sha256(value: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _normalize_cutover_release_metadata(
    value: Any, *, field_name: str = "release_metadata"
) -> dict[str, Any]:
    """Validate a release record that is complete enough for cutover.

    Generic release/evidence metadata keeps optional base-image references for
    compatibility.  A formal cutover must bind them because they are stable
    build inputs shared by all target architectures.
    """

    if not isinstance(value, Mapping):
        raise HostPortabilityError(f"cutover {field_name} 必须完整提供。")
    try:
        normalized = validate_release_metadata(value)
    except MetadataValidationError as exc:
        raise HostPortabilityError(f"cutover {field_name} 无效。") from exc
    if "base_image_references" not in normalized:
        raise HostPortabilityError(f"cutover {field_name} 缺少 base image identity。")
    if not isinstance(normalized.get("release_input_sha256"), str):
        raise HostPortabilityError(f"cutover {field_name} 缺少 source/input identity。")
    return normalized


def _validate_release_pair(
    source_release_metadata: Mapping[str, Any],
    target_release_metadata: Mapping[str, Any],
) -> None:
    """Require stable release inputs while allowing host-specific outputs."""

    for field_name in (
        "application_version",
        "git_commit",
        "migration_head",
        "release_input_sha256",
        "base_image_references",
    ):
        if source_release_metadata.get(field_name) != target_release_metadata.get(
            field_name
        ):
            raise HostPortabilityError(
                f"cutover release input identity 不一致：{field_name}。"
            )


def _normalize_backup_artifact_identity(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise HostPortabilityError("paired backup artifact checksum 无效。")
    normalized: dict[str, str] = {}
    consumed_keys: set[str] = set()
    for canonical_name, aliases in BACKUP_ARTIFACT_ALIASES.items():
        matching = [key for key in aliases if key in value]
        if not matching:
            raise HostPortabilityError(
                f"paired backup 缺少 artifact checksum：{canonical_name}。"
            )
        first = value[matching[0]]
        if any(value[key] != first for key in matching[1:]):
            raise HostPortabilityError("paired backup artifact checksum 别名不一致。")
        if not isinstance(first, str) or SHA256_PATTERN.fullmatch(first) is None:
            raise HostPortabilityError(
                f"paired backup artifact checksum 无效：{canonical_name}。"
            )
        normalized[canonical_name] = first
        consumed_keys.update(matching)
    if set(value) != consumed_keys:
        raise HostPortabilityError("paired backup artifact checksum 包含未知条目。")
    return normalized


def _backup_artifact_checksums(directory: Path) -> dict[str, str]:
    """Return the immutable identities bound into a cutover manifest."""

    try:
        entries = {entry.name for entry in directory.iterdir()}
    except OSError as exc:
        raise MigrationInputError("paired backup 目录无法读取。") from exc
    if entries != set(BACKUP_ARTIFACT_NAMES):
        raise MigrationInputError("paired backup 产物集合不完整。")
    checksums: dict[str, str] = {}
    for name in (
        DATABASE_DUMP_NAME,
        MEDIA_ARCHIVE_NAME,
        MANIFEST_NAME,
        CHECKSUMS_NAME,
        SUCCESS_MARKER_NAME,
    ):
        path = directory / name
        try:
            checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise MigrationInputError("paired backup artifact 无法读取。") from exc
    return checksums


def _normalize_source_stop_proof(
    value: Any,
    *,
    source_project: str,
    fallback_stopped: bool,
    observed_at: str,
) -> dict[str, Any]:
    if value is None:
        value = {
            "whole_project_stopped": fallback_stopped,
            "whole_project": fallback_stopped,
            "project": source_project,
            "observed_at": observed_at,
            "running_services": [],
            "method": "adapter-attestation",
        }
    if not isinstance(value, Mapping):
        raise HostPortabilityError("source whole-project stop proof 无效。")
    _ensure_no_secret_fields(value)
    whole_value = _cutover_value(
        value,
        "whole_project_stopped",
        "wholeProjectStopped",
        "whole_project",
        "wholeProject",
    )
    whole_stopped = _normalize_cutover_bool(
        whole_value, "source_stop_proof.whole_project_stopped"
    )
    if whole_stopped != fallback_stopped:
        raise HostPortabilityError("source stop proof 与 stopped 字段不一致。")
    project = _cutover_value(value, "project", "source_project", "sourceProject")
    if project != source_project:
        raise HostPortabilityError("source stop proof project 与 source 不一致。")
    checked_at = _validate_timestamp(
        _cutover_value(value, "observed_at", "observedAt", "checked_at"),
        required=True,
    )
    running_services = _cutover_value(
        value, "running_services", "runningServices", "services"
    )
    if not isinstance(running_services, list) or any(
        not isinstance(service, str) or not service.strip()
        for service in running_services
    ):
        raise HostPortabilityError("source stop proof running_services 无效。")
    method = _cutover_value(value, "method", "proof_method", "proofMethod")
    if (
        not isinstance(method, str)
        or re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", method) is None
    ):
        raise HostPortabilityError("source stop proof method 无效。")
    if whole_stopped and running_services:
        raise HostPortabilityError("source stop proof 仍有运行中的 service。")
    if not whole_stopped:
        raise HostPortabilityError("source stop proof 必须证明整个 source 已停止。")
    evidence_sha256 = _cutover_value(
        value, "evidence_sha256", "evidenceSha256", "proof_sha256"
    )
    if evidence_sha256 is not None and (
        not isinstance(evidence_sha256, str)
        or SHA256_PATTERN.fullmatch(evidence_sha256) is None
    ):
        raise HostPortabilityError("source stop proof evidence checksum 无效。")
    result: dict[str, Any] = {
        "whole_project_stopped": whole_stopped,
        "whole_project": whole_stopped,
        "project": source_project,
        "observed_at": checked_at,
        "running_services": list(running_services),
        "method": method,
    }
    if evidence_sha256 is not None:
        result["evidence_sha256"] = evidence_sha256
    return result


def _extract_target_release_metadata(value: Any) -> dict[str, Any]:
    """Extract the target release identity carried by preflight evidence."""

    if not isinstance(value, Mapping):
        raise HostPortabilityError("target preflight evidence 无效。")
    _ensure_no_secret_fields(value)
    evidence_release_values = [
        value[key]
        for key in (
            "target_release_metadata",
            "targetReleaseMetadata",
            "release_metadata",
            "releaseMetadata",
            "release",
        )
        if key in value
    ]
    if evidence_release_values and any(
        item != evidence_release_values[0] for item in evidence_release_values[1:]
    ):
        raise HostPortabilityError("target preflight release metadata 别名不一致。")
    evidence_release = evidence_release_values[0] if evidence_release_values else value
    return _normalize_cutover_release_metadata(
        evidence_release, field_name="target_release_metadata"
    )


def _normalize_target_preflight_evidence(
    value: Any,
    *,
    dataset_id: str,
    target_host_id: str,
    target_writer_generation: int,
    target_release_metadata: Mapping[str, Any] | None = None,
    release_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HostPortabilityError("target preflight evidence 无效。")
    _ensure_no_secret_fields(value)
    status = _cutover_value(value, "status", "outcome")
    if status != "passed":
        raise HostPortabilityError("target preflight evidence 必须是 passed。")
    checked_at = _validate_timestamp(
        _cutover_value(value, "checked_at", "checkedAt", "observed_at"),
        required=True,
    )
    evidence_dataset = _normalize_cutover_identifier(
        _cutover_value(value, "dataset_id", "datasetId"), "target_preflight.dataset_id"
    )
    evidence_target = _normalize_cutover_identifier(
        _cutover_value(value, "target_host_id", "targetHostId", "host_id", "hostId"),
        "target_preflight.target_host_id",
    )
    evidence_generation = _normalize_writer_generation(
        _cutover_value(
            value,
            "target_writer_generation",
            "targetWriterGeneration",
            "writer_generation",
            "writerGeneration",
        ),
        "target_preflight.target_writer_generation",
    )
    if evidence_dataset != dataset_id:
        raise HostPortabilityError("target preflight dataset identity 不一致。")
    if evidence_target != target_host_id:
        raise HostPortabilityError("target preflight host identity 不一致。")
    if evidence_generation != target_writer_generation:
        raise HostPortabilityError("target preflight writer generation 不一致。")

    if target_release_metadata is None:
        target_release_metadata = release_metadata
    normalized_release = _extract_target_release_metadata(value)
    if target_release_metadata is None:
        raise HostPortabilityError("target preflight 缺少 target release identity。")
    expected_release = _normalize_cutover_release_metadata(
        target_release_metadata, field_name="target release metadata"
    )
    if normalized_release != expected_release:
        raise HostPortabilityError("target preflight release identity 不一致。")
    release_digest_values = [
        value[key]
        for key in (
            "target_release_metadata_sha256",
            "targetReleaseMetadataSha256",
            "release_metadata_sha256",
            "releaseMetadataSha256",
        )
        if key in value
    ]
    if release_digest_values and any(
        item != release_digest_values[0] for item in release_digest_values[1:]
    ):
        raise HostPortabilityError("target preflight release checksum 别名不一致。")
    release_digest = release_digest_values[0] if release_digest_values else None
    expected_release_digest = _canonical_json_sha256(normalized_release)
    if release_digest is not None and release_digest != expected_release_digest:
        raise HostPortabilityError("target preflight release checksum 不一致。")
    kind = _cutover_value(value, "kind", "type") or "target-preflight"
    if (
        not isinstance(kind, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", kind) is None
    ):
        raise HostPortabilityError("target preflight evidence 类型无效。")
    checks = value.get("checks")
    if checks is not None:
        if not isinstance(checks, Mapping):
            raise HostPortabilityError("target preflight checks 无效。")
        _ensure_no_secret_fields(checks)
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": kind,
        "status": "passed",
        "checked_at": checked_at,
        "dataset_id": dataset_id,
        "target_host_id": target_host_id,
        "target_writer_generation": target_writer_generation,
        "target_release_metadata": normalized_release,
        "target_release_metadata_sha256": expected_release_digest,
        # A target-preflight record predates the source/target split and its
        # legacy release field therefore unambiguously denotes the target.
        "release_metadata": normalized_release,
        "release_metadata_sha256": expected_release_digest,
    }
    if checks is not None:
        result["checks"] = dict(checks)
    return result


def _resolve_source_stop_proof(
    *,
    source_fully_stopped: bool | None,
    source_gateway_stopped: bool | None,
    source_stopped: bool | None = None,
) -> bool:
    provided = [
        value
        for value in (
            source_fully_stopped,
            source_gateway_stopped,
            source_stopped,
        )
        if value is not None
    ]
    if provided and any(value != provided[0] for value in provided[1:]):
        raise HostPortabilityError("source stopped 证明字段不一致。")
    resolved = provided[0] if provided else False
    return _normalize_cutover_bool(resolved, "source_fully_stopped")


def _cutover_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _read_json_mapping(path: Path, error: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HostPortabilityError(error) from exc
    if not isinstance(value, Mapping):
        raise HostPortabilityError(error)
    return value


def _cutover_checksum_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".sha256")


def _cutover_temp_path(path: Path, suffix: str) -> Path:
    return path.with_name(f".{path.name}{suffix}")


def _cutover_destination_identity(path: Path) -> str:
    """Return a portable identity for a resolved cutover destination.

    Cutover state can be retained outside the host that created it, so the
    durable marker must not carry the host's absolute path.  Hashing the
    canonical resolved path binds reservations to one destination while
    keeping that path out of portable metadata.
    """

    try:
        resolved = path.expanduser().resolve(strict=False)
        return hashlib.sha256(os.fsencode(str(resolved))).hexdigest()
    except (OSError, RuntimeError, TypeError, ValueError, UnicodeError) as exc:
        raise HostPortabilityError("cutover accepted output identity 无效。") from exc


def _fsync_directory(path: Path) -> None:
    """Best-effort directory fsync after an atomic replace."""

    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        return
    finally:
        os.close(descriptor)


def _stage_cutover_bytes(path: Path, payload: bytes, *, label: str) -> None:
    """Create a deterministic staging file, refusing stale bytes."""

    try:
        if path.is_symlink():
            raise HostPortabilityError(f"{label} staging 文件不能是符号链接。")
        if path.exists():
            if not path.is_file() or path.read_bytes() != payload:
                raise HostPortabilityError(f"{label} staging 文件与本次操作不一致。")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as staged:
            staged.write(payload)
            staged.flush()
            os.fsync(staged.fileno())
        _fsync_directory(path.parent)
    except HostPortabilityError:
        raise
    except (OSError, UnicodeError) as exc:
        raise HostPortabilityError(f"{label} staging 文件无法写入。") from exc


def _replace_cutover_staging(staging: Path, destination: Path, *, label: str) -> None:
    try:
        staging.replace(destination)
        _fsync_directory(destination.parent)
    except OSError as exc:
        raise HostPortabilityError(f"{label} canonical 文件无法替换。") from exc


def _remove_cutover_temp(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # The canonical pair is already safe.  Leaving exact staging bytes is
        # recoverable on the next invocation; never remove canonical state as
        # a cleanup fallback.
        return


def _checksum_line(path: Path, digest: str) -> bytes:
    return f"{digest}  {path.name}\n".encode("ascii")


def _read_optional_bytes(path: Path, *, label: str) -> bytes | None:
    try:
        if not path.exists():
            return None
        if path.is_symlink() or not path.is_file():
            raise HostPortabilityError(f"{label} 必须是普通文件。")
        return path.read_bytes()
    except HostPortabilityError:
        raise
    except OSError as exc:
        raise HostPortabilityError(f"{label} 无法读取。") from exc


def _canonical_cutover_json(state: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    except (TypeError, UnicodeError) as exc:
        raise HostPortabilityError("cutover state JSON 无法序列化。") from exc


def _parse_cutover_json(payload: bytes, *, error: str) -> Mapping[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HostPortabilityError(error) from exc
    if not isinstance(value, Mapping):
        raise HostPortabilityError(error)
    return value


def _cutover_consumed_marker_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + CONSUMED_MARKER_SUFFIX)


def _validate_consumed_marker_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    marker_state = payload.get("state")
    # Markers written before the reservation phase are treated as consumed
    # for compatibility; a new marker always carries an explicit state.
    if marker_state is None and "consumed_state_sha256" in payload:
        marker_state = "consumed"
    if marker_state not in {"reserved", "consumed"}:
        raise HostPortabilityError("cutover consumed marker 状态无效。")
    source_digest = payload.get("source_sha256")
    if (
        not isinstance(source_digest, str)
        or SHA256_PATTERN.fullmatch(source_digest) is None
    ):
        raise HostPortabilityError("cutover consumed marker source checksum 无效。")
    accepted_name = payload.get("accepted_state_name")
    if accepted_name is not None and (
        not isinstance(accepted_name, str)
        or not accepted_name
        or Path(accepted_name).name != accepted_name
    ):
        raise HostPortabilityError("cutover reservation output 无效。")
    accepted_identity = payload.get("accepted_state_identity")
    if (
        not isinstance(accepted_identity, str)
        or SHA256_PATTERN.fullmatch(accepted_identity) is None
    ):
        raise HostPortabilityError("cutover reservation output identity 无效。")
    if marker_state == "reserved" and accepted_name is None:
        raise HostPortabilityError("cutover reservation output 无效。")
    if marker_state == "reserved" and payload.get("accepted_sha256") is not None:
        accepted_digest = payload["accepted_sha256"]
        if (
            not isinstance(accepted_digest, str)
            or SHA256_PATTERN.fullmatch(accepted_digest) is None
        ):
            raise HostPortabilityError("cutover reservation accepted checksum 无效。")
    if marker_state == "consumed":
        for key in (
            "consumed_state_sha256",
            "accepted_sha256",
            "accepted_state_identity",
        ):
            value = payload.get(key)
            if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
                raise HostPortabilityError("cutover consumed marker checksum 无效。")
    return dict(payload) | {"state": marker_state}


def _read_consumed_marker_file(
    path: Path,
) -> tuple[dict[str, Any], bytes, bool]:
    """Read marker JSON and report whether its sidecar is currently valid."""

    marker_path = _cutover_consumed_marker_path(path)
    checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    marker_bytes = _read_optional_bytes(marker_path, label="cutover consumed marker")
    if marker_bytes is None:
        raise HostPortabilityError("cutover consumed marker 不完整。")
    payload = _validate_consumed_marker_payload(
        _parse_cutover_json(marker_bytes, error="cutover consumed marker JSON 无效。")
    )
    checksum_bytes = _read_optional_bytes(
        checksum_path, label="cutover consumed marker checksum"
    )
    checksum_valid = False
    if checksum_bytes is not None:
        try:
            checksum_text = checksum_bytes.decode("ascii").strip()
        except UnicodeError:
            checksum_text = ""
        match = CHECKSUM_LINE_PATTERN.fullmatch(checksum_text)
        checksum_valid = bool(
            match is not None
            and match.group(2) == marker_path.name
            and match.group(1) == hashlib.sha256(marker_bytes).hexdigest()
        )
    return payload, marker_bytes, checksum_valid


def _repair_cutover_checksum(
    path: Path,
    payload: bytes,
    *,
    label: str,
    temporary: Path | None = None,
) -> None:
    expected = _checksum_line(path, hashlib.sha256(payload).hexdigest())
    checksum_path = _cutover_checksum_path(path)
    existing = _read_optional_bytes(checksum_path, label=f"{label} checksum")
    if existing is not None:
        if existing != expected:
            raise HostPortabilityError(f"{label} checksum 校验失败。")
        return
    temporary = temporary or _cutover_temp_path(
        checksum_path, CUTOVER_WRITE_TEMP_SUFFIX
    )
    _stage_cutover_bytes(temporary, expected, label=f"{label} checksum")
    _replace_cutover_staging(temporary, checksum_path, label=f"{label} checksum")


def _read_consumed_marker(path: Path) -> dict[str, Any]:
    payload, marker_bytes, checksum_valid = _read_consumed_marker_file(path)
    marker_path = _cutover_consumed_marker_path(path)
    checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    if not checksum_valid and checksum_path.exists():
        raise HostPortabilityError("cutover consumed marker checksum 校验失败。")
    try:
        current_source_bytes = path.read_bytes()
    except OSError as exc:
        raise HostPortabilityError("cutover source state 无法读取。") from exc
    current_source_digest = hashlib.sha256(current_source_bytes).hexdigest()
    source_digest = payload["source_sha256"]
    if payload["state"] == "reserved":
        if source_digest != current_source_digest:
            raise HostPortabilityError("cutover reservation 与 source state 不匹配。")
        source_state = _parse_cutover_json(
            current_source_bytes,
            error="reserved source state JSON 无法读取。",
        )
        if source_state.get("state") != "prepared":
            raise HostPortabilityError("cutover reservation 与 source state 不匹配。")
        if not checksum_valid:
            _repair_cutover_checksum(
                marker_path,
                marker_bytes,
                label="cutover consumed marker",
            )
        return payload

    consumed_digest = payload["consumed_state_sha256"]
    accepted_digest = payload["accepted_sha256"]
    if consumed_digest != current_source_digest:
        raise HostPortabilityError("cutover consumed marker source checksum 无效。")
    source_state = _parse_cutover_json(
        current_source_bytes,
        error="consumed source state JSON 无法读取。",
    )
    if (
        source_state.get("state") != "consumed"
        or source_state.get("consumed_source_sha256") != source_digest
        or source_state.get("accepted_sha256") != accepted_digest
    ):
        raise HostPortabilityError("cutover consumed marker 与 source state 不匹配。")
    if payload.get("accepted_state_name") is not None and (
        source_state.get("accepted_state_name") != payload["accepted_state_name"]
    ):
        raise HostPortabilityError("cutover consumed marker 与 source state 不匹配。")
    if source_state.get("accepted_state_identity") != payload.get(
        "accepted_state_identity"
    ):
        raise HostPortabilityError("cutover consumed marker 与 source state 不匹配。")
    if not checksum_valid:
        _repair_cutover_checksum(
            marker_path,
            marker_bytes,
            label="cutover consumed marker",
        )
    return payload


def _assert_cutover_state_unconsumed(path: Path) -> None:
    marker_path = _cutover_consumed_marker_path(path)
    checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    if not marker_path.exists() and not checksum_path.exists():
        return
    payload = _read_consumed_marker(path)
    if payload["state"] == "consumed":
        raise HostPortabilityError("prepared cutover state 已被消费。")


def _validate_exact_cutover_output(path: Path, expected_digest: str) -> None:
    payload = _read_optional_bytes(path, label="accepted cutover state")
    checksum_path = _cutover_checksum_path(path)
    checksum = _read_optional_bytes(
        checksum_path, label="accepted cutover state checksum"
    )
    if payload is None or checksum is None:
        raise HostPortabilityError("accepted cutover state 输出不完整。")
    if hashlib.sha256(payload).hexdigest() != expected_digest:
        raise HostPortabilityError("accepted cutover state 与已消费 state 不一致。")
    expected_checksum = _checksum_line(path, expected_digest)
    if checksum != expected_checksum:
        raise HostPortabilityError("accepted cutover state checksum 校验失败。")
    normalized = validate_cutover_state(
        _parse_cutover_json(payload, error="accepted cutover state JSON 无效。")
    )
    if normalized["state"] != "accepted":
        raise HostPortabilityError("accepted cutover state 阶段无效。")


def _reserve_cutover_state(
    source_path: Path,
    accepted_path: Path,
    *,
    accepted_digest: str | None = None,
) -> dict[str, str]:
    """Reserve a prepared state, recovering only an exact reservation commit."""

    marker_path = _cutover_consumed_marker_path(source_path)
    checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    marker_temporary = _cutover_temp_path(marker_path, CUTOVER_WRITE_TEMP_SUFFIX)
    checksum_temporary = _cutover_temp_path(checksum_path, CUTOVER_WRITE_TEMP_SUFFIX)
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        raise HostPortabilityError("cutover source state 无法读取。") from exc
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    accepted_identity = _cutover_destination_identity(accepted_path)
    source_state = _parse_cutover_json(
        source_bytes, error="prepared source state JSON 无法读取."
    )

    marker_present = marker_path.exists()
    checksum_present = checksum_path.exists()
    if checksum_present and not marker_present:
        raise HostPortabilityError("cutover consumed marker 不完整。")
    if marker_present:
        # A previous attempt may have written marker JSON and not its sidecar.
        # The payload is sufficient to identify the exact reservation, and
        # _read_consumed_marker repairs only that missing sidecar.
        payload, marker_bytes, checksum_valid = _read_consumed_marker_file(source_path)
        if not checksum_valid:
            if checksum_present and payload["state"] == "reserved":
                raise HostPortabilityError(
                    "cutover consumed marker checksum 校验失败。"
                )
            if payload["state"] == "reserved":
                _repair_cutover_checksum(
                    marker_path,
                    marker_bytes,
                    label="cutover consumed marker",
                    temporary=checksum_temporary,
                )
                checksum_present = True
        marker_state = payload["state"]
        marker_source_digest = payload["source_sha256"]
        accepted_name = payload.get("accepted_state_name")
        if marker_state == "reserved":
            marker_accepted_digest = payload.get("accepted_sha256")
            if marker_accepted_digest is not None and (
                accepted_digest is None or marker_accepted_digest != accepted_digest
            ):
                raise HostPortabilityError(
                    "cutover reservation accepted digest 不一致。"
                )
            prepared_reservation = (
                source_state.get("state") == "prepared"
                and marker_source_digest == source_digest
            )
            claim_in_progress = (
                source_state.get("state") == "consumed"
                and marker_source_digest == source_state.get("consumed_source_sha256")
                and accepted_digest is not None
                and source_state.get("accepted_sha256") == accepted_digest
            )
            if (
                not (prepared_reservation or claim_in_progress)
                or accepted_name != accepted_path.name
                or payload.get("accepted_state_identity") != accepted_identity
            ):
                raise HostPortabilityError("cutover reservation 已被其他操作占用。")
            return {"source_sha256": marker_source_digest, "state": "reserved"}
        if (
            marker_source_digest != source_state.get("consumed_source_sha256")
            or accepted_name != accepted_path.name
            or payload.get("accepted_state_identity") != accepted_identity
            or source_state.get("state") != "consumed"
        ):
            raise HostPortabilityError("prepared cutover state 已被消费。")
        consumed_digest = payload["accepted_sha256"]
        if accepted_digest is None or consumed_digest != accepted_digest:
            raise HostPortabilityError("prepared cutover state 已被其他操作消费。")
        _validate_exact_cutover_output(accepted_path, consumed_digest)
        return {
            "source_sha256": marker_source_digest,
            "accepted_sha256": consumed_digest,
            "state": "consumed",
        }

    if source_state.get("state") != "prepared":
        raise HostPortabilityError("cutover source state 阶段无效。")

    existing_temporary = _read_optional_bytes(
        marker_temporary, label="cutover reservation staging"
    )
    if existing_temporary is None:
        payload = {
            "schema_version": CUTOVER_SCHEMA_VERSION,
            "kind": "formal-cutover-reservation",
            "state": "reserved",
            "source_sha256": source_digest,
            "accepted_state_name": accepted_path.name,
            "accepted_state_identity": accepted_identity,
            "reserved_at": datetime.now(UTC).isoformat(),
        }
        if accepted_digest is not None:
            payload["accepted_sha256"] = accepted_digest
        serialized = _canonical_cutover_json(payload)
    else:
        serialized = existing_temporary
        payload = _validate_consumed_marker_payload(
            _parse_cutover_json(
                serialized, error="cutover reservation staging JSON 无效。"
            )
        )
        if (
            payload["state"] != "reserved"
            or payload["source_sha256"] != source_digest
            or payload.get("accepted_state_name") != accepted_path.name
            or payload.get("accepted_state_identity") != accepted_identity
        ):
            raise HostPortabilityError("cutover reservation staging 与本次操作不一致。")
        if payload.get("accepted_sha256") is not None and (
            accepted_digest is None or payload["accepted_sha256"] != accepted_digest
        ):
            raise HostPortabilityError("cutover reservation accepted digest 不一致。")
    _stage_cutover_bytes(marker_temporary, serialized, label="cutover reservation")
    _stage_cutover_bytes(
        checksum_temporary,
        _checksum_line(marker_path, hashlib.sha256(serialized).hexdigest()),
        label="cutover reservation checksum",
    )

    # The marker itself is the one-shot reservation lock.  O_EXCL preserves
    # the existing race guarantee; the staged bytes make a crash during the
    # write recoverable without allowing a replacement reservation.
    try:
        if not marker_path.exists():
            with marker_path.open("xb") as marker_file:
                marker_file.write(serialized)
                marker_file.flush()
                os.fsync(marker_file.fileno())
            _fsync_directory(marker_path.parent)
        else:
            current = _read_optional_bytes(marker_path, label="cutover consumed marker")
            if current != serialized:
                raise HostPortabilityError("cutover reservation 已被其他操作占用。")
    except FileExistsError as exc:
        raise HostPortabilityError("prepared cutover state 已被消费。") from exc
    except HostPortabilityError:
        raise
    except OSError as exc:
        raise HostPortabilityError("cutover reservation 无法写入。") from exc

    current_checksum = _read_optional_bytes(
        checksum_path, label="cutover reservation checksum"
    )
    expected_checksum = _checksum_line(
        marker_path, hashlib.sha256(serialized).hexdigest()
    )
    if current_checksum is not None and current_checksum != expected_checksum:
        raise HostPortabilityError("cutover reservation checksum 校验失败。")
    if current_checksum is None:
        _replace_cutover_staging(
            checksum_temporary,
            checksum_path,
            label="cutover reservation checksum",
        )
    _remove_cutover_temp(marker_temporary)
    _remove_cutover_temp(checksum_temporary)
    return {"source_sha256": source_digest, "state": "reserved"}


def _claim_cutover_state(
    source_path: Path,
    *,
    source_digest: str,
    accepted_digest: str,
    accepted_state_name: str,
    accepted_state_identity: str,
    prepared_state: Mapping[str, Any],
) -> None:
    marker_path = _cutover_consumed_marker_path(source_path)
    marker_checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    source_checksum_path = _cutover_checksum_path(source_path)
    source_temporary = _cutover_temp_path(source_path, CUTOVER_CLAIM_TEMP_SUFFIX)
    source_checksum_temporary = _cutover_temp_path(
        source_checksum_path, CUTOVER_CLAIM_TEMP_SUFFIX
    )
    marker_temporary = _cutover_temp_path(marker_path, CUTOVER_CLAIM_TEMP_SUFFIX)
    marker_checksum_temporary = _cutover_temp_path(
        marker_checksum_path, CUTOVER_CLAIM_TEMP_SUFFIX
    )

    marker_bytes, marker_payload, marker_checksum_valid = _claim_marker_snapshot(
        source_path
    )
    if marker_payload.get("accepted_state_name") != accepted_state_name:
        raise HostPortabilityError("cutover reservation 已失效。")
    if marker_payload.get("accepted_state_identity") != accepted_state_identity:
        raise HostPortabilityError("cutover reservation output identity 已失效。")
    if marker_payload.get("source_sha256") != source_digest:
        raise HostPortabilityError("cutover reservation 已失效。")
    if (
        marker_payload.get("accepted_sha256") is not None
        and marker_payload.get("accepted_sha256") != accepted_digest
    ):
        raise HostPortabilityError("cutover reservation accepted digest 不一致。")
    if not marker_checksum_valid and marker_payload.get("state") == "reserved":
        if marker_checksum_path.exists():
            raise HostPortabilityError("cutover consumed marker checksum 校验失败。")
        _repair_cutover_checksum(
            marker_path,
            marker_bytes,
            label="cutover consumed marker",
            temporary=marker_checksum_temporary,
        )
        marker_checksum_valid = True

    source_bytes = _read_optional_bytes(source_path, label="cutover source state")
    if source_bytes is None:
        raise HostPortabilityError("cutover source state 无法读取。")
    source_state = _parse_cutover_json(
        source_bytes, error="cutover source state JSON 无法读取。"
    )

    # Recover the timestamp and target bytes from any surviving claim staging
    # file.  This makes retries deterministic even after source JSON has
    # already been replaced but its sidecar/marker pair has not.
    source_staged = _read_optional_bytes(
        source_temporary, label="consumed source staging"
    )
    marker_staged = _read_optional_bytes(
        marker_temporary, label="consumed marker staging"
    )
    consumed_at: str | None = None
    for candidate in (source_staged, marker_staged):
        if candidate is None:
            continue
        candidate_payload = _parse_cutover_json(
            candidate, error="consumed cutover staging JSON 无效。"
        )
        candidate_time = candidate_payload.get("consumed_at")
        if not isinstance(candidate_time, str):
            raise HostPortabilityError("consumed cutover staging 时间无效。")
        _validate_timestamp(candidate_time, required=True)
        if consumed_at is not None and candidate_time != consumed_at:
            raise HostPortabilityError("consumed cutover staging 时间不一致。")
        consumed_at = candidate_time
    if source_state.get("state") == "consumed":
        current_time = source_state.get("consumed_at")
        if not isinstance(current_time, str):
            raise HostPortabilityError("consumed source state 时间无效。")
        _validate_timestamp(current_time, required=True)
        if consumed_at is not None and consumed_at != current_time:
            raise HostPortabilityError("consumed cutover state 时间不一致。")
        consumed_at = current_time
    if consumed_at is None:
        consumed_at = datetime.now(UTC).isoformat()

    consumed_state = dict(prepared_state)
    consumed_state.update(
        {
            "state": "consumed",
            "consumed_at": consumed_at,
            "consumed_source_sha256": source_digest,
            "accepted_sha256": accepted_digest,
            "accepted_state_name": accepted_state_name,
            "accepted_state_identity": accepted_state_identity,
        }
    )
    consumed_serialized = _canonical_cutover_json(consumed_state)
    consumed_digest = hashlib.sha256(consumed_serialized).hexdigest()
    marker_payload_expected: dict[str, Any] = {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "kind": "formal-cutover-consumed",
        "state": "consumed",
        "source_sha256": source_digest,
        "consumed_state_sha256": consumed_digest,
        "accepted_sha256": accepted_digest,
        "accepted_state_name": accepted_state_name,
        "accepted_state_identity": accepted_state_identity,
        "consumed_at": consumed_at,
    }
    marker_serialized = _canonical_cutover_json(marker_payload_expected)

    # Existing canonical files may already be the target state from an
    # interrupted claim.  They must be byte-for-byte equal to this exact
    # transaction; a different/tampered state is never overwritten.
    if source_state.get("state") == "consumed" and source_bytes != consumed_serialized:
        raise HostPortabilityError("consumed source state 与本次 claim 不一致。")
    if marker_payload.get("state") == "consumed" and marker_bytes != marker_serialized:
        raise HostPortabilityError("consumed marker 与本次 claim 不一致。")
    source_digest_current = hashlib.sha256(source_bytes).hexdigest()
    if (
        source_state.get("state") == "prepared"
        and source_digest_current != source_digest
    ):
        raise HostPortabilityError("cutover reservation 与 source state 不匹配。")
    if source_state.get("state") not in {"prepared", "consumed"}:
        raise HostPortabilityError("cutover source state 阶段无效。")
    if marker_payload.get("state") not in {"reserved", "consumed"}:
        raise HostPortabilityError("cutover reservation 已失效。")

    source_checksum_expected = _checksum_line(source_path, consumed_digest)
    marker_checksum_expected = _checksum_line(
        marker_path, hashlib.sha256(marker_serialized).hexdigest()
    )
    source_checksum = _read_optional_bytes(
        source_checksum_path, label="consumed source checksum"
    )
    marker_checksum = _read_optional_bytes(
        marker_checksum_path, label="consumed marker checksum"
    )
    source_checksum_staged = _read_optional_bytes(
        source_checksum_temporary, label="consumed source checksum staging"
    )
    marker_checksum_staged = _read_optional_bytes(
        marker_checksum_temporary, label="consumed marker checksum staging"
    )
    if (
        marker_payload["state"] == "consumed"
        and source_checksum != source_checksum_expected
        and source_checksum_staged != source_checksum_expected
    ):
        raise HostPortabilityError("consumed source checksum 校验失败。")
    if (
        marker_payload["state"] == "consumed"
        and marker_checksum != marker_checksum_expected
        and marker_checksum_staged != marker_checksum_expected
    ):
        raise HostPortabilityError("consumed marker checksum 校验失败。")
    if (
        marker_payload["state"] == "reserved"
        and source_state.get("state") == "prepared"
        and source_checksum != _checksum_line(source_path, source_digest)
    ):
        raise HostPortabilityError("prepared source checksum 校验失败。")
    # Stage all four target bytes before replacing any canonical file.  A
    # retry can therefore complete whichever suffix remains after a crash.
    _stage_cutover_bytes(source_temporary, consumed_serialized, label="consumed source")
    _stage_cutover_bytes(
        source_checksum_temporary,
        source_checksum_expected,
        label="consumed source checksum",
    )
    _stage_cutover_bytes(marker_temporary, marker_serialized, label="consumed marker")
    _stage_cutover_bytes(
        marker_checksum_temporary,
        marker_checksum_expected,
        label="consumed marker checksum",
    )

    if source_bytes != consumed_serialized:
        _replace_cutover_staging(source_temporary, source_path, label="consumed source")
        source_bytes = consumed_serialized
    if source_checksum != source_checksum_expected:
        _replace_cutover_staging(
            source_checksum_temporary,
            source_checksum_path,
            label="consumed source checksum",
        )
    if marker_bytes != marker_serialized:
        _replace_cutover_staging(marker_temporary, marker_path, label="consumed marker")
        marker_bytes = marker_serialized
    if marker_checksum != marker_checksum_expected:
        _replace_cutover_staging(
            marker_checksum_temporary,
            marker_checksum_path,
            label="consumed marker checksum",
        )
    for temporary in (
        source_temporary,
        source_checksum_temporary,
        marker_temporary,
        marker_checksum_temporary,
    ):
        _remove_cutover_temp(temporary)


def _claim_marker_snapshot(
    source_path: Path,
) -> tuple[bytes, dict[str, Any], bool]:
    marker_path = _cutover_consumed_marker_path(source_path)
    marker_bytes = _read_optional_bytes(marker_path, label="cutover consumed marker")
    if marker_bytes is None:
        raise HostPortabilityError("cutover consumed marker 不完整。")
    marker_payload = _validate_consumed_marker_payload(
        _parse_cutover_json(marker_bytes, error="cutover consumed marker JSON 无效。")
    )
    checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    checksum_bytes = _read_optional_bytes(
        checksum_path, label="cutover consumed marker checksum"
    )
    if checksum_bytes is None:
        marker_checksum_valid = False
    else:
        try:
            checksum_text = checksum_bytes.decode("ascii").strip()
        except UnicodeError:
            checksum_text = ""
        match = CHECKSUM_LINE_PATTERN.fullmatch(checksum_text)
        marker_checksum_valid = bool(
            match is not None
            and match.group(2) == marker_path.name
            and match.group(1) == hashlib.sha256(marker_bytes).hexdigest()
        )
    return marker_bytes, marker_payload, marker_checksum_valid


def validate_cutover_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a pure, checksummed cutover state without changing a host."""

    if not isinstance(state, Mapping):
        raise HostPortabilityError("cutover state 必须是 JSON object。")
    _ensure_no_secret_fields(state)
    schema_version = _cutover_value(state, "schema_version", "schemaVersion")
    if schema_version not in {CUTOVER_SCHEMA_VERSION, str(CUTOVER_SCHEMA_VERSION)}:
        raise HostPortabilityError("cutover state 版本不受支持。")
    kind = _cutover_value(state, "kind", "type")
    if kind != CUTOVER_KIND:
        raise HostPortabilityError("cutover state 类型无效。")
    phase = _cutover_value(state, "state", "phase", "status")
    if phase not in CUTOVER_STATES:
        raise HostPortabilityError("cutover state 阶段无效。")

    dataset_id = _normalize_cutover_identifier(
        _cutover_value(state, "dataset_id", "datasetId"), "dataset_id"
    )
    backup_id = _normalize_cutover_identifier(
        _cutover_value(state, "backup_id", "backupId"), "backup_id"
    )
    source_host_id = _normalize_cutover_identifier(
        _cutover_value(state, "source_host_id", "sourceHostId"), "source_host_id"
    )
    target_host_id = _normalize_cutover_identifier(
        _cutover_value(state, "target_host_id", "targetHostId"), "target_host_id"
    )
    if source_host_id == target_host_id:
        raise HostPortabilityError("cutover source 与 target 必须是不同宿主。")
    source_project = _cutover_value(state, "source_project", "sourceProject")
    target_project = _cutover_value(state, "target_project", "targetProject")
    source_project = validate_project_name(
        source_project if source_project is not None else "", "formal"
    )
    target_project = validate_project_name(
        target_project if target_project is not None else "", "formal"
    )

    writer_generation = _normalize_writer_generation(
        _cutover_value(state, "writer_generation", "writerGeneration")
    )
    source_generation = _normalize_writer_generation(
        _cutover_value(state, "source_writer_generation", "sourceWriterGeneration"),
        "source_writer_generation",
    )
    target_generation = _normalize_writer_generation(
        _cutover_value(state, "target_writer_generation", "targetWriterGeneration"),
        "target_writer_generation",
    )
    expected_writer_generation = (
        source_generation if phase == "prepared" else target_generation
    )
    if (
        writer_generation != expected_writer_generation
        or target_generation != source_generation + 1
    ):
        raise HostPortabilityError("cutover writer generation 不一致。")

    source_quiescent = _normalize_cutover_bool(
        _cutover_value(state, "source_quiescent", "sourceQuiescent"),
        "source_quiescent",
    )
    if not source_quiescent:
        raise HostPortabilityError("cutover source 必须已静默，无进行中的考试。")
    source_fully_stopped_value = _cutover_value(
        state, "source_fully_stopped", "sourceFullyStopped"
    )
    source_gateway_stopped_value = _cutover_value(
        state, "source_gateway_stopped", "sourceGatewayStopped"
    )
    if (
        source_fully_stopped_value is not None
        and source_gateway_stopped_value is not None
        and source_fully_stopped_value != source_gateway_stopped_value
    ):
        raise HostPortabilityError("source stopped 证明字段不一致。")
    source_fully_stopped = _normalize_cutover_bool(
        source_fully_stopped_value
        if source_fully_stopped_value is not None
        else source_gateway_stopped_value,
        "source_fully_stopped",
    )
    if not source_fully_stopped:
        raise HostPortabilityError("cutover 必须证明整个 source 已停止。")
    target_exposed = _normalize_cutover_bool(
        _cutover_value(state, "target_exposed", "targetExposed"), "target_exposed"
    )
    target_write_accepted = _normalize_cutover_bool(
        _cutover_value(state, "target_write_accepted", "targetWriteAccepted"),
        "target_write_accepted",
    )
    target_write_authorized_value = _cutover_value(
        state, "target_write_authorized", "targetWriteAuthorized"
    )
    target_write_authorized = _normalize_cutover_bool(
        target_write_authorized_value
        if target_write_authorized_value is not None
        else False,
        "target_write_authorized",
    )
    preflight_status = _cutover_value(
        state, "target_preflight_status", "targetPreflightStatus"
    )
    if preflight_status not in {"passed", "pending", "not-run"}:
        raise HostPortabilityError("cutover target preflight 状态无效。")
    if phase == "accepted":
        if (
            not source_fully_stopped
            or target_exposed
            or target_write_accepted
            or not target_write_authorized
            or preflight_status != "passed"
        ):
            raise HostPortabilityError(
                "accepted cutover 必须证明 source 已停止、target 尚未暴露且尚未接受写入，并授予后续写入授权。"
            )
    elif target_exposed or target_write_accepted or target_write_authorized:
        raise HostPortabilityError("prepared cutover 不得暴露 target 或授予写入授权。")

    created_at = _validate_timestamp(
        _cutover_value(state, "created_at", "createdAt"), required=True
    )
    updated_at = _validate_timestamp(
        _cutover_value(state, "updated_at", "updatedAt"), required=True
    )
    proof_values = [
        state[key]
        for key in (
            "source_stop_proof",
            "sourceStopProof",
            "source_project_stop_proof",
            "sourceProjectStopProof",
        )
        if key in state
    ]
    if proof_values and any(value != proof_values[0] for value in proof_values[1:]):
        raise HostPortabilityError("source stop proof 别名不一致。")
    source_stop_proof = _normalize_source_stop_proof(
        proof_values[0] if proof_values else None,
        source_project=source_project,
        fallback_stopped=source_fully_stopped,
        observed_at=created_at if created_at is not None else "",
    )
    if not source_stop_proof["whole_project_stopped"]:
        raise HostPortabilityError("source stop proof 无法证明整个项目已停止。")

    source_release_values = [
        state[key]
        for key in ("source_release_metadata", "sourceReleaseMetadata")
        if key in state
    ]
    if source_release_values and any(
        value != source_release_values[0] for value in source_release_values[1:]
    ):
        raise HostPortabilityError("source release metadata 别名不一致。")
    legacy_release_values = [
        state[key] for key in ("release_metadata", "releaseMetadata") if key in state
    ]
    if legacy_release_values and any(
        value != legacy_release_values[0] for value in legacy_release_values[1:]
    ):
        raise HostPortabilityError("cutover release metadata 别名不一致。")
    source_release_value = (
        source_release_values[0]
        if source_release_values
        else legacy_release_values[0]
        if legacy_release_values
        else None
    )
    if source_release_value is None:
        raise HostPortabilityError("cutover source release metadata 必须完整提供。")
    normalized_source_release = _normalize_cutover_release_metadata(
        source_release_value, field_name="source_release_metadata"
    )
    if legacy_release_values:
        legacy_release = _normalize_cutover_release_metadata(
            legacy_release_values[0], field_name="release_metadata"
        )
        if legacy_release != normalized_source_release:
            raise HostPortabilityError(
                "legacy release metadata 必须是 source release metadata 别名。"
            )
    source_release_digest_values = [
        state[key]
        for key in (
            "source_release_metadata_sha256",
            "sourceReleaseMetadataSha256",
            "release_metadata_sha256",
            "releaseMetadataSha256",
        )
        if key in state
    ]
    if source_release_digest_values and any(
        value != source_release_digest_values[0]
        for value in source_release_digest_values[1:]
    ):
        raise HostPortabilityError("source release metadata checksum 别名不一致。")
    source_release_digest = (
        source_release_digest_values[0] if source_release_digest_values else None
    )
    if (
        not isinstance(source_release_digest, str)
        or SHA256_PATTERN.fullmatch(source_release_digest) is None
    ):
        raise HostPortabilityError("source release metadata checksum 无效。")
    if source_release_digest != _canonical_json_sha256(normalized_source_release):
        raise HostPortabilityError("source release metadata checksum 不匹配。")

    target_release_values = [
        state[key]
        for key in ("target_release_metadata", "targetReleaseMetadata")
        if key in state
    ]
    if target_release_values and any(
        value != target_release_values[0] for value in target_release_values[1:]
    ):
        raise HostPortabilityError("target release metadata 别名不一致。")
    target_release_digest_values = [
        state[key]
        for key in (
            "target_release_metadata_sha256",
            "targetReleaseMetadataSha256",
        )
        if key in state
    ]
    if target_release_digest_values and any(
        value != target_release_digest_values[0]
        for value in target_release_digest_values[1:]
    ):
        raise HostPortabilityError("target release metadata checksum 别名不一致。")
    if phase == "prepared" and (target_release_values or target_release_digest_values):
        raise HostPortabilityError(
            "prepared cutover 不得携带 target release metadata。"
        )
    normalized_target_release: dict[str, Any] | None = None
    target_release_digest: str | None = None
    if phase == "accepted":
        if not target_release_values or not target_release_digest_values:
            raise HostPortabilityError(
                "accepted cutover 必须完整提供 target release metadata 及 checksum。"
            )
        normalized_target_release = _normalize_cutover_release_metadata(
            target_release_values[0], field_name="target_release_metadata"
        )
        _validate_release_pair(normalized_source_release, normalized_target_release)
        target_release_digest = target_release_digest_values[0]
        if (
            not isinstance(target_release_digest, str)
            or SHA256_PATTERN.fullmatch(target_release_digest) is None
        ):
            raise HostPortabilityError("target release metadata checksum 无效。")
        if target_release_digest != _canonical_json_sha256(normalized_target_release):
            raise HostPortabilityError("target release metadata checksum 不匹配。")
    elif target_release_values:
        raise HostPortabilityError(
            "prepared cutover 不得携带 target release metadata。"
        )

    backup_artifact_values = [
        state[key]
        for key in (
            "backup_artifact_sha256",
            "backupArtifactSha256",
            "backup_artifacts",
            "backupArtifacts",
            "paired_backup_artifacts",
            "pairedBackupArtifacts",
        )
        if key in state
    ]
    if backup_artifact_values and any(
        value != backup_artifact_values[0] for value in backup_artifact_values[1:]
    ):
        raise HostPortabilityError("paired backup artifact checksum 别名不一致。")
    backup_artifacts = _normalize_backup_artifact_identity(
        backup_artifact_values[0] if backup_artifact_values else None
    )

    preflight_values = [
        state[key]
        for key in ("target_preflight_evidence", "targetPreflightEvidence")
        if key in state
    ]
    if preflight_values and any(
        value != preflight_values[0] for value in preflight_values[1:]
    ):
        raise HostPortabilityError("target preflight evidence 别名不一致。")
    preflight_evidence: dict[str, Any] | None = None
    preflight_digest: str | None = None
    if phase == "accepted" and not preflight_values:
        raise HostPortabilityError("accepted cutover 缺少 target preflight evidence。")
    if phase == "prepared" and preflight_values:
        raise HostPortabilityError(
            "prepared cutover 不得携带 target preflight evidence。"
        )
    if preflight_values:
        preflight_evidence = _normalize_target_preflight_evidence(
            preflight_values[0],
            dataset_id=dataset_id,
            target_host_id=target_host_id,
            target_writer_generation=target_generation,
            target_release_metadata=normalized_target_release,
        )
        digest_values = [
            state[key]
            for key in (
                "target_preflight_evidence_sha256",
                "targetPreflightEvidenceSha256",
            )
            if key in state
        ]
        if digest_values and any(
            value != digest_values[0] for value in digest_values[1:]
        ):
            raise HostPortabilityError(
                "target preflight evidence checksum 别名不一致。"
            )
        if len(digest_values) != 1 or not isinstance(digest_values[0], str):
            raise HostPortabilityError("target preflight evidence checksum 缺失。")
        preflight_digest = digest_values[0]
        if SHA256_PATTERN.fullmatch(preflight_digest) is None:
            raise HostPortabilityError("target preflight evidence checksum 无效。")
        if preflight_digest != _canonical_json_sha256(preflight_evidence):
            raise HostPortabilityError("target preflight evidence checksum 不匹配。")
    elif any(
        key in state
        for key in (
            "target_preflight_evidence_sha256",
            "targetPreflightEvidenceSha256",
        )
    ):
        raise HostPortabilityError(
            "target preflight evidence checksum 无对应 evidence。"
        )

    return {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "kind": CUTOVER_KIND,
        "state": phase,
        "dataset_id": dataset_id,
        "backup_id": backup_id,
        "source_host_id": source_host_id,
        "target_host_id": target_host_id,
        "writer_generation": writer_generation,
        "source_writer_generation": source_generation,
        "target_writer_generation": target_generation,
        "source_project": source_project,
        "target_project": target_project,
        "source_quiescent": source_quiescent,
        "source_fully_stopped": source_fully_stopped,
        "source_gateway_stopped": source_fully_stopped,
        "source_stop_proof": source_stop_proof,
        "source_project_stop_proof": source_stop_proof,
        "target_preflight_status": preflight_status,
        "target_exposed": target_exposed,
        "target_write_accepted": target_write_accepted,
        "target_write_authorized": target_write_authorized,
        "created_at": created_at,
        "updated_at": updated_at,
        "source_release_metadata": normalized_source_release,
        "source_release_metadata_sha256": source_release_digest,
        # Legacy callers read release_metadata as the source identity.  It is
        # retained only as an exact alias and is never used for target data.
        "release_metadata": normalized_source_release,
        "release_metadata_sha256": source_release_digest,
        "backup_artifact_sha256": backup_artifacts,
        "backup_artifacts": backup_artifacts,
        **(
            {
                "target_preflight_evidence": preflight_evidence,
                "target_preflight_evidence_sha256": preflight_digest,
                "target_release_metadata": normalized_target_release,
                "target_release_metadata_sha256": target_release_digest,
            }
            if preflight_evidence is not None
            else {}
        ),
    }


def _stage_checksummed_cutover_state(
    path: str | Path,
    state: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, bytes, bytes | None, bytes | None]:
    """Validate and stage an exact cutover pair without promoting it."""

    normalized = validate_cutover_state(state)
    destination = Path(path).expanduser()
    if not destination.is_absolute():
        raise HostPortabilityError("cutover state 路径必须是绝对路径。")
    serialized = _canonical_cutover_json(normalized)
    checksum_path = _cutover_checksum_path(destination)
    expected_checksum = _checksum_line(
        destination, hashlib.sha256(serialized).hexdigest()
    )
    destination_temporary = _cutover_temp_path(destination, CUTOVER_WRITE_TEMP_SUFFIX)
    checksum_temporary = _cutover_temp_path(checksum_path, CUTOVER_WRITE_TEMP_SUFFIX)

    existing_destination = _read_optional_bytes(destination, label="cutover state 输出")
    existing_checksum = _read_optional_bytes(
        checksum_path, label="cutover state checksum"
    )
    staged_destination = _read_optional_bytes(
        destination_temporary, label="cutover state staging"
    )
    staged_checksum = _read_optional_bytes(
        checksum_temporary, label="cutover state checksum staging"
    )
    # A surviving temp file is the explicit evidence that a previous process
    # started this exact write.  Any different temp bytes are stale/tampered.
    if staged_destination is not None and staged_destination != serialized:
        raise HostPortabilityError("cutover state staging 与本次操作不一致。")
    if staged_checksum is not None and staged_checksum != expected_checksum:
        raise HostPortabilityError("cutover state checksum staging 与本次操作不一致。")
    if existing_destination is not None and existing_destination != serialized:
        raise HostPortabilityError("cutover state 输出与本次操作不一致。")
    if (
        existing_checksum is not None
        and existing_checksum != expected_checksum
        and not (existing_destination == serialized and staged_checksum is not None)
    ):
        # A stale sidecar is repairable only when a prior staged checksum
        # proves this exact transaction; otherwise it is treated as tamper.
        raise HostPortabilityError("cutover state checksum 校验失败。")
    _stage_cutover_bytes(destination_temporary, serialized, label="cutover state")
    _stage_cutover_bytes(
        checksum_temporary, expected_checksum, label="cutover state checksum"
    )
    return (
        normalized,
        serialized,
        expected_checksum,
        existing_destination,
        existing_checksum,
    )


def write_checksummed_cutover_state(path: str | Path, state: Mapping[str, Any]) -> Path:
    """Write a cutover pair with exact-byte crash recovery on retry."""

    (
        _normalized,
        serialized,
        expected_checksum,
        existing_destination,
        existing_checksum,
    ) = _stage_checksummed_cutover_state(path, state)
    destination = Path(path).expanduser()
    checksum_path = _cutover_checksum_path(destination)
    destination_temporary = _cutover_temp_path(destination, CUTOVER_WRITE_TEMP_SUFFIX)
    checksum_temporary = _cutover_temp_path(checksum_path, CUTOVER_WRITE_TEMP_SUFFIX)
    if existing_destination == serialized and existing_checksum == expected_checksum:
        _remove_cutover_temp(destination_temporary)
        _remove_cutover_temp(checksum_temporary)
        return destination
    if existing_destination != serialized:
        _replace_cutover_staging(
            destination_temporary, destination, label="cutover state"
        )
    else:
        _remove_cutover_temp(destination_temporary)
    if existing_checksum != expected_checksum:
        _replace_cutover_staging(
            checksum_temporary, checksum_path, label="cutover state checksum"
        )
    else:
        _remove_cutover_temp(checksum_temporary)
    _remove_cutover_temp(destination_temporary)
    _remove_cutover_temp(checksum_temporary)
    return destination


def validate_checksummed_cutover_state(path: str | Path) -> dict[str, Any]:
    """Validate cutover JSON, sidecar checksum, and state generation."""

    candidate = Path(path).expanduser()
    if not candidate.is_absolute() or not candidate.is_file():
        raise HostPortabilityError("cutover state 文件不存在。")
    _assert_cutover_state_unconsumed(candidate)
    checksum_path = _cutover_checksum_path(candidate)
    if not checksum_path.is_file():
        raise HostPortabilityError("cutover state checksum 文件不存在。")
    try:
        checksum_text = checksum_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise HostPortabilityError("cutover state checksum 无法读取。") from exc
    match = CHECKSUM_LINE_PATTERN.fullmatch(checksum_text)
    actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if match is None or match.group(2) != candidate.name or match.group(1) != actual:
        raise HostPortabilityError("cutover state checksum 校验失败。")
    return validate_cutover_state(
        _read_json_mapping(candidate, "cutover state JSON 无法读取。")
    )


def build_cutover_metadata(
    *,
    dataset_id: str,
    backup_id: str,
    source_host_id: str,
    target_host_id: str,
    writer_generation: int,
    state: str = "prepared",
    source_project: str = DEFAULT_PROJECT_NAMES["formal"],
    target_project: str = DEFAULT_PROJECT_NAMES["formal"],
    source_quiescent: bool = True,
    source_fully_stopped: bool | None = None,
    source_gateway_stopped: bool | None = None,
    target_preflight_status: str = "pending",
    target_preflight_evidence: Mapping[str, Any] | None = None,
    target_exposed: bool = False,
    target_write_accepted: bool = False,
    target_write_authorized: bool = False,
    source_writer_generation: int | None = None,
    target_writer_generation: int | None = None,
    backup_artifact_sha256: Mapping[str, str] | None = None,
    backup_artifacts: Mapping[str, str] | None = None,
    release_metadata: Mapping[str, Any] | None = None,
    source_release_metadata: Mapping[str, Any] | None = None,
    target_release_metadata: Mapping[str, Any] | None = None,
    source_stop_proof: Mapping[str, Any] | None = None,
    created_at: datetime | str | None = None,
    updated_at: datetime | str | None = None,
) -> dict[str, Any]:
    if (
        source_stop_proof is not None
        and source_fully_stopped is None
        and source_gateway_stopped is None
    ):
        proof_stopped = _cutover_value(
            source_stop_proof,
            "whole_project_stopped",
            "wholeProjectStopped",
            "whole_project",
            "wholeProject",
        )
        if isinstance(proof_stopped, bool):
            source_fully_stopped = proof_stopped
    resolved_source_stopped = _resolve_source_stop_proof(
        source_fully_stopped=source_fully_stopped,
        source_gateway_stopped=source_gateway_stopped,
    )
    created_value = _cutover_time_value(created_at)
    updated_value = _cutover_time_value(updated_at) or created_value
    resolved_source_generation = _normalize_writer_generation(
        source_writer_generation
        if source_writer_generation is not None
        else writer_generation,
        "source_writer_generation",
    )
    resolved_target_generation = _normalize_writer_generation(
        target_writer_generation
        if target_writer_generation is not None
        else resolved_source_generation + 1,
        "target_writer_generation",
    )
    if resolved_target_generation != resolved_source_generation + 1:
        raise HostPortabilityError("cutover target writer generation 不是下一代。")
    if (
        backup_artifact_sha256 is not None
        and backup_artifacts is not None
        and _normalize_backup_artifact_identity(backup_artifact_sha256)
        != _normalize_backup_artifact_identity(backup_artifacts)
    ):
        raise HostPortabilityError("paired backup artifact checksum 别名不一致。")
    resolved_artifacts = _normalize_backup_artifact_identity(
        backup_artifact_sha256
        if backup_artifact_sha256 is not None
        else backup_artifacts
    )
    source_release_values = [
        value
        for value in (release_metadata, source_release_metadata)
        if value is not None
    ]
    if not source_release_values:
        raise HostPortabilityError("cutover source release metadata 必须完整提供。")
    normalized_source_release = _normalize_cutover_release_metadata(
        source_release_values[0], field_name="source_release_metadata"
    )
    if len(source_release_values) == 2:
        other_source_release = _normalize_cutover_release_metadata(
            source_release_values[1], field_name="source_release_metadata"
        )
        if other_source_release != normalized_source_release:
            raise HostPortabilityError("source release metadata 参数不一致。")
    if state == "prepared" and target_release_metadata is not None:
        raise HostPortabilityError(
            "prepared cutover 不得携带 target release metadata。"
        )
    normalized_target_release = (
        _normalize_cutover_release_metadata(
            target_release_metadata, field_name="target_release_metadata"
        )
        if target_release_metadata is not None
        else (
            _extract_target_release_metadata(target_preflight_evidence)
            if state == "accepted" and target_preflight_evidence is not None
            else None
        )
    )
    if state == "accepted" and normalized_target_release is None:
        raise HostPortabilityError(
            "accepted cutover 必须提供 target release metadata。"
        )
    if normalized_target_release is not None:
        _validate_release_pair(normalized_source_release, normalized_target_release)
    normalized_proof = _normalize_source_stop_proof(
        source_stop_proof,
        source_project=source_project,
        fallback_stopped=resolved_source_stopped,
        observed_at=created_value,
    )
    normalized_preflight = (
        _normalize_target_preflight_evidence(
            target_preflight_evidence,
            dataset_id=dataset_id,
            target_host_id=target_host_id,
            target_writer_generation=resolved_target_generation,
            target_release_metadata=normalized_target_release,
        )
        if target_preflight_evidence is not None
        else None
    )
    preflight_payload: dict[str, Any] = {}
    if normalized_preflight is not None:
        if normalized_target_release is None:
            raise HostPortabilityError(
                "target preflight 必须绑定 target release metadata。"
            )
        preflight_payload = {
            "target_preflight_evidence": normalized_preflight,
            "target_preflight_evidence_sha256": _canonical_json_sha256(
                normalized_preflight
            ),
            "target_release_metadata": normalized_target_release,
            "target_release_metadata_sha256": _canonical_json_sha256(
                normalized_target_release
            ),
        }
    payload: dict[str, Any] = {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "kind": CUTOVER_KIND,
        "state": state,
        "dataset_id": dataset_id,
        "backup_id": backup_id,
        "source_host_id": source_host_id,
        "target_host_id": target_host_id,
        # Keep the historical single-field meaning: a prepared state names
        # the current source writer, while an accepted state names the newly
        # accepted target writer.  The explicit source/target fields below
        # are authoritative for both phases.
        "writer_generation": (
            resolved_source_generation
            if state == "prepared"
            else resolved_target_generation
        ),
        "source_writer_generation": resolved_source_generation,
        "target_writer_generation": resolved_target_generation,
        "source_project": source_project,
        "target_project": target_project,
        "source_quiescent": source_quiescent,
        "source_fully_stopped": resolved_source_stopped,
        "source_gateway_stopped": resolved_source_stopped,
        "source_stop_proof": normalized_proof,
        "source_project_stop_proof": normalized_proof,
        "target_preflight_status": target_preflight_status,
        "target_exposed": target_exposed,
        "target_write_accepted": target_write_accepted,
        "target_write_authorized": target_write_authorized,
        "created_at": created_value,
        "updated_at": updated_value,
        "source_release_metadata": normalized_source_release,
        "source_release_metadata_sha256": _canonical_json_sha256(
            normalized_source_release
        ),
        # Compatibility aliases retain the historical source-only meaning.
        "release_metadata": normalized_source_release,
        "release_metadata_sha256": _canonical_json_sha256(normalized_source_release),
        "backup_artifact_sha256": resolved_artifacts,
        "backup_artifacts": resolved_artifacts,
        **preflight_payload,
    }
    return validate_cutover_state(payload)


def _cutover_time_value(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise HostPortabilityError("cutover 时间必须包含时区。")
        return value.astimezone(UTC).isoformat()
    _validate_timestamp(value, required=True)
    return value


def _backup_manifest_identity(manifest: Mapping[str, Any]) -> tuple[str, int, str]:
    if not isinstance(manifest, Mapping):
        raise MigrationInputError("跨主机 backup manifest 无效。")
    return (
        _normalize_cutover_identifier(manifest.get("dataset_id"), "dataset_id"),
        _normalize_writer_generation(manifest.get("writer_generation")),
        _normalize_cutover_identifier(manifest.get("source_host_id"), "source_host_id"),
    )


def prepare_cutover(
    backup_dir: str | Path | None = None,
    *,
    backup_manifest: Mapping[str, Any] | None = None,
    dataset_id: str | None = None,
    backup_id: str | None = None,
    source_host_id: str | None = None,
    target_host_id: str,
    writer_generation: int | None = None,
    source_project: str = DEFAULT_PROJECT_NAMES["formal"],
    target_project: str = DEFAULT_PROJECT_NAMES["formal"],
    source_quiescent: bool = True,
    in_progress_attempts: int | None = None,
    source_fully_stopped: bool | None = None,
    source_gateway_stopped: bool | None = None,
    source_stopped: bool | None = None,
    source_stop_proof: Mapping[str, Any] | None = None,
    backup_artifact_sha256: Mapping[str, str] | None = None,
    backup_artifacts: Mapping[str, str] | None = None,
    release_metadata: Mapping[str, Any] | None = None,
    state_path: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prepare a cutover attestation; this function never stops a service."""

    manifest = backup_manifest
    resolved_backup: Path | None = None
    resolved_artifacts: Mapping[str, str] | None = None
    if backup_dir is not None:
        resolved_backup = Path(backup_dir).expanduser().resolve(strict=False)
        try:
            # A cutover is a writer-fence boundary, not merely a portable
            # restore input.  Keep ``validate_migration_input`` for staging
            # and ordinary migration, and require the dedicated validator so
            # a legacy ``backup`` artifact cannot be promoted into cutover.
            manifest = validate_cutover_backup(resolved_backup)
        except (BackupError, OSError, UnicodeError, ValueError) as exc:
            raise MigrationInputError(
                "cutover 输入必须是已完成、backup_kind=cutover 且绑定 identity 的 "
                "paired backup。"
            ) from exc
        resolved_artifacts = _backup_artifact_checksums(resolved_backup)
    if manifest is not None:
        if manifest.get("backup_kind") != "cutover":
            raise MigrationInputError(
                "cutover backup manifest 必须标记 backup_kind=cutover。"
            )
        manifest_dataset, manifest_generation, manifest_source = (
            _backup_manifest_identity(manifest)
        )
        if dataset_id is not None and dataset_id != manifest_dataset:
            raise MigrationInputError("cutover dataset_id 与 backup manifest 不一致。")
        if writer_generation is not None and writer_generation != manifest_generation:
            raise MigrationInputError(
                "cutover writer_generation 与 backup manifest 不一致。"
            )
        if source_host_id is not None and source_host_id != manifest_source:
            raise MigrationInputError(
                "cutover source_host_id 与 backup manifest 不一致。"
            )
        dataset_id = manifest_dataset
        writer_generation = manifest_generation
        source_host_id = manifest_source
        if backup_id is None and resolved_backup is not None:
            backup_id = resolved_backup.name
        if resolved_backup is not None and backup_id != resolved_backup.name:
            raise MigrationInputError("cutover backup_id 与 backup 路径不一致。")
    if dataset_id is None or writer_generation is None or source_host_id is None:
        raise MigrationInputError("cutover 必须提供完整的 backup identity。")
    if backup_id is None:
        raise MigrationInputError("cutover 必须提供 backup_id。")
    if resolved_artifacts is not None:
        if backup_artifact_sha256 is not None and _normalize_backup_artifact_identity(
            backup_artifact_sha256
        ) != dict(resolved_artifacts):
            raise MigrationInputError("paired backup artifact checksum 与文件不一致。")
        if backup_artifacts is not None and _normalize_backup_artifact_identity(
            backup_artifacts
        ) != dict(resolved_artifacts):
            raise MigrationInputError("paired backup artifact checksum 与文件不一致。")
        resolved_artifact_value: Mapping[str, str] = resolved_artifacts
    else:
        if (
            backup_artifact_sha256 is not None
            and backup_artifacts is not None
            and _normalize_backup_artifact_identity(backup_artifact_sha256)
            != _normalize_backup_artifact_identity(backup_artifacts)
        ):
            raise MigrationInputError("paired backup artifact checksum 别名不一致。")
        resolved_artifact_value = (
            backup_artifact_sha256
            if backup_artifact_sha256 is not None
            else backup_artifacts
        )
    if resolved_artifact_value is None:
        raise MigrationInputError("cutover 必须绑定 paired backup artifact checksum。")
    if release_metadata is None:
        raise MigrationInputError("cutover 必须绑定完整 release metadata。")
    normalized_release = _normalize_cutover_release_metadata(
        release_metadata, field_name="source_release_metadata"
    )
    if manifest is not None and normalized_release["migration_head"] != str(
        manifest["migration_head"]
    ):
        raise MigrationInputError("release migration head 与 backup manifest 不一致。")
    if in_progress_attempts is not None:
        if isinstance(in_progress_attempts, bool) or in_progress_attempts < 0:
            raise MigrationInputError("in_progress_attempts 无效。")
        source_quiescent = source_quiescent and in_progress_attempts == 0
    if (
        source_stop_proof is not None
        and source_fully_stopped is None
        and source_gateway_stopped is None
        and source_stopped is None
    ):
        proof_stopped = _cutover_value(
            source_stop_proof,
            "whole_project_stopped",
            "wholeProjectStopped",
            "whole_project",
            "wholeProject",
        )
        if isinstance(proof_stopped, bool):
            source_fully_stopped = proof_stopped
    source_fully_stopped = _resolve_source_stop_proof(
        source_fully_stopped=source_fully_stopped,
        source_gateway_stopped=source_gateway_stopped,
        source_stopped=source_stopped,
    )
    if not source_quiescent:
        raise MigrationInputError("cutover source 仍有进行中的考试。")
    existing_prepared_retry = (
        _load_prepared_retry_state(state_path) if state_path is not None else None
    )
    prepared_created_at = (
        existing_prepared_retry[1]
        if existing_prepared_retry is not None and now is None
        else now
    )
    prepared_updated_at = (
        existing_prepared_retry[2]
        if existing_prepared_retry is not None and now is None
        else now
    )
    prepared = build_cutover_metadata(
        dataset_id=dataset_id,
        backup_id=backup_id,
        source_host_id=source_host_id,
        target_host_id=target_host_id,
        writer_generation=writer_generation,
        source_project=source_project,
        target_project=target_project,
        source_quiescent=True,
        source_fully_stopped=source_fully_stopped,
        source_stop_proof=source_stop_proof,
        backup_artifact_sha256=resolved_artifact_value,
        source_release_metadata=normalized_release,
        created_at=prepared_created_at,
        updated_at=prepared_updated_at,
    )
    if existing_prepared_retry is not None and prepared != existing_prepared_retry[0]:
        raise MigrationInputError(
            "prepared cutover state 与本次 immutable input 不一致。"
        )
    if state_path is not None:
        write_checksummed_cutover_state(state_path, prepared)
    return prepared


def _recover_prepared_state_after_claim_crash(
    source_path: Path,
    accepted_path: Path,
) -> dict[str, Any]:
    """Recover the original prepared view from an exact consumed half-commit."""

    source_bytes = _read_optional_bytes(source_path, label="cutover source state")
    if source_bytes is None:
        raise HostPortabilityError("cutover source state 文件不存在。")
    source_state = _parse_cutover_json(
        source_bytes, error="consumed source state JSON 无法读取。"
    )
    if source_state.get("state") != "consumed":
        raise HostPortabilityError("cutover source state 阶段无效。")
    marker_bytes, marker_payload, marker_checksum_valid = _claim_marker_snapshot(
        source_path
    )
    source_digest = marker_payload.get("source_sha256")
    accepted_digest = source_state.get("accepted_sha256")
    accepted_name = source_state.get("accepted_state_name")
    accepted_identity = source_state.get("accepted_state_identity")
    expected_accepted_identity = _cutover_destination_identity(accepted_path)
    if (
        not isinstance(source_digest, str)
        or SHA256_PATTERN.fullmatch(source_digest) is None
        or not isinstance(accepted_digest, str)
        or SHA256_PATTERN.fullmatch(accepted_digest) is None
        or accepted_name != accepted_path.name
        or accepted_identity != expected_accepted_identity
        or source_state.get("consumed_source_sha256") != source_digest
    ):
        raise HostPortabilityError("prepared cutover state 已被消费。")
    prepared_candidate = dict(source_state)
    prepared_candidate["state"] = "prepared"
    for key in (
        "consumed_at",
        "consumed_source_sha256",
        "accepted_sha256",
        "accepted_state_name",
        "accepted_state_identity",
    ):
        prepared_candidate.pop(key, None)
    prepared = validate_cutover_state(prepared_candidate)
    prepared_serialized = _canonical_cutover_json(prepared)
    if hashlib.sha256(prepared_serialized).hexdigest() != source_digest:
        raise HostPortabilityError("consumed source state 与原 prepared state 不匹配。")
    consumed_at = source_state.get("consumed_at")
    if not isinstance(consumed_at, str):
        raise HostPortabilityError("consumed source state 时间无效。")
    _validate_timestamp(consumed_at, required=True)
    expected_consumed = dict(prepared)
    expected_consumed.update(
        {
            "state": "consumed",
            "consumed_at": consumed_at,
            "consumed_source_sha256": source_digest,
            "accepted_sha256": accepted_digest,
            "accepted_state_name": accepted_name,
            "accepted_state_identity": accepted_identity,
        }
    )
    expected_consumed_bytes = _canonical_cutover_json(expected_consumed)
    if source_bytes != expected_consumed_bytes:
        raise HostPortabilityError("consumed source state 内容不一致。")
    consumed_state_digest = hashlib.sha256(source_bytes).hexdigest()
    marker_expected: dict[str, Any] = {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "kind": "formal-cutover-consumed",
        "state": "consumed",
        "source_sha256": source_digest,
        "consumed_state_sha256": consumed_state_digest,
        "accepted_sha256": accepted_digest,
        "accepted_state_name": accepted_name,
        "accepted_state_identity": accepted_identity,
        "consumed_at": consumed_at,
    }
    if marker_payload["state"] == "consumed":
        if marker_bytes != _canonical_cutover_json(marker_expected):
            raise HostPortabilityError("consumed marker 内容不一致。")
        if marker_payload.get("accepted_sha256") != accepted_digest:
            raise HostPortabilityError("consumed marker 与 source state 不匹配。")
    else:
        if marker_payload.get("accepted_state_name") != accepted_name:
            raise HostPortabilityError("cutover reservation output 不一致。")
        if marker_payload.get("accepted_state_identity") != accepted_identity:
            raise HostPortabilityError("cutover reservation output identity 不一致。")
        if not marker_checksum_valid:
            raise HostPortabilityError("cutover reservation checksum 校验失败。")
    return prepared


def _load_path_backed_prepared_state(
    source_path: Path,
    accepted_path: Path,
) -> dict[str, Any]:
    source_bytes = _read_optional_bytes(source_path, label="cutover source state")
    if source_bytes is None:
        raise HostPortabilityError("cutover state 文件不存在。")
    source_state = _parse_cutover_json(
        source_bytes, error="cutover source state JSON 无法读取。"
    )
    if source_state.get("state") == "consumed":
        return _recover_prepared_state_after_claim_crash(source_path, accepted_path)
    return validate_checksummed_cutover_state(source_path)


def _existing_accepted_timestamp(path: Path) -> str | None:
    payload = _read_optional_bytes(path, label="accepted cutover state")
    if payload is None:
        payload = _read_optional_bytes(
            _cutover_temp_path(path, CUTOVER_WRITE_TEMP_SUFFIX),
            label="accepted cutover state staging",
        )
    if payload is None:
        return None
    value = _parse_cutover_json(payload, error="accepted cutover state JSON 无效。")
    if value.get("state") != "accepted":
        return None
    timestamp = value.get("updated_at")
    if timestamp is None:
        return None
    if not isinstance(timestamp, str):
        raise HostPortabilityError("accepted cutover state 时间无效。")
    _validate_timestamp(timestamp, required=True)
    return timestamp


def _validate_accepted_against_prepared(
    accepted: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> None:
    """Bind a recovered accepted payload to its prepared source identity."""

    for key in (
        "dataset_id",
        "backup_id",
        "source_host_id",
        "target_host_id",
        "source_project",
        "target_project",
        "source_writer_generation",
        "target_writer_generation",
        "source_quiescent",
        "source_fully_stopped",
        "source_gateway_stopped",
        "source_stop_proof",
        "source_project_stop_proof",
        "source_release_metadata",
        "source_release_metadata_sha256",
        "release_metadata",
        "release_metadata_sha256",
        "backup_artifact_sha256",
        "backup_artifacts",
    ):
        if accepted.get(key) != prepared.get(key):
            raise HostPortabilityError(
                f"accepted cutover 与 prepared state identity 不一致：{key}。"
            )
    if (
        accepted.get("target_exposed") is not False
        or accepted.get("target_write_accepted") is not False
    ):
        raise HostPortabilityError("accepted cutover target 已暴露或接受写入。")


def _read_recovery_accepted_state(
    path: Path,
    *,
    require_staging_pair: bool = False,
) -> tuple[dict[str, Any], bytes, str] | None:
    """Read an accepted payload and prove any surviving write staging."""

    destination_temporary = _cutover_temp_path(path, CUTOVER_WRITE_TEMP_SUFFIX)
    checksum_path = _cutover_checksum_path(path)
    checksum_temporary = _cutover_temp_path(checksum_path, CUTOVER_WRITE_TEMP_SUFFIX)
    canonical = _read_optional_bytes(path, label="accepted cutover state")
    staged = _read_optional_bytes(
        destination_temporary, label="accepted cutover state staging"
    )
    canonical_checksum = _read_optional_bytes(
        checksum_path, label="accepted cutover state checksum"
    )
    staged_checksum = _read_optional_bytes(
        checksum_temporary, label="accepted cutover state checksum staging"
    )
    if staged is not None and canonical is not None and staged != canonical:
        raise HostPortabilityError("accepted cutover state staging 与输出不一致。")
    if require_staging_pair and (staged is None or staged_checksum is None):
        raise HostPortabilityError("accepted cutover state staging 不完整。")
    payload = staged if staged is not None else canonical
    if payload is None:
        if staged_checksum is not None:
            raise HostPortabilityError("accepted cutover state staging 不完整。")
        return None
    accepted = validate_cutover_state(
        _parse_cutover_json(payload, error="accepted cutover state JSON 无效。")
    )
    if accepted["state"] != "accepted":
        raise HostPortabilityError("accepted cutover state 阶段无效。")
    canonical_payload = _canonical_cutover_json(accepted)
    if payload != canonical_payload:
        raise HostPortabilityError("accepted cutover state 内容不一致。")
    accepted_digest = hashlib.sha256(payload).hexdigest()
    expected_checksum = _checksum_line(path, accepted_digest)
    if staged_checksum is not None and staged_checksum != expected_checksum:
        raise HostPortabilityError("accepted cutover state checksum staging 校验失败。")
    # A stale canonical sidecar is repairable only when the exact staged
    # checksum is also present; otherwise it is indistinguishable from
    # tampering.
    if (
        canonical_checksum is not None
        and canonical_checksum != expected_checksum
        and staged_checksum != expected_checksum
    ):
        raise HostPortabilityError("accepted cutover state checksum 校验失败。")
    return accepted, payload, accepted_digest


def _load_prepared_retry_state(
    path: str | Path,
) -> tuple[dict[str, Any], str, str] | None:
    """Load exact prepared bytes left by an interrupted pair write."""

    destination = Path(path).expanduser()
    if not destination.is_absolute():
        raise HostPortabilityError("cutover state 路径必须是绝对路径。")
    marker_path = _cutover_consumed_marker_path(destination)
    marker_checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    if marker_path.exists() or marker_checksum_path.exists():
        raise HostPortabilityError("prepared cutover state 已被保留或消费。")
    payload = _read_optional_bytes(destination, label="prepared cutover state")
    if payload is None:
        payload = _read_optional_bytes(
            _cutover_temp_path(destination, CUTOVER_WRITE_TEMP_SUFFIX),
            label="prepared cutover state staging",
        )
    if payload is None:
        return None
    normalized = validate_cutover_state(
        _parse_cutover_json(payload, error="prepared cutover state JSON 无效。")
    )
    if normalized["state"] != "prepared":
        raise HostPortabilityError("prepared cutover state 阶段无效。")
    if payload != _canonical_cutover_json(normalized):
        raise HostPortabilityError("prepared cutover state 内容不一致。")
    expected_checksum = _checksum_line(destination, hashlib.sha256(payload).hexdigest())
    checksum_path = _cutover_checksum_path(destination)
    checksum = _read_optional_bytes(
        checksum_path, label="prepared cutover state checksum"
    )
    checksum_staging = _read_optional_bytes(
        _cutover_temp_path(checksum_path, CUTOVER_WRITE_TEMP_SUFFIX),
        label="prepared cutover state checksum staging",
    )
    # A surviving exact checksum staging file can repair a canonical sidecar
    # that was replaced with stale bytes during the same write.
    if (
        checksum is not None
        and checksum != expected_checksum
        and checksum_staging != expected_checksum
    ):
        raise HostPortabilityError("prepared cutover state checksum 校验失败。")
    if checksum_staging is not None and checksum_staging != expected_checksum:
        raise HostPortabilityError("prepared cutover state checksum staging 校验失败。")
    # The pair writer can stop after durable JSON but before creating either
    # checksum file.  prepare_cutover reconstructs the complete payload from
    # immutable caller inputs below and compares it byte-for-byte before the
    # sidecar is repaired; no unchecked state is accepted here by itself.
    created_at = normalized.get("created_at")
    updated_at = normalized.get("updated_at")
    if not isinstance(created_at, str) or not isinstance(updated_at, str):
        raise HostPortabilityError("prepared cutover state timestamp 无效。")
    return normalized, created_at, updated_at


def recover_cutover_state(
    source: str | Path,
    accepted: str | Path,
) -> dict[str, Any]:
    """Repair only an already-started exact cutover file transaction.

    This entry point intentionally accepts no target/preflight/business
    inputs.  It may finish a staged reservation, accepted output, or claim;
    it cannot create a fresh reservation when no marker or complete accepted
    staging evidence is present.  Host wrappers can call it before their
    strict checksum gates.
    """

    source_path = Path(source).expanduser()
    accepted_path = Path(accepted).expanduser()
    if (
        not source_path.is_absolute()
        or not accepted_path.is_absolute()
        or source_path.is_symlink()
        or accepted_path.is_symlink()
        or source_path.resolve() == accepted_path.resolve()
    ):
        raise HostPortabilityError("cutover recovery 路径必须是不同的绝对普通文件。")
    marker_path = _cutover_consumed_marker_path(source_path)
    marker_checksum_path = marker_path.with_suffix(
        marker_path.suffix + CONSUMED_MARKER_CHECKSUM_SUFFIX
    )
    marker_temporary = _cutover_temp_path(marker_path, CUTOVER_WRITE_TEMP_SUFFIX)
    accepted_temporary = _cutover_temp_path(accepted_path, CUTOVER_WRITE_TEMP_SUFFIX)
    accepted_checksum_temporary = _cutover_temp_path(
        _cutover_checksum_path(accepted_path), CUTOVER_WRITE_TEMP_SUFFIX
    )
    marker_evidence = any(
        path.exists() for path in (marker_path, marker_checksum_path, marker_temporary)
    )
    accepted_staging_evidence = any(
        path.exists() for path in (accepted_temporary, accepted_checksum_temporary)
    )
    if not marker_evidence and not accepted_staging_evidence:
        raise HostPortabilityError("没有可恢复的 cutover half-commit。")

    source_bytes = _read_optional_bytes(source_path, label="cutover source state")
    if source_bytes is None:
        raise HostPortabilityError("cutover source state 文件不存在。")
    source_payload = _parse_cutover_json(
        source_bytes, error="cutover source state JSON 无法读取。"
    )
    marker_payload: dict[str, Any] | None = None
    if marker_path.exists():
        _, marker_payload, _ = _claim_marker_snapshot(source_path)
    elif marker_checksum_path.exists():
        raise HostPortabilityError("cutover consumed marker 不完整。")
    marker_temporary_payload: dict[str, Any] | None = None
    if marker_payload is None and marker_temporary.exists():
        marker_temporary_bytes = _read_optional_bytes(
            marker_temporary, label="cutover reservation staging"
        )
        if marker_temporary_bytes is None:
            raise HostPortabilityError("cutover reservation staging 不完整。")
        marker_temporary_payload = _validate_consumed_marker_payload(
            _parse_cutover_json(
                marker_temporary_bytes,
                error="cutover reservation staging JSON 无效。",
            )
        )

    # A reservation may have staged only its marker so far.  _reserve sees
    # the existing marker temp and never creates a new reservation in this
    # mode; it merely installs/repairs that exact payload.
    if marker_payload is None:
        if source_payload.get("state") != "prepared":
            raise HostPortabilityError("cutover source state 阶段无效。")
        prepared = validate_checksummed_cutover_state(source_path)
        if (
            marker_temporary_payload is not None
            and marker_temporary_payload.get("accepted_sha256") is None
        ):
            reservation = _reserve_cutover_state(source_path, accepted_path)
            return {
                "status": "recovered",
                "state": reservation["state"],
                "source_sha256": reservation["source_sha256"],
            }
        # The JSON staging file is itself the exact payload proof for this
        # phase.  The accepted identity check below binds it to prepared
        # state before the reservation is created; a checksum staging file
        # may not have been written yet.
        accepted_record = _read_recovery_accepted_state(accepted_path)
        if accepted_record is None:
            raise HostPortabilityError("cutover reservation 缺少 accepted output。")
        accepted_state, _accepted_bytes, accepted_digest = accepted_record
        if marker_temporary_payload is not None and (
            marker_temporary_payload.get("accepted_sha256") != accepted_digest
        ):
            raise HostPortabilityError("cutover reservation accepted digest 不一致。")
        _validate_accepted_against_prepared(accepted_state, prepared)
        reservation = _reserve_cutover_state(
            source_path,
            accepted_path,
            accepted_digest=accepted_digest,
        )
        write_checksummed_cutover_state(accepted_path, accepted_state)
        _claim_cutover_state(
            source_path,
            source_digest=reservation["source_sha256"],
            accepted_digest=accepted_digest,
            accepted_state_name=accepted_path.name,
            accepted_state_identity=_cutover_destination_identity(accepted_path),
            prepared_state=prepared,
        )
        return {
            "status": "recovered",
            "state": "consumed",
            "source_sha256": reservation["source_sha256"],
            "accepted_sha256": accepted_digest,
            "accepted_state_name": accepted_path.name,
        }

    accepted_record = _read_recovery_accepted_state(accepted_path)
    if accepted_record is None:
        if marker_payload["state"] != "reserved":
            raise HostPortabilityError("consumed cutover state 缺少 accepted output。")
        if marker_payload.get("accepted_sha256") is not None:
            raise HostPortabilityError("cutover reservation 缺少 accepted output。")
        reservation = _reserve_cutover_state(source_path, accepted_path)
        return {
            "status": "recovered",
            "state": reservation["state"],
            "source_sha256": reservation["source_sha256"],
        }
    accepted_state, _accepted_bytes, accepted_digest = accepted_record
    if marker_payload["state"] == "reserved" and (
        marker_payload.get("accepted_sha256") != accepted_digest
    ):
        raise HostPortabilityError("cutover reservation 缺少 accepted digest。")

    if source_payload.get("state") == "consumed":
        prepared = _recover_prepared_state_after_claim_crash(source_path, accepted_path)
    elif source_payload.get("state") == "prepared":
        prepared = validate_checksummed_cutover_state(source_path)
    else:
        raise HostPortabilityError("cutover source state 阶段无效。")
    _validate_accepted_against_prepared(accepted_state, prepared)
    reservation = _reserve_cutover_state(
        source_path,
        accepted_path,
        accepted_digest=accepted_digest,
    )
    write_checksummed_cutover_state(accepted_path, accepted_state)
    _claim_cutover_state(
        source_path,
        source_digest=reservation["source_sha256"],
        accepted_digest=accepted_digest,
        accepted_state_name=accepted_path.name,
        accepted_state_identity=_cutover_destination_identity(accepted_path),
        prepared_state=prepared,
    )
    return {
        "status": "recovered",
        "state": "consumed",
        "source_sha256": reservation["source_sha256"],
        "accepted_sha256": accepted_digest,
        "accepted_state_name": accepted_path.name,
    }


def accept_cutover(
    state: Mapping[str, Any] | str | Path,
    *,
    target_host_id: str | None = None,
    source_fully_stopped: bool | None = None,
    source_gateway_stopped: bool | None = None,
    source_stopped: bool | None = None,
    target_preflight_status: str = "passed",
    target_preflight: Mapping[str, Any] | bool | None = None,
    target_preflight_evidence: Mapping[str, Any] | None = None,
    target_writer_generation: int | None = None,
    target_write_accepted: bool | None = None,
    target_exposed: bool | None = None,
    backup_artifact_sha256: Mapping[str, str] | None = None,
    release_metadata: Mapping[str, Any] | None = None,
    source_release_metadata: Mapping[str, Any] | None = None,
    target_release_metadata: Mapping[str, Any] | None = None,
    state_path: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Authorize a prepared cutover without stopping or exposing any host.

    The target fence is an input contract: callers must prove that the target
    is still private and has not accepted formal writes.  The returned
    ``accepted`` state grants a later, separately audited exposure step via
    ``target_write_authorized``; this function performs no external action.
    """

    source_state_path: Path | None = None
    if isinstance(state, (str, Path)):
        if state_path is None:
            raise HostPortabilityError(
                "path-backed prepared state 必须提供新的 state_path。"
            )
        source_state_path = Path(state).expanduser().resolve()
        destination_state_path = Path(state_path).expanduser()
        if not destination_state_path.is_absolute():
            raise HostPortabilityError("accepted cutover state 路径必须是绝对路径。")
        if destination_state_path.resolve() == source_state_path:
            raise HostPortabilityError(
                "accepted cutover state 必须写入不同于 prepared source 的路径。"
            )
        destination_resolved = destination_state_path.resolve()
        reserved_paths = {
            source_state_path,
            _cutover_checksum_path(source_state_path),
            _cutover_consumed_marker_path(source_state_path),
            _cutover_consumed_marker_path(source_state_path).with_suffix(
                _cutover_consumed_marker_path(source_state_path).suffix
                + CONSUMED_MARKER_CHECKSUM_SUFFIX
            ),
        }
        if destination_resolved in reserved_paths:
            raise HostPortabilityError("accepted cutover state 输出路径不安全。")
        prepared = _load_path_backed_prepared_state(
            source_state_path, destination_state_path
        )
    else:
        prepared = validate_cutover_state(state)
    if prepared["state"] != "prepared":
        raise HostPortabilityError("cutover 只能从 prepared 阶段 accept。")
    if target_host_id is not None and target_host_id != prepared["target_host_id"]:
        raise HostPortabilityError(
            "accept target host identity 与 prepared state 不一致。"
        )
    if target_exposed is None or target_write_accepted is None:
        raise HostPortabilityError(
            "accept cutover 必须显式证明 target 尚未暴露且尚未接受正式写入。"
        )
    if target_exposed or target_write_accepted:
        raise HostPortabilityError(
            "accept cutover 拒绝已暴露或已接受正式写入的 target。"
        )
    source_release_values = [
        value
        for value in (release_metadata, source_release_metadata)
        if value is not None
    ]
    if source_release_values:
        normalized_source_release = _normalize_cutover_release_metadata(
            source_release_values[0], field_name="source_release_metadata"
        )
        if (
            len(source_release_values) == 2
            and _normalize_cutover_release_metadata(
                source_release_values[1], field_name="source_release_metadata"
            )
            != normalized_source_release
        ):
            raise HostPortabilityError("source release metadata 参数不一致。")
        if normalized_source_release != prepared["source_release_metadata"]:
            raise HostPortabilityError(
                "accept source release metadata 与 prepared state 不一致。"
            )
    if (
        backup_artifact_sha256 is not None
        and _normalize_backup_artifact_identity(backup_artifact_sha256)
        != prepared["backup_artifact_sha256"]
    ):
        raise HostPortabilityError(
            "accept paired backup artifact checksum 与 prepared state 不一致。"
        )
    source_fully_stopped = _resolve_source_stop_proof(
        source_fully_stopped=source_fully_stopped,
        source_gateway_stopped=source_gateway_stopped,
        source_stopped=source_stopped,
    )
    if target_preflight is not None:
        if isinstance(target_preflight, Mapping):
            if (
                target_preflight_evidence is not None
                and target_preflight_evidence != target_preflight
            ):
                raise HostPortabilityError("target preflight evidence 参数不一致。")
            target_preflight_evidence = target_preflight
            target_preflight_status = str(
                target_preflight.get("status", target_preflight.get("outcome", ""))
            )
        elif isinstance(target_preflight, bool):
            target_preflight_status = "passed" if target_preflight else "failed"
        else:
            raise HostPortabilityError("target preflight 证明无效。")
    if not source_fully_stopped:
        raise HostPortabilityError(
            "accept cutover 前必须由宿主适配器证明整个 source 已停止。"
        )
    if target_preflight_status != "passed":
        raise HostPortabilityError("accept cutover 前必须通过 target preflight。")
    if target_preflight_evidence is None:
        raise HostPortabilityError(
            "accept cutover 必须提供 target preflight evidence。"
        )
    normalized_target_release = _extract_target_release_metadata(
        target_preflight_evidence
    )
    if target_release_metadata is not None:
        expected_target_release = _normalize_cutover_release_metadata(
            target_release_metadata, field_name="target_release_metadata"
        )
        if expected_target_release != normalized_target_release:
            raise HostPortabilityError(
                "accept target release metadata 与 target preflight 不一致。"
            )
        normalized_target_release = expected_target_release
    _validate_release_pair(
        prepared["source_release_metadata"], normalized_target_release
    )
    expected_generation = prepared["target_writer_generation"]
    if (
        target_writer_generation is not None
        and target_writer_generation != expected_generation
    ):
        raise HostPortabilityError("target writer_generation 不是 source 的下一代。")
    accepted_now = now
    if accepted_now is None and source_state_path is not None:
        accepted_now = _existing_accepted_timestamp(destination_state_path)
    accepted = build_cutover_metadata(
        dataset_id=prepared["dataset_id"],
        backup_id=prepared["backup_id"],
        source_host_id=prepared["source_host_id"],
        target_host_id=prepared["target_host_id"],
        writer_generation=prepared["target_writer_generation"],
        state="accepted",
        source_project=prepared["source_project"],
        target_project=prepared["target_project"],
        source_quiescent=prepared["source_quiescent"],
        source_fully_stopped=True,
        target_preflight_status="passed",
        target_preflight_evidence=target_preflight_evidence,
        target_exposed=False,
        target_write_accepted=False,
        target_write_authorized=True,
        source_writer_generation=prepared["source_writer_generation"],
        target_writer_generation=expected_generation,
        source_stop_proof=prepared["source_stop_proof"],
        backup_artifact_sha256=prepared["backup_artifact_sha256"],
        source_release_metadata=prepared["source_release_metadata"],
        target_release_metadata=normalized_target_release,
        created_at=prepared["created_at"],
        updated_at=accepted_now,
    )
    if source_state_path is not None:
        (
            _accepted_normalized,
            accepted_serialized,
            _accepted_checksum,
            _existing_accepted,
            _existing_accepted_checksum,
        ) = _stage_checksummed_cutover_state(destination_state_path, accepted)
        accepted_digest = hashlib.sha256(accepted_serialized).hexdigest()
        reservation = _reserve_cutover_state(
            source_state_path,
            destination_state_path,
            accepted_digest=accepted_digest,
        )
        try:
            write_checksummed_cutover_state(destination_state_path, accepted)
            _claim_cutover_state(
                source_state_path,
                source_digest=reservation["source_sha256"],
                accepted_digest=accepted_digest,
                accepted_state_name=destination_state_path.name,
                accepted_state_identity=_cutover_destination_identity(
                    destination_state_path
                ),
                prepared_state=prepared,
            )
        except (HostPortabilityError, OSError, UnicodeError, ValueError, TypeError):
            # Preserve every canonical artifact.  A later exact retry must be
            # able to repair a missing sidecar or finish a half claim.
            raise
    elif state_path is not None:
        write_checksummed_cutover_state(state_path, accepted)
    return accepted


# Descriptive aliases used by host adapters and older wrappers.
build_cutover_state = build_cutover_metadata
validate_cutover_metadata = validate_cutover_state
write_cutover_state = write_checksummed_cutover_state
write_checksummed_metadata = write_checksummed_cutover_state
validate_cutover_state_file = validate_checksummed_cutover_state
validate_checksummed_metadata = validate_checksummed_cutover_state
prepare_cutover_state = prepare_cutover
accept_cutover_state = accept_cutover
prepare_cutover_metadata = prepare_cutover
accept_cutover_metadata = accept_cutover
recover_cutover = recover_cutover_state


def _looks_like_raw_runtime_input(path: Path) -> bool:
    lower_name = path.name.lower()
    if lower_name in {"docker.raw", "docker.raw.vhdx", "docker.raw.qcow2"}:
        return True
    if lower_name.endswith(".raw") or lower_name.endswith(".vhdx"):
        return True
    parts = {part.lower() for part in path.parts}
    if "docker" in parts and "volumes" in parts:
        return True
    if lower_name.endswith("_data") or lower_name in {
        "postgres_data",
        "learning_media",
        "postgres-data",
        "learning-media",
    }:
        return True
    # Common PostgreSQL named-volume fingerprints.  A paired backup never
    # contains these at its root, and rejecting them avoids accepting a raw
    # data directory merely because a caller renamed it.
    try:
        children = {child.name.lower() for child in path.iterdir()}
    except OSError:
        return False
    return {"base", "global", "pg_wal"}.issubset(children) or "pg_version" in children


def validate_migration_input(path: str | Path) -> dict[str, Any]:
    """Validate the only migration format: a complete paired backup.

    Raw Docker Desktop disks, named-volume internals, archives without the
    paired manifest/checksum set, and partial directories are all rejected
    before any restore command could be invoked.
    """

    try:
        candidate = Path(path).expanduser().resolve(strict=False)
    except (TypeError, ValueError, OSError) as exc:
        raise MigrationInputError("迁移输入路径无效。") from exc
    if _looks_like_raw_runtime_input(candidate):
        raise MigrationInputError(
            "迁移输入必须是配对备份，不接受 Docker runtime internals。"
        )
    if not candidate.is_dir():
        raise MigrationInputError("迁移输入必须是包含 SUCCESS 的配对备份目录。")
    try:
        if any(_looks_like_raw_runtime_input(child) for child in candidate.iterdir()):
            raise MigrationInputError("迁移输入不得包含 Docker runtime internals。")
    except OSError as exc:
        raise MigrationInputError("迁移输入目录无法读取。") from exc
    try:
        return validate_backup(candidate, require_cross_host_identity=True)
    except (BackupError, OSError, UnicodeError, ValueError) as exc:
        raise MigrationInputError(
            "迁移输入不是完整且已 SUCCESS 校验的配对备份。"
        ) from exc


validate_portable_backup = validate_migration_input
validate_backup_input = validate_migration_input


def validate_cutover_bindings(
    state: str | Path,
    backup: str | Path,
    *,
    target_release_metadata: str | Path | None = None,
) -> dict[str, Any]:
    """Bind a restored cutover backup and selected release to one state.

    The state and optional target release are path-backed inputs so their
    adjacent checksum files can be verified before any identity comparison.
    The returned evidence contains identities and checksums only; host paths
    are intentionally not persisted or emitted as part of the binding.
    """

    state_path = Path(state).expanduser()
    if (
        not state_path.is_absolute()
        or state_path.is_symlink()
        or not state_path.is_file()
    ):
        raise HostPortabilityError("cutover binding state 必须是绝对普通文件。")
    normalized_state = validate_checksummed_cutover_state(state_path)

    backup_path = Path(backup).expanduser()
    if backup_path.is_symlink():
        raise MigrationInputError("cutover binding backup 目录不能是符号链接。")
    try:
        resolved_backup = backup_path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise MigrationInputError("cutover binding backup 路径无效。") from exc
    if resolved_backup.name != normalized_state["backup_id"]:
        raise MigrationInputError("cutover binding backup 目录名与 state 不一致。")
    try:
        validate_cutover_backup(
            resolved_backup,
            dataset_id=normalized_state["dataset_id"],
            source_host_id=normalized_state["source_host_id"],
            writer_generation=normalized_state["source_writer_generation"],
        )
        actual_artifacts = _backup_artifact_checksums(resolved_backup)
    except (BackupError, OSError, UnicodeError, ValueError) as exc:
        raise MigrationInputError(
            "cutover binding backup 必须是匹配 state identity 的完整 paired backup。"
        ) from exc
    expected_artifacts = _normalize_backup_artifact_identity(
        normalized_state["backup_artifact_sha256"]
    )
    if actual_artifacts != expected_artifacts:
        raise MigrationInputError("cutover binding backup artifact checksum 不匹配。")

    target_release: dict[str, Any] | None = None
    if target_release_metadata is not None:
        target_release = _normalize_cutover_release_metadata(
            _load_checksummed_json_mapping(target_release_metadata),
            field_name="target_release_metadata",
        )
    if normalized_state["state"] == "accepted":
        if target_release is None:
            raise HostPortabilityError(
                "accepted cutover binding 必须提供 checksummed target release metadata。"
            )
        if target_release != normalized_state["target_release_metadata"]:
            raise HostPortabilityError(
                "accepted cutover binding target release metadata 不匹配。"
            )

    result: dict[str, Any] = {
        "status": "passed",
        "state": normalized_state["state"],
        "backup_id": normalized_state["backup_id"],
        "dataset_id": normalized_state["dataset_id"],
        "source_host_id": normalized_state["source_host_id"],
        "writer_generation": normalized_state["source_writer_generation"],
        "backup_artifact_sha256": actual_artifacts,
    }
    if target_release is not None:
        result["target_release_metadata_sha256"] = _canonical_json_sha256(
            target_release
        )
    return result


def _load_json_value(value: str) -> Any:
    candidate = Path(value)
    try:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HostPortabilityError("JSON 参数无法读取。") from exc
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise HostPortabilityError("JSON 参数格式无效。") from exc


def _load_checksummed_json_mapping(path: str | Path) -> Mapping[str, Any]:
    """Load a JSON evidence file only when its adjacent SHA-256 matches."""

    candidate = Path(path).expanduser()
    if not candidate.is_absolute() or candidate.is_symlink() or not candidate.is_file():
        raise HostPortabilityError("source stop proof 文件必须是绝对普通文件。")
    checksum_path = _cutover_checksum_path(candidate)
    if checksum_path.is_symlink() or not checksum_path.is_file():
        raise HostPortabilityError("source stop proof checksum 文件不存在。")
    try:
        source_bytes = candidate.read_bytes()
        checksum_text = checksum_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise HostPortabilityError("source stop proof 文件无法读取。") from exc
    match = CHECKSUM_LINE_PATTERN.fullmatch(checksum_text)
    if (
        match is None
        or match.group(2) != candidate.name
        or match.group(1) != hashlib.sha256(source_bytes).hexdigest()
    ):
        raise HostPortabilityError("source stop proof checksum 校验失败。")
    try:
        value = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HostPortabilityError("source stop proof JSON 无效。") from exc
    if not isinstance(value, Mapping):
        raise HostPortabilityError("source stop proof 必须是 JSON object。")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, TypeError) as exc:
        raise HostPortabilityError("元数据输出文件无法写入。") from exc


def _write_json_checksum(path: Path) -> None:
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _cutover_checksum_path(path).write_text(
            f"{digest}  {path.name}\n", encoding="ascii"
        )
    except OSError as exc:
        raise HostPortabilityError("元数据输出 checksum 无法写入。") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Internal exam host portability contracts (non-secret only)"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    project_parser = subparsers.add_parser(
        "validate-project-name", aliases=("project-name", "project")
    )
    project_parser.add_argument("--environment", "--env", required=True)
    project_parser.add_argument("--project-name", required=True)

    paths_parser = subparsers.add_parser(
        "validate-paths", aliases=("formal-paths", "paths")
    )
    paths_parser.add_argument("--development-root", type=Path)
    paths_parser.add_argument("--formal-root", type=Path)
    for field in FORMAL_PATH_FIELDS:
        paths_parser.add_argument(f"--{field.replace('_', '-')}", required=True)

    release_parser = subparsers.add_parser(
        "release-metadata",
        aliases=("generate-release-metadata", "release", "generate-release"),
    )
    release_parser.add_argument("--application-version", required=True)
    release_parser.add_argument("--git-commit", required=True)
    release_parser.add_argument("--host-os")
    release_parser.add_argument("--architecture", "--cpu-architecture")
    release_parser.add_argument("--target-platform", "--target-linux-platform")
    release_parser.add_argument("--migration-head", required=True)
    release_parser.add_argument("--image-references", required=True)
    release_parser.add_argument(
        "--base-image-references",
        "--base-image-digests",
        "--image-digests",
    )
    release_parser.add_argument(
        "--release-file-checksums", "--checksums", required=True
    )
    release_parser.add_argument("--created-at")
    release_parser.add_argument("--output", type=Path)

    validate_release_parser = subparsers.add_parser(
        "validate-release-metadata", aliases=("validate-release",)
    )
    validate_release_parser.add_argument("metadata", type=Path)

    evidence_parser = subparsers.add_parser(
        "evidence-metadata",
        aliases=("generate-evidence-metadata", "evidence"),
    )
    evidence_parser.add_argument("--release-metadata", required=True, type=Path)
    evidence_parser.add_argument("--kind", required=True)
    evidence_parser.add_argument("--status", required=True)
    evidence_parser.add_argument("--checks")
    evidence_parser.add_argument("--checked-at")
    evidence_parser.add_argument("--output", type=Path)

    validate_evidence_parser = subparsers.add_parser("validate-evidence")
    validate_evidence_parser.add_argument("metadata", type=Path)

    prepare_parser = subparsers.add_parser(
        "prepare-cutover", aliases=("prepare-cutover-state",)
    )
    prepare_parser.add_argument("--backup", type=Path, required=True)
    prepare_parser.add_argument("--target-host-id", required=True)
    prepare_parser.add_argument("--release-metadata", type=Path, required=True)
    prepare_parser.add_argument("--source-stop-proof", type=Path, required=True)
    prepare_parser.add_argument("--state-path", type=Path)
    prepare_parser.add_argument(
        "--source-project", default=DEFAULT_PROJECT_NAMES["formal"]
    )
    prepare_parser.add_argument(
        "--target-project", default=DEFAULT_PROJECT_NAMES["formal"]
    )
    prepare_parser.add_argument(
        "--source-fully-stopped",
        "--source-gateway-stopped",
        dest="source_fully_stopped",
        action="store_true",
    )
    prepare_parser.add_argument("--in-progress-attempts", type=int, default=0)

    accept_parser = subparsers.add_parser(
        "accept-cutover", aliases=("accept-cutover-state",)
    )
    accept_parser.add_argument("state", type=Path)
    accept_parser.add_argument("--target-host-id", required=True)
    accept_parser.add_argument("--target-preflight-evidence", type=Path, required=True)
    accept_parser.add_argument("--state-path", type=Path)
    accept_parser.add_argument("--target-writer-generation", type=int)
    accept_parser.add_argument(
        "--target-not-exposed", action="store_true", required=True
    )
    accept_parser.add_argument(
        "--target-write-not-accepted", action="store_true", required=True
    )
    # Legacy positive assertions are retained only to fail closed when an old
    # wrapper attempts to claim exposure or accepted writes.
    accept_parser.add_argument("--target-exposed", action="store_true")
    accept_parser.add_argument("--target-write-accepted", action="store_true")
    accept_parser.add_argument(
        "--source-fully-stopped",
        "--source-gateway-stopped",
        dest="source_fully_stopped",
        action="store_true",
    )

    recover_parser = subparsers.add_parser(
        "recover-cutover-state", aliases=("recover-cutover",)
    )
    recover_parser.add_argument("source", type=Path)
    recover_parser.add_argument(
        "--accepted-state", "--state-path", required=True, type=Path
    )

    bindings_parser = subparsers.add_parser("validate-cutover-bindings")
    bindings_parser.add_argument("state", type=Path)
    bindings_parser.add_argument("--backup", type=Path, required=True)
    bindings_parser.add_argument("--target-release-metadata", type=Path)

    migration_parser = subparsers.add_parser(
        "validate-migration-input",
        aliases=("validate-migration", "migration", "inspect-migration"),
    )
    migration_parser.add_argument("path", type=Path)
    return parser


def _emit(value: Mapping[str, Any], output: Path | None = None) -> None:
    if output is not None:
        _write_json(output, value)
        _write_json_checksum(output)
    sys.stdout.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.action in {"validate-project-name", "project-name", "project"}:
            environment = _canonical_environment(args.environment)
            project_name = validate_project_name(args.project_name, environment)
            _emit(
                {
                    "status": "passed",
                    "environment": environment,
                    "project_name": project_name,
                }
            )
        elif args.action in {"validate-paths", "formal-paths", "paths"}:
            paths = validate_formal_host_paths(
                development_root=args.development_root,
                formal_root=args.formal_root,
                **{field: getattr(args, field) for field in FORMAL_PATH_FIELDS},
            )
            _emit(
                {
                    "status": "passed",
                    "paths": {key: str(value) for key, value in paths.items()},
                }
            )
        elif args.action in {
            "release-metadata",
            "generate-release-metadata",
            "release",
            "generate-release",
        }:
            metadata = build_release_metadata(
                application_version=args.application_version,
                git_commit=args.git_commit,
                host_os=args.host_os,
                architecture=args.architecture,
                target_platform=args.target_platform,
                migration_head=args.migration_head,
                image_references=_load_json_value(args.image_references),
                release_file_checksums=_load_json_value(args.release_file_checksums),
                base_image_references=(
                    _load_json_value(args.base_image_references)
                    if args.base_image_references
                    else None
                ),
                created_at=args.created_at,
            )
            _emit(metadata, args.output)
        elif args.action in {"validate-release-metadata", "validate-release"}:
            payload = _load_json_value(str(args.metadata))
            _emit(validate_release_metadata(payload))
        elif args.action in {
            "evidence-metadata",
            "generate-evidence-metadata",
            "evidence",
        }:
            checks = _load_json_value(args.checks) if args.checks else None
            release_metadata = _load_json_value(str(args.release_metadata))
            _emit(
                build_evidence_metadata(
                    release_metadata=release_metadata,
                    kind=args.kind,
                    status=args.status,
                    checks=checks,
                    checked_at=args.checked_at,
                ),
                args.output,
            )
        elif args.action == "validate-evidence":
            payload = _load_json_value(str(args.metadata))
            _emit(validate_evidence_metadata(payload))
        elif args.action in {"prepare-cutover", "prepare-cutover-state"}:
            _emit(
                prepare_cutover(
                    backup_dir=args.backup,
                    target_host_id=args.target_host_id,
                    release_metadata=_load_checksummed_json_mapping(
                        args.release_metadata
                    ),
                    source_stop_proof=_load_checksummed_json_mapping(
                        args.source_stop_proof
                    ),
                    source_project=args.source_project,
                    target_project=args.target_project,
                    source_fully_stopped=args.source_fully_stopped,
                    in_progress_attempts=args.in_progress_attempts,
                    state_path=args.state_path,
                )
            )
        elif args.action in {"accept-cutover", "accept-cutover-state"}:
            _emit(
                accept_cutover(
                    args.state,
                    target_host_id=args.target_host_id,
                    target_preflight_evidence=_load_checksummed_json_mapping(
                        args.target_preflight_evidence
                    ),
                    source_fully_stopped=args.source_fully_stopped,
                    target_writer_generation=args.target_writer_generation,
                    target_write_accepted=(
                        args.target_write_accepted or not args.target_write_not_accepted
                    ),
                    target_exposed=(args.target_exposed or not args.target_not_exposed),
                    state_path=args.state_path,
                )
            )
        elif args.action in {"recover-cutover-state", "recover-cutover"}:
            _emit(recover_cutover_state(args.source, args.accepted_state))
        elif args.action == "validate-cutover-bindings":
            _emit(
                validate_cutover_bindings(
                    args.state,
                    args.backup,
                    target_release_metadata=args.target_release_metadata,
                )
            )
        else:
            manifest = validate_migration_input(args.path)
            _emit({"status": "passed", "migration_head": manifest["migration_head"]})
    except (HostPortabilityError, BackupError, OSError, UnicodeError, ValueError):
        # Do not print exception text: callers may have supplied a path or
        # payload containing a secret, and host logs are retained as evidence.
        sys.stderr.write("host_portability_failed error=validation\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
