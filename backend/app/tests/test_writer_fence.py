import io
import json
import tarfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auto_submit_worker import process_due_attempts
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_candidate_token
from app.main import create_app
from app.models import AdminAuditEvent, ExamAttempt, ImportBatch, OperationalLock
from app.ops import internal_backup
from app.ops.operational_lock import _build_parser
from app.schemas.question import QuestionCreate, QuestionOptionBase
from app.services import backup_service, question_service
from app.services.backup_service import data_change_fingerprint
from app.services.operational_lock_service import (
    BACKUP_WRITE_FREEZE,
    FORMAL_WRITER_FENCE,
    WriterFenceActiveError,
    WriterFenceConflictError,
    acquire_fenced_backup_write_freeze,
    acquire_writer_fence,
    assert_writer_fence_clear,
    inspect_writer_fence,
    release_writer_fence,
    transfer_writer_fence,
)
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)


def _build_api_client(db: Session) -> TestClient:
    api_app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    api_app.dependency_overrides[get_db] = override_get_db
    return TestClient(api_app)


def test_writer_fence_cli_contract_accepts_acquire_release_and_inspect() -> None:
    parser = _build_parser()
    acquire = parser.parse_args(
        [
            "acquire",
            "--datasetId",
            "formal-dataset-1",
            "--hostId",
            "host-a",
            "--writerGeneration",
            "1",
            "--reason",
            "cutover",
        ]
    )
    release = parser.parse_args(
        [
            "release",
            "--dataset-id",
            "formal-dataset-1",
            "--host-id",
            "host-a",
            "--writer-generation",
            "1",
        ]
    )
    inspect = parser.parse_args(["inspect"])
    transfer = parser.parse_args(
        [
            "accept",
            "--datasetId",
            "formal-dataset-1",
            "--sourceHostId",
            "host-a",
            "--sourceWriterGeneration",
            "1",
            "--targetHostId",
            "host-b",
            "--targetWriterGeneration",
            "2",
            "--reason",
            "restored-target",
        ]
    )
    assert acquire.action == "acquire"
    assert acquire.writer_generation == 1
    assert release.action == "release"
    assert inspect.action == "inspect"
    assert transfer.action == "accept"
    assert transfer.target_writer_generation == 2
    assert transfer.restored_cutover_backup is None
    transfer_with_artifact = parser.parse_args(
        [
            "transfer-fence",
            "--dataset-id",
            "formal-dataset-1",
            "--source-host-id",
            "host-a",
            "--source-writer-generation",
            "1",
            "--target-host-id",
            "host-b",
            "--target-writer-generation",
            "2",
            "--reason",
            "restored-target",
            "--restored-cutover-backup",
            "/portable/backups/backup-20260807T100000Z",
        ]
    )
    assert transfer_with_artifact.restored_cutover_backup.endswith(
        "backup-20260807T100000Z"
    )
    container = internal_backup._build_parser().parse_args(
        [
            "container-backup",
            "--dataset-id",
            "formal-dataset-1",
            "--source-host-id",
            "host-a",
            "--writer-generation",
            "1",
            "--kind",
            "cutover",
            "--under-writer-fence",
        ]
    )
    assert container.under_writer_fence is True


