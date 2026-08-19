"""FastAPI authentication dependencies."""

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import DomainError
from app.core.security import parse_admin_token, parse_candidate_token
from app.models import Candidate
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

    def __init__(self, detail: str = "请先通过邮箱验证码登录。") -> None:
        super().__init__(detail)


def _resolve_active_candidate(
    x_candidate_token: str | None,
    db: Session,
    *,
    default_detail: str,
    missing_detail: str,
    max_age_seconds: int | None = None,
) -> int:
    """Parse a candidate token, enforce OTP freshness, and confirm active status.

    Token issuance alone is not enough: an operator can deactivate an account
    while a four-hour token is still held by the browser.  The session used for
    the lookup is intentionally uncached and released as soon as the auth check
    completes so a concurrent exam flow never sees an idle-in-transaction
    connection tied to authentication.
    """

    if x_candidate_token is None:
        raise CandidateAuthError(default_detail)
    if max_age_seconds is None:
        candidate_id = parse_candidate_token(x_candidate_token)
    else:
        candidate_id = parse_candidate_token(
            x_candidate_token, max_age_seconds=max_age_seconds
        )
    if candidate_id is None:
        raise CandidateAuthError(missing_detail)

    try:
        candidate = db.get(Candidate, candidate_id, populate_existing=True)
        candidate_status = candidate.status if candidate is not None else None
    finally:
        db.close()
    if candidate_status is None:
        raise CandidateAuthError(missing_detail)
    if candidate_status != "active":
        raise CandidateAuthError("账号暂不可用，请联系管理员重新激活。")
    return candidate_id


def get_current_candidate_id(
    x_candidate_token: str | None = Header(None, alias="X-Candidate-Token"),
    db: Session = Depends(get_db, use_cache=False),
) -> int:
    """Parse the token and enforce the account's current active status.

    Every candidate route receives this dependency, including attempt
    save/submit, takeover, result, learning, practice, and profile APIs.
    """

    return _resolve_active_candidate(
        x_candidate_token,
        db,
        default_detail="请先通过邮箱验证码登录。",
        missing_detail="无效的考试人身份",
    )


def get_fresh_candidate_id(
    x_candidate_token: str | None = Header(None, alias="X-Candidate-Token"),
    db: Session = Depends(get_db, use_cache=False),
) -> int:
    """Require a candidate token freshly issued by OTP verification for takeover."""

    return _resolve_active_candidate(
        x_candidate_token,
        db,
        default_detail="请重新通过邮件验证码登录后接管考试。",
        missing_detail="请重新通过邮件验证码登录后接管考试。",
        max_age_seconds=settings.candidate_login_otp_ttl_seconds,
    )
