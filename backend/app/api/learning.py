from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id
from app.schemas.common import ApiResponse
from app.schemas.learning import (
    CandidateLearningVideoRead,
    LearningProgressUpdate,
    LearningReportRow,
    LearningVideoProgressRead,
    LearningVideoRead,
    LearningVideoUpdate,
)
from app.services import learning_service

router = APIRouter(prefix="/learning", tags=["learning"])
admin_router = APIRouter(prefix="/admin/learning", tags=["admin-learning"])


@router.get("/videos", response_model=ApiResponse[list[CandidateLearningVideoRead]])
def list_learning_videos(
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[CandidateLearningVideoRead]]:
    return ApiResponse(data=learning_service.list_candidate_videos(db, candidate_id))


@router.get(
    "/videos/{video_id}", response_model=ApiResponse[CandidateLearningVideoRead]
)
def get_learning_video(
    video_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[CandidateLearningVideoRead]:
    return ApiResponse(
        data=learning_service.get_candidate_video(db, candidate_id, video_id)
    )


@router.post(
    "/videos/{video_id}/progress",
    response_model=ApiResponse[LearningVideoProgressRead],
)
def update_learning_progress(
    video_id: int,
    payload: LearningProgressUpdate,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[LearningVideoProgressRead]:
    return ApiResponse(
        data=learning_service.update_progress(db, candidate_id, video_id, payload)
    )


@admin_router.get("/videos", response_model=ApiResponse[list[LearningVideoRead]])
def list_admin_learning_videos(
    db: Session = Depends(get_db),
) -> ApiResponse[list[LearningVideoRead]]:
    return ApiResponse(data=learning_service.list_admin_videos(db))


@admin_router.post("/videos", response_model=ApiResponse[LearningVideoRead])
def upload_learning_video(
    title: Annotated[str, Form()],
    duration_seconds: Annotated[int, Form()],
    file: Annotated[UploadFile, File()],
    description: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
) -> ApiResponse[LearningVideoRead]:
    return ApiResponse(
        data=learning_service.create_video(
            db,
            title=title,
            description=description,
            duration_seconds=duration_seconds,
            file=file,
        )
    )


@admin_router.put("/videos/{video_id}", response_model=ApiResponse[LearningVideoRead])
def update_admin_learning_video(
    video_id: int,
    payload: LearningVideoUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[LearningVideoRead]:
    return ApiResponse(data=learning_service.update_video(db, video_id, payload))


@admin_router.post(
    "/videos/{video_id}/publish", response_model=ApiResponse[LearningVideoRead]
)
def publish_admin_learning_video(
    video_id: int, db: Session = Depends(get_db)
) -> ApiResponse[LearningVideoRead]:
    return ApiResponse(data=learning_service.publish_video(db, video_id))


@admin_router.post(
    "/videos/{video_id}/archive", response_model=ApiResponse[LearningVideoRead]
)
def archive_admin_learning_video(
    video_id: int, db: Session = Depends(get_db)
) -> ApiResponse[LearningVideoRead]:
    return ApiResponse(data=learning_service.archive_video(db, video_id))


@admin_router.get("/reports", response_model=ApiResponse[list[LearningReportRow]])
def get_learning_report(
    video_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse[list[LearningReportRow]]:
    return ApiResponse(
        data=learning_service.get_learning_report(db, video_id=video_id, status=status)
    )


@admin_router.get("/reports/export")
def export_learning_report(
    video_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    stream = learning_service.generate_learning_report_workbook(
        db, video_id=video_id, status=status
    )
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('视频学习报表.xlsx')}"
        },
    )