def test_writer_fence_is_persistent_monotonic_and_owned(db: Session) -> None:
    now = datetime(2026, 8, 7, 8, tzinfo=UTC)
    acquired = acquire_writer_fence(
        db,
        dataset_id="formal-dataset-1",
        host_id="host-a",
        writer_generation=1,
        reason="paired-backup-cutover",
        ttl_seconds=600,
        now=now,
    )
    db.commit()
    assert acquired.writer_generation == 1

    inspected = inspect_writer_fence(db, now=now + timedelta(seconds=1))
    assert inspected["active"] is True
    assert inspected["datasetId"] == "formal-dataset-1"
    assert inspected["hostId"] == "host-a"
    assert inspected["writerGeneration"] == 1
    assert inspected["reason"] == "paired-backup-cutover"
    assert db.get(OperationalLock, FORMAL_WRITER_FENCE) is not None

    with pytest.raises(WriterFenceConflictError):
        acquire_writer_fence(
            db,
            dataset_id="formal-dataset-1",
            host_id="host-b",
            writer_generation=2,
            reason="stale-host",
            now=now + timedelta(seconds=2),
        )
    db.rollback()

    release_writer_fence(
        db,
        host_id="host-a",
        dataset_id="formal-dataset-1",
        writer_generation=1,
        now=now + timedelta(seconds=3),
    )
    db.commit()

    with pytest.raises(WriterFenceConflictError):
        acquire_writer_fence(
            db,
            dataset_id="formal-dataset-1",
            host_id="host-b",
            writer_generation=1,
            reason="replay",
            now=now + timedelta(seconds=4),
        )
    db.rollback()

    with pytest.raises(WriterFenceConflictError):
        acquire_writer_fence(
            db,
            dataset_id="formal-dataset-1",
            host_id="host-b",
            writer_generation=2,
            reason="target-host-cutover",
            now=now + timedelta(seconds=5),
        )
    db.commit()
    same_fence = acquire_writer_fence(
        db,
        dataset_id="formal-dataset-1",
        host_id="host-a",
        writer_generation=1,
        reason="next-prepare",
        now=now + timedelta(seconds=6),
    )
    db.commit()
    assert same_fence.host_id == "host-a"
    assert same_fence.writer_generation == 1


def test_writer_fence_expiry_never_reopens_and_current_generation_can_reacquire(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "internal")
    now = datetime(2026, 8, 7, 8, tzinfo=UTC)
    acquire_writer_fence(
        db,
        dataset_id="persistent-dataset",
        host_id="host-a",
        writer_generation=1,
        reason="prepare",
        ttl_seconds=1,
        now=now,
    )
    db.commit()

    with pytest.raises(WriterFenceActiveError):
        assert_writer_fence_clear(db, now=now + timedelta(seconds=2))
    db.rollback()
    assert inspect_writer_fence(db, now=now + timedelta(seconds=2))["active"] is True

    release_writer_fence(
        db,
        host_id="host-a",
        dataset_id="persistent-dataset",
        writer_generation=1,
        now=now + timedelta(seconds=3),
    )
    db.commit()
    reacquired = acquire_writer_fence(
        db,
        dataset_id="persistent-dataset",
        host_id="host-a",
        writer_generation=1,
        reason="next-prepare",
        now=now + timedelta(seconds=4),
    )
    db.commit()
    assert reacquired.writer_generation == 1


def test_writer_fence_transfer_is_atomic_and_source_cannot_reopen(
    db: Session,
) -> None:
    now = datetime(2026, 8, 7, 9, tzinfo=UTC)
    acquire_writer_fence(
        db,
        dataset_id="transfer-dataset",
        host_id="source-host",
        writer_generation=7,
        reason="prepare",
        ttl_seconds=1,
        now=now,
    )
    db.commit()

    transferred = transfer_writer_fence(
        db,
        dataset_id="transfer-dataset",
        source_host_id="source-host",
        source_writer_generation=7,
        target_host_id="target-host",
        target_writer_generation=8,
        reason="target-accepted",
        now=now + timedelta(seconds=2),
    )
    db.commit()
    assert transferred.host_id == "target-host"
    assert transferred.writer_generation == 8
    assert inspect_writer_fence(db, now=now + timedelta(days=1))["active"] is True

    with pytest.raises(WriterFenceConflictError):
        release_writer_fence(
            db,
            host_id="source-host",
            dataset_id="transfer-dataset",
            writer_generation=7,
        )
    db.rollback()
    with pytest.raises(WriterFenceConflictError):
        transfer_writer_fence(
            db,
            dataset_id="transfer-dataset",
            source_host_id="source-host",
            source_writer_generation=7,
            target_host_id="other-target",
            target_writer_generation=8,
            reason="replay",
        )
    db.rollback()

    release_writer_fence(
        db,
        host_id="target-host",
        dataset_id="transfer-dataset",
        writer_generation=8,
    )
    db.commit()
    for stale_generation in (7, 8, 9):
        with pytest.raises(WriterFenceConflictError):
            acquire_writer_fence(
                db,
                dataset_id="transfer-dataset",
                host_id="source-host",
                writer_generation=stale_generation,
                reason="stale-source",
            )
        db.rollback()
    reacquired = acquire_writer_fence(
        db,
        dataset_id="transfer-dataset",
        host_id="target-host",
        writer_generation=8,
        reason="reverse-prepare",
    )
    db.commit()
    assert reacquired.host_id == "target-host"


