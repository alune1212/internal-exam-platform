import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from ops.security.evaluate_scans import (  # ty: ignore[unresolved-import]
    ImageIdentityError,
    ScanInputError,
    evaluate,
    main,
    normalize_host_identity,
    normalize_npm_audit,
    normalize_trivy,
    scanner_evidence_digest,
    validate_built_image_identity,
    validate_dispositions,
    validate_image_record,
    validate_npm_audit,
    validate_pip_audit,
    validate_scan_inputs,
    validate_trivy,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_FIXTURES = REPO_ROOT / "ops" / "security" / "fixtures"


def _built_identity_path() -> Path:
    return SECURITY_FIXTURES / "example-built-image-identity.json"


def _image_record_path() -> Path:
    return SECURITY_FIXTURES / "example-final-image-record.json"


def _scan_fixture_path(image_name: str) -> Path:
    return SECURITY_FIXTURES / f"trivy-{image_name}.json"


def _scan_inputs() -> list[tuple[str, object]]:
    return [
        (f"trivy:{name}", json.loads(_scan_fixture_path(name).read_text()))
        for name in ("database", "backend", "frontend", "gateway")
    ]


def _identity_and_records() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity = validate_built_image_identity(_built_identity_path())
    records = json.loads(_image_record_path().read_text(encoding="utf-8"))
    return identity, records


def test_critical_and_unreviewed_high_block_release_evidence() -> None:
    findings = [
        {
            "key": "trivy:backend:openssl:CVE-1",
            "source": "trivy:backend",
            "package": "openssl",
            "installed_version": "1",
            "vulnerability_id": "CVE-1",
            "severity": "CRITICAL",
        },
        {
            "key": "npm-audit:vite:GHSA-2",
            "source": "npm-audit",
            "package": "vite",
            "installed_version": "1",
            "vulnerability_id": "GHSA-2",
            "severity": "HIGH",
        },
    ]
    _reviewed, blockers = evaluate(findings, {})
    assert blockers == ["trivy:backend:openssl:CVE-1", "npm-audit:vite:GHSA-2"]


def test_reviewed_non_exploitable_high_is_documented_and_nonblocking() -> None:
    finding = {
        "key": "npm-audit:tool:GHSA-1",
        "source": "npm-audit",
        "package": "tool",
        "installed_version": "1",
        "vulnerability_id": "GHSA-1",
        "severity": "HIGH",
    }
    reviewed, blockers = evaluate(
        [finding],
        {
            "findings": {
                finding["key"]: {"exploitable": False, "rationale": "not shipped"}
            }
        },
    )
    assert blockers == []
    assert reviewed[0]["policy_reason"] == "reviewed_not_exploitable"


def test_scan_normalizers_preserve_source_identity() -> None:
    npm = normalize_npm_audit(
        {"vulnerabilities": {"pkg": {"name": "pkg", "range": "<2", "severity": "high"}}}
    )
    trivy = normalize_trivy(
        {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "PkgName": "lib",
                            "InstalledVersion": "1",
                            "VulnerabilityID": "CVE-3",
                            "Severity": "LOW",
                        }
                    ]
                }
            ]
        },
        "trivy:frontend",
    )
    assert npm[0]["key"] == "npm-audit:pkg:pkg"
    assert trivy[0]["key"] == "trivy:frontend:lib:CVE-3"


def test_trivy_v070_clean_result_may_omit_vulnerabilities() -> None:
    payload = {
        "SchemaVersion": 2,
        "Results": [
            {
                "Target": "debian 12.11",
                "Class": "os-pkgs",
                "Type": "debian",
            }
        ],
    }

    validate_trivy(payload)

    assert normalize_trivy(payload, "trivy:backend") == []


@pytest.mark.parametrize(
    "result",
    [
        {"Class": "os-pkgs", "Type": "debian"},
        {"Target": "debian 12.11", "Type": "debian"},
        {"Target": "debian 12.11", "Class": "os-pkgs"},
        {
            "Target": "debian 12.11",
            "Class": "not-a-trivy-class",
            "Type": "debian",
        },
        {"Target": "debian 12.11", "Class": "os-pkgs", "Type": ""},
        {
            "Target": "debian 12.11",
            "Class": "os-pkgs",
            "Type": "debian",
            "Vulnerabilities": None,
        },
        {
            "Target": "debian 12.11",
            "Class": "os-pkgs",
            "Type": "debian",
            "Vulnerabilities": {},
        },
    ],
)
def test_trivy_clean_result_missing_or_malformed_fields_fails_closed(
    result: dict[str, Any],
) -> None:
    with pytest.raises(ScanInputError) as error:
        validate_trivy({"SchemaVersion": 2, "Results": [result]})

    assert error.value.code == "trivy_schema_invalid"


