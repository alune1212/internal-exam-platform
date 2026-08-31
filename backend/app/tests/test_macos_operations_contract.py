import hashlib
import json
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MACOS_OPS = REPO_ROOT / "ops" / "macos"
RELEASE_INSTALLER = MACOS_OPS / "Install-Release.zsh"


def _git_mode(path: Path) -> int:
    relative = path.relative_to(REPO_ROOT)
    git = shutil.which("git")
    assert git is not None, "git is required to inspect the repository index"
    result = subprocess.run(  # noqa: S603
        [git, "-C", str(REPO_ROOT), "ls-files", "--stage", "--", str(relative)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    rows = [line for line in result.stdout.splitlines() if line]
    # A newly added operation is intentionally untracked until the parent
    # change is assembled.  Keep the contract useful in that worktree while
    # retaining the Git-index assertion for every tracked operation.
    if not rows:
        assert path.is_file(), f"operation is missing: {path}"
        # Match Git's regular-file mode representation for a new, not-yet-
        # staged operation while preserving the executable-bit assertion.
        return 0o100000 | (path.stat().st_mode & 0o777)
    assert len(rows) == 1, f"expected one Git index entry for {relative}: {rows!r}"
    return int(rows[0].split(maxsplit=1)[0], 8)


def _require_macos_zsh() -> str:
    if platform.system() != "Darwin":
        pytest.skip("macOS Common.zsh runtime tests are skipped off Darwin")
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh is unavailable on this runner")
    return zsh


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


def test_close_exam_sessions_generates_canonical_external_session_secret() -> None:
    closer = (MACOS_OPS / "Close-ExamSessions.zsh").read_text(encoding="utf-8")

    assert "secrets.token_bytes(32)" in closer
    assert "base64.urlsafe_b64encode" in closer
    assert '.rstrip(b"=")' in closer
    assert "openssl rand" not in closer
    assert (
        'macos_dotenv_set_atomic "$MACOS_FORMAL_ENV" TOKEN_SECRET "$new_secret"'
        in closer
    )
    assert "generated session secret is not canonical" in closer

    generated = subprocess.run(
        [
            sys.executable,
            "-c",
            "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii'), end='')",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", generated)


def test_macos_release_signing_uses_trusted_rsa_sidecars_and_verifier() -> None:
    common = (MACOS_OPS / "Common.zsh").read_text(encoding="utf-8")
    signer = (MACOS_OPS / "Sign-ReleaseBundle.zsh").read_text(encoding="utf-8")
    verifier = (MACOS_OPS / "Test-ReleaseBundle.zsh").read_text(encoding="utf-8")
    installer = RELEASE_INSTALLER.read_text(encoding="utf-8")
    seal = (MACOS_OPS / "Seal-Release.zsh").read_text(encoding="utf-8")

    assert "RSA-3072" in signer
    assert 'openssl dgst -sha256 -sign "$private_key"' in signer
    assert "releaseSignature" in signer
    assert "signedFiles" in signer
    assert "release-manifest.json" in signer
    assert "SHA256SUMS" in signer
    assert "sidecars" in signer
    assert "release-manifest.json.sig" in signer
    assert "SHA256SUMS.sig" in signer
    assert "release-signing-public-key.pem" in common
    assert "release-signing-public-key.fingerprint" in common
    assert "SPKI" in common
    assert 'openssl dgst -sha256 -verify "$public_key"' in common
    assert "macos_validate_release_signing_trust" in verifier
    assert "releaseSignature.keyFingerprint" in verifier
    assert "releaseSignature.signedFiles.2" in verifier
    assert "releaseSignature.sidecars.2" in verifier
    assert "release-manifest.json.sig|SHA256SUMS.sig" in verifier
    assert (
        '"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$temporary_target"'
        in installer
    )
    assert '"$temporary_target/ops/macos/Test-ReleaseBundle.zsh"' not in installer
    assert "next=Sign-ReleaseBundle" in seal


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
        arguments = [str(value) for value in document["ProgramArguments"]]
        assert "__TRUSTED_RUNTIME_DIR__/Trusted-LaunchAgent.zsh" in arguments
        assert "__MACOS_OPS_DIR__" not in " ".join(arguments)
        assert not any("/ops/macos/" in value for value in arguments)


def test_trusted_launchagent_rejects_runtime_support_tamper_before_dispatch() -> None:
    zsh = _require_macos_zsh()
    if not Path("/usr/bin/shasum").is_file():
        pytest.skip("macOS shasum is unavailable on this runner")

    runtime_files = (
        "Trusted-LaunchAgent.zsh",
        "LaunchAgent-Dispatcher.zsh",
        "Common.zsh",
        "Test-ReleaseBundle.zsh",
    )
    launcher_source = MACOS_OPS / "Trusted-LaunchAgent.zsh"
    with tempfile.TemporaryDirectory(
        prefix="internal-exam-trusted-runtime-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        base = Path(temporary) / "base"

        def install_runtime(destination: Path) -> None:
            destination.mkdir(mode=0o700)
            destination.chmod(0o700)
            for name in runtime_files:
                source = MACOS_OPS / name
                target = destination / name
                shutil.copy2(source, target)
                target.chmod(0o700)
            manifest = destination / "trusted-runtime.SHA256SUMS"
            manifest.write_text(
                "".join(
                    f"{hashlib.sha256((destination / name).read_bytes()).hexdigest()}  {name}\n"
                    for name in runtime_files
                ),
                encoding="ascii",
            )
            manifest.chmod(0o600)

        install_runtime(base)
        valid = subprocess.run(  # noqa: S603
            [zsh, str(base / launcher_source.name), "--validate-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert valid.returncode == 0, valid.stderr

        for index, name in enumerate(runtime_files[1:], start=1):
            candidate = Path(temporary) / f"candidate-{index}"
            install_runtime(candidate)
            marker = candidate / "dispatch-marker"
            with (candidate / name).open("a", encoding="utf-8") as tampered:
                tampered.write(f'\nprint -r -- "tampered" > "{marker}"\n')
            result = subprocess.run(  # noqa: S603
                [
                    zsh,
                    str(candidate / launcher_source.name),
                    "bootstrap",
                    "--root",
                    str(Path(temporary) / "formal-root"),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            assert result.returncode != 0, name
            assert not marker.exists(), (
                f"tampered {name} executed before trust validation"
            )


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
    installer = RELEASE_INSTALLER.read_text(encoding="utf-8")
    assert (
        "find \"$temporary_target/ops/macos\" -type f -name '*.zsh' -print" in installer
    )
    assert 'chmod 700 "$file"' in installer
    for script in _shell_scripts():
        # The Git index stores 100755, while Install-Release.zsh applies the
        # owner-only 0700 runtime contract on the formal host.
        assert _git_mode(script) == 0o100755, f"{script} must be executable in Git"


def test_common_uses_real_temporary_layout_and_rejects_dangerous_roots() -> None:
    zsh = _require_macos_zsh()

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
    zsh = _require_macos_zsh()

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


def test_macos_release_verifier_accepts_tagged_immutable_base_refs_only() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    verifier = (MACOS_OPS / "Test-ReleaseBundle.zsh").read_text(encoding="utf-8")
    pattern_match = re.search(
        r"\[\[ \"\$base_reference\" =~ '([^']+)' \]\]",
        verifier,
    )
    assert pattern_match, "base image immutability regex is missing"
    pattern = pattern_match.group(1)

    valid = (
        "nginx:1.27-alpine@sha256:" + "a" * 64,
        "ghcr.io/astral-sh/uv:python3.12-alpine@sha256:" + "b" * 64,
        "postgres@sha256:" + "c" * 64,
        "example/repo:Release_1.0@sha256:" + "d" * 64,
    )
    invalid = (
        "nginx:latest",
        "nginx:1.27-alpine@sha256:" + "a" * 63,
        "nginx:1.27-alpine@sha256:" + "g" * 64,
        "nginx:1.27-alpine@sha512:" + "a" * 64,
        "Nginx:1.27-alpine@sha256:" + "a" * 64,
    )

    for reference in valid:
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", f"[[ \"$1\" =~ '{pattern}' ]]", "contract", reference],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, reference

    for reference in invalid:
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", f"[[ \"$1\" =~ '{pattern}' ]]", "contract", reference],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, reference


def test_macos_security_scan_accepts_tagged_frontend_builder_digest_only() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    scanner = (MACOS_OPS / "Invoke-ReleaseSecurityScan.zsh").read_text(encoding="utf-8")
    pattern_match = re.search(
        r"\[\[ \"\$node_image\" =~ '([^']+)' \]\]",
        scanner,
    )
    assert pattern_match, "security scan node image immutability regex is missing"
    pattern = pattern_match.group(1)
    frontend_builder = json.loads(
        (REPO_ROOT / "ops" / "release" / "image-digests.json").read_text(
            encoding="utf-8"
        )
    )["frontend_builder"]
    valid = (frontend_builder,)
    invalid = (
        "node:22-alpine",
        "node:22-alpine@sha256:" + "a" * 63,
        "node:22-alpine@sha256:" + "g" * 64,
        "node:22-alpine@sha512:" + "a" * 64,
    )

    for reference in valid:
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", f"[[ \"$1\" =~ '{pattern}' ]]", "contract", reference],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, reference

    for reference in invalid:
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", f"[[ \"$1\" =~ '{pattern}' ]]", "contract", reference],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, reference


def test_macos_security_scan_inspect_output_uses_real_delimiter() -> None:
    scanner = (MACOS_OPS / "Invoke-ReleaseSecurityScan.zsh").read_text(encoding="utf-8")
    assert "{{.Id}}\\t{{.Os}}\\t{{.Architecture}}" not in scanner
    assert "{{.Id}}|{{.Os}}|{{.Architecture}}" in scanner
    assert "IFS='|' read -r actual_id actual_os actual_architecture extra" in scanner
    assert 'separator_count="${inspect_line//[^|]/}"' in scanner
    assert '[[ "${#separator_count}" -eq 2 ]]' in scanner
    assert "built image inspect output contains multiple lines" in scanner
    assert "built image inspect output is malformed" in scanner
    assert '-n "$actual_id"' in scanner
    assert '-n "$actual_os"' in scanner
    assert '-n "$actual_architecture"' in scanner
    assert '-z "${extra:-}"' in scanner


def test_macos_security_scan_reuses_private_trivy_cache_across_images() -> None:
    scanner = (MACOS_OPS / "Invoke-ReleaseSecurityScan.zsh").read_text(encoding="utf-8")
    assert 'trivy_cache="$work/trivy-cache"' in scanner
    assert 'mkdir -p -- "$trivy_cache"' in scanner
    assert 'chmod 700 "$trivy_cache"' in scanner
    assert "for image_name in db backend frontend gateway; do" in scanner
    assert scanner.count("--cache-dir /evidence/trivy-cache") == 1
    assert '--volume "$work:/evidence" "$trivy_image" image' in scanner
    assert 'typeset -r MACOS_TRIVY_IMAGE="aquasec/trivy@sha256:' in scanner
    assert '[[ "$trivy_image" == "$MACOS_TRIVY_IMAGE" ]]' in scanner
    assert 'cp -p -- "$work/trivy-cache"' not in scanner
    assert 'rm -R -- "$work"' in scanner


def test_macos_release_verifier_checksum_lookup_uses_plain_associative_key() -> None:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")

    verifier = (MACOS_OPS / "Test-ReleaseBundle.zsh").read_text(encoding="utf-8")
    assignment_match = re.search(
        r"^\s*(checksum_rows\[[^\n]+\]=\"\$digest\")$",
        verifier,
        re.MULTILINE,
    )
    assert assignment_match, "checksum row assignment is missing"
    assignment = assignment_match.group(1)
    assert 'checksum_rows["$relative"]' not in assignment

    manifest_assignment_match = re.search(
        r"^\s*(manifest_rows\[[^\n]+\]=1)$",
        verifier,
        re.MULTILINE,
    )
    assert manifest_assignment_match, "manifest row assignment is missing"
    manifest_assignment = manifest_assignment_match.group(1)
    assert 'manifest_rows["$relative"]' not in manifest_assignment

    shell = f"""
typeset -A checksum_rows
typeset -A manifest_rows
relative="$1"
digest="$2"
{assignment}
[[ "${{checksum_rows[$relative]-}}" == "$digest" ]]
record_manifest_row() {{
  [[ -z "${{manifest_rows[$relative]-}}" ]] || return 1
  {manifest_assignment}
}}
record_manifest_row
if record_manifest_row; then
  exit 1
fi
"""
    result = subprocess.run(  # noqa: S603
        [zsh, "-c", shell, "contract", "release-evidence/security-scan.json", "a" * 64],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


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
    zsh = _require_macos_zsh()

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
    zsh = _require_macos_zsh()

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


def test_lifecycle_cleanup_preserves_lock_release() -> None:
    start = (MACOS_OPS / "Start-Platform.zsh").read_text(encoding="utf-8")
    staging = (MACOS_OPS / "Invoke-Staging.zsh").read_text(encoding="utf-8")
    assert "macos_restore_environment" in start
    assert "macos_release_lock" in start
    assert "macos_restore_environment" in staging
    assert "macos_release_lock" in staging


def test_candidate_public_base_url_tracks_formal_maintenance_and_staging_modes() -> (
    None
):
    start = (MACOS_OPS / "Start-Platform.zsh").read_text(encoding="utf-8")
    preflight = (MACOS_OPS / "Test-FormalPreflight.zsh").read_text(encoding="utf-8")
    staging = (MACOS_OPS / "Invoke-Staging.zsh").read_text(encoding="utf-8")
    runtime = (MACOS_OPS / "Invoke-StagingRuntimeChecks.zsh").read_text(
        encoding="utf-8"
    )
    restore = (MACOS_OPS / "Invoke-StagingBackupRestoreCheck.zsh").read_text(
        encoding="utf-8"
    )
    drill = (MACOS_OPS / "Invoke-RestoreDrill.zsh").read_text(encoding="utf-8")
    capture = (MACOS_OPS / "Capture-PrivilegedHostEvidence.zsh").read_text(
        encoding="utf-8"
    )

    assert "CANDIDATE_PUBLIC_BASE_URL" in start
    assert "export CANDIDATE_PUBLIC_BASE_URL=http://127.0.0.1:28080" in start
    assert "CANDIDATE_PUBLIC_BASE_URL" in preflight
    assert "http://${formal_lan_ip}:${formal_candidate_port}" in preflight
    assert "http://${lan_ip}:${candidate_port}" in preflight
    assert (
        'export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"'
        in staging
    )
    assert (
        'export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"'
        in runtime
    )
    assert (
        'export CANDIDATE_PUBLIC_BASE_URL="http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}"'
        in restore
    )
    assert "export CANDIDATE_PUBLIC_BASE_URL=http://127.0.0.1:28080" in drill
    assert "read_formal_value_into CANDIDATE_PUBLIC_BASE_URL" in capture
    assert "candidatePublicBaseUrl" in capture


def test_public_writer_guard_rejects_pending_bootstrap_and_allows_private_maintenance() -> (
    None
):
    zsh = _require_macos_zsh()

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-bootstrap-guard-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "formal-root"
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
macos_layout "$2"
state="$2/state/current-release.json"
macos_write_atomic "$state" '{"schemaVersion":1,"datasetId":"dataset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","hostId":"host-test-aaaaaaaa","writerGeneration":1,"bootstrapPending":true}'
macos_write_checksum "$state"
if macos_assert_formal_writer_ready 0; then
  exit 1
fi
macos_assert_formal_writer_ready 1
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_activated_generation_one_lineage_survives_current_release_upgrade_and_tamper() -> (
    None
):
    zsh = _require_macos_zsh()

    with tempfile.TemporaryDirectory(
        prefix="internal-exam-macos-lineage-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None,
    ) as temporary:
        root = Path(temporary) / "formal-root"
        shell = r"""
source "$1/Common.zsh"
macos_initialize_layout "$2"
macos_layout "$2"
release_one="$2/releases/1.0.0"
release_two="$2/releases/1.1.0"
mkdir -p "$release_one" "$release_two"
dataset="dataset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
host="host-test-aaaaaaaa"
macos_write_atomic "$2/state/host-identity.json" "{\"schemaVersion\":1,\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"lineageState\":\"bound\"}"
macos_write_checksum "$2/state/host-identity.json"
bootstrap="$2/state/formal-writer-bootstrap-intent.json"
activation="$2/state/formal-writer-activation-intent.json"
phase="$2/state/formal-writer-activation-phase.json"
terminal="$2/state/formal-writer-activation-terminal.json"
lineage="$2/state/formal-writer-lineage.json"
current="$2/state/current-release.json"
macos_write_atomic "$bootstrap" "{\"schemaVersion\":1,\"kind\":\"formal-writer-bootstrap-intent\",\"status\":\"prepared\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"releasePath\":\"$release_one\"}"
macos_write_checksum "$bootstrap"
bootstrap_sha="$(macos_sha256 "$bootstrap")"
macos_write_atomic "$activation" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-intent\",\"status\":\"intent\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"bootstrapIntentSha256\":\"$bootstrap_sha\",\"releasePath\":\"$release_one\"}"
macos_write_checksum "$activation"
activation_sha="$(macos_sha256 "$activation")"
macos_write_atomic "$2/state/current-release.json" "{\"schemaVersion\":1,\"kind\":\"formal-writer-current\",\"applicationVersion\":\"1.0.0\",\"gitCommit\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"path\":\"$release_one\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"bootstrapPending\":false,\"activationReady\":true}"
macos_write_checksum "$current"
initial_sha="$(macos_sha256 "$current")"
macos_write_atomic "$phase" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-phase\",\"phase\":\"terminal\",\"activationIntentSha256\":\"$activation_sha\",\"bootstrapIntentSha256\":\"$bootstrap_sha\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"releasePath\":\"$release_one\"}"
macos_write_checksum "$phase"
phase_sha="$(macos_sha256 "$phase")"
macos_write_atomic "$terminal" "{\"schemaVersion\":1,\"kind\":\"formal-writer-activation-terminal\",\"status\":\"passed\",\"activationIntentSha256\":\"$activation_sha\",\"phaseSha256\":\"$phase_sha\",\"currentStateSha256\":\"$initial_sha\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"releasePath\":\"$release_one\"}"
macos_write_checksum "$terminal"
terminal_sha="$(macos_sha256 "$terminal")"
macos_write_atomic "$lineage" "{\"schemaVersion\":1,\"kind\":\"formal-writer-lineage\",\"status\":\"commissioned\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":1,\"bootstrapIntentSha256\":\"$bootstrap_sha\",\"activationIntentSha256\":\"$activation_sha\",\"activationPhaseSha256\":\"$phase_sha\",\"activationTerminalSha256\":\"$terminal_sha\",\"initialCurrentStateSha256\":\"$initial_sha\",\"initialReleasePath\":\"$release_one\"}"
macos_write_checksum "$lineage"
# Legal commissioning completion: current-release points to a newer sealed
# release while the generation-1 proof remains unchanged and checksummed.
macos_json_replace_atomic "$2/state/host-identity.json" writerGeneration 2
macos_write_checksum "$2/state/host-identity.json"
macos_write_atomic "$current" "{\"schemaVersion\":1,\"kind\":\"formal-writer-current\",\"applicationVersion\":\"1.1.0\",\"gitCommit\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"path\":\"$release_two\",\"datasetId\":\"$dataset\",\"hostId\":\"$host\",\"writerGeneration\":2,\"bootstrapPending\":false,\"activationReady\":true}"
macos_write_checksum "$current"
macos_assert_formal_writer_ready 0
expect_fail() { if macos_assert_formal_writer_ready 0 >/dev/null 2>&1; then exit 1; fi; }
cp -p "$lineage" "$lineage.orig"
cp -p "$lineage.sha256" "$lineage.sha256.orig"
cp -p "$terminal" "$terminal.orig"
cp -p "$terminal.sha256" "$terminal.sha256.orig"
cp -p "$phase" "$phase.orig"
cp -p "$phase.sha256" "$phase.sha256.orig"
cp -p "$activation" "$activation.orig"
cp -p "$activation.sha256" "$activation.sha256.orig"
cp -p "$current" "$current.orig"
cp -p "$current.sha256" "$current.sha256.orig"
macos_json_replace_atomic "$lineage" datasetId '"dataset-tampered"'; macos_write_checksum "$lineage"; expect_fail
cp -p "$lineage.orig" "$lineage"; cp -p "$lineage.sha256.orig" "$lineage.sha256"
macos_json_replace_atomic "$lineage" hostId '"host-tampered"'; macos_write_checksum "$lineage"; expect_fail
cp -p "$lineage.orig" "$lineage"; cp -p "$lineage.sha256.orig" "$lineage.sha256"
macos_json_replace_atomic "$lineage" writerGeneration 9; macos_write_checksum "$lineage"; expect_fail
cp -p "$lineage.orig" "$lineage"; cp -p "$lineage.sha256.orig" "$lineage.sha256"
macos_json_replace_atomic "$terminal" datasetId '"dataset-tampered"'; macos_write_checksum "$terminal"; expect_fail
cp -p "$terminal.orig" "$terminal"; cp -p "$terminal.sha256.orig" "$terminal.sha256"
macos_json_replace_atomic "$phase" phase '"state-bound"'; macos_write_checksum "$phase"; expect_fail
cp -p "$phase.orig" "$phase"; cp -p "$phase.sha256.orig" "$phase.sha256"
macos_json_replace_atomic "$activation" releasePath '"/tampered"'; macos_write_checksum "$activation"; expect_fail
cp -p "$activation.orig" "$activation"; cp -p "$activation.sha256.orig" "$activation.sha256"
macos_json_replace_atomic "$current" datasetId '"dataset-tampered"'; macos_write_checksum "$current"; expect_fail
"""
        result = subprocess.run(  # noqa: S603
            [zsh, "-c", shell, "contract", str(MACOS_OPS), str(root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
