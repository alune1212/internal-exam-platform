from __future__ import annotations

import hashlib
import json
import tarfile
from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    text,
)

from app.ops import internal_backup
from app.ops.account_migration_preflight import (
    _validate_pre_upgrade_backup,
    _validate_restore_drill_evidence,
    _validate_second_copy_evidence,
    _validate_second_copy_storage_evidence,
    check_maintenance_gate,
    run_account_migration_preflight,
)


def test_destructive_migration_downgrade_is_restore_only() -> None:
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "202608110001_email_accounts_and_invited_exam_scopes.py"
    )
    spec = spec_from_file_location("email_account_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(RuntimeError, match="paired PostgreSQL/media backup"):
        module.downgrade()


@pytest.fixture
def legacy_database():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    timestamp = DateTime()
    Table(
        "candidate",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100)),
        Column("employee_no", String(100)),
        Column("department", String(100)),
        Column("position", String(100)),
        Column("phone_suffix", String(20)),
        Column("email", String(255)),
        Column("exam_group", String(100)),
        Column("should_attend", Boolean),
        Column("status", String(20)),
        Column("remark", Text),
        Column("is_login_sentinel", Boolean),
        Column("created_at", timestamp),
        Column("updated_at", timestamp),
    )
    Table(
        "exam",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    Table(
        "exam_candidate_scope",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("exam_id", Integer),
        Column("candidate_id", Integer),
    )
    Table(
        "exam_retake_grant",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("exam_id", Integer),
        Column("candidate_id", Integer),
        Column("used_at", timestamp),
    )
    Table(
        "exam_attempt",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("exam_id", Integer),
        Column("candidate_id", Integer),
        Column("status", String(20)),
    )
    Table(
        "candidate_login_challenge",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("candidate_id", Integer),
        Column("otp_hash", String(128)),
        Column("expires_at", timestamp),
        Column("consumed_at", timestamp),
    )
    metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO candidate "
                "(id, name, email, status, is_login_sentinel, should_attend, "
                "created_at, updated_at) VALUES "
                "(1, :sentinel, NULL, 'inactive', true, false, :now, :now), "
                "(2, 'Alice', 'alice@example.com', 'active', false, true, :now, :now)"
            ),
            {"sentinel": "__candidate_login_sentinel__", "now": now},
        )
        connection.execute(text("INSERT INTO exam (id) VALUES (1)"))
        connection.execute(
            text(
                "INSERT INTO exam_candidate_scope (id, exam_id, candidate_id) "
                "VALUES (1, 1, 2)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO exam_retake_grant (id, exam_id, candidate_id, used_at) "
                "VALUES (1, 1, 2, NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO exam_attempt (id, exam_id, candidate_id, status) "
                "VALUES (1, 1, 2, 'submitted')"
            )
        )
    return engine


def test_clean_legacy_data_passes_without_mutating_rows(legacy_database) -> None:
    with legacy_database.connect() as connection:
        connection.execute(
            text(
                "INSERT INTO candidate_login_challenge "
                "(id, candidate_id, otp_hash, expires_at, consumed_at) "
                "VALUES (99, 1, 'sentinel-hash', CURRENT_TIMESTAMP, NULL)"
            )
        )
        before = connection.execute(
            text("SELECT id, email, status FROM candidate ORDER BY id")
        ).all()
        challenge_before = connection.execute(
            text("SELECT id, candidate_id, consumed_at FROM candidate_login_challenge")
        ).all()
        report = run_account_migration_preflight(connection)
        after = connection.execute(
            text("SELECT id, email, status FROM candidate ORDER BY id")
        ).all()
        challenge_after = connection.execute(
            text("SELECT id, candidate_id, consumed_at FROM candidate_login_challenge")
        ).all()

    assert report.can_migrate is True
    assert report.findings == ()
    assert before == after
    assert challenge_before == challenge_after


def test_current_schema_without_sentinel_marker_is_supported() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE candidate (id INTEGER PRIMARY KEY, name VARCHAR(100), "
            "email VARCHAR(255) NOT NULL, status VARCHAR(20) NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE exam_candidate_scope (id INTEGER PRIMARY KEY, exam_id INTEGER, "
            "candidate_id INTEGER, roster_email VARCHAR(255), roster_name VARCHAR(100))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE exam_attempt (id INTEGER PRIMARY KEY, exam_id INTEGER, "
            "candidate_id INTEGER, status VARCHAR(20))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE candidate_login_challenge (id INTEGER PRIMARY KEY, "
            "candidate_id INTEGER, email VARCHAR(255) NOT NULL, "
            "consumed_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO candidate VALUES (1, 'Alice', 'alice@example.com', 'active')"
        )
        connection.exec_driver_sql(
            "INSERT INTO exam_candidate_scope VALUES "
            "(1, 1, 1, 'alice@example.com', 'Alice')"
        )
        connection.exec_driver_sql(
            "INSERT INTO candidate_login_challenge VALUES "
            "(1, NULL, 'new@example.com', NULL)"
        )
        report = run_account_migration_preflight(connection)

    assert report.can_migrate is True


