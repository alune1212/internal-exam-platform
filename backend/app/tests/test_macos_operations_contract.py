import plistlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MACOS_OPS = REPO_ROOT / "ops" / "macos"


def _shell_scripts() -> list[Path]:
    if not MACOS_OPS.is_dir():
        raise AssertionError(
            "ops/macos is required by the macOS formal-host contract; "
            "the operations implementation has not landed yet"
        )

    scripts: list[Path] = []
    for path in sorted(MACOS_OPS.rglob("*")):
        if not path.is_file():
            continue
        first_line = path.read_text(encoding="utf-8").splitlines()[:1]
        if path.suffix in {".sh", ".zsh", ".command"} or (
            first_line and "zsh" in first_line[0]
        ):
            scripts.append(path)
    if not scripts:
        raise AssertionError("ops/macos must contain at least one zsh operation")
    return scripts


def _shell_contract() -> str:
    scripts = _shell_scripts()
    return "\n".join(
        f"{path.name}\n{path.read_text(encoding='utf-8')}" for path in scripts
    )


def _launch_agent_files() -> list[Path]:
    if not MACOS_OPS.is_dir():
        raise AssertionError("ops/macos is required before LaunchAgent checks run")
    return sorted(
        path
        for path in MACOS_OPS.rglob("*")
        if path.is_file()
        and (
            path.suffix in {".plist", ".xml"}
            or path.name.endswith(".plist.in")
            or path.name.endswith(".plist.template")
        )
    )


def test_macos_operation_surface_is_present() -> None:
    contract = _shell_contract().lower()
    for marker in (
        "initialize",
        "release",
        "build",
        "start",
        "stop",
        "status",
        "staging",
        "preflight",
        "backup",
        "restore",
        "promot",
        "rollback",
        "session",
        "diagnostic",
    ):
        assert marker in contract, f"macOS operation marker missing: {marker}"


def test_macos_formal_and_staging_projects_are_explicit_and_isolated() -> None:
    contract = _shell_contract()
    lowered = contract.lower()

    assert "internal-exam-formal" in lowered
    assert re.search(r"internal-exam-staging(?:[-_$]|\b)", lowered)
    assert "--project-name" in lowered or re.search(r"\b-p\b", lowered)
    assert "compose" in lowered
    assert "--no-build" in lowered or "no_build" in lowered


def test_macos_formal_layout_uses_absolute_operator_owned_paths() -> None:
    lowered = _shell_contract().lower()

    assert "library/application support/internalexam" in lowered
    for directory in (
        "configuration",
        "releases",
        "backups",
        "evidence",
        "diagnostics",
        "state",
    ):
        assert directory in lowered

    # Formal host paths must not silently fall back to repository-relative data.
    assert not re.search(
        r"(?:formal|backup|evidence|release|diagnostic|state)[^=\n]*=\s*['\"]?\./",
        lowered,
    )
    assert "chmod" in lowered or "umask" in lowered or "owner" in lowered


def test_macos_release_evidence_records_identity_architecture_and_redaction() -> None:
    lowered = _shell_contract().lower()
    for marker in (
        "darwin",
        "arm64",
        "architecture",
        "git_commit",
        "application_version",
        "migration_head",
        "image",
    ):
        assert marker in lowered, (
            f"architecture-aware evidence marker missing: {marker}"
        )
    assert any(marker in lowered for marker in ("redact", "redacted", "[redacted]"))
    assert "sha256" in lowered or "shasum" in lowered


def test_macos_secret_isolation_and_bounded_logging_contract() -> None:
    lowered = _shell_contract().lower()
    assert "--env-file" in lowered or "env_file" in lowered
    assert any(marker in lowered for marker in ("tail", "max-size", "max_file"))
    assert any(marker in lowered for marker in ("log", "diagnostic"))
    for development_secret in (
        "local-dev-token-secret",
        "local-dev-admin-password",
        "local-dev-postgres-password",
    ):
        assert development_secret not in lowered


