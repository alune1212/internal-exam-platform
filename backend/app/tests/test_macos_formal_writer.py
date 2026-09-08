"""Static contract tests for the fresh generation-1 writer reservation."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "ops" / "macos" / "Initialize-FormalWriter.zsh"
MACOS_OPS = SCRIPT.parent


def _extract_function(name: str) -> str:
    """Extract one top-level zsh function for the isolated state harness."""

    lines = SCRIPT.read_text(encoding="utf-8").splitlines(keepends=True)
    start_marker = f"{name}() {{"
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.rstrip("\n") == start_marker
        ),
        None,
    )
    assert start is not None, f"missing production function: {name}"
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].rstrip("\n") == "}"
        ),
        None,
    )
    assert end is not None, f"unterminated production function: {name}"
    return "".join(lines[start : end + 1])


def test_fresh_writer_reservation_is_private_and_fail_closed() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert SCRIPT.stat().st_mode & 0o777 == 0o755

    for marker in (
        "--empty-dataset",
        "formal-writer-bootstrap-intent",
        "bootstrapPending",
        "writerGeneration",
        "formal-volume-override.yml",
        "releaseManifestSha256",
        "releaseChecksumsSha256",
        "builtImageIdentitySha256",
        "diff-index --quiet HEAD --",
        "trusted checkout",
        "Test-ReleaseBundle.zsh",
        "127.0.0.1",
        "--maintenance",
        "formal-writer-activation-intent",
        "formal-writer-activation-phase",
        "formal-writer-activation-terminal",
        "formal-writer-lineage",
        "acquire-fence",
        "release-fence",
        "Start-Platform.zsh",
    ):
        assert marker in script, marker

    assert "docker volume rm" not in script
    assert "down -v" not in script

    # A copied release script must fail before it can source bundle helpers.
    assert script.index('source "$SCRIPT_DIR/Common.zsh"') > script.index(
        'if [[ -f "$self_release_path/release-manifest.json" ]]'
    )


def test_fresh_writer_help_and_seed_rejection_are_local() -> None:
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh is unavailable on this runner")

    help_result = subprocess.run(  # noqa: S603
        [zsh, str(SCRIPT), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "Prepare" in help_result.stdout

    seed_result = subprocess.run(  # noqa: S603
        [zsh, str(SCRIPT), "--action", "Prepare", "--seed", str(REPO_ROOT / "seed")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert seed_result.returncode != 0
    assert "seed inputs are not supported" in seed_result.stderr


def test_fresh_root_activate_writes_public_ready_lineage_and_rejects_missing_evidence() -> (
    None
):
    """Exercise the production state finalizers against a genuinely empty root."""

    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh is unavailable on this runner")

    # Keep the harness independent of Docker and signed images while executing
    # the exact production terminal/lineage and evidence validators.  The
    # real Activate path validates these records immediately around the
    # fenced backup/restore/preflight operations.
    derived_state_writer = _extract_function("bootstrap_write_derived_state")
    terminal_validator = _extract_function("bootstrap_validate_terminal_semantics")
    lineage_writer = _extract_function("bootstrap_write_lineage")
    staging_validator = _extract_function("bootstrap_validate_staging")
    activation_evidence_validator = _extract_function(
        "bootstrap_validate_activation_evidence"
    )
    shell = (
        r"""source "$1/Common.zsh"
"""
        + derived_state_writer
        + terminal_validator
        + lineage_writer
        + staging_validator
        + activation_evidence_validator
        + r"""
macos_initialize_layout "$2"
macos_layout "$2"
release_path="$2/releases/1.0.0"
staging_path="$2/evidence/staging.json"
backup_path="$2/backups/backup-20260904T000000Z"
preflight_path="$2/evidence/preflight.json"
restore_path="$2/evidence/restore.json"
mkdir -p -- "$release_path" "$backup_path"
dataset_id=dataset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
host_id=host-test-aaaaaaaa
release_commit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
release_version=1.0.0
intent_path="$2/state/formal-writer-bootstrap-intent.json"
activation_intent_path="$2/state/formal-writer-activation-intent.json"
phase_path="$2/state/formal-writer-activation-phase.json"
activation_terminal_path="$2/state/formal-writer-activation-terminal.json"
lineage_path="$2/state/formal-writer-lineage.json"
identity_path="$2/state/host-identity.json"
BOOTSTRAP_DATASET_ID="$dataset_id"
BOOTSTRAP_HOST_ID="$host_id"
BOOTSTRAP_RELEASE_PATH="$release_path"
BOOTSTRAP_RELEASE_VERSION="$release_version"
BOOTSTRAP_RELEASE_COMMIT="$release_commit"
BOOTSTRAP_STAGING_PATH="$staging_path"
BOOTSTRAP_BACKUP_PATH="$backup_path"
BOOTSTRAP_PREFLIGHT_PATH="$preflight_path"
BOOTSTRAP_RESTORE_DRILL_PATH="$restore_path"
write_checked() {
  macos_write_atomic "$1" "$2"
  macos_write_checksum "$1"
}
for evidence_path in "$staging_path" "$preflight_path" "$restore_path"; do
  write_checked "$evidence_path" '{"status":"passed"}'