def _acquire_source_fence_with_backup_lock(
    db: Session, *, now: datetime, ttl_seconds: int = 1
) -> None:
    acquire_writer_fence(
        db,
        dataset_id="transfer-dataset",
        host_id="source-host",
        writer_generation=7,
        reason="prepare",
        now=now,
    )
    acquire_fenced_backup_write_freeze(
        db,
        owner="backup-operator",
        dataset_id="transfer-dataset",
        host_id="source-host",
        writer_generation=7,
        ttl_seconds=ttl_seconds,
        now=now,
    )
    db.commit()


def test_writer_fence_transfer_releases_restored_stale_backup_lock_atomically(
    db: Session, tmp_path
) -> None:
    now = datetime(2026, 8, 7, 9, tzinfo=UTC)
    _acquire_source_fence_with_backup_lock(db, now=now, ttl_seconds=1)
    artifact = _create_fenced_backup(
        tmp_path,
        dataset_id="transfer-dataset",
        host_id="source-host",
        writer_generation=7,
    )

    transferred = transfer_writer_fence(
        db,
        dataset_id="transfer-dataset",
        source_host_id="source-host",
        source_writer_generation=7,
        target_host_id="target-host",
        target_writer_generation=8,
        reason="target-accepted",
        now=now + timedelta(days=1),
        restored_cutover_backup=artifact,
    )
    db.commit()

    backup_lock = db.get(OperationalLock, BACKUP_WRITE_FREEZE)
    assert backup_lock is not None
    assert backup_lock.released_at is not None
    assert backup_lock.released_at.replace(tzinfo=UTC) == now + timedelta(days=1)
    assert transferred.host_id == "target-host"
    assert transferred.writer_generation == 8


def test_writer_fence_transfer_rejects_source_in_flight_without_artifact(
    db: Session,
) -> None:
    now = datetime(2026, 8, 7, 9, tzinfo=UTC)
    _acquire_source_fence_with_backup_lock(db, now=now, ttl_seconds=3600)

    with pytest.raises(WriterFenceConflictError, match="restored-cutover-backup"):
        transfer_writer_fence(
            db,
            dataset_id="transfer-dataset",
            source_host_id="source-host",
            source_writer_generation=7,
            target_host_id="target-host",
            target_writer_generation=8,
            reason="target-accepted",
            now=now + timedelta(seconds=2),
        )
    db.rollback()
    assert inspect_writer_fence(db)["hostId"] == "source-host"
    backup_lock = db.get(OperationalLock, BACKUP_WRITE_FREEZE)
    assert backup_lock is not None
    assert backup_lock.released_at is None


@pytest.mark.parametrize("artifact_case", ["wrong", "incomplete", "stale"])
def test_writer_fence_transfer_rejects_invalid_restored_cutover_artifact(
    db: Session, tmp_path, artifact_case: str
) -> None:
    now = datetime(2026, 8, 7, 9, tzinfo=UTC)
    _acquire_source_fence_with_backup_lock(db, now=now, ttl_seconds=3600)
    artifact_dataset = (
        "wrong-dataset" if artifact_case == "wrong" else "transfer-dataset"
    )
    artifact_generation = 6 if artifact_case == "stale" else 7
    artifact = _create_fenced_backup(
        tmp_path,
        dataset_id=artifact_dataset,
        host_id="source-host",
        writer_generation=artifact_generation,
    )
    if artifact_case == "incomplete":
        (artifact / internal_backup.SUCCESS_MARKER_NAME).unlink()

    with pytest.raises(WriterFenceConflictError, match="restored cutover backup"):
        transfer_writer_fence(
            db,
            dataset_id="transfer-dataset",
            source_host_id="source-host",
            source_writer_generation=7,
            target_host_id="target-host",
            target_writer_generation=8,
            reason="target-accepted",
            restored_cutover_backup=artifact,
        )
    db.rollback()
    assert inspect_writer_fence(db)["hostId"] == "source-host"
    backup_lock = db.get(OperationalLock, BACKUP_WRITE_FREEZE)
    assert backup_lock is not None
    assert backup_lock.released_at is None


