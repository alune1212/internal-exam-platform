"""Normalize dependency/image scans and enforce the release evidence policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

IMAGE_NAMES = ("db", "backend", "frontend", "gateway")
IMAGE_PLATFORM = "linux/arm64"
_IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE_REFERENCE_RE = re.compile(
    r"^[a-z0-9][a-z0-9._/-]{0,254}:[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
)
_CHECKSUM_RE = re.compile(r"^([0-9a-fA-F]{64})[ \t]{2}([^ \t\r\n]+)$")
_HOST_OS_ALIASES = {
    "darwin": "darwin",
    "macos": "darwin",
    "linux": "linux",
    "windows": "windows",
}
_HOST_ARCHITECTURE_ALIASES = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "amd64": "amd64",
    "x86_64": "amd64",
}
_HOST_PLATFORMS = {
    ("darwin", "arm64"),
    ("linux", "arm64"),
    ("linux", "amd64"),
    ("windows", "amd64"),
}
# ResultClass is a string alias in Trivy, but these are the classes emitted by
# the v2 JSON report.  Keeping the allowlist here prevents an arbitrary result
# with an omitted Vulnerabilities field from being treated as a clean scan.
_TRIVY_RESULT_CLASSES = frozenset(
    {
        "unknown",
        "os-pkgs",
        "lang-pkgs",
        "config",
        "secret",
        "license",
        "license-file",
        "custom",
    }
)


class ImageIdentityError(ValueError):
    """A safe, non-sensitive image identity validation error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ScanInputError(ValueError):
    """A safe, non-sensitive scan input validation error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(
    *, source: str, package: str, version: str, vulnerability_id: str, severity: str
) -> dict[str, str]:
    return {
        "key": f"{source}:{package}:{vulnerability_id}",
        "source": source,
        "package": package,
        "installed_version": version,
        "vulnerability_id": vulnerability_id,
        "severity": severity.upper(),
    }


def normalize_pip_audit(payload: Any) -> list[dict[str, str]]:
    dependencies = (
        payload.get("dependencies", []) if isinstance(payload, dict) else payload
    )
    findings: list[dict[str, str]] = []
    for dependency in dependencies or []:
        package = str(dependency.get("name", "unknown"))
        version = str(dependency.get("version", "unknown"))
        for vulnerability in dependency.get("vulns", []):
            severity = str(vulnerability.get("severity", "HIGH"))
            findings.append(
                _finding(
                    source="pip-audit",
                    package=package,
                    version=version,
                    vulnerability_id=str(vulnerability.get("id", "unknown")),
                    severity=severity,
                )
            )
    return findings


def normalize_npm_audit(payload: Any) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for package, vulnerability in (payload.get("vulnerabilities", {}) or {}).items():
        vulnerability_id = str(vulnerability.get("name", package))
        via = vulnerability.get("via", [])
        advisory = next((item for item in via if isinstance(item, dict)), None)
        if advisory:
            vulnerability_id = str(
                advisory.get("url") or advisory.get("source") or vulnerability_id
            )
        findings.append(
            _finding(
                source="npm-audit",
                package=str(package),
                version=str(vulnerability.get("range", "unknown")),
                vulnerability_id=vulnerability_id,
                severity=str(vulnerability.get("severity", "unknown")),
            )
        )
    return findings


def normalize_trivy(payload: Any, source_name: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for result in payload.get("Results", []) or []:
        findings.extend(
            _finding(
                source=source_name,
                package=str(vulnerability.get("PkgName", "unknown")),
                version=str(vulnerability.get("InstalledVersion", "unknown")),
                vulnerability_id=str(vulnerability.get("VulnerabilityID", "unknown")),
                severity=str(vulnerability.get("Severity", "unknown")),
            )
            for vulnerability in result.get("Vulnerabilities", []) or []
        )
    return findings


def validate_pip_audit(payload: Any) -> None:
    """Require the JSON shape emitted by pip-audit before normalization."""

    if not isinstance(payload, dict) or not isinstance(
        payload.get("dependencies"), list
    ):
        raise ScanInputError("pip_audit_schema_invalid")
    if payload.get("error") or payload.get("errors"):
        raise ScanInputError("pip_audit_scan_error")
    for dependency in payload["dependencies"]:
        if (
            not isinstance(dependency, dict)
            or not isinstance(dependency.get("name"), str)
            or not dependency.get("name")
            or not isinstance(dependency.get("version"), str)
            or not dependency.get("version")
            or not isinstance(dependency.get("vulns"), list)
            or any(
                not isinstance(vulnerability, dict)
                for vulnerability in dependency["vulns"]
            )
        ):
            raise ScanInputError("pip_audit_schema_invalid")


def validate_npm_audit(payload: Any) -> None:
    """Require the npm v2 audit report shape before normalization."""

    if not isinstance(payload, dict):
        raise ScanInputError("npm_audit_schema_invalid")
    audit_version = payload.get("auditReportVersion")
    metadata = payload.get("metadata")
    vulnerabilities = payload.get("vulnerabilities")
    if (
        not isinstance(audit_version, int)
        or isinstance(audit_version, bool)
        or audit_version < 1
        or not isinstance(vulnerabilities, dict)
        or not isinstance(metadata, dict)
        or not isinstance(metadata.get("vulnerabilities"), dict)
        or not isinstance(metadata.get("dependencies"), dict)
    ):
        raise ScanInputError("npm_audit_schema_invalid")
    if payload.get("error") or payload.get("errors"):
        raise ScanInputError("npm_audit_scan_error")
    for package, vulnerability in vulnerabilities.items():
        if (
            not isinstance(package, str)
            or not isinstance(vulnerability, dict)
            or not isinstance(vulnerability.get("severity"), str)
            or not vulnerability.get("severity")
            or not isinstance(vulnerability.get("via"), list)
        ):
            raise ScanInputError("npm_audit_schema_invalid")


def validate_trivy(payload: Any) -> None:
    """Require a successful Trivy JSON report before normalization."""

    if not isinstance(payload, dict) or payload.get("SchemaVersion") != 2:
        raise ScanInputError("trivy_schema_invalid")
    results = payload.get("Results")
    if not isinstance(results, list):
        raise ScanInputError("trivy_schema_invalid")
    errors = payload.get("Errors")
    if errors is not None and (not isinstance(errors, list) or errors):
        raise ScanInputError("trivy_scan_error")
    for result in results:
        if not isinstance(result, dict):
            raise ScanInputError("trivy_schema_invalid")

        # Trivy v0.70 omits Vulnerabilities for some clean results.  The
        # omission is only meaningful when the Result still identifies the
        # scanned target and result class/type.  An explicit null or any other
        # non-list value is malformed and must fail closed.
        result_target = result.get("Target")
        result_class = result.get("Class")
        result_type = result.get("Type")
        if (
            not isinstance(result_target, str)
            or not result_target.strip()
            or not isinstance(result_class, str)
            or result_class not in _TRIVY_RESULT_CLASSES
            or not isinstance(result_type, str)
            or not result_type.strip()
        ):
            raise ScanInputError("trivy_schema_invalid")
        if "Vulnerabilities" not in result:
            continue

        vulnerabilities = result["Vulnerabilities"]
        if not isinstance(vulnerabilities, list) or any(
            not isinstance(vulnerability, dict)
            or not isinstance(vulnerability.get("VulnerabilityID"), str)
            or not vulnerability.get("VulnerabilityID")
            or not isinstance(vulnerability.get("Severity"), str)
            or not vulnerability.get("Severity")
            for vulnerability in vulnerabilities
        ):
            raise ScanInputError("trivy_schema_invalid")


def normalize_host_identity(host_os: str, architecture: str) -> tuple[str, str]:
    """Normalize the trusted host identity supplied by the release wrapper."""

    normalized_os = _HOST_OS_ALIASES.get(host_os.strip().lower())
    normalized_architecture = _HOST_ARCHITECTURE_ALIASES.get(
        architecture.strip().lower()
    )
    if (
        normalized_os is None
        or normalized_architecture is None
        or (normalized_os, normalized_architecture) not in _HOST_PLATFORMS
    ):
        raise ScanInputError("host_identity_invalid")
    return normalized_os, normalized_architecture


def validate_dispositions(payload: Any) -> dict[str, Any]:
    """Validate the allowlisted disposition schema before policy evaluation."""

    if not isinstance(payload, dict):
        raise ScanInputError("dispositions_schema_invalid")
    schema_version = payload.get("schema_version", payload.get("schemaVersion"))
    if (
        isinstance(schema_version, bool)
        or schema_version != 1
        or not isinstance(payload.get("findings"), dict)
    ):
        raise ScanInputError("dispositions_schema_invalid")
    findings = payload["findings"]
    for finding_key, disposition in findings.items():
        if not isinstance(finding_key, str) or not isinstance(disposition, dict):
            raise ScanInputError("dispositions_schema_invalid")
        if "exploitable" in disposition and not isinstance(
            disposition["exploitable"], bool
        ):
            raise ScanInputError("dispositions_schema_invalid")
        if "rationale" in disposition and not isinstance(disposition["rationale"], str):
            raise ScanInputError("dispositions_schema_invalid")
    return payload


def scanner_evidence_digest(
    pip_payload: Any,
    npm_payload: Any,
    trivy_payloads: list[tuple[str, Any]],
    dispositions: dict[str, Any],
) -> str:
    """Hash canonical validated scan payloads without hashing the report itself."""

    canonical_payload = {
        "pip_audit": pip_payload,
        "npm_audit": npm_payload,
        "trivy": [
            {"source": _canonical_scan_source(source), "payload": payload}
            for source, payload in sorted(trivy_payloads, key=lambda item: item[0])
        ],
        "dispositions": dispositions,
    }
    serialized = json.dumps(
        canonical_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _read_identity_checksum(path: Path) -> str:
    checksum_path = path.with_name(path.name + ".sha256")
    try:
        checksum_text = checksum_path.read_text(encoding="ascii").strip()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, UnicodeError):
        raise ImageIdentityError("built_image_identity_checksum_unreadable") from None
    match = _CHECKSUM_RE.fullmatch(checksum_text)
    if match is None or match.group(2) != path.name:
        raise ImageIdentityError("built_image_identity_checksum_invalid")
    if match.group(1).lower() != actual:
        raise ImageIdentityError("built_image_identity_checksum_mismatch")
    return actual


def _load_identity_json(path: Path) -> Any:
    try:
        return _load_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ImageIdentityError("built_image_identity_unreadable") from None


def validate_built_image_identity(path: Path) -> dict[str, Any]:
    """Validate and normalize the exact final image identity contract.

    The returned structure contains only release identity data that is safe to
    copy into policy evidence. Validation errors intentionally use stable
    codes instead of embedding paths, image references, or command output.
    """

    if not path.is_file():
        raise ImageIdentityError("built_image_identity_missing")
    checksum = _read_identity_checksum(path)
    payload = _load_identity_json(path)
    if not isinstance(payload, dict):
        raise ImageIdentityError("built_image_identity_invalid")
    if payload.get("schemaVersion") != 1 or payload.get("status") != "passed":
        raise ImageIdentityError("built_image_identity_status_invalid")
    if payload.get("platform") != IMAGE_PLATFORM:
        raise ImageIdentityError("built_image_identity_platform_invalid")

    images = payload.get("images")
    if not isinstance(images, dict) or set(images) != set(IMAGE_NAMES):
        raise ImageIdentityError("built_image_identity_images_invalid")

    normalized_images: dict[str, dict[str, str]] = {}
    references: set[str] = set()
    for image_name in IMAGE_NAMES:
        row = images.get(image_name)
        if not isinstance(row, dict):
            raise ImageIdentityError("built_image_identity_image_invalid")
        reference = row.get("reference")
        image_id = row.get("id")
        if (
            not isinstance(reference, str)
            or not _IMAGE_REFERENCE_RE.fullmatch(reference)
            or reference in references
        ):
            raise ImageIdentityError("built_image_identity_reference_invalid")
        if not isinstance(image_id, str) or not _IMAGE_ID_RE.fullmatch(image_id):
            raise ImageIdentityError("built_image_identity_id_invalid")
        if row.get("os") != "linux" or row.get("architecture") != "arm64":
            raise ImageIdentityError("built_image_identity_image_platform_invalid")
        references.add(reference)
        normalized_images[image_name] = {
            "reference": reference,
            "id": image_id,
            "os": "linux",
            "architecture": "arm64",
        }

    return {
        "platform": IMAGE_PLATFORM,
        "sha256": checksum,
        "images": normalized_images,
    }


def _record_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def _record_references(record: dict[str, Any]) -> list[str]:
    raw_references = _record_value(
        record,
        "RepoTags",
        "repo_tags",
        "References",
        "references",
        "reference",
        "Reference",
    )
    if isinstance(raw_references, str):
        return [raw_references]
    if isinstance(raw_references, list):
        return [value for value in raw_references if isinstance(value, str)]
    return []


def _image_record_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("images"), list):
        rows = payload["images"]
    elif (
        isinstance(payload, dict)
        and payload
        and all(isinstance(value, dict) for value in payload.values())
    ):
        rows = list(payload.values())
    else:
        raise ImageIdentityError("image_record_invalid")
    if len(rows) != len(IMAGE_NAMES) or not all(isinstance(row, dict) for row in rows):
        raise ImageIdentityError("image_record_images_invalid")
    return cast("list[dict[str, Any]]", rows)


def validate_image_record(
    payload: Any, identity: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Bind Docker inspect records to every image in a built identity."""

    rows = _image_record_rows(payload)
    expected_images = identity["images"]
    matched_indexes: set[int] = set()
    normalized: dict[str, dict[str, str]] = {}
    for image_name in IMAGE_NAMES:
        expected = expected_images[image_name]
        matches = [
            index
            for index, row in enumerate(rows)
            if expected["reference"] in _record_references(row)
        ]
        if len(matches) != 1:
            raise ImageIdentityError("image_record_missing_image")
        index = matches[0]
        if index in matched_indexes:
            raise ImageIdentityError("image_record_duplicate_image")
        matched_indexes.add(index)
        row = rows[index]
        actual_id = _record_value(row, "Id", "id", "ID")
        actual_os = _record_value(row, "Os", "os", "OS")
        actual_architecture = _record_value(
            row, "Architecture", "architecture", "ARCHITECTURE"
        )
        if actual_id != expected["id"]:
            raise ImageIdentityError("image_record_id_mismatch")
        if (
            actual_os != expected["os"]
            or actual_architecture != expected["architecture"]
        ):
            raise ImageIdentityError("image_record_platform_mismatch")
        normalized[image_name] = {
            "reference": expected["reference"],
            "id": expected["id"],
            "os": expected["os"],
            "architecture": expected["architecture"],
        }
    if matched_indexes != set(range(len(rows))):
        raise ImageIdentityError("image_record_images_invalid")
    return normalized


