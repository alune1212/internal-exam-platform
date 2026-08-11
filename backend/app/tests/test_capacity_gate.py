import hashlib
import json
from argparse import ArgumentTypeError
from pathlib import Path

import pytest

from app.core.config import settings
from app.ops.capacity_gate import (
    EXPECTED_CAPACITY_SERVICES,
    CapacityMetrics,
    Thresholds,
    _assert_base_url,
    _assert_capacity_run_identity,
    _assert_disposable_database,
    _assert_formal_evidence_identity,
    _evaluate,
    _evidence_identity,
    _exact_client_count,
    _normalise_docker_platform,
    _normalise_image_evidence,
    _p95,
    _warmup_run_id,
    _write_report,
)


def test_capacity_gate_acceptance_thresholds() -> None:
    thresholds = Thresholds()
    metrics: CapacityMetrics = {
        "run_id": "test",
        "exam_id": 1,
        "clients": 100,
        "errors": [],
        "submitted_count": 100,
        "start_p95_ms": 4999,
        "save_p95_ms": 1999,
        "submit_p95_ms": 2999,
        "max_database_connections": 40,
        "worker_heartbeat_age_seconds": 89.9,
    }
    assert _evaluate(metrics, thresholds) == []
    metrics["start_p95_ms"] = 5001
    assert _evaluate(metrics, thresholds) == ["start_p95_ms"]


def test_capacity_gate_p95_uses_nearest_rank() -> None:
    assert _p95([value / 1000 for value in range(1, 101)]) == 95


def test_capacity_gate_refuses_non_disposable_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+psycopg://exam:secret@db:5432/internal_exam",
    )
    monkeypatch.setenv("E2E_DISPOSABLE_DATABASE", "true")
    with pytest.raises(RuntimeError, match="disposable"):
        _assert_disposable_database()


def test_capacity_gate_accepts_only_exact_disposable_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+psycopg://exam_e2e:secret@db:5432/internal_exam_e2e",
    )
    monkeypatch.setenv("E2E_DISPOSABLE_DATABASE", "true")
    monkeypatch.setenv("CAPACITY_PROJECT_NAME", "internal-exam-capacity")
    monkeypatch.setenv("CAPACITY_RUN_ID", "run-123")
    _assert_disposable_database()

    monkeypatch.setenv("CAPACITY_PROJECT_NAME", "internal-exam-dev")
    with pytest.raises(RuntimeError, match="exact disposable"):
        _assert_disposable_database()


def test_capacity_gate_requires_exactly_100_clients() -> None:
    assert _exact_client_count("100") == 100
    with pytest.raises(ArgumentTypeError, match="exactly 100"):
        _exact_client_count("99")


def test_capacity_warmup_run_identity_is_scoped_to_current_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAPACITY_RUN_ID", "run-current")
    warmup_run_id = _warmup_run_id()
    assert warmup_run_id.startswith("warmup-run-current-")
    _assert_capacity_run_identity(warmup_run_id)

    monkeypatch.setenv("CAPACITY_RUN_ID", "run-other")
    with pytest.raises(RuntimeError, match="run identity"):
        _assert_capacity_run_identity(warmup_run_id)


def test_capacity_gate_allowlists_disposable_base_url() -> None:
    _assert_base_url("http://nginx")
    _assert_base_url("http://nginx/")
    for base_url in ("http://localhost", "https://nginx", "http://nginx:8080"):
        with pytest.raises(ValueError, match="base URL"):
            _assert_base_url(base_url)


def test_capacity_evidence_requires_clean_commit_and_final_images() -> None:
    image_id = "sha256:" + "a" * 64
    images = _normalise_image_evidence(
        json.dumps(
            [
                {"Service": service, "ID": image_id, "Digest": image_id}
                for service in sorted(EXPECTED_CAPACITY_SERVICES)
            ]
        )
    )
    _assert_formal_evidence_identity(
        commit="a" * 40,
        commit_state="clean",
        host_os="darwin",
        host_arch="arm64",
        compose_project="internal-exam-capacity",
        docker_platform="linux/arm64",
        image_evidence=images,
    )
    with pytest.raises(ValueError, match="clean Git commit"):
        _assert_formal_evidence_identity(
            commit="unknown",
            commit_state="dirty",
            host_os="darwin",
            host_arch="arm64",
            compose_project="internal-exam-capacity",
            docker_platform="linux/arm64",
            image_evidence=images,
        )