done
write_checked "$intent_path" "{\"schemaVersion\":1,\"kind\":\"formal-writer-bootstrap-intent\",\"status\":\"prepared\",\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":1,\"releasePath\":\"$release_path\"}"
bootstrap_sha=$(macos_sha256 "$intent_path")
bootstrap_write_derived_state
write_checked "$activation_intent_path" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-intent\",\"status\":\"intent\",\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":1,\"bootstrapIntentSha256\":\"$bootstrap_sha\",\"releasePath\":\"$release_path\"}"
activation_sha=$(macos_sha256 "$activation_intent_path")
macos_adopt_cutover_identity "$dataset_id" "$host_id" 1
macos_write_atomic "$2/state/current-release.json" "{\"schemaVersion\":1,\"kind\":\"formal-writer-current\",\"applicationVersion\":\"$release_version\",\"gitCommit\":\"$release_commit\",\"path\":\"$release_path\",\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":1,\"bootstrapPending\":false,\"activationReady\":true}"
macos_write_checksum "$2/state/current-release.json"
current_sha=$(macos_sha256 "$2/state/current-release.json")
write_checked "$phase_path" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-phase\",\"phase\":\"terminal\",\"activationIntentSha256\":\"$activation_sha\",\"bootstrapIntentSha256\":\"$bootstrap_sha\",\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":1,\"releasePath\":\"$release_path\"}"
phase_sha=$(macos_sha256 "$phase_path")
write_checked "$activation_terminal_path" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-terminal\",\"status\":\"passed\",\"activationIntentSha256\":\"$activation_sha\",\"phaseSha256\":\"$phase_sha\",\"currentStateSha256\":\"$current_sha\",\"datasetId\":\"$dataset_id\",\"hostId\":\"$host_id\",\"writerGeneration\":1,\"releasePath\":\"$release_path\",\"pairedBackupPath\":\"$backup_path\",\"stagingAcceptancePath\":\"$staging_path\",\"preflightPath\":\"$preflight_path\",\"restoreDrillPath\":\"$restore_path\",\"targetExposed\":false,\"targetWriteAccepted\":false}"
bootstrap_validate_terminal_semantics
bootstrap_write_lineage
macos_assert_formal_writer_ready 0
[[ -f "$lineage_path" && -f "$lineage_path.sha256" ]] || exit 20
[[ "$(macos_json_get "$lineage_path" status)" == commissioned ]] || exit 21
macos_json_replace_atomic "$2/state/current-release.json" applicationVersion '"tampered"'
macos_write_checksum "$2/state/current-release.json"
if bootstrap_validate_terminal_semantics >/dev/null 2>&1; then exit 22; fi
if macos_assert_formal_writer_ready 0 >/dev/null 2>&1; then exit 23; fi
print -r -- "fresh-root-activate-contract-passed"
"""
    )

    missing_evidence_shell = (
        r"""source "$1/Common.zsh"
"""
        + staging_validator
        + activation_evidence_validator
        + r"""
macos_initialize_layout "$2"
macos_layout "$2"
staging_arg="$2/evidence/missing-staging.json"
browser_arg=""
bootstrap_validate_activation_evidence
"""
    )

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-formal-writer-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "formal-root"
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "fresh-root", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        missing_result = subprocess.run(  # noqa: S603
            [
                zsh,
                "-c",
                missing_evidence_shell,
                "missing-evidence",
                str(MACOS_OPS),
                str(root / "missing-evidence-root"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr
    assert "fresh-root-activate-contract-passed" in result.stdout
    assert missing_result.returncode != 0
    assert "staging acceptance" in missing_result.stderr
