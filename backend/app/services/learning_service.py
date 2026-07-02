from collections.abc import Iterable
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models import Candidate, LearningVideo, LearningVideoProgress
from app.models.learning import LearningVideoStatus
from app.schemas.learning import (
    CandidateLearningVideoRead,
    LearningProgressUpdate,
    LearningReportRow,
    LearningVideoProgressRead,
    LearningVideoRead,
    LearningVideoUpdate,
)
from app.services.excel_security import escape_excel_cell
from app.services.learning_storage import build_public_media_url, save_video_upload

COMPLETION_THRESHOLD_PERCENT = 90
MAX_WATCHED_INTERVAL_SECONDS = 30
LEARNING_STATUS_LABELS = {
    "not_started": "未开始",
    "in_progress": "学习中",
    "completed": "已完成",
}
VIDEO_STATUS_LABELS = {
    "draft": "草稿",
    "published": "已发布",
    "archived": "已归档",
}


class LearningVideoNotFoundError(DomainError):
    status_code = 404

    def __init__(self, video_id: int) -> None:
        super().__init__(f"学习视频 #{video_id} 不存在")


class LearningCandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考试人 #{candidate_id} 不存在")


class LearningVideoValidationError(DomainError):
    status_code = 400


def list_admin_videos(db: Session) -> list[LearningVideoRead]:
    videos = db.query(LearningVideo).order_by(LearningVideo.created_at.desc()).all()
    return [_video_read(video) for video in videos]


