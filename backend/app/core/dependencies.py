"""FastAPI 鉴权依赖。"""

from fastapi import Header, Request

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.security import parse_candidate_token, verify_session_token
from app.services.exam_service import AdminAuthError


def require_admin(request: Request) -> None:
    """校验 X-Admin-Token 头与配置的管理员 token 一致。"""
    token = request.headers.get("X-Admin-Token", "")
    if not verify_session_token(
        token,
        subject=settings.admin_username,
        secret=settings.token_secret,
        max_age_seconds=settings.token_ttl_seconds,
    ):
        raise AdminAuthError()


class CandidateAuthError(DomainError):
    """候选人鉴权失败。"""

    status_code = 401

    def __init__(self, detail: str = "请先输入姓名登录。") -> None:
        super().__init__(detail)


def get_current_candidate_id(
    x_candidate_token: str | None = Header(None, alias="X-Candidate-Token"),
) -> int:
    """从签名 X-Candidate-Token 请求头提取候选人 ID。"""
    if x_candidate_token is None:
        raise CandidateAuthError()
    candidate_id = parse_candidate_token(x_candidate_token)
    if candidate_id is None:
        raise CandidateAuthError("无效的候选人身份")
    return candidate_id
