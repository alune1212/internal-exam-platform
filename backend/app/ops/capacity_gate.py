"""Reproducible 100-client start/save/submit release capacity gate."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy import func, text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import create_candidate_token
from app.models import (
    Candidate,
    Exam,
    ExamAttempt,
    ExamCandidateScope,
    ExamQuestionPool,
    Question,
    QuestionOption,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


EXPECTED_CLIENTS = 100
EXPECTED_CAPACITY_PROJECT = "internal-exam-capacity"
EXPECTED_DATABASE_SCHEME = "postgresql+psycopg"
EXPECTED_DATABASE_HOST = "db"
EXPECTED_DATABASE_PORT = 5432
EXPECTED_DATABASE_NAME = "internal_exam_e2e"
EXPECTED_DATABASE_USER = "exam_e2e"
EXPECTED_BASE_URL = "http://nginx"
EXPECTED_CAPACITY_SERVICES = frozenset(
    {
        "db",
        "fake-smtp",
        "backend",
        "frontend",
        "auto-submit-worker",
        "nginx",
        "operator-nginx",
    }
)
DOCKER_PLATFORM_ARCH_ALIASES = {
    "aarch64": "arm64",
    "x86_64": "amd64",
}
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _exact_client_count(value: str) -> int:
    try:
        clients = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("clients must be exactly 100") from exc
    if clients != EXPECTED_CLIENTS:
        raise argparse.ArgumentTypeError("clients must be exactly 100")
    return clients


@dataclass(frozen=True)
class Thresholds:
    clients: int = 100
    error_count: int = 0
    start_p95_ms: int = 5000
    save_p95_ms: int = 2000
    submit_p95_ms: int = 3000
    max_database_connections: int = 40
    worker_heartbeat_age_seconds: int = 90


class CapacityMetrics(TypedDict):
    run_id: str
    exam_id: int
    clients: int
    errors: list[str]
    submitted_count: int
    start_p95_ms: int
    save_p95_ms: int
    submit_p95_ms: int
    max_database_connections: int
    worker_heartbeat_age_seconds: float
    warmup_performed: NotRequired[bool]
    warmup_errors: NotRequired[list[str]]


def _assert_disposable_database(run_id: str | None = None) -> None:
    parsed = urlparse(settings.database_url)
    database_name = parsed.path.removeprefix("/")
    project_name = os.getenv("CAPACITY_PROJECT_NAME", "")
    expected_run_id = os.getenv("CAPACITY_RUN_ID", "")
    try:
        database_port = parsed.port
    except ValueError:
        database_port = None
    if (
        settings.environment != "development"
        or os.getenv("E2E_DISPOSABLE_DATABASE") != "true"
        or parsed.scheme != EXPECTED_DATABASE_SCHEME
        or parsed.hostname != EXPECTED_DATABASE_HOST
        or database_port != EXPECTED_DATABASE_PORT
        or parsed.username != EXPECTED_DATABASE_USER
        or database_name != EXPECTED_DATABASE_NAME
        or project_name != EXPECTED_CAPACITY_PROJECT
        or not expected_run_id
    ):
        raise RuntimeError(
            "Capacity gate requires the exact disposable capacity Compose database"
        )
    if run_id is not None:
        _assert_capacity_run_identity(run_id)


def _assert_capacity_run_identity(run_id: str) -> None:
    expected_run_id = os.getenv("CAPACITY_RUN_ID", "")
    if not expected_run_id or run_id == expected_run_id:
        return
    if run_id.startswith(f"warmup-{expected_run_id}-"):
        return
    raise RuntimeError("Capacity gate run identity does not match its Compose run")


def _warmup_run_id() -> str:
    expected_run_id = os.getenv("CAPACITY_RUN_ID", "")
    if not expected_run_id:
        raise RuntimeError("Capacity gate warm-up requires its Compose run identity")
    return f"warmup-{expected_run_id}-{uuid4().hex[:12]}"


def _normalise_docker_platform(value: str) -> str:
    operating_system, separator, architecture = value.partition("/")
    if not separator:
        return value
    return f"{operating_system}/{DOCKER_PLATFORM_ARCH_ALIASES.get(architecture, architecture)}"


def _assert_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    try:
        base_port = parsed.port
    except ValueError:
        base_port = -1
    if (
        parsed.scheme != "http"
        or parsed.hostname != "nginx"
        or base_port is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"Capacity gate base URL must be {EXPECTED_BASE_URL}")


def _normalise_image_evidence(raw: str) -> list[dict[str, str]]:
    if not raw.strip() or raw.strip() in {"null", "[]"}:
        return []
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("capacity image evidence is not valid JSON") from exc
    if isinstance(decoded, dict):
        decoded = [decoded]
    if not isinstance(decoded, list):
        raise ValueError("capacity image evidence must be a JSON list")

    normalised: list[dict[str, str]] = []
    seen_services: set[str] = set()
    for item in decoded:
        if not isinstance(item, dict):
            raise ValueError("capacity image evidence contains a non-object")
        image_id = str(item.get("ID") or item.get("id") or "")
        # Compose's local image JSON does not expose registry digests; a full
        # image ID is the immutable content digest available for this run.
        digest = str(item.get("Digest") or item.get("digest") or image_id)
        service = str(item.get("Service") or item.get("service") or "").strip()
        if not service:
            container_name = str(
                item.get("ContainerName") or item.get("container_name") or ""
            )
            # Compose v5.3.1 emits ContainerName but no Service field for
            # `images --format json`; recover the service from its stable
            # `<project>-<service>-<index>` suffix.
            for candidate in sorted(EXPECTED_CAPACITY_SERVICES, key=len, reverse=True):
                if re.search(rf"-{re.escape(candidate)}-\d+$", container_name):
                    service = candidate
                    break
        if service not in EXPECTED_CAPACITY_SERVICES:
            raise ValueError("capacity image evidence contains an unexpected service")
        if service in seen_services:
            raise ValueError("capacity image evidence contains a duplicate service")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ValueError("capacity image evidence is missing a full image ID")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError("capacity image evidence is missing a full image digest")
        seen_services.add(service)
        normalised.append(
            {
                "service": service,
                "image_id": image_id,
                "digest": digest,
            }
        )
    if not normalised:
        raise ValueError("capacity image evidence is empty")
    if seen_services != EXPECTED_CAPACITY_SERVICES:
        missing = sorted(EXPECTED_CAPACITY_SERVICES - seen_services)
        unexpected = sorted(seen_services - EXPECTED_CAPACITY_SERVICES)
        raise ValueError(
            "capacity image evidence services do not match expected app services: "
            f"missing={missing}, unexpected={unexpected}"
        )
    return normalised


def _assert_formal_evidence_identity(
    *,
    commit: str,
    commit_state: str,
    host_os: str,
    host_arch: str,
    compose_project: str,
    docker_platform: str,
    image_evidence: list[dict[str, str]],
) -> None:
    docker_platform = _normalise_docker_platform(docker_platform)
    if not COMMIT_PATTERN.fullmatch(commit) or commit_state != "clean":
        raise ValueError("capacity evidence requires a known clean Git commit")
    if compose_project != EXPECTED_CAPACITY_PROJECT:
        raise ValueError("capacity evidence Compose project is not disposable")
    if host_os not in {"darwin", "linux", "windows"}:
        raise ValueError("capacity evidence host OS is unknown")
    if not re.fullmatch(r"(arm64|aarch64|x86_64|amd64)", host_arch):
        raise ValueError("capacity evidence host architecture is unknown")
    if not re.fullmatch(r"linux/(amd64|arm64)", docker_platform):
        raise ValueError("capacity evidence Docker platform is not supported")
    image_services = {item.get("service") for item in image_evidence}
    if (
        len(image_evidence) != len(image_services)
        or image_services != EXPECTED_CAPACITY_SERVICES
    ):
        raise ValueError(
            "capacity evidence requires final image IDs and digests for exactly "
            "the expected app services"
        )


def _seed(
    clients: int,
    *,
    run_id: str | None = None,
) -> tuple[int, list[tuple[int, str]], str]:
    run_id = run_id or uuid4().hex[:12]
    _assert_disposable_database(run_id)
    now = datetime.now(UTC)
    with SessionLocal() as db:
        question = Question(
            question_type="single",
            stem=f"Capacity {run_id}: 请选择 A",
            analysis="容量门禁固定答案。",
            category_1="capacity-gate",
            score=Decimal("1"),
            status="active",
            source="capacity-gate",
            source_no=f"CAP-{run_id}",
        )
        db.add(question)
        db.flush()
        db.add_all(
            [
                QuestionOption(
                    question_id=question.id,
                    label="A",
                    content="正确",
                    is_correct=True,
                    sort_order=0,
                ),
                QuestionOption(
                    question_id=question.id,
                    label="B",
                    content="错误",
                    is_correct=False,
                    sort_order=1,
                ),
            ]
        )
        exam = Exam(
            title=f"Capacity Gate {run_id}",
            duration_minutes=30,
            question_rule={
                "question_count": 1,
                "total_score": 1,
                "pass_score": 1,
                "mode": "fixed_paper",
                "type_counts": {"single": 1},
            },
            status="active",
            show_answer_after_submit=False,
            show_ranking=False,
            available_from=now - timedelta(minutes=5),
            available_until=now + timedelta(hours=2),
        )
        db.add(exam)
        db.flush()
        db.add(ExamQuestionPool(exam_id=exam.id, question_id=question.id, sort_order=0))
        identities: list[tuple[int, str]] = []
        for index in range(clients):
            email = f"capacity-{run_id}-{index + 1:03d}@example.test"
            display_name = f"容量用户 {index + 1:03d}"
            candidate = Candidate(
                name=display_name,
                email=email,
                status="active",
            )
            db.add(candidate)
            db.flush()
            db.add(
                ExamCandidateScope(
                    exam_id=exam.id,
                    candidate_id=candidate.id,
                    roster_email=email,
                    roster_name=display_name,
                )
            )
            identities.append((candidate.id, create_candidate_token(candidate.id)))
        db.commit()
        return exam.id, identities, run_id


def _p95(values: list[float]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)] * 1000)


def _database_connection_count() -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                )
            ).scalar_one()
        )


def _post_json(
    base_url: str,
    path: str,
    headers: dict[str, str],
    payload: object | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    request = Request(  # noqa: S310 - guarded LAN URL
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - guarded LAN URL
            decoded = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("capacity endpoint returned a non-object JSON response")
    return cast("dict[str, Any]", decoded)


def _run_unmeasured_candidate(
    base_url: str,
    exam_id: int,
    token: str,
) -> None:
    """Exercise one complete flow without adding it to latency samples.

    This warm-up deliberately runs before the measured exam is seeded.  It
    brings the HTTP connection path, ORM metadata and database pools into the
    steady state while keeping cold-start/recovery testing as a separate gate.
    """

    headers = {"X-Candidate-Token": token}
    response = _post_json(
        base_url,
        f"/api/exams/{exam_id}/start",
        headers,
    )
    data = response["data"]
    attempt_id = int(data["attempt_id"])
    credential = str(data["attempt_session_credential"])
    question_id = int(data["questions"][0]["id"])
    session_headers = {**headers, "X-Attempt-Session": credential}
    _post_json(
        base_url,
        f"/api/attempts/{attempt_id}/answers/save",
        session_headers,
        {
            "answer_revision": int(data["answer_revision"]),
            "answers": [
                {
                    "attempt_question_id": question_id,
                    "selected_answer": "A",
                }
            ],
        },
    )
    _post_json(
        base_url,
        f"/api/attempts/{attempt_id}/submit",
        session_headers,
        {"submit_type": "manual"},
    )


def _run_warmup(base_url: str) -> tuple[bool, list[str]]:
    """Run one non-measured flow and return safe, non-sensitive diagnostics."""

    try:
        exam_id, identities, _ = _seed(
            1,
            run_id=_warmup_run_id(),
        )
        _, token = identities[0]
        _run_unmeasured_candidate(base_url, exam_id, token)
    except Exception as exc:  # report a type only; never persist exception text
        return False, [f"warmup:{type(exc).__name__}"]
    return True, []


async def _run_gate(
    base_url: str,
    clients: int,
    *,
    run_id: str | None = None,
) -> CapacityMetrics:
    _assert_base_url(base_url)
    if clients != EXPECTED_CLIENTS:
        raise ValueError(f"Capacity gate requires exactly {EXPECTED_CLIENTS} clients")
    run_id = run_id or uuid4().hex[:12]
    latencies: dict[str, list[float]] = {"start": [], "save": [], "submit": []}
    errors: list[str] = []
    max_connections = 0
    finished = asyncio.Event()
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(
        max_workers=max(8, clients + 4), thread_name_prefix="capacity-client"
    )

    warmup_performed, warmup_errors = await loop.run_in_executor(
        executor, partial(_run_warmup, base_url)
    )
    errors.extend(warmup_errors)

    async def monitor_connections() -> None:
        nonlocal max_connections
        while not finished.is_set():
            try:
                current = await loop.run_in_executor(
                    executor, _database_connection_count
                )
                max_connections = max(max_connections, current)
            except Exception as exc:  # report monitoring failures as gate failures
                errors.append(f"database-monitor:{type(exc).__name__}")
                return
            await asyncio.sleep(0.05)

    try:
        exam_id, identities, seeded_run_id = _seed(clients, run_id=run_id)
    except Exception:
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    if seeded_run_id != run_id:
        errors.append("seed:run_id_mismatch")

    async def one_candidate(candidate_id: int, token: str) -> None:
        headers = {"X-Candidate-Token": token}
        try:
            started = time.perf_counter()
            response = await loop.run_in_executor(
                executor,
                partial(
                    _post_json,
                    base_url,
                    f"/api/exams/{exam_id}/start",
                    headers,
                ),
            )
            latencies["start"].append(time.perf_counter() - started)
            data = response["data"]
            attempt_id = int(data["attempt_id"])
            credential = str(data["attempt_session_credential"])
            question_id = int(data["questions"][0]["id"])

            started = time.perf_counter()
            await loop.run_in_executor(
                executor,
                partial(
                    _post_json,
                    base_url,
                    f"/api/attempts/{attempt_id}/answers/save",
                    {**headers, "X-Attempt-Session": credential},
                    {
                        "answer_revision": int(data["answer_revision"]),
                        "answers": [
                            {
                                "attempt_question_id": question_id,
                                "selected_answer": "A",
                            }
                        ],
                    },
                ),
            )
            latencies["save"].append(time.perf_counter() - started)

            started = time.perf_counter()
            await loop.run_in_executor(
                executor,
                partial(
                    _post_json,
                    base_url,
                    f"/api/attempts/{attempt_id}/submit",
                    {**headers, "X-Attempt-Session": credential},
                    {"submit_type": "manual"},
                ),
            )
            latencies["submit"].append(time.perf_counter() - started)
        except Exception as exc:
            # Keep evidence useful for triage without persisting response bodies
            # or any accidental credential/token material.
            errors.append(f"candidate:{candidate_id}:{type(exc).__name__}")

    monitor = asyncio.create_task(monitor_connections())
    try:
        await asyncio.gather(
            *(one_candidate(candidate_id, token) for candidate_id, token in identities)
        )
    finally:
        finished.set()
        await monitor
        executor.shutdown(wait=True, cancel_futures=True)

    heartbeat = Path(settings.auto_submit_heartbeat_path)
    worker_age = (
        max(0.0, time.time() - heartbeat.stat().st_mtime)
        if heartbeat.is_file()
        else 1_000_000_000.0
    )
    with SessionLocal() as db:
        submitted_count = int(
            db.query(func.count(ExamAttempt.id))
            .filter(ExamAttempt.exam_id == exam_id, ExamAttempt.status == "submitted")
            .scalar()
            or 0
        )

    return {
        "run_id": seeded_run_id,
        "exam_id": exam_id,
        "clients": clients,
        "errors": errors,
        "submitted_count": submitted_count,
        "start_p95_ms": _p95(latencies["start"]),
        "save_p95_ms": _p95(latencies["save"]),
        "submit_p95_ms": _p95(latencies["submit"]),
        "max_database_connections": max_connections,
        "worker_heartbeat_age_seconds": round(worker_age, 3),
        "warmup_performed": warmup_performed,
        "warmup_errors": warmup_errors,
    }


def _evaluate(metrics: CapacityMetrics, thresholds: Thresholds) -> list[str]:
    failures: list[str] = []
    checks = {
        "client_count": int(metrics["clients"]) == thresholds.clients,
        "error_count": len(metrics["errors"]) == thresholds.error_count,
        "submitted_count": int(metrics["submitted_count"]) == thresholds.clients,
        "start_p95_ms": int(metrics["start_p95_ms"]) <= thresholds.start_p95_ms,
        "save_p95_ms": int(metrics["save_p95_ms"]) <= thresholds.save_p95_ms,
        "submit_p95_ms": int(metrics["submit_p95_ms"]) <= thresholds.submit_p95_ms,
        "max_database_connections": int(metrics["max_database_connections"])
        <= thresholds.max_database_connections,
        "worker_heartbeat": float(metrics["worker_heartbeat_age_seconds"])
        <= thresholds.worker_heartbeat_age_seconds,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    return failures


def _write_report(path: Path, report: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Clear both artifacts before writing so a failed rerun can never leave a
    # previous passing report/checksum looking current.
    path.unlink(missing_ok=True)
    path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    path.chmod(0o600)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    checksum_path.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    checksum_path.chmod(0o600)


def _evidence_identity(
    run_id: str,
    *,
    commit: str | None = None,
    commit_state: str | None = None,
    host_os: str | None = None,
    host_arch: str | None = None,
    run_directory: str | None = None,
    compose_project: str | None = None,
    docker_platform: str | None = None,
    image_evidence: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Return non-secret identity fields that bind evidence to one run/host."""

    reported_docker_platform = (
        docker_platform or os.getenv("CAPACITY_DOCKER_PLATFORM") or "unknown"
    )
    return {
        "run_id": run_id,
        "commit": commit or os.getenv("CAPACITY_GIT_COMMIT") or settings.git_commit,
        "commit_state": commit_state or os.getenv("CAPACITY_COMMIT_STATE") or "unknown",
        "host_os": host_os
        or os.getenv("CAPACITY_HOST_OS")
        or platform.system().lower(),
        "host_arch": host_arch or os.getenv("CAPACITY_HOST_ARCH") or platform.machine(),
        "run_directory": run_directory or os.getenv("CAPACITY_RUN_DIRECTORY") or run_id,
        "compose_project": compose_project
        or os.getenv("CAPACITY_PROJECT_NAME")
        or "unknown",
        "docker_platform": _normalise_docker_platform(reported_docker_platform),
        "final_images": image_evidence or [],
    }