def create_video(
    db: Session,
    *,
    title: str,
    description: str | None,
    duration_seconds: int,
    file: UploadFile,
) -> LearningVideoRead:
    cleaned_title = title.strip()
    if not cleaned_title:
        raise LearningVideoValidationError("视频标题不能为空")
    if duration_seconds <= 0:
        raise LearningVideoValidationError("视频时长必须大于 0 秒")

    storage_key, file_size, content_type = save_video_upload(file)
    video = LearningVideo(
        title=cleaned_title,
        description=_clean_optional_text(description),
        original_filename=Path(file.filename or "video").name,
        storage_key=storage_key,
        content_type=content_type,
        file_size_bytes=file_size,
        duration_seconds=duration_seconds,
        completion_threshold_percent=COMPLETION_THRESHOLD_PERCENT,
        status=LearningVideoStatus.draft.value,
        uploaded_at=datetime.now(UTC),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return _video_read(video)


def update_video(
    db: Session, video_id: int, payload: LearningVideoUpdate
) -> LearningVideoRead:
    video = _get_video(db, video_id)
    if payload.title is not None:
        cleaned_title = payload.title.strip()
        if not cleaned_title:
            raise LearningVideoValidationError("视频标题不能为空")
        video.title = cleaned_title
    if payload.description is not None:
        video.description = _clean_optional_text(payload.description)
    db.commit()
    db.refresh(video)
    return _video_read(video)


def publish_video(db: Session, video_id: int) -> LearningVideoRead:
    return _set_video_status(db, video_id, LearningVideoStatus.published.value)


def archive_video(db: Session, video_id: int) -> LearningVideoRead:
    return _set_video_status(db, video_id, LearningVideoStatus.archived.value)


def list_candidate_videos(
    db: Session, candidate_id: int
) -> list[CandidateLearningVideoRead]:
    _get_active_candidate(db, candidate_id)
    videos = (
        db.query(LearningVideo)
        .filter(LearningVideo.status == LearningVideoStatus.published.value)
        .order_by(LearningVideo.created_at.desc())
        .all()
    )
    progress_by_video = _progress_by_video(
        db, candidate_id, [video.id for video in videos]
    )
    return [
        _candidate_video_read(video, progress_by_video.get(video.id))
        for video in videos
    ]


def get_candidate_video(
    db: Session, candidate_id: int, video_id: int
) -> CandidateLearningVideoRead:
    _get_active_candidate(db, candidate_id)
    video = (
        db.query(LearningVideo)
        .filter(
            LearningVideo.id == video_id,
            LearningVideo.status == LearningVideoStatus.published.value,
        )
        .one_or_none()
    )
    if video is None:
        raise LearningVideoNotFoundError(video_id)
    progress = _get_progress(db, candidate_id, video_id)
    return _candidate_video_read(video, progress)


def update_progress(
    db: Session,
    candidate_id: int,
    video_id: int,
    payload: LearningProgressUpdate,
) -> LearningVideoProgressRead:
    _get_active_candidate(db, candidate_id)
    video = (
        db.query(LearningVideo)
        .filter(
            LearningVideo.id == video_id,
            LearningVideo.status == LearningVideoStatus.published.value,
        )
        .one_or_none()
    )
    if video is None:
        raise LearningVideoNotFoundError(video_id)

    progress = _get_or_create_progress(db, candidate_id, video_id)
    now = datetime.now(UTC)
    progress.last_position_seconds = min(
        payload.current_position_seconds, video.duration_seconds
    )
    progress.last_heartbeat_at = now

    start, end = _normalize_interval(
        payload.watched_start_seconds,
        payload.watched_end_seconds,
        video.duration_seconds,
    )
    if end > start:
        intervals = _merge_intervals(
            [*_read_intervals(progress.watched_intervals), (start, end)]
        )
        progress.watched_intervals = [
            {"start": interval_start, "end": interval_end}
            for interval_start, interval_end in intervals
        ]
        progress.watched_seconds = sum(
            interval_end - interval_start for interval_start, interval_end in intervals
        )

    progress.completion_percent = _completion_percent(
        progress.watched_seconds, video.duration_seconds
    )
    if (
        progress.completed_at is None
        and progress.completion_percent >= video.completion_threshold_percent
    ):
        progress.completed_at = now

    db.commit()
    db.refresh(progress)
    return _progress_read(progress)


def get_learning_report(
    db: Session,
    *,
    video_id: int | None = None,
    status: str | None = None,
) -> list[LearningReportRow]:
    query = db.query(LearningVideo)
    if video_id is not None:
        query = query.filter(LearningVideo.id == video_id)
    videos = query.order_by(LearningVideo.created_at.desc()).all()
    candidates = (
        db.query(Candidate)
        .filter(Candidate.status == "active")
        .order_by(Candidate.name, Candidate.id)
        .all()
    )
    progress_rows = (
        db.query(LearningVideoProgress)
        .filter(LearningVideoProgress.video_id.in_([video.id for video in videos]))
        .all()
        if videos
        else []
    )
    progress_by_key = {
        (progress.video_id, progress.candidate_id): progress
        for progress in progress_rows
    }

    rows: list[LearningReportRow] = []
    for video in videos:
        for candidate in candidates:
            progress = progress_by_key.get((video.id, candidate.id))
            row = _report_row(video, candidate, progress)
            if status is None or row.completion_status == status:
                rows.append(row)
    return rows


def generate_learning_report_workbook(
    db: Session,
    *,
    video_id: int | None = None,
    status: str | None = None,
) -> BytesIO:
    rows = get_learning_report(db, video_id=video_id, status=status)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "视频学习"
    sheet.append(
        [
            "CID · 人员ID",
            "NAME · 姓名",
            "EMP NO · 工号",
            "DEPT · 部门",
            "GROUP · 分组",
            "VID · 视频ID",
            "VIDEO · 视频",
            "VIDEO STATUS · 视频状态",
            "DURATION · 时长秒",
            "PROGRESS · 完成度",
            "STATUS · 学习状态",
            "LAST SEEN · 最近学习",
            "COMPLETED AT · 完成时间",
        ]
    )
    for row in rows:
        sheet.append(
            [
                escape_excel_cell(row.candidate_id),
                escape_excel_cell(row.candidate_name),
                escape_excel_cell(row.employee_no),
                escape_excel_cell(row.department),
                escape_excel_cell(row.exam_group),
                escape_excel_cell(row.video_id),
                escape_excel_cell(row.video_title),
                VIDEO_STATUS_LABELS.get(row.video_status, row.video_status),
                row.duration_seconds,
                row.completion_percent,
                LEARNING_STATUS_LABELS.get(
                    row.completion_status, row.completion_status
                ),
                row.last_heartbeat_at.isoformat() if row.last_heartbeat_at else None,
                row.completed_at.isoformat() if row.completed_at else None,
            ]
        )
    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(
            max(max_length + 2, 10), 48
        )
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def _set_video_status(db: Session, video_id: int, status: str) -> LearningVideoRead:
    video = _get_video(db, video_id)
    video.status = status
    db.commit()
    db.refresh(video)
    return _video_read(video)


def _get_video(db: Session, video_id: int) -> LearningVideo:
    video = db.get(LearningVideo, video_id)
    if video is None:
        raise LearningVideoNotFoundError(video_id)
    return video


def _get_active_candidate(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or candidate.status != "active":
        raise LearningCandidateNotFoundError(candidate_id)
    return candidate


def _get_progress(
    db: Session, candidate_id: int, video_id: int
) -> LearningVideoProgress | None:
    return (
        db.query(LearningVideoProgress)
        .filter(
            LearningVideoProgress.candidate_id == candidate_id,
            LearningVideoProgress.video_id == video_id,
        )
        .one_or_none()
    )


def _get_or_create_progress(
    db: Session, candidate_id: int, video_id: int
) -> LearningVideoProgress:
    progress = _get_progress(db, candidate_id, video_id)
    if progress is not None:
        return progress
    progress = LearningVideoProgress(
        candidate_id=candidate_id,
        video_id=video_id,
        watched_intervals=[],
    )
    db.add(progress)
    db.flush()
    return progress


def _progress_by_video(
    db: Session, candidate_id: int, video_ids: list[int]
) -> dict[int, LearningVideoProgress]:
    if not video_ids:
        return {}
    rows = (
        db.query(LearningVideoProgress)
        .filter(
            LearningVideoProgress.candidate_id == candidate_id,
            LearningVideoProgress.video_id.in_(video_ids),
        )
        .all()
    )
    return {row.video_id: row for row in rows}


def _candidate_video_read(
    video: LearningVideo, progress: LearningVideoProgress | None
) -> CandidateLearningVideoRead:
    return CandidateLearningVideoRead(
        **_video_read(video).model_dump(),
        progress=_progress_read(progress),
    )


def _video_read(video: LearningVideo) -> LearningVideoRead:
    return LearningVideoRead(
        id=video.id,
        title=video.title,
        description=video.description,
        original_filename=video.original_filename,
        storage_key=video.storage_key,
        content_type=video.content_type,
        file_size_bytes=video.file_size_bytes,
        duration_seconds=video.duration_seconds,
        completion_threshold_percent=video.completion_threshold_percent,
        status=video.status,
        uploaded_at=video.uploaded_at,
        created_at=video.created_at,
        updated_at=video.updated_at,
        playback_url=build_public_media_url(video.storage_key),
    )


def _progress_read(
    progress: LearningVideoProgress | None,
) -> LearningVideoProgressRead:
    if progress is None:
        return LearningVideoProgressRead()
    return LearningVideoProgressRead(
        last_position_seconds=progress.last_position_seconds,
        watched_seconds=progress.watched_seconds,
        completion_percent=progress.completion_percent,
        completed_at=progress.completed_at,
        last_heartbeat_at=progress.last_heartbeat_at,
    )


def _report_row(
    video: LearningVideo,
    candidate: Candidate,
    progress: LearningVideoProgress | None,
) -> LearningReportRow:
    progress_read = _progress_read(progress)
    if progress_read.completed_at is not None:
        completion_status = "completed"
    elif progress_read.watched_seconds > 0:
        completion_status = "in_progress"
    else:
        completion_status = "not_started"
    return LearningReportRow(
        candidate_id=candidate.id,
        candidate_name=candidate.name,
        employee_no=candidate.employee_no,
        department=candidate.department,
        exam_group=candidate.exam_group,
        video_id=video.id,
        video_title=video.title,
        video_status=video.status,
        duration_seconds=video.duration_seconds,
        completion_percent=progress_read.completion_percent,
        completion_status=completion_status,
        last_heartbeat_at=progress_read.last_heartbeat_at,
        completed_at=progress_read.completed_at,
    )


def _normalize_interval(
    start_seconds: int, end_seconds: int, duration_seconds: int
) -> tuple[int, int]:
    start = max(0, min(start_seconds, duration_seconds))
    end = max(0, min(end_seconds, duration_seconds))
    if end <= start:
        return start, start
    end = min(end, start + MAX_WATCHED_INTERVAL_SECONDS)
    return start, end


def _read_intervals(raw_intervals: list[dict] | None) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for interval in raw_intervals or []:
        try:
            start = int(interval["start"])
            end = int(interval["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end > start:
            intervals.append((start, end))
    return intervals


def _merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    sorted_intervals = sorted(intervals)
    merged: list[tuple[int, int]] = []
    for start, end in sorted_intervals:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return merged


def _completion_percent(watched_seconds: int, duration_seconds: int) -> int:
    if duration_seconds <= 0:
        return 0
    return min(100, int((watched_seconds / duration_seconds) * 100))


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
