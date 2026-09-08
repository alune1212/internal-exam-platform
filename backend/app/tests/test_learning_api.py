from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import _sign, create_candidate_token, create_session_token
from app.main import create_app
from app.models import (
    Candidate,
    ExamAttempt,
    ExamCandidateScope,
    LearningVideo,
    LearningVideoProgress,
)
from app.services.learning_service import MAX_WATCHED_INTERVALS
from app.services.operational_lock_service import acquire_backup_write_freeze
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
)


def _build_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_local()
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), db


def _admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": create_session_token(settings.admin_username)}


def _candidate_headers(candidate_id: int) -> dict[str, str]:
    return {"X-Candidate-Token": create_candidate_token(candidate_id)}


def _upload_video(
    client: TestClient,
    *,
    title: str = "安全培训",
    filename: str = "training.mp4",
    content_type: str = "video/mp4",
    duration_seconds: int = 100,
) -> dict:
    response = client.post(
        "/api/admin/learning/videos",
        headers=_admin_headers(),
        data={"title": title, "duration_seconds": str(duration_seconds)},
        files={"file": (filename, b"video-bytes", content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_admin_upload_learning_video_generates_storage_key() -> None:
    client, db = _build_client()

    video = _upload_video(client)

    assert video["title"] == "安全培训"
    assert video["original_filename"] == "training.mp4"
    assert video["content_type"] == "video/mp4"
    assert video["file_size_bytes"] == len(b"video-bytes")
    assert video["completion_threshold_percent"] == 90
    assert video["status"] == "draft"
    assert video["storage_key"] != "training.mp4"
    assert video["playback_url"] == ""
    assert (db.query(LearningVideo).one()).storage_key == video["storage_key"]


def test_admin_upload_rejects_invalid_video_file() -> None:
    client, db = _build_client()

    response = client.post(
        "/api/admin/learning/videos",
        headers=_admin_headers(),
        data={"title": "安全培训", "duration_seconds": "100"},
        files={"file": ("training.txt", b"not-video", "text/plain")},
    )

    assert response.status_code == 400
    assert db.query(LearningVideo).count() == 0


def test_formal_attempt_blocks_video_upload_before_media_or_row_persistence() -> None:
    client, db = _build_client()
    exam = create_exam(db)
    candidate = create_candidate(db)
    now = datetime.now(UTC)
    db.add(
        ExamAttempt(
            exam_id=exam.id,
            candidate_id=candidate.id,
            status="in_progress",
            started_at=now,
            ends_at=now + timedelta(hours=1),
            duration_minutes_snapshot=60,
        )
    )
    db.commit()

    response = client.post(
        "/api/admin/learning/videos",
        headers=_admin_headers(),
        data={"title": "考试中禁止上传", "duration_seconds": "100"},
        files={"file": ("blocked.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 409
    assert "正式考试" in response.json()["detail"]
    assert db.query(LearningVideo).count() == 0


def test_backup_freeze_blocks_progress_but_keeps_video_reads_available() -> None:
    client, db = _build_client()
    video = _upload_video(client)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    candidate = create_candidate(db)
    acquire_backup_write_freeze(db, owner="api-backup", ttl_seconds=600)
    db.commit()

    listed = client.get(
        "/api/learning/videos", headers=_candidate_headers(candidate.id)
    )
    progress = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=_candidate_headers(candidate.id),
        json={
            "current_position_seconds": 10,
            "watched_start_seconds": 0,
            "watched_end_seconds": 10,
        },
    )

    assert listed.status_code == 200
    assert progress.status_code == 409
    assert "配对备份" in progress.json()["detail"]


def test_candidate_learning_videos_require_active_candidate_token() -> None:
    client, db = _build_client()
    video = _upload_video(client)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    inactive = Candidate(
        name="停用人员", email="inactive@example.com", status="inactive"
    )
    db.add(inactive)
    db.commit()

    missing_token = client.get("/api/learning/videos")
    inactive_token = client.get(
        "/api/learning/videos", headers=_candidate_headers(inactive.id)
    )

    assert missing_token.status_code == 401
    assert inactive_token.status_code == 401


def test_candidate_sees_only_published_learning_videos() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习人员", status="active")
    draft = _upload_video(client, title="草稿视频")
    published = _upload_video(client, title="公开视频")
    archived = _upload_video(client, title="归档视频")
    client.post(
        f"/api/admin/learning/videos/{published['id']}/publish",
        headers=_admin_headers(),
    )
    client.post(
        f"/api/admin/learning/videos/{archived['id']}/archive",
        headers=_admin_headers(),
    )

    response = client.get(
        "/api/learning/videos", headers=_candidate_headers(candidate.id)
    )

    assert response.status_code == 200
    titles = [row["title"] for row in response.json()["data"]]
    assert titles == ["公开视频"]
    assert draft["title"] not in titles
    assert archived["title"] not in titles


def test_candidate_learning_videos_paginate_and_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习分页人员")
    videos = [_upload_video(client, title=f"公开视频 {index}") for index in range(3)]
    for video in videos:
        client.post(
            f"/api/admin/learning/videos/{video['id']}/publish",
            headers=_admin_headers(),
        )
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)

    page = client.get(
        "/api/learning/videos",
        params={"limit": 1, "offset": 1},
        headers=_candidate_headers(candidate.id),
    )
    limited = client.get(
        "/api/learning/videos",
        params={"limit": 1, "offset": 1},
        headers=_candidate_headers(candidate.id),
    )

    assert page.status_code == 200
    assert [item["id"] for item in page.json()["data"]] == [videos[1]["id"]]
    assert limited.status_code == 429


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 2**31}],
)
def test_candidate_learning_videos_reject_invalid_pagination(
    params: dict[str, int],
) -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习分页校验人员")

    response = client.get(
        "/api/learning/videos",
        params=params,
        headers=_candidate_headers(candidate.id),
    )

    assert response.status_code == 422


def test_learning_progress_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习限流人员")
    video = _upload_video(client, duration_seconds=100)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    monkeypatch.setattr(settings, "public_token_rate_limit_count", 1)
    payload = {
        "current_position_seconds": 10,
        "watched_start_seconds": 0,
        "watched_end_seconds": 10,
    }

    first = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=_candidate_headers(candidate.id),
        json=payload,
    )
    limited = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=_candidate_headers(candidate.id),
        json=payload,
    )

    assert first.status_code == 200
    assert limited.status_code == 429


