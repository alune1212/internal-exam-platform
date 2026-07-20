import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainError
from app.schemas.common import ReadinessStatus


class ReadinessUnavailableError(DomainError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("服务尚未就绪。")


def check_readiness(db: Session) -> ReadinessStatus:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise ReadinessUnavailableError() from None

    storage_dir = Path(settings.learning_media_storage_dir)
    required_access = os.R_OK | os.W_OK | os.X_OK
    if not storage_dir.is_dir() or not os.access(storage_dir, required_access):
        raise ReadinessUnavailableError()

    return ReadinessStatus()