def _empty_metrics(run_id: str, clients: int) -> CapacityMetrics:
    return {
        "run_id": run_id,
        "exam_id": 0,
        "clients": clients,
        "errors": [],
        "submitted_count": 0,
        "start_p95_ms": 0,
        "save_p95_ms": 0,
        "submit_p95_ms": 0,
        "max_database_connections": 0,
        "worker_heartbeat_age_seconds": 1_000_000_000.0,
        "warmup_performed": False,
        "warmup_errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://nginx")
    parser.add_argument("--clients", type=_exact_client_count, default=EXPECTED_CLIENTS)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--commit-state", default=None)
    parser.add_argument("--host-os", default=None)
    parser.add_argument("--host-arch", default=None)
    parser.add_argument("--run-directory", default=None)
    parser.add_argument("--compose-project", default=None)
    parser.add_argument("--docker-platform", default=None)
    parser.add_argument("--image-evidence", default="[]")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / "capacity-report.json",
    )
    args = parser.parse_args()
    thresholds = Thresholds(clients=args.clients)
    run_id = args.run_id or uuid4().hex[:12]
    image_evidence: list[dict[str, str]] = []
    identity_error = False
    runtime_error: str | None = None
    docker_platform = _normalise_docker_platform(
        args.docker_platform or os.getenv("CAPACITY_DOCKER_PLATFORM", "")
    )
    try:
        image_evidence = _normalise_image_evidence(args.image_evidence)
        _assert_formal_evidence_identity(
            commit=args.commit or os.getenv("CAPACITY_GIT_COMMIT", ""),
            commit_state=args.commit_state
            or os.getenv("CAPACITY_COMMIT_STATE", "unknown"),
            host_os=args.host_os or os.getenv("CAPACITY_HOST_OS", ""),
            host_arch=args.host_arch or os.getenv("CAPACITY_HOST_ARCH", ""),
            compose_project=args.compose_project
            or os.getenv("CAPACITY_PROJECT_NAME", ""),
            docker_platform=docker_platform,
            image_evidence=image_evidence,
        )
        _assert_base_url(args.base_url)
    except (ValueError, RuntimeError) as exc:
        identity_error = True
        runtime_error = type(exc).__name__
    identity = _evidence_identity(
        run_id,
        commit=args.commit,
        commit_state=args.commit_state,
        host_os=args.host_os,
        host_arch=args.host_arch,
        run_directory=args.run_directory,
        compose_project=args.compose_project,
        docker_platform=docker_platform,
        image_evidence=image_evidence,
    )
    # This happens before any database or HTTP work and makes stale evidence
    # impossible even when the gate raises before producing metrics.
    args.output.unlink(missing_ok=True)
    args.output.with_suffix(args.output.suffix + ".sha256").unlink(missing_ok=True)
    metrics = _empty_metrics(run_id, args.clients)
    if runtime_error is None:
        try:
            metrics = asyncio.run(_run_gate(args.base_url, args.clients, run_id=run_id))
        except Exception as exc:  # always persist this run's failed evidence
            runtime_error = type(exc).__name__
    if runtime_error:
        metrics["errors"] = [f"capacity-run:{runtime_error}"]
    failures = _evaluate(metrics, thresholds)
    if runtime_error:
        failures.insert(0, "runtime_error")
    if identity_error:
        failures.insert(0, "evidence_identity")
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "failed" if failures else "passed",
        "identity": identity,
        "commit": identity["commit"],
        "commit_state": identity["commit_state"],
        "host_os": identity["host_os"],
        "host_arch": identity["host_arch"],
        "run_directory": identity["run_directory"],
        "compose_project": identity["compose_project"],
        "docker_platform": identity["docker_platform"],
        "final_images": identity["final_images"],
        "base_url": args.base_url,
        "warmup": {
            "performed": bool(metrics.get("warmup_performed", False)),
            "measured": False,
            "errors": metrics.get("warmup_errors", []),
            "cold_start_recovery": "separate-gate",
        },
        "thresholds": asdict(thresholds),
        "metrics": metrics,
        "failed_checks": failures,
    }
    if runtime_error:
        report["runtime_error"] = runtime_error
    _write_report(args.output, report)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
