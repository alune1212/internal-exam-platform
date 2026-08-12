"""Focused contract checks for external staging evidence producers."""

from __future__ import annotations

import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from app.ops import staging_acceptance

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "ops" / "macos" / "Invoke-StagingExternalChecks.zsh"


def test_external_staging_producer_is_executable_and_syntax_valid() -> None:
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & 0o111
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is unavailable on this runner")
    result = subprocess.run(  # noqa: S603
        [zsh, "-n", str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_external_staging_producer_has_fail_closed_real_gate_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "CANDIDATE_PUBLIC_BASE_URL" in script
    assert "http://127.0.0.1:${MACOS_STAGE_PORT_CANDIDATE}" in script

    # SMTP evidence comes from the selected backend image and retains only the
    # recipient domain/timestamp; a failed command never reaches the writer.
    assert "app.ops.preflight smtp" in script
    assert "real-smtp" in script
    assert "recipientDomain" in script
    assert "sentAt" in script
    assert "macos_checksummed_json" in script

    # Browser evidence uses the repository's installed Playwright CLI and is
    # explicitly desktop-only; mobile UAT cannot be claimed by automation.
    assert "browser-report" in script
    assert "browser-e2e-report" in script
    assert "scenarioMarkers" in script
    assert "browserReportSha256" in script
    assert "mobileUat" in script
    assert "--browser-command" in script

    # Capacity evidence must be an independently measured, checksummed report
    # tied to the run's exact image IDs and 100-client zero-error result.
    assert "--capacity-report" in script
    assert "--live-image-ids" in script
    assert 'report.get("status") != "passed"' in script
    assert 'metrics.get("clients") != 100' in script
    assert 'metrics.get("errors") != []' in script
    assert 'metrics.get("submitted_count") != 100' in script
    assert "capacity image ID does not match exact staging image" in script
    assert (
        "capacity project must be staging or an explicitly approved isolated clone"
        in script
    )
    assert '"$capacity_project" == internal-exam-capacity ||' in script
    assert '"failed_checks": []' in script
    assert '"metrics": {' in script
    assert '"thresholds": {' in script
    assert "object_pairs_hook=reject_duplicate_keys" in script
    assert "parse_constant=reject_non_finite" in script
    assert 'report.get("failed_checks") != []' in script
    assert "def required_metric" in script


def test_capacity_shape_is_accepted_by_staging_validator() -> None:
    payload = {
        "failed_checks": [],
        "metrics": {
            "run_id": "run-capacity-20260811",
            "clients": 100,
            "errors": [],
            "submitted_count": 100,
            "start_p95_ms": 100,
            "save_p95_ms": 100,
            "submit_p95_ms": 100,
            "max_database_connections": 8,
            "worker_heartbeat_age_seconds": 1,
        },
        "thresholds": {
            "clients": 100,
            "error_count": 0,
            "start_p95_ms": 5000,
            "save_p95_ms": 2000,
            "submit_p95_ms": 3000,
            "max_database_connections": 40,
            "worker_heartbeat_age_seconds": 90,
        },
        "runId": "run-20260811T010203Z-123456",
        "imageIds": {"db": "sha256:" + "1" * 64},
        "details": {"capacityProject": "internal-exam-capacity-run"},
        "sourceMeasurementRunId": "run-capacity-20260811",
        "sourceReportPath": "capacity-source.json",
        "sourceReportSha256": "a" * 64,
    }
    staging_acceptance._validate_capacity_report(payload)


def test_capacity_validator_rejects_missing_or_negative_measurements() -> None:
    payload: dict[str, Any] = {
        "failed_checks": [],
        "metrics": {
            "run_id": "run-capacity-20260811",
            "clients": 100,
            "errors": [],
            "submitted_count": 100,
            "start_p95_ms": 100,
            "save_p95_ms": 100,
            "submit_p95_ms": 100,
            "max_database_connections": 8,
            "worker_heartbeat_age_seconds": 1,
        },
        "thresholds": {
            "clients": 100,
            "error_count": 0,
            "start_p95_ms": 5000,
            "save_p95_ms": 2000,
            "submit_p95_ms": 3000,
            "max_database_connections": 40,
            "worker_heartbeat_age_seconds": 90,
        },
        "runId": "run-20260811T010203Z-123456",
        "sourceMeasurementRunId": "run-capacity-20260811",
        "sourceReportPath": "capacity-source.json",
        "sourceReportSha256": "a" * 64,
    }
    missing = deepcopy(payload)
    del missing["metrics"]["save_p95_ms"]
    with pytest.raises(staging_acceptance.StagingAcceptanceError):
        staging_acceptance._validate_capacity_report(missing)
    negative = deepcopy(payload)
    negative["metrics"]["save_p95_ms"] = -1
    with pytest.raises(staging_acceptance.StagingAcceptanceError):
        staging_acceptance._validate_capacity_report(negative)
    failed = deepcopy(payload)
    failed["failed_checks"] = ["worker-heartbeat"]
    with pytest.raises(staging_acceptance.StagingAcceptanceError):
        staging_acceptance._validate_capacity_report(failed)


def test_external_staging_producer_does_not_accept_manual_pass_flags() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "--status passed" not in script
    assert "--passed" not in script
    assert '"status"' in script
    assert '"passed"' in script  # only emitted after a real producer succeeds
    assert "self-asserted" not in script


def test_embedded_json_readers_reject_duplicate_keys_and_nonfinite(
    tmp_path: Path,
) -> None:
    """Exercise the producer's actual embedded strict JSON readers offline."""

    chunks = SCRIPT.read_text(encoding="utf-8").split("<<'PY'\n")[1:]
    browser_reader = chunks[0].split("\nPY\n", 1)[0]
    capacity_reader = chunks[1].split("\nPY\n", 1)[0]

    def run_reader(source: str, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, "-", *args],
            input=source,
            capture_output=True,
            text=True,
            check=False,
        )

    browser_report = tmp_path / "browser.json"
    browser_live = tmp_path / "browser-live.json"
    browser_report.write_text(
        '{"kind":"browser-e2e-report","kind":"browser-e2e-report"}',
        encoding="utf-8",
    )
    browser_live.write_text("{}", encoding="utf-8")
    browser_duplicate = run_reader(
        browser_reader,
        [
            str(browser_report),
            str(browser_live),
            "run-20260811T010203Z-123456",
            "a" * 40,
            "internal-exam-staging-123456789abc",
            "host-test",
            "b" * 64,
            "2026-08-11T01:02:03+00:00",
            "http://127.0.0.1:18080",
            "http://127.0.0.1:18081",
            str(tmp_path),
        ],
    )
    assert browser_duplicate.returncode != 0
    assert "duplicate keys" in browser_duplicate.stderr

    browser_report.write_text(
        '{"kind":"browser-e2e-report","status":"passed"}', encoding="utf-8"
    )
    browser_live.write_text('{"notFinite":NaN}', encoding="utf-8")
    browser_nonfinite = run_reader(
        browser_reader,
        [
            str(browser_report),
            str(browser_live),
            "run-20260811T010203Z-123456",
            "a" * 40,
            "internal-exam-staging-123456789abc",
            "host-test",
            "b" * 64,
            "2026-08-11T01:02:03+00:00",
            "http://127.0.0.1:18080",
            "http://127.0.0.1:18081",
            str(tmp_path),
        ],
    )
    assert browser_nonfinite.returncode != 0
    assert "NaN or Infinity" in browser_nonfinite.stderr

    capacity_report = tmp_path / "capacity.json"
    capacity_live = tmp_path / "capacity-live.json"
    capacity_report.write_text(
        '{"status":"passed","status":"passed"}', encoding="utf-8"
    )
    capacity_live.write_text("[]", encoding="utf-8")
    capacity_duplicate = run_reader(
        capacity_reader,
        [
            str(capacity_report),
            str(capacity_live),
            "run-20260811T010203Z-123456",
            "a" * 40,
            "host-test",
            "internal-exam-staging-123456789abc",
            "internal-exam-capacity",
            "2026-08-11T01:02:03+00:00",
        ],
    )
    assert capacity_duplicate.returncode != 0
    assert "duplicate keys" in capacity_duplicate.stderr

    capacity_report.write_text(
        '{"status":"passed","failed_checks":[]}', encoding="utf-8"
    )
    capacity_live.write_text("[Infinity]", encoding="utf-8")
    capacity_nonfinite = run_reader(
        capacity_reader,
        [
            str(capacity_report),
            str(capacity_live),
            "run-20260811T010203Z-123456",
            "a" * 40,
            "host-test",
            "internal-exam-staging-123456789abc",
            "internal-exam-capacity",
            "2026-08-11T01:02:03+00:00",
        ],
    )
    assert capacity_nonfinite.returncode != 0
    assert "NaN or Infinity" in capacity_nonfinite.stderr


def test_external_producer_binds_release_env_urls_and_operation_lock() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert 'macos_acquire_lock "$MACOS_LAYOUT_STATE/.operation.lock"' in script
    assert "macos_release_lock" in script
    assert 'export APP_VERSION_TAG="${run_commit:l}"' in script
    assert 'export GIT_COMMIT="${run_commit:l}"' in script
    assert '"$candidate_url" == http://127.0.0.1:18080' in script
    assert '"$operator_url" == http://127.0.0.1:18081' in script