def _canonical_record_name(reference: str) -> str | None:
    image_name = reference.rsplit("/", 1)[-1].split(":", 1)[0]
    if image_name.endswith("-database") or image_name == "database":
        return "db"
    for known_name in ("backend", "frontend", "gateway"):
        if image_name == known_name or image_name.endswith(f"-{known_name}"):
            return known_name
    return None


def canonicalize_image_record(payload: Any) -> dict[str, dict[str, str]]:
    """Keep only image identity fields from a Docker inspect payload."""

    if (
        isinstance(payload, dict)
        and payload
        and all(isinstance(value, str) for value in payload.values())
    ):
        # Preserve the pre-identity fixture contract without copying arbitrary
        # values. These legacy rows contain references only.
        canonical: dict[str, dict[str, str]] = {}
        for name, value in payload.items():
            canonical_name = "db" if name == "database" else name
            if (
                not isinstance(name, str)
                or canonical_name not in IMAGE_NAMES
                or canonical_name in canonical
                or not _IMAGE_REFERENCE_RE.fullmatch(value)
            ):
                raise ScanInputError("image_record_schema_invalid")
            canonical[canonical_name] = {"reference": value}
        return canonical

    rows = _image_record_rows(payload)
    canonical: dict[str, dict[str, str]] = {}
    for row in rows:
        references = _record_references(row)
        image_id = _record_value(row, "Id", "id", "ID")
        image_os = _record_value(row, "Os", "os", "OS")
        image_architecture = _record_value(
            row, "Architecture", "architecture", "ARCHITECTURE"
        )
        if (
            len(references) != 1
            or not isinstance(image_id, str)
            or not _IMAGE_ID_RE.fullmatch(image_id)
            or image_os not in {"linux"}
            or image_architecture not in {"amd64", "arm64"}
        ):
            raise ScanInputError("image_record_schema_invalid")
        image_name = _canonical_record_name(references[0])
        if image_name is None or image_name in canonical:
            raise ScanInputError("image_record_schema_invalid")
        canonical[image_name] = {
            "reference": references[0],
            "id": image_id,
            "os": image_os,
            "architecture": image_architecture,
        }
    return canonical


