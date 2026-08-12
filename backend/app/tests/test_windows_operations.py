import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WINDOWS_OPS = REPO_ROOT / "ops" / "windows"


def _script(name: str) -> str:
    return (WINDOWS_OPS / name).read_text(encoding="utf-8")


def test_versioned_windows_workflow_is_complete() -> None:
    required_scripts = {
        "Initialize-InternalExamHost.ps1",
        "Install-Release.ps1",
        "Build-ReleaseImages.ps1",
        "Start-Platform.ps1",
        "Stop-Platform.ps1",
        "Get-PlatformStatus.ps1",
        "Invoke-Staging.ps1",
        "Test-FormalPreflight.ps1",
        "Promote-Release.ps1",
        "Rollback-Release.ps1",
        "Set-BackupOperator.ps1",
        "Close-ExamSessions.ps1",
        "Invoke-PairedBackup.ps1",
        "Invoke-RestoreDrill.ps1",
        "Export-Diagnostics.ps1",
        "Test-PowerShellSyntax.ps1",
    }

    assert required_scripts <= {path.name for path in WINDOWS_OPS.glob("*.ps1")}


def test_release_bundle_is_commit_version_and_checksum_bound() -> None:
    generator = _script("New-ReleaseBundle.ps1")
    verifier = _script("Test-ReleaseBundle.ps1")

    assert "ValidatePattern('^[0-9a-f]{40}$')" in generator
    assert "applicationVersion = $ApplicationVersion" in generator
    assert "gitCommit = $GitCommit" in generator
    assert "baseImageReferences = $baseImageReferences" in generator
    assert "built-image-identity.json" in generator
    assert "finalImageReferences" in generator
    assert "imagePlatformSupport" in generator
    assert "linux/arm64" in verifier
    assert "linux/amd64" in verifier
    assert "migrationHead" in generator
    assert "SecurityEvidencePath" in generator
    assert "Security scan did not pass release policy" in generator
    assert "securityEvidence" in verifier
    assert "SHA256SUMS" in generator
    assert "Get-FileHash -Algorithm SHA256" in verifier
    assert "Release bundle contains a forbidden runtime file" in verifier
    assert "Test-ForbiddenReleaseFile" in generator
    assert "Test-ForbiddenReleaseFile" in verifier


def test_windows_release_inputs_accept_tagged_immutable_base_images() -> None:
    generator = _script("New-ReleaseBundle.ps1")
    verifier = _script("Test-ReleaseBundle.ps1")
    pattern = (
        r"^([a-z0-9][a-z0-9._/-]{0,254})"
        r"(:[A-Za-z0-9_][A-Za-z0-9._-]{0,127})?@sha256:[0-9a-f]{64}$"
    )
    assert f"'{pattern}'" in generator
    assert f"'{pattern}'" in verifier

    references = json.loads(
        (REPO_ROOT / "ops" / "release" / "image-digests.json").read_text(
            encoding="utf-8"
        )
    )
    frontend_builder = references["frontend_builder"]
    assert re.fullmatch(pattern, frontend_builder)
    for invalid_reference in (
        "node:22-alpine",
        "node:22-alpine@sha256:" + "a" * 63,
        "node:22-alpine@sha256:" + "g" * 64,
        "node:22-alpine@sha512:" + "a" * 64,
    ):
        assert re.fullmatch(pattern, invalid_reference) is None


def test_windows_release_bundle_uses_shared_architecture_metadata_contract() -> None:
    generator = _script("New-ReleaseBundle.ps1")
    verifier = _script("Test-ReleaseBundle.ps1")

    for field in (
        "hostOS",
        "host_os",
        "architecture",
        "targetPlatform",
        "target_platform",
        "migrationHead",
        "migration_head",
        "releaseFileChecksums",
        "release_file_checksums",
        "baseImageReferences",
        "base_image_references",
        "imageReferenceKind",
        "builtImageIdentity",
        "built_image_identity",
        "finalImageReferences",
        "final_image_references",
    ):
        assert field in generator
    assert "targetPlatform -ne 'linux/amd64'" in verifier
    assert "Pinned base image references" in verifier
    assert (
        "Final image identity is not an exact linux/amd64 release image set" in verifier
        or "Assert-ReleaseImageIdentity" in verifier
    )