@pytest.mark.parametrize(
    ("dataset_id", "host_id", "writer_generation"),
    [
        ("wrong-dataset", "source-host", 7),
        ("transfer-dataset", "wrong-host", 7),
        ("transfer-dataset", "source-host", 6),
    ],
)
def test_writer_fence_transfer_rejects_wrong_identity_without_mutation(
    db: Session, dataset_id: str, host_id: str, writer_generation: int
) -> None:
    acquire_writer_fence(
        db,
        dataset_id="transfer-dataset",
        host_id="source-host",
        writer_generation=7,
        reason="prepare",
    )
    db.commit()
    with pytest.raises(WriterFenceConflictError):
        transfer_writer_fence(
            db,
            dataset_id=dataset_id,
            source_host_id=host_id,
            source_writer_generation=writer_generation,
            target_host_id="target-host",
            target_writer_generation=writer_generation + 1,
            reason="reject",
        )
    db.rollback()
    inspected = inspect_writer_fence(db)
    assert inspected["hostId"] == "source-host"
    assert inspected["writerGeneration"] == 7


def _create_fenced_backup(
    output_root,
    *,
    dataset_id: str,
    host_id: str,
    writer_generation: int,
    backup_kind: str = "cutover",
):
    backup_dir = output_root / "backup-20260807T100000Z"
    backup_dir.mkdir()
    (backup_dir / internal_backup.DATABASE_DUMP_NAME).write_bytes(b"database")
    with tarfile.open(
        backup_dir / internal_backup.MEDIA_ARCHIVE_NAME, "w:gz"
    ) as archive:
        content = b"media"
        member = tarfile.TarInfo("learning/video.mp4")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    manifest: dict[str, object] = {
        "format_version": 1,
        "created_at": "2026-08-07T10:00:00+00:00",
        "migration_head": "test-head",
        "table_counts": dict.fromkeys(internal_backup.TABLE_NAMES, 0),
        "media_file_count": 1,
        "dataset_id": dataset_id,
        "source_host_id": host_id,
        "writer_generation": writer_generation,
        "backup_kind": backup_kind,
    }
    if backup_kind == internal_backup.CUTOVER_BACKUP_KIND:
        manifest["writer_fence_boundary"] = {
            "dataset_id": dataset_id,
            "source_host_id": host_id,
            "writer_generation": writer_generation,
        }
    internal_backup.finalize_backup(backup_dir, manifest)
    return backup_dir


def test_fenced_final_backup_requires_owner_and_records_boundary(
    db: Session, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "internal")
    acquire_writer_fence(
        db,
        dataset_id="backup-dataset",
        host_id="source-host",
        writer_generation=7,
        reason="prepare",
    )
    db.commit()
    media_root = tmp_path / "media"
    media_root.mkdir()
    output_root = tmp_path / "output"

    result = backup_service.run_paired_backup(
        db,
        output_root=output_root,
        media_root=media_root,
        create_backup=lambda _fingerprint: _create_fenced_backup(
            output_root,
            dataset_id="backup-dataset",
            host_id="source-host",
            writer_generation=7,
        ),
        owner="backup-operator",
        opportunistic=False,
        fence_dataset_id="backup-dataset",
        fence_host_id="source-host",
        fence_writer_generation=7,
        under_writer_fence=True,
        backup_kind="cutover",
    )
    assert result.status == "passed"
    assert result.fence_boundary == {
        "dataset_id": "backup-dataset",
        "source_host_id": "source-host",
        "writer_generation": 7,
    }
    evidence = result.evidence_path.read_text(encoding="utf-8")
    assert '"writer_fence_boundary"' in evidence
    assert db.get(OperationalLock, "backup-write-freeze") is not None
    assert inspect_writer_fence(db)["active"] is True


