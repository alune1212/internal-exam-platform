"""Static contract tests for the generation-1 formal browser-smoke producer."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "ops" / "macos" / "Capture-FormalBrowserSmokeEvidence.zsh"
INSTALLER = REPO_ROOT / "ops" / "macos" / "Install-Release.zsh"


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
    assert len(rows) == 1, f"expected one Git index entry for {relative}: {rows!r}"
    return int(rows[0].split(maxsplit=1)[0], 8)


def test_formal_browser_smoke_producer_is_owner_only_and_parses() -> None:
    assert SCRIPT.is_file()
    # Git can persist only the executable bit.  The formal release installer
    # tightens this to owner-only mode after copying the immutable bundle.
    assert _git_mode(SCRIPT) == 0o100755
    installer = INSTALLER.read_text(encoding="utf-8")
    assert (
        "find \"$temporary_target/ops/macos\" -type f -name '*.zsh' -print" in installer
    )
    assert 'chmod 700 "$file"' in installer
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")
    result = subprocess.run(  # noqa: S603
        [zsh, "-n", "--", str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_formal_browser_smoke_is_scoped_to_pending_generation_one() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    for marker in (
        "formal-writer-bootstrap-intent",
        "formal-writer-current",
        "bootstrapPending",
        "writerGeneration",
        "releaseCommit",
        "releaseVersion",
        "hostId",
        "macos_read_cutover_identity",
        "Test-ReleaseBundle.zsh",
        "http://127.0.0.1:28080",
        "http://127.0.0.1:28081",
        "candidateUrl",
        "operatorUrl",
        "checkedAt",
        "macos_checksummed_json",
        "macos_write_evidence",
    ):
        assert marker in script, marker

    assert 'kind: "browser-smoke"' in script
    assert 'scope: "browser-smoke"' in script
    assert 'stagingE2e: "not-run"' in script
    assert 'mobileUat: "not-run"' in script
    assert 'macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"' in script
    assert 'macos_secure_path "$MACOS_LAYOUT_EVIDENCE"' in script
    assert "refusing to overwrite existing browser evidence" in script
    assert (
        "browser source must be the repository root of a clean exact-commit Git worktree"
        in script
    )
    assert "--browser-source-manifest" not in script


def test_formal_browser_smoke_uses_local_chromium_and_blocks_external_assets() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    for marker in (
        'require("playwright")',
        "chromium.launch",
        'page.on("console"',
        'page.on("pageerror"',
        "context.setOffline(true)",
        "offlineStaticResources",
        'route.abort("blockedbyclient")',
        "externalOrigins",
        "node_modules/.bin/playwright",
        'git -C "$browser_source" rev-parse --verify HEAD',
        'git -C "$browser_source" diff-index --quiet HEAD --',
    ):
        assert marker in script, marker

    lowered = script.lower()
    assert "npm install" not in lowered
    assert "npm ci" not in lowered
    assert "npx " not in lowered
    assert "https://cdn" not in lowered
    assert "Invoke-Staging" not in script
    assert "Start-Platform" not in script


def test_formal_browser_smoke_does_not_write_evidence_before_a_pass() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    smoke_start = script.index("browser_payload=")
    output_start = script.index('if [[ -n "$output_arg" ]]', smoke_start)
    smoke_block = script[smoke_start:output_start]
    assert "macos_write_atomic" not in smoke_block
    assert "macos_write_evidence" not in smoke_block
    assert 'status: "passed"' in smoke_block
    assert "macos_assert_fresh_timestamp" in script
