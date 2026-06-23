from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.rate_limit import check_public_token_rate_limit
from app.core.security import constant_time_equals, create_session_token
from app.schemas.auth import AdminLoginRequest, LoginResponse
from app.schemas.common import ApiResponse
from app.services.exam_service import AdminAuthError

router = APIRouter(tags=["auth"])


@router.post("/admin/login", response_model=ApiResponse[LoginResponse])
def admin_login(
    payload: AdminLoginRequest, request: Request
) -> ApiResponse[LoginResponse]:
    check_public_token_rate_limit(
        request, bucket="admin-login", identifier=payload.username
    )
    username_ok = constant_time_equals(payload.username, settings.admin_username)
    password_ok = constant_time_equals(payload.password, settings.admin_password)
    if not username_ok or not password_ok:
        raise AdminAuthError()
    return ApiResponse(data=LoginResponse(token=create_session_token(payload.username)))
