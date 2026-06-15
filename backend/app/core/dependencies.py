"""FastAPI 鉴权依赖。"""

from fastapi import Header, Request

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.security import constant_time_equals
from app.services.exam_service import AdminAuthError


def require_admin(request: Request) -> None:
    """校验 X-Admin-Token 头与配置的管理员 token 一致。"""
    token = request.headers.get("X-Admin-Token", "")
    if not constant_time_equals(token, settings.admin_password):
        raise AdminAuthError()


class CandidateAuthError(DomainError):
    """候选人鉴权失败。"""

    status_code = 401

    def __init__(self, detail: str = "请先输入姓名登录。") -> None:
        super().__init__(detail)


def get_current_candidate_id(
    x_candidate_id: str | None = Header(None, alias="X-Candidate-Id"),
) -> int:
    """从 X-Candidate-Id 请求头提取候选人 ID。"""
    if x_candidate_id is None:
        raise CandidateAuthError()
    try:
        return int(x_candidate_id)
    except (ValueError, TypeError) as err:
        raise CandidateAuthError("无效的候选人身份") from err