def _scan_image_name(source_name: str) -> str | None:
    stem = source_name.rsplit(":", 1)[-1].removesuffix(".json")
    stem = stem.removeprefix("trivy-")
    if stem == "database":
        return "db"
    return stem if stem in IMAGE_NAMES else None


def _canonical_scan_source(source_name: str) -> str:
    image_name = _scan_image_name(source_name)
    return f"trivy:{image_name}" if image_name is not None else source_name


def _scan_target_values(payload: Any) -> tuple[str | None, list[str]]:
    if not isinstance(payload, dict):
        return None, []
    target = next(
        (
            payload.get(key)
            for key in (
                "ArtifactName",
                "artifactName",
                "RepoTag",
                "repoTag",
                "Target",
                "target",
                "ImageRef",
                "imageRef",
            )
            if isinstance(payload.get(key), str)
        ),
        None,
    )
    if target is None:
        top_level_tags = payload.get("RepoTags") or payload.get("repoTags")
        if isinstance(top_level_tags, str):
            target = top_level_tags
        elif isinstance(top_level_tags, list):
            target = next(
                (value for value in top_level_tags if isinstance(value, str)),
                None,
            )
    image_ids: list[str] = []
    for key in (
        "ArtifactID",
        "artifactID",
        "ImageID",
        "imageID",
    ):
        value = payload.get(key)
        if isinstance(value, str):
            image_ids.append(value)
    metadata = payload.get("Metadata")
    if isinstance(metadata, dict):
        if target is None:
            metadata_tag = metadata.get("RepoTag") or metadata.get("repoTag")
            metadata_tags = metadata.get("RepoTags") or metadata.get("repoTags")
            if isinstance(metadata_tag, str):
                target = metadata_tag
            elif isinstance(metadata_tags, list):
                target = next(
                    (value for value in metadata_tags if isinstance(value, str)),
                    None,
                )
        for key in ("ImageID", "imageID", "ArtifactID", "artifactID"):
            value = metadata.get(key)
            if isinstance(value, str):
                image_ids.append(value)
    return target, image_ids


