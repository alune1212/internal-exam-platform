from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models import Candidate
from app.schemas.candidate import CandidateLoginRequest, CandidateRead


class CandidateLoginError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("未找到匹配的考试人员")


class CandidateLoginAmbiguousError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("姓名匹配到多名考试人员，请填写员工号")


def login_candidate(db: Session, payload: CandidateLoginRequest) -> CandidateRead:
    if payload.employee_no:
        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.employee_no == payload.employee_no,
                Candidate.status == "active",
            )
            .one_or_none()
        )
        if candidate is None:
            raise CandidateLoginError()
        return CandidateRead.model_validate(candidate)

    candidates = (
        db.query(Candidate)
        .filter(Candidate.name == payload.name, Candidate.status == "active")
        .order_by(Candidate.id)
        .limit(2)
        .all()
    )
    if not candidates:
        raise CandidateLoginError()
    if len(candidates) > 1:
        raise CandidateLoginAmbiguousError()
    return CandidateRead.model_validate(candidates[0])