def test_learning_progress_rejects_over_interval_cap_without_mutating_row() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习区间上限人员")
    duration = MAX_WATCHED_INTERVALS * 2 + 2
    video = _upload_video(client, duration_seconds=duration)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    intervals = [
        {"start": index * 2, "end": index * 2 + 1}
        for index in range(MAX_WATCHED_INTERVALS)
    ]
    progress = LearningVideoProgress(
        candidate_id=candidate.id,
        video_id=video["id"],
        last_position_seconds=7,
        watched_seconds=MAX_WATCHED_INTERVALS,
        completion_percent=1,
        watched_intervals=intervals,
    )
    db.add(progress)
    db.commit()
    progress_id = progress.id
    original_intervals = list(progress.watched_intervals)

    response = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=_candidate_headers(candidate.id),
        json={
            "current_position_seconds": duration - 1,
            "watched_start_seconds": duration - 2,
            "watched_end_seconds": duration - 1,
        },
    )

    persisted = db.query(LearningVideoProgress).filter_by(id=progress_id).one()
    assert response.status_code == 409
    assert "上限" in response.json()["detail"]
    assert persisted.last_position_seconds == 7
    assert persisted.watched_seconds == MAX_WATCHED_INTERVALS
    assert persisted.watched_intervals == original_intervals


def test_candidate_playback_uses_short_lived_bound_token_and_supports_ranges() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习人员", status="active")
    video = _upload_video(client)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish",
        headers=_admin_headers(),
    )

    detail = client.get(
        f"/api/learning/videos/{video['id']}",
        headers=_candidate_headers(candidate.id),
    )
    playback_url = detail.json()["data"]["playback_url"]
    parsed = urlsplit(playback_url)
    playback_token = parse_qs(parsed.query)["playback_token"][0]

    assert parsed.path == f"/api/learning/videos/{video['id']}/playback"
    assert playback_token
    assert "/media/learning/" not in playback_url

    playback = client.get(playback_url)
    ranged = client.get(playback_url, headers={"Range": "bytes=0-4"})

    assert playback.status_code == 200
    assert playback.content == b"video-bytes"
    assert playback.headers["cache-control"] == "private, no-store"
    assert playback.headers["accept-ranges"] == "bytes"
    assert ranged.status_code == 206
    assert ranged.content == b"video"
    assert ranged.headers["content-range"] == "bytes 0-4/11"