def test_trivy_vulnerability_policy_still_blocks_critical_findings() -> None:
    payload = {
        "SchemaVersion": 2,
        "Results": [
            {
                "Target": "debian 12.11",
                "Class": "os-pkgs",
                "Type": "debian",
                "Vulnerabilities": [
                    {
                        "PkgName": "openssl",
                        "InstalledVersion": "1",
                        "VulnerabilityID": "CVE-1",
                        "Severity": "CRITICAL",
                    }
                ],
            }
        ],
    }

    validate_trivy(payload)
    _reviewed, blockers = evaluate(
        normalize_trivy(payload, "trivy:backend"),
        {},
    )

    assert blockers == ["trivy:backend:openssl:CVE-1"]


def test_built_image_identity_binds_exact_images_and_report_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity, records = _identity_and_records()
    bound = validate_image_record(records, identity)

    assert identity["platform"] == "linux/arm64"
    assert set(bound) == {"db", "backend", "frontend", "gateway"}
    assert bound["backend"]["id"] == identity["images"]["backend"]["id"]

    output_dir = tmp_path / "evidence"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_scans.py",
            "--repository",
            str(REPO_ROOT),
            "--pip-audit",
            str(SECURITY_FIXTURES / "empty-pip-audit.json"),
            "--npm-audit",
            str(SECURITY_FIXTURES / "empty-npm-audit.json"),
            "--trivy",
            str(_scan_fixture_path("database")),
            "--trivy",
            str(_scan_fixture_path("backend")),
            "--trivy",
            str(_scan_fixture_path("frontend")),
            "--trivy",
            str(_scan_fixture_path("gateway")),
            "--image-record",
            str(_image_record_path()),
            "--built-image-identity",
            str(_built_identity_path()),
            "--host-os",
            "macos",
            "--host-architecture",
            "aarch64",
            "--output-dir",
            str(output_dir),
        ],
    )
    assert main() == 0
    report = json.loads(next(output_dir.glob("security-scan-*.json")).read_text())
    assert report["status"] == "passed"
    assert report["scannerMode"] == "identity-bound"
    assert report["hostOS"] == "darwin"
    assert report["architecture"] == "arm64"
    assert report["imagePlatform"] == "linux/arm64"
    assert report["builtImageIdentitySha256"] == identity["sha256"]
    assert (
        report["imageRecordSha256"]
        == hashlib.sha256(_image_record_path().read_bytes()).hexdigest()
    )
    assert report["finalImageRecord"] == bound
    assert report["scannerEvidenceSha256"] == scanner_evidence_digest(
        json.loads(
            (SECURITY_FIXTURES / "empty-pip-audit.json").read_text(encoding="utf-8")
        ),
        json.loads(
            (SECURITY_FIXTURES / "empty-npm-audit.json").read_text(encoding="utf-8")
        ),
        _scan_inputs(),
        {},
    )
    assert report["imageIds"] == {
        name: identity["images"][name]["id"]
        for name in ("db", "backend", "frontend", "gateway")
    }
    assert report["imageReferences"] == {
        name: identity["images"][name]["reference"]
        for name in ("db", "backend", "frontend", "gateway")
    }
    manifest = json.loads(
        next(output_dir.glob("dependency-image-manifest-*.json")).read_text()
    )
    assert manifest["final_images"] == bound
    assert "REDACT_ME" not in json.dumps(report)
    assert "REDACT_ME" not in json.dumps(manifest)


def test_mismatched_image_id_blocks_identity_binding() -> None:
    identity, records = _identity_and_records()
    records[1]["Id"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )

    with pytest.raises(ImageIdentityError) as error:
        validate_image_record(records, identity)

    assert error.value.code == "image_record_id_mismatch"


def test_mismatched_image_platform_blocks_identity_binding() -> None:
    identity, records = _identity_and_records()
    records[2]["Architecture"] = "amd64"

    with pytest.raises(ImageIdentityError) as error:
        validate_image_record(records, identity)

    assert error.value.code == "image_record_platform_mismatch"


def test_tampered_built_image_identity_checksum_is_rejected(tmp_path: Path) -> None:
    identity_path = tmp_path / "built-image-identity.json"
    identity_path.write_bytes(_built_identity_path().read_bytes() + b"\n")
    checksum = (
        _built_identity_path()
        .with_name(_built_identity_path().name + ".sha256")
        .read_text(encoding="ascii")
        .split()[0]
    )
    identity_path.with_name(identity_path.name + ".sha256").write_text(
        f"{checksum}  {identity_path.name}\n",
        encoding="ascii",
    )

    with pytest.raises(ImageIdentityError) as error:
        validate_built_image_identity(identity_path)

    assert error.value.code == "built_image_identity_checksum_mismatch"