@pytest.mark.parametrize(
    ("email", "code"),
    [
        (None, "account_email_missing"),
        ("not-an-email", "account_email_invalid"),
        (" Alice@Example.com ", "account_email_noncanonical"),
    ],
)
def test_account_email_blockers_are_reported_and_redacted(
    legacy_database, email: str | None, code: str
) -> None:
    with legacy_database.begin() as connection:
        connection.execute(
            text("UPDATE candidate SET email = :email WHERE id = 2"),
            {"email": email},
        )
        report = run_account_migration_preflight(connection)

    assert report.blocked is True
    assert code in {finding.code for finding in report.findings}
    serialized = report.redacted_json()
    assert "alice@example.com" not in serialized


def test_casefold_duplicate_blocks_without_merging(legacy_database) -> None:
    with legacy_database.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO candidate "
                "(id, name, email, status, is_login_sentinel, should_attend) "
                "VALUES (3, 'Bob', 'ALICE@EXAMPLE.COM', 'active', false, true)"
            )
        )
        report = run_account_migration_preflight(connection)
        ids = [
            row[0]
            for row in connection.execute(text("SELECT id FROM candidate ORDER BY id"))
        ]

    assert report.blocked is True
    assert "account_email_duplicate_casefold" in {
        finding.code for finding in report.findings
    }
    assert ids == [1, 2, 3]


def test_flagged_real_account_is_not_treated_as_deletable_sentinel(
    legacy_database,
) -> None:
    with legacy_database.begin() as connection:
        connection.execute(
            text("UPDATE candidate SET is_login_sentinel = false WHERE id = 1")
        )
        connection.execute(
            text("UPDATE candidate SET is_login_sentinel = true WHERE id = 2")
        )
        before = connection.execute(
            text("SELECT id, name, email, is_login_sentinel FROM candidate ORDER BY id")
        ).all()
        report = run_account_migration_preflight(connection)
        after = connection.execute(
            text("SELECT id, name, email, is_login_sentinel FROM candidate ORDER BY id")
        ).all()

    assert report.blocked is True
    assert "sentinel_contamination" in {finding.code for finding in report.findings}
    assert before == after
    assert any(2 in finding.row_ids for finding in report.findings)


def test_retake_grant_sentinel_reference_blocks_without_mutation(
    legacy_database,
) -> None:
    with legacy_database.begin() as connection:
        connection.execute(
            text("UPDATE exam_retake_grant SET candidate_id = 1 WHERE id = 1")
        )
        before = connection.execute(
            text("SELECT id, exam_id, candidate_id, used_at FROM exam_retake_grant")
        ).all()
        report = run_account_migration_preflight(connection)
        after = connection.execute(
            text("SELECT id, exam_id, candidate_id, used_at FROM exam_retake_grant")
        ).all()

    assert report.blocked is True
    assert before == after
    findings = [
        finding
        for finding in report.findings
        if finding.code == "sentinel_reference" and finding.table == "exam_retake_grant"
    ]
    assert len(findings) == 1
    assert findings[0].row_ids == (1,)


@pytest.mark.parametrize(
    ("statement", "code"),
    [
        (
            "UPDATE exam_candidate_scope SET candidate_id = 1",
            "sentinel_reference",
        ),
        (
            "DELETE FROM exam_candidate_scope",
            "attempt_missing_scope",
        ),
        (
            "UPDATE exam_attempt SET status = 'in_progress'",
            "formal_attempt_in_progress",
        ),
    ],
)
def test_historical_and_operational_blockers_fail_closed(
    legacy_database, statement: str, code: str
) -> None:
    with legacy_database.begin() as connection:
        connection.execute(text(statement))
        before = connection.execute(
            text("SELECT id, candidate_id, status FROM exam_attempt")
        ).all()
        report = run_account_migration_preflight(connection)
        after = connection.execute(
            text("SELECT id, candidate_id, status FROM exam_attempt")
        ).all()

    assert report.blocked is True
    assert code in {finding.code for finding in report.findings}
    assert before == after


def test_missing_scope_snapshot_blocks_and_does_not_change_challenge(
    legacy_database,
) -> None:
    with legacy_database.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO candidate_login_challenge "
                "(id, candidate_id, otp_hash, expires_at, consumed_at) "
                "VALUES (1, 2, 'hash', CURRENT_TIMESTAMP, NULL)"
            )
        )
        connection.execute(text("UPDATE candidate SET name = '   ' WHERE id = 2"))
        before = connection.execute(
            text("SELECT id, candidate_id, consumed_at FROM candidate_login_challenge")
        ).all()
        report = run_account_migration_preflight(connection)
        after = connection.execute(
            text("SELECT id, candidate_id, consumed_at FROM candidate_login_challenge")
        ).all()

    assert report.blocked is True
    assert "scope_snapshot_unavailable" in {finding.code for finding in report.findings}
    assert before == after