def test_candidate_playback_rejects_missing_expired_tampered_or_mismatched_tokens() -> (
    None
):
    client, db = _build_client()
    candidate = create_candidate(db, name="学习人员", status="active")
    video = _upload_video(client)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish",
        headers=_admin_headers(),
    )
    detail = client.get(
        f"/api/learning/videos/{video['id']}",
        headers=_candidate_headers(candidate.id),
    )
    playback_url = detail.json()["data"]["playback_url"]
    playback_token = parse_qs(urlsplit(playback_url).query)["playback_token"][0]
    tampered_token = f"{playback_token[:-1]}{'A' if playback_token[-1] != 'A' else 'B'}"
    expired_issued_at = int((datetime.now(UTC) - timedelta(minutes=6)).timestamp())
    expired_payload = f"learning:{candidate.id}:{video['id']}.{expired_issued_at}.nonce"
    expired_token = f"{expired_payload}.{_sign(expired_payload)}"

    missing = client.get(f"/api/learning/videos/{video['id']}/playback")
    tampered = client.get(
        f"/api/learning/videos/{video['id']}/playback",
        params={"playback_token": tampered_token},
    )
    expired = client.get(
        f"/api/learning/videos/{video['id']}/playback",
        params={"playback_token": expired_token},
    )
    mismatched = client.get(
        f"/api/learning/videos/{video['id'] + 1}/playback",
        params={"playback_token": playback_token},
    )

    assert missing.status_code == 401
    assert tampered.status_code == 401
    assert expired.status_code == 401
    assert mismatched.status_code == 401


def test_candidate_playback_rechecks_account_and_video_lifecycle() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习人员", status="active")
    video = _upload_video(client)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish",
        headers=_admin_headers(),
    )
    detail = client.get(
        f"/api/learning/videos/{video['id']}",
        headers=_candidate_headers(candidate.id),
    )
    playback_url = detail.json()["data"]["playback_url"]

    db.execute(
        update(Candidate).where(Candidate.id == candidate.id).values(status="inactive")
    )
    db.commit()
    inactive = client.get(playback_url)

    db.execute(
        update(Candidate).where(Candidate.id == candidate.id).values(status="active")
    )
    db.commit()
    archived = client.post(
        f"/api/admin/learning/videos/{video['id']}/archive",
        headers=_admin_headers(),
    )
    after_archive = client.get(playback_url)

    assert inactive.status_code == 401
    assert archived.status_code == 200
    assert after_archive.status_code == 404


def test_candidate_playback_rejects_unsafe_or_missing_storage_paths() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习人员", status="active")
    video = _upload_video(client)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish",
        headers=_admin_headers(),
    )
    detail = client.get(
        f"/api/learning/videos/{video['id']}",
        headers=_candidate_headers(candidate.id),
    )
    playback_url = detail.json()["data"]["playback_url"]

    video_row = db.get(LearningVideo, video["id"])
    assert video_row is not None
    video_row.storage_key = "../outside.mp4"
    db.commit()
    traversal = client.get(playback_url)

    video_row.storage_key = "missing.mp4"
    db.commit()
    missing = client.get(playback_url)

    old_static_path = client.get(f"/media/learning/{video['storage_key']}")

    assert traversal.status_code == 404
    assert missing.status_code == 404
    assert old_static_path.status_code == 404


def test_learning_progress_completion_skips_jumps_and_deduplicates_intervals() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="学习人员", status="active")
    video = _upload_video(client, duration_seconds=100)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    headers = _candidate_headers(candidate.id)

    first = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=headers,
        json={
            "current_position_seconds": 30,
            "watched_start_seconds": 0,
            "watched_end_seconds": 30,
        },
    )
    repeated = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=headers,
        json={
            "current_position_seconds": 30,
            "watched_start_seconds": 0,
            "watched_end_seconds": 30,
        },
    )
    jump = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=headers,
        json={
            "current_position_seconds": 95,
            "watched_start_seconds": 95,
            "watched_end_seconds": 95,
        },
    )
    second = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=headers,
        json={
            "current_position_seconds": 60,
            "watched_start_seconds": 30,
            "watched_end_seconds": 60,
        },
    )
    completed = client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=headers,
        json={
            "current_position_seconds": 90,
            "watched_start_seconds": 60,
            "watched_end_seconds": 90,
        },
    )

    assert first.status_code == 200
    assert first.json()["data"]["completion_percent"] == 30
    assert repeated.json()["data"]["completion_percent"] == 30
    assert jump.json()["data"]["completion_percent"] == 30
    assert second.json()["data"]["completion_percent"] == 60
    assert completed.json()["data"]["completion_percent"] == 90
    assert completed.json()["data"]["completed_at"] is not None