def test_missing_final_image_blocks_identity_binding() -> None:
    identity, records = _identity_and_records()
    records.pop()

    with pytest.raises(ImageIdentityError) as error:
        validate_image_record(records, identity)

    assert error.value.code == "image_record_images_invalid"


def test_identity_mode_requires_all_unique_targeted_trivy_inputs() -> None:
    identity, _records = _identity_and_records()

    errors = validate_scan_inputs(_scan_inputs()[:-1], identity)

    assert "scan_input_count_invalid" in errors
    assert "scan_input_missing" in errors


def test_identity_mode_rejects_duplicate_and_unknown_trivy_inputs() -> None:
    identity, _records = _identity_and_records()
    scans = _scan_inputs()
    scans[3] = ("trivy:backend", scans[1][1])

    errors = validate_scan_inputs(scans, identity)

    assert "scan_input_duplicate" in errors
    assert "scan_input_missing" in errors

    unknown_errors = validate_scan_inputs(
        [*scans[:3], ("trivy:unknown", scans[3][1])], identity
    )
    assert "scan_input_unknown" in unknown_errors


def test_identity_mode_rejects_missing_or_mismatched_scan_metadata() -> None:
    identity, _records = _identity_and_records()
    scans = _scan_inputs()
    scans[0] = ("trivy:database", {"Results": []})

    missing_errors = validate_scan_inputs(scans, identity)
    assert "scan_target_metadata_missing" in missing_errors

    mismatch = json.loads(_scan_fixture_path("backend").read_text())
    mismatch["ArtifactName"] = "wrong/image:tag"
    mismatch_scans = _scan_inputs()
    mismatch_scans[1] = ("trivy:backend", mismatch)

    mismatch_errors = validate_scan_inputs(mismatch_scans, identity)
    assert "scan_target_reference_mismatch" in mismatch_errors

    id_mismatch = json.loads(_scan_fixture_path("backend").read_text())
    id_mismatch["Metadata"]["ImageID"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    id_mismatch_scans = _scan_inputs()
    id_mismatch_scans[1] = ("trivy:backend", id_mismatch)

    id_mismatch_errors = validate_scan_inputs(id_mismatch_scans, identity)
    assert "scan_target_id_mismatch" in id_mismatch_errors


def test_identity_mode_distinguishes_trivy_artifact_id_from_docker_image_id() -> None:
    identity, _records = _identity_and_records()
    scan = json.loads(_scan_fixture_path("backend").read_text())

    # Trivy's ArtifactID is a scanner artifact digest and can legitimately
    # differ from Docker's config ImageID.  The nested Metadata.ImageID is the
    # value that must bind to the built image identity.
    assert scan["ArtifactID"] != identity["images"]["backend"]["id"]
    assert scan["Metadata"]["ImageID"] == identity["images"]["backend"]["id"]
    scans = _scan_inputs()
    scans[1] = ("trivy:backend", scan)
    assert validate_scan_inputs(scans, identity) == []

    scan["Metadata"].pop("ImageID")
    errors = validate_scan_inputs(scans, identity)
    assert "scan_target_id_metadata_missing" in errors


@pytest.mark.parametrize(
    ("validator", "payload"),
    [
        (validate_pip_audit, {}),
        (validate_npm_audit, {"error": "audit failed"}),
        (
            validate_npm_audit,
            {"auditReportVersion": 2, "vulnerabilities": {}, "metadata": {}},
        ),
        (validate_trivy, {"Results": []}),
    ],
)
def test_scan_schema_errors_fail_closed(validator, payload: Any) -> None:
    with pytest.raises(ScanInputError) as error:
        validator(payload)

    assert error.value.code.endswith("_schema_invalid")


def test_policy_report_records_scan_schema_error_without_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_pip = tmp_path / "pip-error.json"
    invalid_pip.write_text('{"error":"pip-audit failed"}', encoding="utf-8")
    output_dir = tmp_path / "evidence"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_scans.py",
            "--repository",
            str(REPO_ROOT),
            "--pip-audit",
            str(invalid_pip),
            "--npm-audit",
            str(SECURITY_FIXTURES / "empty-npm-audit.json"),
            "--trivy",
            str(SECURITY_FIXTURES / "empty-trivy.json"),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert main() == 1
    report = json.loads(next(output_dir.glob("security-scan-*.json")).read_text())
    assert report["status"] == "failed"
    assert report["security_errors"] == ["pip_audit_schema_invalid"]
    assert str(invalid_pip) not in json.dumps(report)


def test_host_identity_and_scanner_evidence_digest_bind_and_detect_tampering() -> None:
    assert normalize_host_identity("macOS", "aarch64") == ("darwin", "arm64")
    with pytest.raises(ScanInputError) as error:
        normalize_host_identity("darwin", "amd64")
    assert error.value.code == "host_identity_invalid"

    pip_payload = json.loads(
        (SECURITY_FIXTURES / "empty-pip-audit.json").read_text(encoding="utf-8")
    )
    npm_payload = json.loads(
        (SECURITY_FIXTURES / "empty-npm-audit.json").read_text(encoding="utf-8")
    )
    scans = _scan_inputs()
    original = scanner_evidence_digest(pip_payload, npm_payload, scans, {})
    tampered_scan = json.loads(_scan_fixture_path("backend").read_text())
    tampered_scan["ArtifactID"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    tampered = scanner_evidence_digest(
        pip_payload,
        npm_payload,
        [
            (source, tampered_scan if source == "trivy:backend" else payload)
            for source, payload in scans
        ],
        {},
    )
    assert original != tampered


def test_dispositions_schema_errors_fail_closed() -> None:
    with pytest.raises(ScanInputError) as error:
        validate_dispositions({"findings": []})
    assert error.value.code == "dispositions_schema_invalid"

    with pytest.raises(ScanInputError) as error:
        validate_dispositions(
            {"findings": {"npm-audit:pkg:CVE": {"exploitable": "no"}}}
        )
    assert error.value.code == "dispositions_schema_invalid"


def test_invalid_dispositions_are_reported_without_path_or_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispositions_path = tmp_path / "dispositions.json"
    dispositions_path.write_text('{"findings":[]}', encoding="utf-8")
    output_dir = tmp_path / "evidence"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_scans.py",
            "--repository",
            str(REPO_ROOT),
            "--pip-audit",
            str(SECURITY_FIXTURES / "empty-pip-audit.json"),
            "--npm-audit",
            str(SECURITY_FIXTURES / "empty-npm-audit.json"),
            "--trivy",
            str(SECURITY_FIXTURES / "empty-trivy.json"),
            "--dispositions",
            str(dispositions_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert main() == 1
    report = json.loads(next(output_dir.glob("security-scan-*.json")).read_text())
    assert report["security_errors"] == ["dispositions_schema_invalid"]
    assert str(dispositions_path) not in json.dumps(report)


def test_weekly_workflow_scans_every_final_image_with_digest_pinned_trivy() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "security-maintenance.yml"
    ).read_text(encoding="utf-8")

    assert 'cron: "23 18 * * 5"' in workflow
    for image_name in ("database", "backend", "frontend", "gateway"):
        assert f"internal-exam-platform-{image_name}:security-scan" in workflow
        assert f"trivy-{image_name}.json" in workflow
    trivy_image = (
        "aquasec/trivy@sha256:"
        "be1190afcb28352bfddc4ddeb71470835d16462af68d310f9f4bca710961a41e"
    )
    assert trivy_image in workflow
    assert 'docker run --rm "$TRIVY_IMAGE" --version' in workflow
    assert "aquasecurity/trivy-action@" not in workflow


def test_weekly_workflow_keeps_raw_inspect_outside_artifact_and_evaluates_it() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "security-maintenance.yml"
    ).read_text(encoding="utf-8")

    raw_record = "$RUNNER_TEMP/final-images.inspect.json"
    assert raw_record in workflow
    assert '--image-record "$RUNNER_TEMP/final-images.inspect.json"' in workflow
    assert "python ops/security/evaluate_scans.py" in workflow
    assert "--output-dir security-evidence" in workflow
    assert "> security-evidence/final-images.json" not in workflow
    assert "Remove temporary raw image inspection" in workflow
    assert "if: always()" in workflow
    assert 'rm -f -- "$RUNNER_TEMP/final-images.inspect.json"' in workflow


def test_weekly_workflow_pins_pip_audit_and_preserves_hash_checks() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "security-maintenance.yml"
    ).read_text(encoding="utf-8")

    assert "pip-audit==2.9.0" in workflow
    assert "--disable-pip" in workflow
    assert "--require-hashes" in workflow


def test_pinned_base_images_are_verified_for_arm64_and_amd64() -> None:
    release_root = REPO_ROOT / "ops" / "release"
    image_digests = json.loads(
        (release_root / "image-digests.json").read_text(encoding="utf-8")
    )
    support = json.loads(
        (release_root / "platform-support.json").read_text(encoding="utf-8")
    )

    assert support["schema_version"] == 1
    assert support["required_platforms"] == ["linux/amd64", "linux/arm64"]
    assert set(support["images"]) == set(image_digests)
    for name, image_ref in image_digests.items():
        row = support["images"][name]
        assert image_ref.endswith(f"@{row['index_digest']}")
        assert row["platforms"] == support["required_platforms"]
