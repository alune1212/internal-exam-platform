from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.security import create_candidate_token
from app.models import Candidate
from app.schemas.candidate import (
    CandidateLoginRequest,
    CandidateLoginResponse,
    CandidateRead,
)


class CandidateLoginError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("未找到匹配的考试人员")


class CandidateLoginAmbiguousError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("姓名匹配到多名考试人员，请填写员工号")


def _with_token(candidate: Candidate) -> CandidateLoginResponse:
    candidate_read = CandidateRead.model_validate(candidate)
    return CandidateLoginResponse(
        **candidate_read.model_dump(),
        token=create_candidate_token(candidate.id),
    )


def login_candidate(
    db: Session, payload: CandidateLoginRequest
) -> CandidateLoginResponse:
    phone_suffix = payload.phone_suffix.strip() if payload.phone_suffix else None
    if not phone_suffix:
        raise CandidateLoginError()

    if payload.employee_no:
        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.name == payload.name,
                Candidate.employee_no == payload.employee_no,
                Candidate.phone_suffix == phone_suffix,
                Candidate.status == "active",
            )
            .one_or_none()
        )
        if candidate is None:
            raise CandidateLoginError()
        return _with_token(candidate)

    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.name == payload.name,
            Candidate.phone_suffix == phone_suffix,
            Candidate.status == "active",
        )
        .order_by(Candidate.id)
        .limit(2)
        .all()
    )
    if not candidates:
        raise CandidateLoginError()
    if len(candidates) > 1:
        raise CandidateLoginAmbiguousError()
    return _with_token(candidates[0])