def test_admin_learning_report_and_export() -> None:
    client, db = _build_client()
    candidate = create_candidate(
        db, name="学习人员", email="learning@example.com", status="active"
    )
    video = _upload_video(client, duration_seconds=100)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    client.post(
        f"/api/learning/videos/{video['id']}/progress",
        headers=_candidate_headers(candidate.id),
        json={
            "current_position_seconds": 90,
            "watched_start_seconds": 0,
            "watched_end_seconds": 90,
        },
    )

    report = client.get("/api/admin/learning/reports", headers=_admin_headers())
    export = client.get("/api/admin/learning/reports/export", headers=_admin_headers())

    assert report.status_code == 200
    row = report.json()["data"][0]
    assert row["display_name"] == "学习人员"
    assert row["account_email"] == "learning@example.com"
    assert row["account_status"] == "active"
    assert set(row) <= {
        "candidate_id",
        "account_email",
        "display_name",
        "account_status",
        "video_id",
        "video_title",
        "video_status",
        "duration_seconds",
        "completion_percent",
        "completion_status",
        "last_heartbeat_at",
        "completed_at",
    }
    assert row["video_title"] == "安全培训"
    assert row["completion_status"] == "in_progress"
    assert row["completion_percent"] == 30
    assert export.status_code == 200
    workbook = load_workbook(BytesIO(export.content))
    assert workbook.active.title == "视频学习"
    assert workbook.active.cell(1, 1).value == "CID · 人员ID"
    assert workbook.active.cell(1, 2).value == "ACCOUNT EMAIL · 用户邮箱"
    assert workbook.active.cell(1, 3).value == "ACCOUNT NAME · 用户姓名"
    assert workbook.active.cell(1, 4).value == "ACCOUNT STATUS · 账户状态"


def test_admin_learning_report_keeps_lifecycle_rows_after_deactivation() -> None:
    client, db = _build_client()
    active = create_candidate(
        db, name="学习用户", email="learning-active@example.com", status="active"
    )
    inactive = Candidate(
        name="停用学习用户",
        email="learning-inactive@example.com",
        status="inactive",
    )
    db.add(inactive)
    db.commit()
    video = _upload_video(client, duration_seconds=100)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    db.refresh(active)
    active.name = "学习用户新显示名"
    db.commit()

    response = client.get("/api/admin/learning/reports", headers=_admin_headers())

    assert response.status_code == 200
    rows = response.json()["data"]
    by_email = {row["account_email"]: row for row in rows}
    assert by_email["learning-active@example.com"]["display_name"] == "学习用户新显示名"
    assert by_email["learning-inactive@example.com"]["account_status"] == "inactive"


def test_video_learning_does_not_gate_exam_start_or_submit() -> None:
    client, db = _build_client()
    candidate = create_candidate(db, name="考试人员", status="active")
    exam = create_exam(db, title="独立考试")
    create_question_with_options(db, stem="学习未完成也可考试")
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name,
        )
    )
    db.commit()
    video = _upload_video(client, duration_seconds=100)
    client.post(
        f"/api/admin/learning/videos/{video['id']}/publish", headers=_admin_headers()
    )
    headers = _candidate_headers(candidate.id)

    active = client.get("/api/exams/active", headers=headers)
    started = client.post(f"/api/exams/{exam.id}/start", headers=headers)
    started_data = started.json()["data"]
    attempt_id = started_data["attempt_id"]
    submitted = client.post(
        f"/api/attempts/{attempt_id}/submit",
        headers={
            **headers,
            "X-Attempt-Session": started_data["attempt_session_credential"],
        },
        json={"submit_type": "manual"},
    )

    assert active.status_code == 200
    assert active.json()["data"][0]["id"] == exam.id
    assert started.status_code == 200
    assert submitted.status_code == 200
