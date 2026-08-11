import hmac
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AdminAuditEvent
from app.services.operational_lock_service import assert_backup_write_allowed

ALLOWED_METADATA_KEYS = {
    "archive_ref",
    "backup_ref",
    "batch_id",
    "count",
    "deleted_count",
    "exam_id",
    "failed_count",
    "fingerprint",
    "granted_count",
    "operator_enabled",
    "outcome_artifact",
    "reason_code",
    "success_count",
    "voided_count",
}


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in ALLOWED_METADATA_KEYS:
            continue
        if value is None or isinstance(value, str | int | float | bool):
            safe[key] = value
    return safe


def _request_source_hash(request: Request | None) -> str | None:
    if request is None:
        return None
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")[:256]
    source = f"{client_host}|{user_agent}".encode()
    return hmac.new(settings.token_secret.encode("utf-8"), source, sha256).hexdigest()


def record_admin_event(
    db: Session,
    *,
    operator_subject: str,
    action: str,
    target_type: str,
    target_id: str | int | None = None,
    result: str = "success",
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AdminAuditEvent:
    # Audit rows are part of the formal dataset and must not bypass the
    # shared writer fence when a caller writes outside an API route.
    assert_backup_write_allowed(db)
    event = AdminAuditEvent(
        operator_subject=operator_subject,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        result=result,
        metadata_json=_safe_metadata(metadata),
        request_source_hash=_request_source_hash(request),
        created_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event
