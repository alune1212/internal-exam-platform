from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.security import constant_time_equals, create_session_token
from app.schemas.auth import AdminLoginRequest, LoginResponse
from app.schemas.common import ApiResponse


router = APIRouter(tags=["auth"])


@router.post("/admin/login", response_model=ApiResponse[LoginResponse])
def admin_login(payload: AdminLoginRequest) -> ApiResponse[LoginResponse]:
    username_ok = constant_time_equals(payload.username, settings.admin_username)
    password_ok = constant_time_equals(payload.password, settings.admin_password)
    if not username_ok or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return ApiResponse(data=LoginResponse(token=create_session_token(payload.username)))