def test_launchagent_templates_are_valid_and_write_to_bounded_paths() -> None:
    launch_agents = _launch_agent_files()
    if not launch_agents:
        raise AssertionError("ops/macos must provide LaunchAgent plist templates")

    for path in launch_agents:
        raw = path.read_bytes()
        document = plistlib.loads(raw)
        assert isinstance(document, dict)
        assert document.get("Label")
        assert document.get("ProgramArguments")
        stdout = str(document.get("StandardOutPath", ""))
        stderr = str(document.get("StandardErrorPath", ""))
        assert stdout
        assert stderr
        assert stdout != stderr
        assert "internalexam" in f"{stdout} {stderr}".lower()
        assert "token_secret" not in raw.decode("utf-8").lower()
        assert "admin_password" not in raw.decode("utf-8").lower()


def test_ci_runs_macos_contracts_and_keeps_powershell_coverage() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert "ops/macos" in workflow
    assert "zsh -n" in workflow
    assert "plutil" in workflow
    assert "plistlib" in workflow
    assert "test_macos_operations_contract.py" in workflow
    assert "Test-PowerShellSyntax.ps1" in workflow


def test_every_zsh_operation_parses_and_every_launchagent_plist_lints() -> None:
    zsh = shutil.which("zsh")
    plutil = shutil.which("plutil")
    if not zsh or not plutil:
        pytest.skip("macOS shell/plist tools are unavailable on this runner")

    for script in _shell_scripts():
        result = subprocess.run(  # noqa: S603
            [zsh, "-n", "--", str(script)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{script}: {result.stderr}"
    for plist in _launch_agent_files():
        result = subprocess.run(  # noqa: S603
            [plutil, "-lint", "--", str(plist)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{plist}: {result.stderr}"


def test_every_zsh_operation_is_owner_only_executable() -> None:
    for script in _shell_scripts():
        assert script.stat().st_mode & 0o777 == 0o700, (
            f"{script} must be owner-only executable (mode 0700)"
        )


def test_common_uses_real_temporary_layout_and_rejects_dangerous_roots() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-contract-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "Formal Root With Spaces"
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
artifact="$2/evidence/contract.json"
macos_write_atomic "$artifact" '{"status":"passed","secrets":"redacted"}'
macos_write_checksum "$artifact"
macos_check_checksum "$artifact"
[[ "$(stat -f '%Lp' "$artifact")" == 600 ]]
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert (root / "evidence/contract.json.sha256").is_file()

        dangerous = Path(temporary) / "repo-link"
        dangerous.symlink_to(REPO_ROOT, target_is_directory=True)
        rejected = subprocess.run(  # noqa: S603
            [
                zsh,
                "-c",
                'source "$1/Common.zsh"; macos_initialize_layout "$2"',
                "contract",
                str(MACOS_OPS),
                str(dangerous),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert rejected.returncode != 0
        assert not (REPO_ROOT / "configuration").exists()


def test_common_command_vector_and_redaction_do_not_execute_secret_payloads() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-redaction-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        directory = Path(temporary)
        output = directory / "redacted.txt"
        marker = directory / "injected"
        payload = f"value with spaces; touch {marker}"
        source = directory / "raw.txt"
        source.write_text(
            "Authorization: Bearer super-secret\n"
            "token=super-secret password=super-secret\n",
            encoding="utf-8",
        )
        shell = r"""
source "$1/Common.zsh"
result="$(macos_run_capture printf '%s' "$2")"
[[ "$result" == "$2" ]]
macos_redact_file "$3" "$4"
"""
        result = subprocess.run(  # noqa: S603
            [
                zsh,
                "-c",
                shell,
                "contract",
                str(MACOS_OPS),
                payload,
                str(source),
                str(output),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert not marker.exists(), "unquoted command arguments executed payload text"
        redacted = output.read_text(encoding="utf-8")
        assert "super-secret" not in redacted
        assert "[REDACTED]" in redacted


def test_cutover_sidecar_recovery_requires_canonical_binding_and_exact_fence() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-sidecar-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "formal-root"
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
macos_layout "$2"
release="$2/releases/release"
mkdir -p "$release/ops/release"
macos_write_atomic "$release/docker-compose.yml" 'services: {}'
macos_write_atomic "$release/release-manifest.json" '{"applicationVersion":"1.0.0","gitCommit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","migrationHead":"head"}'
macos_write_atomic "$2/state/host-identity.json" '{"schemaVersion":1,"datasetId":"dataset-1","hostId":"host-target","writerGeneration":2,"lineageState":"bound"}'
macos_write_atomic "$2/state/current-release.json" '{"schemaVersion":1,"applicationVersion":"1.0.0","gitCommit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","path":"'$release'","datasetId":"dataset-1","hostId":"host-target","writerGeneration":2}'
macos_write_atomic "$2/state/cutover-accepted-test.json" '{"schemaVersion":1,"kind":"formal-cutover","state":"accepted","dataset_id":"dataset-1","target_host_id":"host-target","target_writer_generation":2,"target_write_accepted":false,"target_exposed":false}'
macos_write_checksum "$2/state/cutover-accepted-test.json"
rm -f -- "$2/state/host-identity.json.sha256" "$2/state/current-release.json.sha256"
macos_compose() { :; }
macos_operational_lock_one_shot_capture() { print -r -- '{"active":true,"datasetId":"dataset-1","hostId":"host-target","writerGeneration":2}'; }
macos_recover_derived_sidecars "$release" "$2/state/cutover-accepted-test.json"
[[ -f "$2/state/host-identity.json.sha256" && -f "$2/state/current-release.json.sha256" ]]
macos_write_atomic "$2/state/host-identity.json" '{"schemaVersion":1,"datasetId":"dataset-other","hostId":"host-target","writerGeneration":2,"lineageState":"bound"}'
rm -f -- "$2/state/host-identity.json.sha256"
if macos_recover_derived_sidecars "$release" "$2/state/cutover-accepted-test.json"; then
  exit 1
fi
[[ ! -f "$2/state/host-identity.json.sha256" ]]
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_pending_cutover_retires_source_and_keeps_target_private() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-retirement-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "formal-root"
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
macos_layout "$2"
MACOS_DATASET_ID=dataset-1
MACOS_HOST_ID=host-source
MACOS_WRITER_GENERATION=1
state="$2/state/cutover-prepared-test.json"
macos_write_atomic "$state" '{"state":"prepared","dataset_id":"dataset-1","source_host_id":"host-source","target_host_id":"host-target","source_writer_generation":1}'
macos_write_checksum "$state"
if macos_assert_no_pending_cutover_start 0; then
  exit 1
fi
MACOS_WRITER_GENERATION=3
macos_assert_no_pending_cutover_start 0
rm -f -- "$state" "$state.sha256"
MACOS_HOST_ID=host-target
MACOS_WRITER_GENERATION=1
macos_write_atomic "$state" '{"state":"prepared","dataset_id":"dataset-1","source_host_id":"host-source","target_host_id":"host-target","source_writer_generation":1}'
macos_write_checksum "$state"
if macos_assert_no_pending_cutover_start 0; then
  exit 1
fi
macos_assert_no_pending_cutover_start 1
rm -f -- "$state" "$state.sha256"
MACOS_HOST_ID=host-target
MACOS_WRITER_GENERATION=2
rollback="$2/state/cutover-rollback-intent-test.json"
macos_write_atomic "$rollback" '{"kind":"formal-cutover-rollback-intent","status":"intent","acceptedStateSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","datasetId":"dataset-1","targetHostId":"host-target","writerGeneration":2}'
macos_write_checksum "$rollback"
if macos_assert_no_pending_cutover_start 0; then
  exit 1
fi
if macos_assert_no_pending_cutover_start 1; then
  exit 1
fi
MACOS_WRITER_GENERATION=3
macos_assert_no_pending_cutover_start 0
rm -f -- "$rollback" "$rollback.sha256"
MACOS_HOST_ID=host-source
MACOS_WRITER_GENERATION=3
accepted_digest=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
cutback_digest=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
resume_intent="$2/state/source-cutback-resume-intent-${accepted_digest}.json"
macos_write_atomic "$resume_intent" '{"kind":"source-cutback-resume-intent","status":"pending","acceptedStateSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","cutbackStateSha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","datasetId":"dataset-1","sourceHostId":"host-source","targetHostId":"host-target","sourceWriterGeneration":1,"targetWriterGeneration":2,"reconciledWriterGeneration":3}'
macos_write_checksum "$resume_intent"
if macos_assert_no_pending_cutover_start 0; then
  exit 1
fi
macos_assert_no_pending_cutover_start 1
preflight="$2/evidence/source-resume-preflight-test.json"
activation="$2/evidence/source-cutback-activation-intent-test.json"
terminal="$2/state/source-cutback-resume-terminal-${accepted_digest}.json"
macos_write_atomic "$preflight" '{"status":"passed"}'
macos_write_checksum "$preflight"
macos_write_atomic "$activation" '{"status":"intent","acceptedStateSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","cutbackStateSha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
macos_write_checksum "$activation"
resume_intent_sha="$(macos_sha256 "$resume_intent")"
preflight_sha="$(macos_sha256 "$preflight")"
activation_sha="$(macos_sha256 "$activation")"
preflight_json="$(macos_json_escape "$preflight")"
activation_json="$(macos_json_escape "$activation")"
macos_write_atomic "$terminal" "{\"kind\":\"source-cutback-resume-terminal\",\"status\":\"readiness-passed\",\"resumeIntentSha256\":\"$resume_intent_sha\",\"acceptedStateSha256\":\"$accepted_digest\",\"cutbackStateSha256\":\"$cutback_digest\",\"datasetId\":\"dataset-1\",\"sourceHostId\":\"host-source\",\"targetHostId\":\"host-target\",\"reconciledWriterGeneration\":3,\"preflightPath\":\"$preflight_json\",\"preflightSha256\":\"$preflight_sha\",\"activationIntentPath\":\"$activation_json\",\"activationIntentSha256\":\"$activation_sha\"}"
macos_write_checksum "$terminal"
macos_assert_no_pending_cutover_start 0
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_release_and_cutover_gates_are_fail_closed() -> None:
    new_bundle = (MACOS_OPS / "New-ReleaseBundle.zsh").read_text(encoding="utf-8")
    test_bundle = (MACOS_OPS / "Test-ReleaseBundle.zsh").read_text(encoding="utf-8")
    build_images = (MACOS_OPS / "Build-ReleaseImages.zsh").read_text(encoding="utf-8")
    prepare = (MACOS_OPS / "Prepare-HostCutover.zsh").read_text(encoding="utf-8")
    accept = (MACOS_OPS / "Accept-HostCutover.zsh").read_text(encoding="utf-8")
    host_rollback = (MACOS_OPS / "Rollback-HostCutover.zsh").read_text(encoding="utf-8")
    host_resume = (MACOS_OPS / "Resume-HostCutover.zsh").read_text(encoding="utf-8")
    paired_backup = (MACOS_OPS / "Invoke-PairedBackup.zsh").read_text(encoding="utf-8")
    restore_drill = (MACOS_OPS / "Invoke-RestoreDrill.zsh").read_text(encoding="utf-8")
    second_copy_capture = (
        MACOS_OPS / "Capture-SecondCopyStorageEvidence.zsh"
    ).read_text(encoding="utf-8")
    start = (MACOS_OPS / "Start-Platform.zsh").read_text(encoding="utf-8")
    seal = (MACOS_OPS / "Seal-Release.zsh").read_text(encoding="utf-8")
    security_scan = (MACOS_OPS / "Invoke-ReleaseSecurityScan.zsh").read_text(
        encoding="utf-8"
    )
    promote = (MACOS_OPS / "Promote-Release.zsh").read_text(encoding="utf-8")
    release_rollback = (MACOS_OPS / "Rollback-Release.zsh").read_text(encoding="utf-8")
    install_agents = (MACOS_OPS / "Install-LaunchAgents.zsh").read_text(
        encoding="utf-8"
    )
    common = (MACOS_OPS / "Common.zsh").read_text(encoding="utf-8")
    backup_operator = (MACOS_OPS / "Set-BackupOperator.zsh").read_text(encoding="utf-8")
    close_sessions = (MACOS_OPS / "Close-ExamSessions.zsh").read_text(encoding="utf-8")

    assert "rev-parse --show-toplevel" in new_bundle
    assert "diff-index --quiet HEAD" in new_bundle
    assert "--ignored" in new_bundle
    for forbidden in (".env.*", "*.env", "*.pem", "*.key"):
        assert forbidden in new_bundle or forbidden in test_bundle
    assert ".env.example" in new_bundle
    assert ".env.example" in test_bundle
    assert "macos_assert_fresh_timestamp" in seal
    assert "built-image-identity.json" in new_bundle
    assert "docker image inspect" in build_images
    assert "imageDigests" in build_images
    assert "baseImageReferences" in new_bundle
    assert "--no-build" in (MACOS_OPS / "Start-Platform.zsh").read_text(
        encoding="utf-8"
    )
    assert "ps --status running -q" in prepare
    assert "prepare-cutover" in prepare
    assert "--state-path" in prepare
    assert "--release-metadata" in prepare
    assert "--source-stop-proof" in prepare
    assert "source-stop-proof" in prepare
    assert "cutover-release-checksums" in prepare
    assert "accept-cutover" in accept
    assert "--target-host-id" in accept
    assert "consumed" in accept
    assert "cutover-phase-" in accept
    assert "activation-intent" in accept
    assert "--restored-cutover-backup" in accept
    assert "target-not-exposed" in accept
    assert "target-write-not-accepted" in accept
    assert "formal-volume-override.yml" in accept
    assert "macos_operational_lock_one_shot_with_mounts_capture" in accept
    assert "release-fence" in accept
    assert "--no-db-audit" in accept
    assert "new canonical cutover must advance" in accept
    assert accept.index("new canonical cutover must advance") < accept.index(
        "docker volume rm"
    )
    assert "macos_recover_derived_sidecars" in accept
    assert "macos_recover_derived_sidecars" in host_resume
    assert "macos_recover_cutover_state" in common
    assert "recover-cutover-state" in common
    assert accept.index("macos_recover_cutover_state") < accept.index(
        'macos_check_checksum "$prepared_state"'
    )
    assert "canonical_transaction_evidence" in accept
    assert "validate_pre_accept_phase_journal" in accept
    assert "validate_accepted_phase_journal" in accept
    assert "validate_cutover_external_bindings" in accept
    assert "validate-cutover-bindings" in accept
    assert "canonical_prepared_digest" in accept
    assert accept.count("validate_cutover_external_bindings") >= 5
    assert '[[ ! -f "$phase_journal.sha256" ]]' in accept
    assert "pre-accept phase journal volume override checksum changed" in accept
    assert "database fence identity does not match canonical cutover binding" in common
    assert "db_audit" in restore_drill
    assert "diskutil info -plist" in second_copy_capture
    assert "distinctPhysicalDevice" in second_copy_capture
    assert "encrypted" in second_copy_capture
    assert "Encryption" in second_copy_capture
    assert "FileVault" in second_copy_capture
    assert "WritableVolume" in second_copy_capture
    assert "ParentWholeDisk" in second_copy_capture
    assert "PartOfWhole" not in second_copy_capture
    assert "macos_checksummed_json" in second_copy_capture
    assert accept.index("activation_intent_path=") < accept.index(
        '"$SCRIPT_DIR/Start-Platform.zsh"'
    )
    assert "transfer-fence" in host_resume
    assert "reconciled_generation" in host_resume
    assert "release-fence" in host_resume
    first_resume_start = host_resume.index('"$SCRIPT_DIR/Start-Platform.zsh"')
    assert host_resume.index("up -d --no-build db") < host_resume.index(
        "transfer-fence"
    )
    assert host_resume.index("release_result=") < first_resume_start
    assert "source-cutback-activation-intent" in host_resume
    assert "source-cutback-resume-intent-" in host_resume
    assert "source-cutback-resume-terminal-" in host_resume
    assert host_resume.index("resume_intent_path=") < host_resume.index(
        "macos_adopt_cutover_identity"
    )
    assert host_resume.index("source-cutback-activation-intent") < host_resume.rindex(
        '"$SCRIPT_DIR/Start-Platform.zsh"'
    )
    assert host_resume.index(
        'macos_checksummed_json "$resume_terminal_path"'
    ) < host_resume.rindex('"$SCRIPT_DIR/Start-Platform.zsh"')
    assert "activationIntentSha256" in host_resume
    assert "cutover-rollback-intent-" in host_rollback
    assert "cutover-rollback-terminal-" in host_rollback
    assert "rollback_validate_terminal" in host_rollback
    assert "validate_post_write_phase_journal" in host_rollback
    assert '[[ ! -f "$post_write_phase.sha256" ]]' in host_rollback
    assert "post-write phase backup manifest changed" in host_rollback
    assert "formal-cutover-rollback-reverse-intent" in host_rollback
    assert "formal-cutover-rollback-reverse-phase" in host_rollback
    assert "validate_reverse_intent_journal" in host_rollback
    assert "validate_reverse_phase_journal" in host_rollback
    assert "validate_reverse_prepared_state" in host_rollback
    assert "cutover-prepared-reverse-${accepted_digest}.json" in host_rollback
    assert host_rollback.index("formal-cutover-rollback-reverse-intent") < (
        host_rollback.index("prepare-cutover --backup")
    )
    assert "rollback_intent_existing" in host_rollback
    assert "handoffStatePath" in host_rollback
    assert "automatic resume is forbidden" in accept
    assert host_rollback.index("cutover-rollback-intent-") < host_rollback.index(
        "up -d --no-build db"
    )
    assert host_resume.index("macos_adopt_cutover_identity") < host_resume.index(
        "release_result="
    )
    assert "TargetNeverAcceptedWrites" in host_rollback
    assert "TargetAcceptedWrites" in host_rollback
    assert "target_write_accepted" in host_rollback
    assert "host-cutback-prewrite" in host_rollback
    assert "acquire-fence" in host_rollback
    assert "validate-migration-input" in host_rollback
    assert "internal_backup" in host_rollback
    assert "postWriteBackupManifestSha256" in host_rollback
    assert "postBackupWritesMayBeLost" in host_rollback
    assert "sourceReopenRequired" in host_rollback
    assert "sourceWriterGeneration" in host_rollback
    assert "canonical prepared state" in host_rollback
    assert "backup_generation" in host_rollback
    assert '"$backup_generation" == "$accepted_generation"' in host_rollback
    assert "ps --status running -q" in host_rollback
    assert "down -v" not in host_rollback
    assert "existing_prepared" in prepare
    assert "host_cutover_prepared_existing" in prepare
    assert "up -d --no-build db" in prepare
    assert "preserve_fence" in prepare
    assert "selected_new_prepared" in prepare
    assert "consumed_generation < MACOS_WRITER_GENERATION" in prepare
    assert "prepare_phase_journal" in prepare
    assert "prepare_phase_update" in prepare
    assert "source-stopped" in prepare
    assert "cutover" in paired_backup
    assert "under_writer_fence" in paired_backup
    assert "under_writer_fence == 0" in paired_backup
    assert "--maintenance" in start
    assert "macos_assert_writer_fence_clear" in start
    assert "macos_assert_no_pending_cutover_start" in common
    assert 'macos_assert_no_pending_cutover_start "$maintenance"' in start
    assert "this source host is retired by a pending cutover" in common
    assert "pending inbound cutover" in common
    assert "source_generation >= current_generation" in common
    assert "this target host is retired by a cutover rollback" in common
    assert "source cutback resume readiness is pending" in common
    assert "Seal-Release" in seal
    assert "evaluate_scans.py" in security_scan
    assert "trivy" in security_scan.lower()
    assert "pip-audit" in security_scan
    assert "npm audit" in security_scan
    assert "--built-image-identity" in security_scan
    assert "--host-os darwin" in security_scan
    assert "--host-architecture arm64" in security_scan
    assert "canonical-images" in security_scan
    assert 'cp -p -- "$work/final-images.json"' not in security_scan
    assert "builtImageIdentitySha256" in security_scan
    assert "imageReferences" in security_scan
    assert "binding_errors" in security_scan
    assert "--platform linux/arm64" in security_scan
    assert "--platform linux/arm64" not in build_images
    assert "DOCKER_DEFAULT_PLATFORM=linux/arm64" in build_images
    assert "blocking_keys" in seal
    assert "builtImageIdentitySha256" in seal
    assert "images.$index.id" in seal
    assert "linux/arm64" in seal
    assert "status 2>/dev/null" in seal
    assert "== passed" in seal
    assert "staging-acceptance" in promote
    assert "pre-upgrade" in promote
    assert "macos_assert_no_pending_cutover_start 0" in promote
    assert '"$SCRIPT_DIR/Start-Platform.zsh"' in promote
    assert "macos_assert_no_pending_cutover_start 0" in release_rollback
    assert '"$SCRIPT_DIR/Start-Platform.zsh"' in release_rollback
    assert release_rollback.index("macos_assert_writer_fence_clear") < (
        release_rollback.index("pg_restore --clean")
    )
    rollback_fence_index = release_rollback.index("macos_assert_writer_fence_clear")
    assert (
        release_rollback.index('export APP_VERSION_TAG="${current_commit:l}"')
        < rollback_fence_index
    )
    assert (
        release_rollback.rindex('export APP_VERSION_TAG="${previous_commit:l}"')
        > rollback_fence_index
    )
    assert "selected_release" in install_agents
    assert "SCRIPT_DIR" not in install_agents.split("ops_dir=", 1)[-1]
    assert "macos_active_operator_password" in common
    assert "primary operator remained active" in backup_operator
    assert "primary operator did not recover" in backup_operator
    assert "audit_committed" in backup_operator
    assert backup_operator.index("audit_committed=1") < backup_operator.index(
        "macos_write_evidence"
    )
    assert "macos_active_operator_password" in close_sessions
    assert "session_closed=1" in close_sessions
    assert close_sessions.index("session_closed=1") < close_sessions.rindex(
        "release-backup"
    )
    preflight = (MACOS_OPS / "Test-FormalPreflight.zsh").read_text(encoding="utf-8")
    assert "AutoStart" in preflight
    assert "docker_ncpu" in preflight
    assert "docker-settings-evidence" in preflight
    assert "--evidence-path" in preflight
    assert "down_revision" in new_bundle
    assert "migration graph must have exactly one head" in new_bundle


def test_common_lock_and_formal_path_contracts_are_canonical() -> None:
    common = (MACOS_OPS / "Common.zsh").read_text(encoding="utf-8")
    dispatcher = (MACOS_OPS / "LaunchAgent-Dispatcher.zsh").read_text(encoding="utf-8")
    assert "kern.boottime" in common
    assert ".stale-" in common
    assert "kill -0" in common
    assert "validate-paths" in common
    assert "formal host paths must be distinct" in common
    assert "RANDOM" in common
    assert "macos_acquire_lock" in dispatcher
    assert 'mkdir -- "$lock"' not in dispatcher


def test_common_evidence_names_are_unique_with_same_second_writes() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-evidence-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "Formal Root"
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
first="$(macos_write_evidence "$2/evidence" same '{"status":"passed","secrets":"redacted"}')"
second="$(macos_write_evidence "$2/evidence" same '{"status":"passed","secrets":"redacted"}')"
[[ "$first" != "$second" && -f "$first.sha256" && -f "$second.sha256" ]]
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_formal_compose_volume_override_is_checksum_bound_and_owner_only() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-volumes-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "Formal Root"
        release = Path(temporary) / "release"
        release.mkdir(mode=0o700)
        (release / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
print -r -- 'INTERNAL_EXAM_LIFECYCLE_HOST_DIR='"$2"'/lifecycle' > "$2/configuration/formal.env"
print -r -- 'INTERNAL_EXAM_BACKUP_HOST_DIR='"$2"'/backups' >> "$2/configuration/formal.env"
print -r -- 'INTERNAL_EXAM_EVIDENCE_HOST_DIR='"$2"'/evidence' >> "$2/configuration/formal.env"
print -r -- 'SECOND_COPY_PATH=/private/tmp/internal-exam-second-copy' >> "$2/configuration/formal.env"
override="$2/state/formal-volume-override.yml"
macos_write_atomic "$override" $'volumes:\n  postgres_data:\n    name: internal-exam-formal-cutover-test-postgres\n'
macos_write_checksum "$override"
macos_compose_base "$3" "$2/configuration/formal.env" "$MACOS_FORMAL_PROJECT"
[[ "${MACOS_COMPOSE_ARGS[-2]}" == -f && "${MACOS_COMPOSE_ARGS[-1]}" == "$override" ]]
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root), str(release)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_release_seal_lifecycle_and_secret_header_contract() -> None:
    new_bundle = (MACOS_OPS / "New-ReleaseBundle.zsh").read_text(encoding="utf-8")
    build = (MACOS_OPS / "Build-ReleaseImages.zsh").read_text(encoding="utf-8")
    seal = (MACOS_OPS / "Seal-Release.zsh").read_text(encoding="utf-8")
    test_bundle = (MACOS_OPS / "Test-ReleaseBundle.zsh").read_text(encoding="utf-8")
    assert "state=unsealed" in new_bundle
    assert '"status":"pending"' in new_bundle
    assert "next=Seal-Release" in build
    assert "--allow-unsealed" in build
    assert "scannerEvidenceSha256" in seal
    assert "scannerMode" in seal
    assert "identity-bound" in seal
    assert "binding_errors" in seal
    assert "scannerMode" in test_bundle
    assert "Seal-Release" in test_bundle
    diagnostics = (MACOS_OPS / "Export-Diagnostics.zsh").read_text(encoding="utf-8")
    close_sessions = (MACOS_OPS / "Close-ExamSessions.zsh").read_text(encoding="utf-8")
    assert '"X-Admin-Token: $token"' not in diagnostics
    assert '"X-Admin-Token: $old_token"' not in close_sessions


def test_lifecycle_cleanup_preserves_lock_release() -> None:
    start = (MACOS_OPS / "Start-Platform.zsh").read_text(encoding="utf-8")
    staging = (MACOS_OPS / "Invoke-Staging.zsh").read_text(encoding="utf-8")
    assert "macos_restore_environment" in start
    assert "macos_release_lock" in start
    assert "macos_restore_environment" in staging
    assert "macos_release_lock" in staging