def validate_scan_target(
    payload: Any,
    source_name: str,
    identity: dict[str, Any],
    *,
    require_metadata: bool = False,
) -> None:
    """Check Trivy target metadata when the scanner emitted it."""

    target, image_ids = _scan_target_values(payload)
    image_name = _scan_image_name(source_name)
    expected_images = identity["images"]
    if require_metadata and target is None:
        raise ImageIdentityError("scan_target_metadata_missing")
    if require_metadata and not image_ids:
        raise ImageIdentityError("scan_target_id_metadata_missing")
    if target is not None:
        if image_name is not None:
            expected_reference = expected_images[image_name]["reference"]
            if target != expected_reference:
                raise ImageIdentityError("scan_target_reference_mismatch")
        elif target not in {expected_images[name]["reference"] for name in IMAGE_NAMES}:
            raise ImageIdentityError("scan_target_reference_mismatch")
    if image_ids:
        if image_name is not None:
            expected_id = expected_images[image_name]["id"]
            if any(image_id != expected_id for image_id in image_ids):
                raise ImageIdentityError("scan_target_id_mismatch")
        elif any(
            image_id not in {expected_images[name]["id"] for name in IMAGE_NAMES}
            for image_id in image_ids
        ):
            raise ImageIdentityError("scan_target_id_mismatch")