def _maintenance_database(*, in_progress: bool = False):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE operational_lock (name VARCHAR(100) PRIMARY KEY, "
            "owner VARCHAR(200) NOT NULL, released_at DATETIME, dataset_id VARCHAR(200), "
            "host_id VARCHAR(200), writer_generation INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE exam_attempt (id INTEGER PRIMARY KEY, status VARCHAR(20))"
        )
        connection.execute(
            text(
                "INSERT INTO operational_lock "
                "(name, owner, released_at, dataset_id, host_id, writer_generation) "
                "VALUES ('formal-writer-fence', 'host-1', NULL, 'dataset-1', 'host-1', 1), "
                "('backup-write-freeze', 'freeze-owner', NULL, NULL, NULL, NULL)"
            )
        )
        if in_progress:
            connection.execute(
                text("INSERT INTO exam_attempt (id, status) VALUES (1, 'in_progress')")
            )
    return engine


def _gate_kwargs(tmp_path: Path) -> dict[str, Any]:
    return {
        "dataset_id": "dataset-1",
        "host_id": "host-1",
        "writer_generation": 1,
        "backup_path": tmp_path / "backup",
        "second_copy_path": tmp_path / "second-copy" / "backup",
        "second_copy_encrypted": True,
        "write_freeze_owner": "freeze-owner",
    }


def _check_gate(connection, kwargs: dict[str, Any]):
    return cast("Any", check_maintenance_gate)(connection, **kwargs)


def test_maintenance_gate_blocks_identity_owner_and_in_progress_attempts(
    tmp_path,
) -> None:
    with _maintenance_database().connect() as connection:
        wrong_identity = _check_gate(
            connection, {**_gate_kwargs(tmp_path), "host_id": "other-host"}
        )
        assert wrong_identity is not None
        assert wrong_identity.code == "writer_fence_mismatch"

        wrong_owner = _check_gate(
            connection,
            {**_gate_kwargs(tmp_path), "write_freeze_owner": "other-owner"},
        )
        assert wrong_owner is not None
        assert wrong_owner.code == "write_freeze_owner_mismatch"

    with _maintenance_database(in_progress=True).connect() as connection:
        in_progress = _check_gate(connection, _gate_kwargs(tmp_path))
        assert in_progress is not None
        assert in_progress.code == "formal_attempt_in_progress"


def test_maintenance_gate_requires_encrypted_second_copy_and_owner(tmp_path) -> None:
    with _maintenance_database().connect() as connection:
        missing_owner = _check_gate(
            connection,
            {**_gate_kwargs(tmp_path), "write_freeze_owner": None},
        )
        assert missing_owner is not None
        assert missing_owner.code == "write_freeze_owner_missing"

        unencrypted = _check_gate(
            connection,
            {**_gate_kwargs(tmp_path), "second_copy_encrypted": False},
        )
        assert unencrypted is not None
        assert unencrypted.code == "second_copy_not_encrypted"


def _write_backup_bundle(path: Path, *, backup_kind: str = "pre-upgrade") -> Path:
    path.mkdir(parents=True)
    (path / "database.dump").write_bytes(b"database")
    with tarfile.open(path / "learning_media.tar.gz", "w:gz"):
        pass
    manifest = {
        "format_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "migration_head": "202608070001",
        "table_counts": {
            "candidate": 1,
            "question": 0,
            "exam": 1,
            "exam_attempt": 0,
            "learning_video": 0,
        },
        "media_file_count": 0,
        "backup_kind": backup_kind,
        "dataset_id": "dataset-1",
        "source_host_id": "host-1",
        "writer_generation": 1,
    }
    (path / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = []
    for filename in ("database.dump", "learning_media.tar.gz", "manifest.json"):
        digest = hashlib.sha256((path / filename).read_bytes()).hexdigest()
        rows.append(f"{digest}  {filename}\n")
    (path / "SHA256SUMS").write_text("".join(rows), encoding="ascii")
    (path / "SUCCESS").write_text("ok\n", encoding="ascii")
    return path


def _write_checksummed_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )


def test_pre_upgrade_backup_rejects_wrong_kind_checksum_and_success(
    tmp_path, monkeypatch
) -> None:
    backup = _write_backup_bundle(tmp_path / "backup")
    with pytest.raises(internal_backup.BackupValidationError):
        _validate_pre_upgrade_backup(
            _write_backup_bundle(tmp_path / "wrong-kind", backup_kind="cutover"),
            dataset_id="dataset-1",
            host_id="host-1",
            writer_generation=1,
        )

    (backup / "database.dump").write_bytes(b"tampered")
    with pytest.raises(internal_backup.BackupValidationError):
        _validate_pre_upgrade_backup(
            backup,
            dataset_id="dataset-1",
            host_id="host-1",
            writer_generation=1,
        )

    restored = _write_backup_bundle(tmp_path / "bad-success")
    (restored / "SUCCESS").write_text("failed\n", encoding="ascii")
    with pytest.raises(internal_backup.BackupValidationError):
        _validate_pre_upgrade_backup(
            restored,
            dataset_id="dataset-1",
            host_id="host-1",
            writer_generation=1,
        )

    monkeypatch.setattr(
        internal_backup,
        "validate_backup",
        lambda *_args, **_kwargs: {
            "backup_kind": "cutover",
            "dataset_id": "dataset-1",
            "source_host_id": "host-1",
            "writer_generation": 1,
        },
    )
    with pytest.raises(ValueError, match="pre-upgrade backup"):
        _validate_pre_upgrade_backup(
            tmp_path / "not-read",
            dataset_id="dataset-1",
            host_id="host-1",
            writer_generation=1,
        )


def test_checksummed_sync_storage_and_restore_evidence_reject_stale_or_tampered(
    tmp_path,
) -> None:
    now = datetime.now(UTC).isoformat()
    backup = _write_backup_bundle(tmp_path / "backup")
    second_copy = _write_backup_bundle(tmp_path / "second-copy" / backup.name)
    (second_copy.parent / ".internal-exam-encrypted-storage").write_text(
        "encrypted\n", encoding="ascii"
    )
    sync_evidence = backup.parent / f"{backup.name}.second-copy.json"
    _write_checksummed_json(
        sync_evidence,
        {
            "status": "passed",
            "kind": "second-copy-sync",
            "backup_id": backup.name,
            "artifact_id": second_copy.name,
            "checked_at": now,
        },
    )
    _validate_second_copy_evidence(backup, second_copy)
    sync_evidence.write_text(sync_evidence.read_text(encoding="utf-8") + "tamper")
    with pytest.raises(ValueError, match="checksum"):
        _validate_second_copy_evidence(backup, second_copy)

    storage = tmp_path / "storage.json"
    _write_checksummed_json(
        storage,
        {
            "status": "passed",
            "hostId": "host-1",
            "path": str(second_copy.parent),
            "mounted": True,
            "encrypted": True,
            "writable": True,
            "distinctPhysicalDevice": True,
            "deviceId": "/dev/disk2s1",
            "wholeDeviceId": "/dev/disk2",
            "formalWholeDeviceId": "/dev/disk1",
            "checkedAt": now,
        },
    )
    _validate_second_copy_storage_evidence(
        storage, second_copy_path=second_copy, host_id="host-1"
    )
    stale_storage = json.loads(storage.read_text(encoding="utf-8"))
    stale_storage["checkedAt"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    _write_checksummed_json(storage, stale_storage)
    with pytest.raises(ValueError, match="stale"):
        _validate_second_copy_storage_evidence(
            storage, second_copy_path=second_copy, host_id="host-1"
        )

    restore = tmp_path / "restore.json"
    manifest_digest = hashlib.sha256(
        (backup / "manifest.json").read_bytes()
    ).hexdigest()
    _write_checksummed_json(
        restore,
        {
            "status": "passed",
            "kind": "second-copy-restore-drill",
            "backupId": backup.name,
            "datasetId": "dataset-1",
            "hostId": "host-1",
            "writerGeneration": 1,
            "formalProjectChanged": False,
            "hostOS": "darwin",
            "architecture": "arm64",
            "sourceBackupManifestSha256": manifest_digest,
            "checkedAt": now,
        },
    )
    _validate_restore_drill_evidence(
        restore,
        backup_path=backup,
        dataset_id="dataset-1",
        host_id="host-1",
        writer_generation=1,
    )
    wrong_restore = json.loads(restore.read_text(encoding="utf-8"))
    wrong_restore["backupId"] = "other-backup"
    _write_checksummed_json(restore, wrong_restore)
    with pytest.raises(ValueError, match="identity"):
        _validate_restore_drill_evidence(
            restore,
            backup_path=backup,
            dataset_id="dataset-1",
            host_id="host-1",
            writer_generation=1,
        )
    stale_restore = json.loads(restore.read_text(encoding="utf-8"))
    stale_restore["backupId"] = backup.name
    stale_restore["checkedAt"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    _write_checksummed_json(restore, stale_restore)
    with pytest.raises(ValueError, match="stale"):
        _validate_restore_drill_evidence(
            restore,
            backup_path=backup,
            dataset_id="dataset-1",
            host_id="host-1",
            writer_generation=1,
        )