def test_normal_identity_backup_uses_regular_freeze_without_fence_flag(
    db: Session, tmp_path
) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    output_root = tmp_path / "output"
    result = backup_service.run_paired_backup(
        db,
        output_root=output_root,
        media_root=media_root,
        create_backup=lambda _fingerprint: _create_fenced_backup(
            output_root,
            dataset_id="portable-dataset",
            host_id="source-host",
            writer_generation=3,
            backup_kind="daily",
        ),
        owner="backup-operator",
        opportunistic=False,
        # Portability identity is carried in the manifest but does not grant
        # the exceptional owner path without the explicit flag.
        fence_dataset_id="portable-dataset",
        fence_host_id="source-host",
        fence_writer_generation=3,
    )
    assert result.status == "passed"
    assert result.fence_boundary is None


def test_normal_backup_fence_race_reports_non_db_skip_after_artifact_passes(
    db: Session, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fence that appears during finalization must not mask the artifact."""

    monkeypatch.setattr(settings, "environment", "internal")
    media_root = tmp_path / "media"
    media_root.mkdir()
    output_root = tmp_path / "output"
    original_record = backup_service.record_admin_event

    def acquire_fence_before_audit(db: Session, **kwargs):
        if kwargs["action"] == "paired_backup_passed":
            acquire_writer_fence(
                db,
                dataset_id="race-dataset",
                host_id="race-host",
                writer_generation=1,
                reason="finalize-race",
            )
            # Model the adversarial ordering explicitly: the fence commits
            # only after the backup-lock release transaction has become
            # visible, before the audit call can finish.
            db.commit()
        return original_record(db, **kwargs)

    monkeypatch.setattr(
        backup_service, "record_admin_event", acquire_fence_before_audit
    )
    result = backup_service.run_paired_backup(
        db,
        output_root=output_root,
        media_root=media_root,
        create_backup=lambda _fingerprint: _create_fenced_backup(
            output_root,
            dataset_id="portable-dataset",
            host_id="source-host",
            writer_generation=3,
            backup_kind="daily",
        ),
        owner="backup-operator",
        opportunistic=False,
    )

    assert result.status == "skipped"
    assert result.reason == "writer-fence-active-before-audit"
    assert result.backup_id == "backup-20260807T100000Z"
    assert result.evidence_path.is_file()
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert evidence["status"] == "skipped"
    assert evidence["reason"] == "writer-fence-active-before-audit"
    assert db.query(AdminAuditEvent).count() == 0
    backup_lock = db.get(OperationalLock, BACKUP_WRITE_FREEZE)
    assert backup_lock is not None
    assert backup_lock.released_at is not None
    assert inspect_writer_fence(db)["active"] is True


def test_fenced_final_backup_without_active_matching_fence_is_blocked(
    db: Session, tmp_path
) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    output_root = tmp_path / "output"
    called = False

    def create(_fingerprint):
        nonlocal called
        called = True
        return _create_fenced_backup(
            output_root,
            dataset_id="portable-dataset",
            host_id="source-host",
            writer_generation=3,
        )

    result = backup_service.run_paired_backup(
        db,
        output_root=output_root,
        media_root=media_root,
        create_backup=create,
        owner="backup-operator",
        opportunistic=False,
        fence_dataset_id="portable-dataset",
        fence_host_id="source-host",
        fence_writer_generation=3,
        under_writer_fence=True,
        backup_kind="cutover",
    )
    assert result.status == "skipped"
    assert result.reason == "writer-fence-owner-mismatch"
    assert called is False


@pytest.mark.parametrize(
    ("fence_dataset_id", "fence_host_id", "fence_writer_generation"),
    [
        ("wrong-dataset", "source-host", 7),
        ("backup-dataset", "wrong-host", 7),
        ("backup-dataset", "source-host", 6),
    ],
)
def test_fenced_final_backup_rejects_wrong_owner_identity(
    db: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fence_dataset_id: str,
    fence_host_id: str,
    fence_writer_generation: int,
) -> None:
    monkeypatch.setattr(settings, "environment", "internal")
    acquire_writer_fence(
        db,
        dataset_id="backup-dataset",
        host_id="source-host",
        writer_generation=7,
        reason="prepare",
    )
    db.commit()
    output_root = tmp_path / "output"
    media_root = tmp_path / "media"
    media_root.mkdir()
    called = False

    def create(_fingerprint):
        nonlocal called
        called = True
        return _create_fenced_backup(
            output_root,
            dataset_id="backup-dataset",
            host_id="source-host",
            writer_generation=7,
        )

    result = backup_service.run_paired_backup(
        db,
        output_root=output_root,
        media_root=media_root,
        create_backup=create,
        owner="backup-operator",
        opportunistic=False,
        fence_dataset_id=fence_dataset_id,
        fence_host_id=fence_host_id,
        fence_writer_generation=fence_writer_generation,
        under_writer_fence=True,
        backup_kind="cutover",
    )
    assert result.status == "skipped"
    assert result.reason == "writer-fence-owner-mismatch"
    assert called is False


def test_backup_fingerprint_tracks_audit_and_import_metadata(
    db: Session, tmp_path
) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    before = data_change_fingerprint(db, media_root)
    db.add(
        AdminAuditEvent(
            operator_subject="operator",
            action="import_completed",
            target_type="import",
            result="success",
            metadata_json={},
            created_at=datetime.now(UTC),
        )
    )
    db.add(
        ImportBatch(
            import_type="question",
            file_name="questions.xlsx",
            total_count=1,
            success_count=1,
            failed_count=0,
            status="completed",
            error_report=[],
        )
    )
    db.commit()
    after = data_change_fingerprint(db, media_root)
    assert after != before


def test_development_writer_fence_does_not_change_existing_write_behavior(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    acquire_writer_fence(
        db,
        dataset_id="dev-dataset",
        host_id="dev-host",
        writer_generation=1,
        reason="test",
    )
    db.commit()

    assert_writer_fence_clear(db)


def test_internal_writer_fence_blocks_admin_mutation_before_rows_change(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "internal")
    acquire_writer_fence(
        db,
        dataset_id="formal-dataset-1",
        host_id="host-a",
        writer_generation=3,
        reason="restore-cutover",
    )
    db.commit()

    with pytest.raises(WriterFenceActiveError):
        question_service.create_question(
            db,
            QuestionCreate(
                question_type="single",
                stem="blocked",
                score=1,
                status="active",
                options=[
                    QuestionOptionBase(
                        label="A", content="A", is_correct=True, sort_order=0
                    ),
                    QuestionOptionBase(
                        label="B", content="B", is_correct=False, sort_order=1
                    ),
                ],
            ),
        )
    db.rollback()
    assert db.query(OperationalLock).filter_by(name="formal-writer-fence").count() == 1


def test_auto_submit_worker_is_silent_during_writer_fence(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "internal")
    exam = create_exam(db, status="active")
    candidate = create_candidate(db)
    now = datetime.now(UTC)
    attempt = ExamAttempt(
        exam_id=exam.id,
        candidate_id=candidate.id,
        status="in_progress",
        started_at=now - timedelta(minutes=2),
        ends_at=now - timedelta(minutes=1),
        duration_minutes_snapshot=1,
        total_score=1,
    )
    db.add(attempt)
    db.commit()
    acquire_writer_fence(
        db,
        dataset_id="formal-dataset-1",
        host_id="host-a",
        writer_generation=4,
        reason="formal-cutover",
    )
    db.commit()

    assert process_due_attempts(db, now=now) == 0
    db.refresh(attempt)
    assert attempt.status == "in_progress"


def test_writer_fence_api_blocks_writes_but_keeps_health_and_reads_available(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = create_candidate(db, name="栅栏读取人")
    question = create_question_with_options(db, stem="栅栏期间仍可读")
    monkeypatch.setattr(settings, "environment", "internal")
    acquire_writer_fence(
        db,
        dataset_id="formal-dataset-1",
        host_id="host-a",
        writer_generation=5,
        reason="formal-cutover",
    )
    db.commit()

    client = _build_api_client(db)
    health = client.get("/api/health")
    assert health.status_code == 200
    readable = client.get(
        "/api/practice/questions",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )
    assert readable.status_code == 200
    assert readable.json()["data"][0]["id"] == question.id

    blocked = client.post(
        "/api/candidates/login",
        json={"name": candidate.name, "email": candidate.email},
    )
    assert blocked.status_code == 409
    assert "写栅栏" in blocked.json()["detail"]
