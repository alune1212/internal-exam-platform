"""FastAPI 鉴权依赖。"""

from fastapi import Header, Request

from app.core.exceptions import DomainError
from app.core.security import parse_admin_token, parse_candidate_token
from app.services.exam_service import AdminAuthError


def require_admin(request: Request) -> str:
    """校验 X-Admin-Token 并返回具名操作员。"""
    token = request.headers.get("X-Admin-Token", "")
    operator_subject = parse_admin_token(token)
    if operator_subject is None:
        raise AdminAuthError()
    request.state.operator_subject = operator_subject
    return operator_subject


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
        raise CandidateAuthError("无效的考试人身份")
    return candidate_id


def get_fresh_candidate_id(
    x_candidate_token: str | None = Header(None, alias="X-Candidate-Token"),
) -> int:
    """Require a candidate token freshly issued by OTP verification for takeover."""
    from app.core.config import settings

    if x_candidate_token is None:
        raise CandidateAuthError("请重新通过邮件验证码登录后接管考试。")
    candidate_id = parse_candidate_token(
        x_candidate_token,
        max_age_seconds=settings.candidate_login_otp_ttl_seconds,
    )
    if candidate_id is None:
        raise CandidateAuthError("请重新通过邮件验证码登录后接管考试。")
    return candidate_id