def validate_scan_inputs(
    scan_inputs: list[tuple[str, Any]], identity: dict[str, Any]
) -> list[str]:
    """Require one complete, uniquely mapped Trivy scan per final image."""

    errors: list[str] = []
    if len(scan_inputs) != len(IMAGE_NAMES):
        errors.append("scan_input_count_invalid")

    seen: set[str] = set()
    for source_name, payload in scan_inputs:
        image_name = _scan_image_name(source_name)
        if image_name is None:
            errors.append("scan_input_unknown")
            continue
        if image_name in seen:
            errors.append("scan_input_duplicate")
            continue
        seen.add(image_name)
        try:
            validate_scan_target(
                payload,
                source_name,
                identity,
                require_metadata=True,
            )
        except ImageIdentityError as error:
            errors.append(error.code)

    if seen != set(IMAGE_NAMES):
        errors.append("scan_input_missing")
    return sorted(set(errors))


def evaluate(
    findings: list[dict[str, str]], dispositions: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    reviewed: list[dict[str, Any]] = []
    blockers: list[str] = []
    disposition_rows = dispositions.get("findings", {}) if dispositions else {}
    for finding in findings:
        disposition = disposition_rows.get(finding["key"])
        severity = finding["severity"]
        reason = "below_release_threshold"
        blocking = False
        if severity == "CRITICAL":
            blocking = True
            reason = "confirmed_critical"
        elif severity == "HIGH":
            if not isinstance(disposition, dict):
                blocking = True
                reason = "high_requires_exploitability_review"
            elif disposition.get("exploitable") is True:
                blocking = True
                reason = "exploitable_high"
            elif (
                disposition.get("exploitable") is False
                and str(disposition.get("rationale", "")).strip()
            ):
                reason = "reviewed_not_exploitable"
            else:
                blocking = True
                reason = "invalid_high_disposition"
        row = {
            **finding,
            "blocking": blocking,
            "policy_reason": reason,
            "disposition": disposition,
        }
        reviewed.append(row)
        if blocking:
            blockers.append(finding["key"])
    return reviewed, blockers


def _dependency_manifest(
    repository: Path,
    image_record: Path | None,
    *,
    canonical_final_image_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    uv_lock_path = repository / "backend" / "uv.lock"
    package_lock_path = repository / "frontend" / "package-lock.json"
    image_digest_path = repository / "ops" / "release" / "image-digests.json"
    platform_support_path = repository / "ops" / "release" / "platform-support.json"
    package_lock = _load_json(package_lock_path)
    python_packages = sorted(
        {
            f"{name}=={version}"
            for name, version in re.findall(
                r'(?ms)^\[\[package\]\]\s+name = "([^"]+)"\s+version = "([^"]+)"',
                uv_lock_path.read_text(encoding="utf-8"),
            )
        }
    )
    npm_packages = sorted(
        {
            f"{path.removeprefix('node_modules/')}@{row['version']}"
            for path, row in package_lock.get("packages", {}).items()
            if path and row.get("version")
        }
    )
    files = [
        uv_lock_path,
        package_lock_path,
        image_digest_path,
        platform_support_path,
    ]
    final_images: dict[str, Any] = {}
    if canonical_final_image_record is not None:
        final_images = canonical_final_image_record
    elif image_record:
        try:
            final_images = canonicalize_image_record(_load_json(image_record))
        except (
            ImageIdentityError,
            OSError,
            ScanInputError,
            UnicodeError,
            json.JSONDecodeError,
        ):
            # The policy report carries the safe binding error code. Keep the
            # companion manifest writable without echoing a local path.
            final_images = {}
    return {
        "schema_version": 1,
        # This standalone gate also runs with the macOS system Python 3.9.
        "generated_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "lockfile_sha256": {
            str(path.relative_to(repository)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in files
        },
        "python_dependencies": python_packages,
        "npm_dependencies": npm_packages,
        "pinned_base_images": _load_json(image_digest_path),
        "base_image_platform_support": _load_json(platform_support_path),
        "final_images": final_images,
    }


def _write_checksummed(path: Path, payload: dict[str, Any]) -> None:
    serialized = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    path.write_text(serialized, encoding="utf-8")
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--pip-audit", type=Path, required=True)
    parser.add_argument("--npm-audit", type=Path, required=True)
    parser.add_argument("--trivy", type=Path, action="append", default=[])
    parser.add_argument("--dispositions", type=Path)
    parser.add_argument("--image-record", type=Path)
    parser.add_argument("--built-image-identity", type=Path)
    parser.add_argument("--host-os")
    parser.add_argument("--host-architecture")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    findings: list[dict[str, str]] = []
    security_errors: list[str] = []
    pip_loaded = True
    try:
        pip_payload = _load_json(args.pip_audit)
    except json.JSONDecodeError:
        pip_payload = None
        pip_loaded = False
        security_errors.append("pip_audit_invalid_json")
    except (OSError, UnicodeError):
        pip_payload = None
        pip_loaded = False
        security_errors.append("pip_audit_unreadable")
    if pip_loaded:
        try:
            validate_pip_audit(pip_payload)
        except ScanInputError as error:
            security_errors.append(error.code)
        else:
            findings.extend(normalize_pip_audit(pip_payload))

    npm_loaded = True
    try:
        npm_payload = _load_json(args.npm_audit)
    except json.JSONDecodeError:
        npm_payload = None
        npm_loaded = False
        security_errors.append("npm_audit_invalid_json")
    except (OSError, UnicodeError):
        npm_payload = None
        npm_loaded = False
        security_errors.append("npm_audit_unreadable")
    if npm_loaded:
        try:
            validate_npm_audit(npm_payload)
        except ScanInputError as error:
            security_errors.append(error.code)
        else:
            findings.extend(normalize_npm_audit(npm_payload))

    trivy_payloads: list[tuple[Path, Any]] = []
    if not args.trivy:
        security_errors.append("trivy_input_missing")
    for trivy_path in args.trivy:
        try:
            trivy_payload = _load_json(trivy_path)
        except json.JSONDecodeError:
            security_errors.append("trivy_invalid_json")
            continue
        except (OSError, UnicodeError):
            security_errors.append("trivy_unreadable")
            continue
        try:
            validate_trivy(trivy_payload)
        except ScanInputError as error:
            security_errors.append(error.code)
            continue
        trivy_payloads.append((trivy_path, trivy_payload))
        findings.extend(normalize_trivy(trivy_payload, f"trivy:{trivy_path.stem}"))
    dispositions: dict[str, Any] = {}
    if args.dispositions:
        try:
            dispositions_payload = _load_json(args.dispositions)
        except json.JSONDecodeError:
            security_errors.append("dispositions_invalid_json")
        except (OSError, UnicodeError):
            security_errors.append("dispositions_unreadable")
        else:
            try:
                dispositions = validate_dispositions(dispositions_payload)
            except ScanInputError as error:
                security_errors.append(error.code)
    reviewed, blockers = evaluate(findings, dispositions)

    scanner_mode = "identity-bound" if args.built_image_identity else "legacy"
    identity: dict[str, Any] | None = None
    binding_errors: list[str] = []
    if args.built_image_identity:
        try:
            identity = validate_built_image_identity(args.built_image_identity)
        except ImageIdentityError as error:
            binding_errors.append(error.code)
        if identity is None:
            # Do not attempt to interpret untrusted records against a malformed
            # identity. The failed report still records the safe error code.
            pass
        if identity is not None:
            binding_errors.extend(
                validate_scan_inputs(
                    [
                        (f"trivy:{trivy_path.stem}", trivy_payload)
                        for trivy_path, trivy_payload in trivy_payloads
                    ],
                    identity,
                )
            )

    host_os: str | None = None
    host_architecture: str | None = None
    if args.built_image_identity:
        if not args.host_os or not args.host_architecture:
            binding_errors.append("host_identity_missing")
        else:
            try:
                host_os, host_architecture = normalize_host_identity(
                    args.host_os,
                    args.host_architecture,
                )
            except ScanInputError as error:
                binding_errors.append(error.code)
    elif args.host_os or args.host_architecture:
        if not args.host_os or not args.host_architecture:
            security_errors.append("host_identity_missing")
        else:
            try:
                normalize_host_identity(args.host_os, args.host_architecture)
            except ScanInputError as error:
                security_errors.append(error.code)

    image_record_payload: Any = None
    image_record_sha256: str | None = None
    canonical_final_image_record: dict[str, dict[str, str]] = {}
    if args.image_record:
        try:
            image_record_bytes = args.image_record.read_bytes()
            image_record_sha256 = hashlib.sha256(image_record_bytes).hexdigest()
            image_record_payload = json.loads(image_record_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            error_code = (
                "image_record_invalid_json"
                if not args.built_image_identity
                else "image_record_unreadable"
            )
            (
                security_errors if not args.built_image_identity else binding_errors
            ).append(error_code)
        except (OSError, UnicodeError):
            error_code = "image_record_unreadable"
            (
                security_errors if not args.built_image_identity else binding_errors
            ).append(error_code)
        else:
            if identity is not None:
                try:
                    canonical_final_image_record = validate_image_record(
                        image_record_payload,
                        identity,
                    )
                except ImageIdentityError as error:
                    binding_errors.append(error.code)
            elif not args.built_image_identity:
                try:
                    canonical_final_image_record = canonicalize_image_record(
                        image_record_payload
                    )
                except (ImageIdentityError, ScanInputError) as error:
                    security_errors.append(error.code)
    elif args.built_image_identity:
        binding_errors.append("image_record_missing")

    scanner_evidence_sha256: str | None = None
    if not security_errors and pip_loaded and npm_loaded:
        scanner_evidence_sha256 = scanner_evidence_digest(
            pip_payload,
            npm_payload,
            [
                (
                    _canonical_scan_source(f"trivy:{trivy_path.stem}"),
                    trivy_payload,
                )
                for trivy_path, trivy_payload in trivy_payloads
            ],
            dispositions,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: UP017
    report: dict[str, Any] = {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "status": (
            "failed" if blockers or binding_errors or security_errors else "passed"
        ),
        "policy": "critical-blocks; high-blocks-until-reviewed-not-exploitable",
        "finding_count": len(reviewed),
        "blocking_keys": blockers,
        "findings": reviewed,
        "binding_errors": sorted(set(binding_errors)),
        "security_errors": sorted(set(security_errors)),
        "scannerMode": scanner_mode,
        "imageRecordSha256": image_record_sha256,
        "scannerEvidenceSha256": scanner_evidence_sha256,
        "finalImageRecord": canonical_final_image_record,
    }
    if args.built_image_identity:
        report.update(
            {
                "hostOS": host_os,
                "architecture": host_architecture,
                "imagePlatform": identity["platform"] if identity else None,
                "builtImageIdentitySha256": identity["sha256"] if identity else None,
                "imageIds": (
                    {name: identity["images"][name]["id"] for name in IMAGE_NAMES}
                    if identity
                    else {}
                ),
                "imageReferences": (
                    {
                        name: identity["images"][name]["reference"]
                        for name in IMAGE_NAMES
                    }
                    if identity
                    else {}
                ),
            }
        )
    _write_checksummed(args.output_dir / f"security-scan-{timestamp}.json", report)
    _write_checksummed(
        args.output_dir / f"dependency-image-manifest-{timestamp}.json",
        _dependency_manifest(
            args.repository,
            args.image_record,
            canonical_final_image_record=canonical_final_image_record,
        ),
    )
    sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 1 if blockers or binding_errors or security_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
