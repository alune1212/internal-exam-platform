from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import DomainError

ALLOWED_EXTENSIONS_BY_CONTENT_TYPE = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


class LearningVideoUploadError(DomainError):
    status_code = 400


class LearningVideoUploadTooLargeError(DomainError):
    status_code = 413


def validate_video_upload(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    if content_type not in settings.learning_video_allowed_content_type_set:
        raise LearningVideoUploadError("仅支持 MP4 或 WebM 视频文件")

    suffix = Path(file.filename or "").suffix.lower()
    expected_suffix = ALLOWED_EXTENSIONS_BY_CONTENT_TYPE.get(content_type)
    if suffix != expected_suffix:
        raise LearningVideoUploadError("视频文件扩展名与内容类型不匹配")
    return suffix


def inspect_upload_size(file: UploadFile) -> int:
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
    except (AttributeError, OSError):
        return 0

    if size <= 0:
        raise LearningVideoUploadError("视频文件不能为空")
    if size > settings.learning_video_max_upload_bytes:
        raise LearningVideoUploadTooLargeError(
            f"视频文件大小不能超过 {settings.learning_video_max_upload_bytes} 字节"
        )
    return size


def save_video_upload(file: UploadFile) -> tuple[str, int, str]:
    suffix = validate_video_upload(file)
    size = inspect_upload_size(file)
    storage_key = f"{uuid4().hex}{suffix}"
    storage_dir = Path(settings.learning_media_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / storage_key

    with destination.open("wb") as target:
        while chunk := file.file.read(1024 * 1024):
            target.write(chunk)
    file.file.seek(0)
    return storage_key, size, file.content_type or "application/octet-stream"


def build_public_media_url(storage_key: str) -> str:
    public_path = settings.learning_media_public_path.rstrip("/")
    return f"{public_path}/{storage_key}"