def test_release_bundle_excludes_secret_like_files_but_keeps_env_example() -> None:
    generator = _script("New-ReleaseBundle.ps1")
    verifier = _script("Test-ReleaseBundle.ps1")

    for script in (generator, verifier):
        for marker in (
            ".env",
            ".env.*",
            "*.env",
            "*.env.*",
            ".env.example",
            ".npmrc",
            ".pem",
            ".key",
            "credentials",
            "private",
            "ReparsePoint",
        ):
            assert marker in script
    assert "credentials" in generator
    assert "secrets" in verifier


def test_release_bundle_requires_exact_clean_git_source_and_rejects_injection() -> None:
    generator = _script("New-ReleaseBundle.ps1")
    verifier = _script("Test-ReleaseBundle.ps1")

    assert "rev-parse --show-toplevel" in generator
    assert "rev-parse --verify HEAD" in generator
    assert "Git commit does not match the source HEAD" in generator
    assert "status --porcelain=v1 --untracked-files=all" in generator
    assert "ls-tree -r --name-only HEAD" in generator
    assert "core.quotePath=false" in generator
    assert "Get-ChildItem -LiteralPath $sourceRoot -File -Recurse" not in generator
    assert "Source Git tree contains an unsupported file entry" in generator
    assert "Source tree must be clean" in generator
    assert "SourcePath must be the Git worktree root" in generator
    assert "unmanifested file" in verifier
    assert "ReparsePoint" in verifier
    assert "unsafe path entry" in verifier


def test_release_bundle_keeps_unicode_git_paths_unquoted() -> None:
    generator = _script("New-ReleaseBundle.ps1")

    assert re.search(
        r"git -C \$sourceRoot -c core\.quotePath=false "
        r"ls-tree -r --name-only HEAD",
        generator,
    )


def test_release_bundle_verifier_counts_single_checksum_metadata_property() -> None:
    verifier = _script("Test-ReleaseBundle.ps1")

    assert "@($manifest.releaseFileChecksums.PSObject.Properties).Count" in verifier


def test_windows_sha256sums_use_utf8_for_unicode_release_paths() -> None:
    generator = _script("New-ReleaseBundle.ps1")
    verifier = _script("Test-ReleaseBundle.ps1")
    image_builder = _script("Build-ReleaseImages.ps1")

    assert "Join-Path $destinationRoot 'SHA256SUMS') -Encoding UTF8" in generator
    assert "Get-Content -LiteralPath $checksumsPath -Encoding UTF8" in verifier
    assert (
        "$checksumLines | Set-Content -LiteralPath $checksumPath -Encoding UTF8"
        in image_builder
    )


def test_release_build_includes_all_patched_final_images() -> None:
    script = _script("Build-ReleaseImages.ps1")

    assert "'db', 'backend', 'frontend', 'nginx'" in script
    assert "--platform', 'linux/amd64'" in script
    assert "built-image-identity.json" in script
    assert "finalImageReferences" in script
    assert "imageID" in script
    assert "imageOS" in script
    assert "imageArchitecture" in script
    assert "Write-ChecksummedJsonFile" in script


def test_staging_isolated_from_formal_ports_project_and_volumes() -> None:
    staging = _script("Invoke-Staging.ps1")

    assert "internal-exam-staging-$shortCommit" in staging
    assert "$env:CANDIDATE_GATEWAY_PORT = '18080'" in staging
    assert "$env:OPERATOR_GATEWAY_PORT = '18081'" in staging
    assert "$env:POSTGRES_LOOPBACK_PORT = '15432'" in staging
    assert "down', '-v', '--remove-orphans'" in staging
    assert "internal-exam-formal" not in staging


