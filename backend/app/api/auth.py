from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import check_public_token_rate_limit
from app.core.security import constant_time_equals, create_admin_token
from app.schemas.auth import AdminLoginRequest, LoginResponse
from app.schemas.common import ApiResponse
from app.services.audit_service import record_admin_event
from app.services.exam_service import AdminAuthError
from app.services.operational_lock_service import assert_backup_write_allowed

router = APIRouter(tags=["auth"])


@router.post("/admin/login", response_model=ApiResponse[LoginResponse])
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[LoginResponse]:
    # Audit events make both successful and rejected admin logins writes.
    assert_backup_write_allowed(db)
    check_public_token_rate_limit(
        request, bucket="admin-login", identifier=payload.username
    )
    active_username, active_password = settings.configured_active_operator
    username_ok = constant_time_equals(payload.username, active_username)
    password_ok = constant_time_equals(payload.password, active_password)
    operator_subject = active_username if username_ok and password_ok else None
    if operator_subject is None:
        primary_username, _primary_password = settings.configured_primary_operator
        backup_username, _backup_password = settings.configured_backup_operator
        known_subject = (
            payload.username
            if payload.username in {primary_username, backup_username}
            else "unknown"
        )
        record_admin_event(
            db,
            operator_subject=known_subject,
            action="admin_login",
            target_type="operator",
            target_id=known_subject,
            result="rejected",
            request=request,
        )
        db.commit()
        raise AdminAuthError()
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="admin_login",
        target_type="operator",
        target_id=operator_subject,
        result="success",
        request=request,
    )
    db.commit()
    return ApiResponse(data=LoginResponse(token=create_admin_token(operator_subject)))