def test_capacity_image_evidence_matches_compose_v5_json_shape() -> None:
    image_id = "sha256:" + "b" * 64
    raw = json.dumps(
        [
            {
                "ID": image_id,
                "ContainerName": f"internal-exam-capacity-{service}-1",
                "Repository": "internal-exam-platform-backend",
                "Tag": "e2e",
                "Platform": "linux/arm64",
            }
            for service in sorted(EXPECTED_CAPACITY_SERVICES)
        ]
    )
    images = _normalise_image_evidence(raw)
    assert {item["service"] for item in images} == EXPECTED_CAPACITY_SERVICES
    assert all(item["digest"] == image_id for item in images)

    missing_service = json.dumps(
        [
            {
                "ID": image_id,
                "ContainerName": f"internal-exam-capacity-{service}-1",
            }
            for service in sorted(EXPECTED_CAPACITY_SERVICES - {"fake-smtp"})
        ]
    )
    with pytest.raises(ValueError, match="expected app services"):
        _normalise_image_evidence(missing_service)


@pytest.mark.parametrize(
    ("reported", "canonical"),
    [("linux/aarch64", "linux/arm64"), ("linux/x86_64", "linux/amd64")],
)
def test_capacity_evidence_normalises_docker_platform_aliases(
    reported: str,
    canonical: str,
) -> None:
    image_id = "sha256:" + "c" * 64
    images = [
        {"service": service, "image_id": image_id, "digest": image_id}
        for service in sorted(EXPECTED_CAPACITY_SERVICES)
    ]
    assert _normalise_docker_platform(reported) == canonical
    _assert_formal_evidence_identity(
        commit="a" * 40,
        commit_state="clean",
        host_os="darwin",
        host_arch="arm64",
        compose_project="internal-exam-capacity",
        docker_platform=reported,
        image_evidence=images,
    )
    identity = _evidence_identity(
        "run-123",
        docker_platform=reported,
        image_evidence=images,
    )
    assert identity["docker_platform"] == canonical


def test_capacity_evidence_identity_binds_run_commit_and_host() -> None:
    image_id = "sha256:" + "a" * 64
    identity = _evidence_identity(
        "run-123",
        commit="a" * 40,
        commit_state="clean",
        host_os="darwin",
        host_arch="arm64",
        run_directory="run-123",
        compose_project="internal-exam-capacity",
        docker_platform="linux/arm64",
        image_evidence=[
            {"service": "backend", "image_id": image_id, "digest": image_id}
        ],
    )
    assert identity == {
        "run_id": "run-123",
        "commit": "a" * 40,
        "commit_state": "clean",
        "host_os": "darwin",
        "host_arch": "arm64",
        "run_directory": "run-123",
        "compose_project": "internal-exam-capacity",
        "docker_platform": "linux/arm64",
        "final_images": [
            {"service": "backend", "image_id": image_id, "digest": image_id}
        ],
    }


def test_capacity_report_replaces_stale_passing_artifact(tmp_path: Path) -> None:
    report_path = tmp_path / "capacity-report.json"
    report_path.write_text('{"status":"passed"}\n', encoding="utf-8")
    checksum_path = report_path.with_suffix(".json.sha256")
    checksum_path.write_text("stale\n", encoding="ascii")

    _write_report(report_path, {"status": "failed", "failed_checks": ["runtime"]})

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert "passed" not in report_path.read_text(encoding="utf-8")
    digest, filename = checksum_path.read_text(encoding="ascii").strip().split("  ")
    assert filename == report_path.name
    assert digest == hashlib.sha256(report_path.read_bytes()).hexdigest()


def test_capacity_script_uses_unique_runs_and_retains_failures() -> None:
    script = (
        Path(__file__).resolve().parents[3] / "ops" / "e2e" / "run-capacity-gate.sh"
    ).read_text(encoding="utf-8")
    assert "mktemp -d" in script
    assert 'rm -f "$report_path" "$checksum_path"' in script
    assert "write_failure_evidence" in script
    assert '--run-id "$run_id"' in script
    assert '--host-arch "$host_arch"' in script
    assert '--commit "$git_commit"' in script
    assert '--commit-state "$commit_state"' in script
    assert '--compose-project "$project_name"' in script
    assert '--image-evidence "$image_evidence"' in script
    assert "E2E_COMPOSE_OVERRIDE=$e2e_compose_file" in script
    assert "linux/aarch64" in script
    assert "linux/x86_64" in script
    assert "--clients 100" in script