def test_candidate_public_base_url_tracks_windows_staging_and_formal_preflight() -> (
    None
):
    staging = _script("Invoke-Staging.ps1")
    preflight = _script("Test-FormalPreflight.ps1")

    assert "CANDIDATE_PUBLIC_BASE_URL = $env:CANDIDATE_PUBLIC_BASE_URL" in staging
    assert "$env:CANDIDATE_PUBLIC_BASE_URL = 'http://127.0.0.1:18080'" in staging
    assert "'CANDIDATE_PUBLIC_BASE_URL'" in preflight
    assert (
        '$expectedCandidateOrigin = "http://$($configuration.INTERNAL_LAN_BIND_IP):8080"'
        in preflight
    )
    assert "-cne $expectedCandidateOrigin" in preflight


def test_preflight_is_fail_closed_and_redacted() -> None:
    preflight = _script("Test-FormalPreflight.ps1")

    for check in (
        "configuration_acl",
        "release_checksums",
        "services_and_split_exposure",
        "health_and_migration",
        "route_isolation",
        "clock",
        "disk_reserve",
        "backup",
        "smtp",
        "browser_smoke",
    ):
        assert f"'{check}'" in preflight
    assert "secrets = 'redacted'" in preflight
    assert "$status = 'failed'" in preflight
    assert "Write-ChecksummedEvidence" in preflight
    assert (
        "validate-migration-input" in preflight
        or "Invoke-PortableMigrationValidation" in preflight
    )
    assert "Assert-WindowsEvidenceIdentity" in preflight
    assert "CheckLocalImages" in preflight
    assert "PRIMARY_OPERATOR_PASSWORD" not in preflight.split("required = @(", 1)[0]


def test_backup_operator_recreates_only_backend_and_rolls_back_config_on_error() -> (
    None
):
    script = _script("Set-BackupOperator.ps1")

    assert "Set-DotEnvValueAtomic" in script
    assert "--force-recreate', 'backend'" in script
    assert "record-backup-operator" in script
    assert (
        "Set-DotEnvValueAtomic -Path $layout.FormalEnv -Name 'BACKUP_OPERATOR_ENABLED' -Value $oldValue"
        in script
    )
    assert "auto-submit-worker" not in script


def test_close_sessions_checks_attempts_rotates_and_proves_revocation() -> None:
    script = _script("Close-ExamSessions.ps1")
    common = _script("Common.ps1")

    acquire_position = script.index("Invoke-BackupWriteFreezeAcquire")
    check_position = script.index("session-closure-readiness")
    rotation_position = script.index("Set-DotEnvValueAtomic")
    old_token_position = script.index("$oldTokensRejected = $true")
    release_position = script.index("Invoke-BackupWriteFreezeRelease")
    audit_position = script.index("record-session-closure")
    finally_position = script.index("} finally {")
    assert (
        acquire_position
        < check_position
        < rotation_position
        < old_token_position
        < release_position
        < audit_position
    )
    assert finally_position < release_position
    assert "if ($lockAcquired)" in script
    assert "if ($secretRotationAttempted)" in script
    assert "acquire-backup" in common
    assert "release-backup" in common
    assert "session-closure-$([Guid]::NewGuid().ToString('N'))" in script
    assert check_position < rotation_position
    assert "check-session-closure" in script
    assert "RandomNumberGenerator" in script
    assert "StatusCode -ne 401" in script
    assert "readinessRecovered = $true" in script
    assert "secretRestored" in script
    assert "lockAcquiredAt" in script
    assert "lockReleasedAt" in script
    assert "old-token-401" in script
    assert "recoveryLock" not in script
    post_commit = script.split("# Login and DB audit", 1)[1]
    assert "Invoke-BackupWriteFreezeAcquire" not in post_commit
    assert "TOKEN_SECRET" not in post_commit
    assert "finally" in script
    assert "record-session-closure" in script


