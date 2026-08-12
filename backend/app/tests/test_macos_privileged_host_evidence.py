"""Focused contract tests for the macOS privileged host evidence boundary."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MACOS_OPS = REPO_ROOT / "ops" / "macos"
BOOT_MARKER = "kern.boottime: { sec = 1, usec = 2 }"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_checked(path: Path, data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    path.write_bytes(data)
    path.chmod(0o600)
    digest = hashlib.sha256(data).hexdigest()
    path.with_name(f"{path.name}.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    path.with_name(f"{path.name}.sha256").chmod(0o600)
    return digest


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = (tmp_path / "formal-root").resolve()
    evidence = root / "evidence"
    state = root / "state"
    configuration = root / "configuration"
    for directory in (root, evidence, state, configuration):
        directory.mkdir(mode=0o700)

    identity = state / "host-identity.json"
    identity_digest = _write_checked(
        identity,
        json.dumps(
            {
                "schemaVersion": 1,
                "datasetId": "dataset-test",
                "hostId": "host-test",
                "writerGeneration": 1,
                "lineageState": "bound",
            },
            separators=(",", ":"),
        ),
    )
    info_digest = _write_checked(evidence / "info.txt", "Status: Enabled\n")
    rules_digest = _write_checked(
        evidence / "rules.txt",
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8080\n",
    )
    network_digest = _write_checked(evidence / "network.txt", "Network Time: On\n")
    designated_account = root.owner()
    checked_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    # The tests use a deterministic fake sysctl and a fresh timestamp generated
    # by the shell at invocation time below; replace this with now in the test
    # caller where freshness is relevant.
    pf_manifest = {
        "schemaVersion": 1,
        "kind": "macos-pf-export",
        "provider": "pf",
        "status": "passed",
        "checkedAt": checked_at,
        "hostOS": "darwin",
        "architecture": "arm64",
        "hostId": "host-test",
        "hostIdentitySha256": identity_digest,
        "bootMarkerSha256": hashlib.sha256(BOOT_MARKER.encode()).hexdigest(),
        "designatedHostAccount": designated_account,
        "approvedCidr": "192.168.2.0/24",
        "candidateAddress": "192.168.2.34",
        "candidatePort": 8080,
        "operatorPort": 8081,
        "postgresPort": 5432,
        "frontendPort": 5173,
        "backendPort": 8000,
        "infoCommand": "/usr/bin/sudo -n /sbin/pfctl -s info",
        "infoExitCode": 0,
        "infoArtifact": "info.txt",
        "infoOutputSha256": info_digest,
        "rulesCommand": "/usr/bin/sudo -n /sbin/pfctl -sr",
        "rulesExitCode": 0,
        "rulesArtifact": "rules.txt",
        "rulesOutputSha256": rules_digest,
        "secrets": "redacted",
    }
    network_manifest = {
        "schemaVersion": 1,
        "kind": "macos-network-time-export",
        "status": "passed",
        "checkedAt": checked_at,
        "hostOS": "darwin",
        "architecture": "arm64",
        "hostId": "host-test",
        "hostIdentitySha256": identity_digest,
        "bootMarkerSha256": hashlib.sha256(BOOT_MARKER.encode()).hexdigest(),
        "designatedHostAccount": designated_account,
        "command": "/usr/bin/sudo -n /usr/sbin/systemsetup -getusingnetworktime",
        "exitCode": 0,
        "outputArtifact": "network.txt",
        "outputSha256": network_digest,
        "secrets": "redacted",
    }
    pf_path = evidence / "pf.json"
    network_path = evidence / "network.json"
    _write_checked(
        pf_path, json.dumps(pf_manifest, separators=(",", ":"), sort_keys=True)
    )
    _write_checked(
        network_path,
        json.dumps(network_manifest, separators=(",", ":"), sort_keys=True),
    )
    return root, {
        "pf": str(pf_path),
        "network": str(network_path),
        "identity": identity_digest,
        "boot": hashlib.sha256(BOOT_MARKER.encode()).hexdigest(),
        "evidence": str(evidence),
    }


def _shell_env(tmp_path: Path) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(mode=0o700, exist_ok=True)
    sysctl = fake_bin / "sysctl"
    sysctl.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'kern.boottime: { sec = 1, usec = 2 }'\n",
        encoding="utf-8",
    )
    sysctl.chmod(0o700)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return env


def _capture_fixture(tmp_path: Path, *, app_operator: str) -> Path:
    root = (tmp_path / "capture-root").resolve()
    evidence = root / "evidence"
    state = root / "state"
    configuration = root / "configuration"
    for directory in (root, evidence, state, configuration):
        directory.mkdir(mode=0o700)
    identity = state / "host-identity.json"
    _write_checked(
        identity,
        json.dumps(
            {
                "schemaVersion": 1,
                "datasetId": "dataset-capture",
                "hostId": "host-capture",
                "writerGeneration": 1,
                "lineageState": "bound",
            },
            separators=(",", ":"),
        ),
    )
    formal_env = configuration / "formal.env"
    formal_env.write_text(
        "\n".join(
            [
                "INTERNAL_LAN_BIND_IP=192.168.2.34",
                "CANDIDATE_PUBLIC_BASE_URL=http://192.168.2.34:8080",
                "PF_APPROVED_CIDR=192.168.2.0/24",
                "CANDIDATE_GATEWAY_PORT=8080",
                "OPERATOR_GATEWAY_PORT=8081",
                "POSTGRES_LOOPBACK_PORT=5432",
                "FRONTEND_LOOPBACK_PORT=5173",
                "BACKUP_OPERATOR_ENABLED=false",
                f"PRIMARY_OPERATOR_USERNAME={app_operator}",
                "BACKUP_OPERATOR_USERNAME=application-backup",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    formal_env.chmod(0o600)
    return root


def _assert_fixture(
    root: Path,
    values: dict[str, str],
    *,
    network: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    function = (
        "macos_assert_network_time_evidence" if network else "macos_assert_pf_evidence"
    )
    if network:
        args = [
            values["network"],
            "host-test",
            values["identity"],
            values["boot"],
            values["evidence"],
        ]
    else:
        args = [
            values["pf"],
            "host-test",
            values["identity"],
            values["boot"],
            "192.168.2.0/24",
            "192.168.2.34",
            "8080",
            "8081",
            "5432",
            "5173",
            "8000",
            values["evidence"],
        ]
    positional = " ".join(f'"${index + 2}"' for index in range(len(args)))
    shell = f'source "$1/Common.zsh"; {function} {positional}'
    # zsh positional arguments are intentionally used rather than interpolated
    # so a fixture path cannot become shell syntax.
    return subprocess.run(  # noqa: S603
        ["zsh", "-c", shell, "fixture", str(MACOS_OPS), *args],  # noqa: S607
        cwd=REPO_ROOT,
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )


def test_privileged_evidence_scripts_use_fixed_commands_and_passthrough() -> None:
    capture = (MACOS_OPS / "Capture-PrivilegedHostEvidence.zsh").read_text()
    preflight = (MACOS_OPS / "Test-FormalPreflight.zsh").read_text()
    accept = (MACOS_OPS / "Accept-HostCutover.zsh").read_text()
    resume = (MACOS_OPS / "Resume-HostCutover.zsh").read_text()

    assert "(( EUID != 0 ))" in capture
    assert "/usr/bin/sudo -n /sbin/pfctl -s info" in capture
    assert "/usr/bin/sudo -n /sbin/pfctl -sr" in capture
    assert "/usr/bin/sudo -n /usr/sbin/systemsetup -getusingnetworktime" in capture
    assert "macos_active_operator_subject" not in capture
    assert "designatedHostAccount" in capture
    assert "--command" not in capture
    assert "--cidr" not in capture
    assert "--candidate-port" not in capture
    assert "--pf-evidence" in preflight
    assert "--network-time-evidence" in preflight
    assert "pfctl" not in preflight
    assert "systemsetup" not in preflight
    assert "sudo" not in preflight
    assert "UseResourceSaver" in preflight
    assert "evidence_memory" not in preflight
    for script in (accept, resume):
        assert "--pf-evidence" in script
        assert "--network-time-evidence" in script
        assert '--pf-evidence "$pf_evidence"' in script
        assert '--network-time-evidence "$network_time_evidence"' in script


def test_capture_uses_protected_owner_not_application_operator(tmp_path: Path) -> None:
    root = _capture_fixture(tmp_path, app_operator="different-application-user")
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh is unavailable on this runner")
    result = subprocess.run(  # noqa: S603
        [
            zsh,
            str(MACOS_OPS / "Capture-PrivilegedHostEvidence.zsh"),
            "--root",
            str(root),
        ],
        cwd=REPO_ROOT,
        env=_shell_env(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0  # fixed sudo probes are unavailable in tests
    pf_manifest = json.loads(
        (root / "evidence" / "pf-privileged-host-evidence.json").read_text()
    )
    network_manifest = json.loads(
        (root / "evidence" / "network-time-privileged-host-evidence.json").read_text()
    )
    # The host-account precondition passed: fixed probes were attempted rather
    # than short-circuited by the unrelated application operator username.
    assert pf_manifest["infoExitCode"] >= 0
    assert pf_manifest["rulesExitCode"] >= 0
    assert network_manifest["exitCode"] >= 0
    assert "capture must be run by the designated operator" not in result.stderr
    assert pf_manifest["designatedHostAccount"] == root.owner()
    assert network_manifest["designatedHostAccount"] == root.owner()


def test_capture_rejects_protected_root_owned_by_another_account(
    tmp_path: Path,
) -> None:
    root = _capture_fixture(tmp_path, app_operator="different-application-user")
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh is unavailable on this runner")
    fake_bin = tmp_path / "owner-check-bin"
    fake_bin.mkdir(mode=0o700)
    fake_stat = fake_bin / "stat"
    fake_stat.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-f" ] && [ "$2" = "%Su" ] && '
        '[ "$4" = "$FAKE_OWNER_PATH" ]; then\n'
        "  printf '%s\\n' another-account\n"
        "  exit 0\n"
        "fi\n"
        'exec /usr/bin/stat "$@"\n',
        encoding="utf-8",
    )
    fake_stat.chmod(0o700)
    env = _shell_env(tmp_path)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_OWNER_PATH"] = str(root)
    result = subprocess.run(  # noqa: S603
        [
            zsh,
            str(MACOS_OPS / "Capture-PrivilegedHostEvidence.zsh"),
            "--root",
            str(root),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "not owned by the current operator" in result.stderr


@pytest.mark.parametrize("network", [False, True])
def test_privileged_evidence_happy_path(tmp_path: Path, network: bool) -> None:
    root, values = _fixture(tmp_path)
    result = _assert_fixture(root, values, network=network, env=_shell_env(tmp_path))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hostId", "other-host"),
        ("hostIdentitySha256", "0" * 64),
        ("bootMarkerSha256", "1" * 64),
        ("designatedHostAccount", "other-account"),
        ("approvedCidr", "192.168.0.0/16"),
        ("candidateAddress", "192.168.2.35"),
        ("candidatePort", 8082),
        ("operatorPort", 8082),
        ("postgresPort", 55432),
        ("frontendPort", 55173),
        ("backendPort", 58000),
        ("infoCommand", "/bin/false"),
        ("infoExitCode", 1),
    ],
)
def test_pf_evidence_rechecks_manifest_bindings(
    tmp_path: Path, field: str, value: object
) -> None:
    root, values = _fixture(tmp_path)
    path = Path(values["pf"])
    manifest = json.loads(path.read_text())
    manifest[field] = value
    _write_checked(path, json.dumps(manifest, separators=(",", ":"), sort_keys=True))
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0


def test_pf_evidence_rejects_tamper_missing_sidecar_and_broad_or_forbidden_rules(
    tmp_path: Path,
) -> None:
    root, values = _fixture(tmp_path)
    rules = Path(values["evidence"]) / "rules.txt"
    rules.write_text(
        "pass in proto tcp from 192.168.0.0/16 to 192.168.2.34 port 8080\n",
        encoding="utf-8",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0

    rules.write_text(
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8081\n",
        encoding="utf-8",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0

    rules.unlink()
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0


def test_pf_rules_require_pass_and_ignore_block_rules(tmp_path: Path) -> None:
    root, values = _fixture(tmp_path)
    rules = Path(values["evidence"]) / "rules.txt"
    manifest_path = Path(values["pf"])
    manifest = json.loads(manifest_path.read_text())

    def write_rules(contents: str) -> None:
        _write_checked(rules, contents)
        manifest["rulesOutputSha256"] = _sha256(rules)
        _write_checked(
            manifest_path,
            json.dumps(manifest, separators=(",", ":"), sort_keys=True),
        )

    write_rules(
        "block in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8080\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0

    write_rules(
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8080\n"
        "block in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8081\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode == 0, result.stderr

    write_rules(
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8080\n"
        "pass in proto tcp from 192.168.2.0/24 to any port 8080\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0

    write_rules(
        "pass in proto tcp from 192.168.2.0/24 to any port 8080\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0

    write_rules(
        "pass in proto tcp from 192.168.0.0/16 to 192.168.2.34 port 8080\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0

    write_rules(
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8080\n"
        "block in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8081\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode == 0, result.stderr

    write_rules(
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8080\n"
        "pass in proto tcp from 192.168.2.0/24 to 192.168.2.34 port 8081\n",
    )
    result = _assert_fixture(root, values, env=_shell_env(tmp_path))
    assert result.returncode != 0


def test_network_time_evidence_rejects_off_and_stale_or_future(tmp_path: Path) -> None:
    root, values = _fixture(tmp_path)
    network_path = Path(values["network"])
    manifest = json.loads(network_path.read_text())
    manifest["checkedAt"] = "2020-01-01T00:00:00Z"
    _write_checked(
        network_path, json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    )
    result = _assert_fixture(root, values, network=True, env=_shell_env(tmp_path))
    assert result.returncode != 0

    manifest["checkedAt"] = "2099-01-01T00:00:00Z"
    _write_checked(
        network_path, json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    )
    result = _assert_fixture(root, values, network=True, env=_shell_env(tmp_path))
    assert result.returncode != 0

    manifest["checkedAt"] = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    network_output = Path(values["evidence"]) / "network.txt"
    _write_checked(network_output, "Network Time: Off\n")
    manifest["outputSha256"] = _sha256(network_output)
    _write_checked(
        network_path, json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    )
    result = _assert_fixture(root, values, network=True, env=_shell_env(tmp_path))
    assert result.returncode != 0


def test_network_time_evidence_rejects_wrong_designated_account(tmp_path: Path) -> None:
    root, values = _fixture(tmp_path)
    network_path = Path(values["network"])
    manifest = json.loads(network_path.read_text())
    manifest["designatedHostAccount"] = "other-account"
    _write_checked(
        network_path, json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    )
    result = _assert_fixture(root, values, network=True, env=_shell_env(tmp_path))
    assert result.returncode != 0


def test_network_time_evidence_requires_normative_on_line(tmp_path: Path) -> None:
    root, values = _fixture(tmp_path)
    network_path = Path(values["network"])
    network_output = Path(values["evidence"]) / "network.txt"
    manifest = json.loads(network_path.read_text())

    _write_checked(network_output, "Not On\n")
    manifest["outputSha256"] = _sha256(network_output)
    _write_checked(
        network_path, json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    )
    result = _assert_fixture(root, values, network=True, env=_shell_env(tmp_path))
    assert result.returncode != 0

    _write_checked(network_output, "  network   time :   on  \n")
    manifest["outputSha256"] = _sha256(network_output)
    _write_checked(
        network_path, json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    )
    result = _assert_fixture(root, values, network=True, env=_shell_env(tmp_path))
    assert result.returncode == 0, result.stderr