def test_rollback_has_distinct_guarded_paths_and_no_generic_downgrade() -> None:
    script = _script("Rollback-Release.ps1")

    assert "ProvenNoMigrationOrWrites" in script
    assert "AllowDestructiveRestore" in script
    assert "ROLLBACK PRE-MIGRATION" in script
    assert "RESTORE PAIRED BACKUP" in script
    assert "DataLossConfirmation" in script
    assert "I UNDERSTAND POST-UPGRADE WRITES WILL BE DISCARDED" in script
    assert "expectedLoss" in script
    assert "lossBoundary" in script
    assert "imageIds" in script
    assert "Invoke-PortableMigrationValidation" in script
    assert "Assert-WriterFenceClearBeforeExpose" in script
    assert "transfer-fence" not in script.lower()
    assert "pg_restore" in script
    assert "alembic downgrade" not in script.lower()


def test_backup_and_restore_use_versioned_one_shot_containers() -> None:
    backup = _script("Invoke-PairedBackup.ps1")
    restore = _script("Invoke-RestoreDrill.ps1")

    assert "container-backup" in backup
    assert "--opportunistic" in backup
    assert "sync-second-copy" in backup
    assert "app.ops.internal_backup" in backup
    assert "internal-exam-restore-verify-$suffix" in restore
    assert "verify-restored" in restore
    assert "down', '-v', '--remove-orphans'" in restore
    assert "formalProjectChanged = $false" in restore
    assert "record-lifecycle" in restore


def test_diagnostic_export_is_bounded_redacted_and_checksummed() -> None:
    script = _script("Export-Diagnostics.ps1")

    assert "operations/snapshot" in script
    assert "--tail', '500'" in script
    assert "[REDACTED]" in script
    assert "release-manifest.json" in script
    assert "Compress-Archive" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    assert "ZeroFreeBSTR" in script


def test_windows_formal_gates_are_bound_to_canonical_native_identity() -> None:
    common = _script("Common.ps1")
    for script_name in (
        "Test-FormalPreflight.ps1",
        "Promote-Release.ps1",
        "Rollback-Release.ps1",
    ):
        script = _script(script_name)
        assert "Assert-ReleaseImageIdentity" in script
        assert "CheckLocalImages" in script
        assert (
            "Assert-WindowsEvidenceIdentity" in script
            or script_name == "Rollback-Release.ps1"
        )
    for marker in (
        "host_os",
        "windows",
        "architecture",
        "amd64",
        "target_platform",
        "linux/amd64",
        "imageReferences",
        "imageIds",
        "Invoke-PortableMigrationValidation",
        "validate-migration-input",
    ):
        assert marker in common


def test_windows_writer_fence_and_operator_subject_contracts_are_fail_closed() -> None:
    common = _script("Common.ps1")
    start = _script("Start-Platform.ps1")
    promote = _script("Promote-Release.ps1")
    rollback = _script("Rollback-Release.ps1")
    for script in (start, promote, rollback):
        assert "Assert-WriterFenceClearBeforeExpose" in script
    assert "catch" in start
    assert "down', '--remove-orphans'" in start
    assert "down', '-v'" not in start
    assert "transfer-fence" in common
    assert "source-writer-generation" in common
    assert "target-writer-generation" in common
    assert "TargetPreflightEvidence" in common
    assert "ExpectedDatasetId" in common
    assert "ExpectedHostId" in common
    assert "ExpectedWriterGeneration" in common
    assert "stale or foreign" in common
    assert "RestoredCutoverBackupPath" in common
    assert "restored-cutover-backup" in common
    assert ":/restored-cutover-backup:ro" in common

    backup = _script("Invoke-PairedBackup.ps1")
    restore = _script("Invoke-RestoreDrill.ps1")
    toggle = _script("Set-BackupOperator.ps1")
    close = _script("Close-ExamSessions.ps1")
    for script in (backup, restore, toggle, close):
        assert "Get-ConfiguredOperatorSubject" in script or "operatorSubject" in script
    assert "PRIMARY_OPERATOR_USERNAME" in toggle
    assert "BACKUP_OPERATOR_USERNAME" in toggle
    assert "operatorSubject" in toggle
    assert "Assert-OperatorLoginState" in common
    assert toggle.count("Assert-OperatorLoginState") >= 5
    assert "ExpectedSuccess:$true" in toggle
    assert "ExpectedSuccess:$false" in toggle
