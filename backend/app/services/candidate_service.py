import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import randbelow

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.security import create_candidate_token
from app.core.time import ensure_aware
from app.models import Candidate, CandidateLoginChallenge
from app.schemas.candidate import (
    CandidateLoginChallengeResponse,
    CandidateLoginRequest,
    CandidateLoginResponse,
    CandidateLoginVerifyRequest,
    CandidateRead,
)
from app.services.email_service import send_candidate_login_otp


class CandidateLoginError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("未找到匹配的考试人员")


class CandidateLoginAmbiguousError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("姓名匹配到多名考试人员，请填写员工号")


class CandidateLoginChallengeError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("验证码无效或已过期")


def _with_token(candidate: Candidate) -> CandidateLoginResponse:
    candidate_read = CandidateRead.model_validate(candidate)
    return CandidateLoginResponse(
        **candidate_read.model_dump(),
        token=create_candidate_token(candidate.id),
    )


def request_candidate_login_challenge(
    db: Session, payload: CandidateLoginRequest, *, request_ip: str | None = None
) -> CandidateLoginChallengeResponse:
    candidate = _find_login_candidate(db, payload)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.candidate_login_otp_ttl_seconds)
    resend_available_at = now + timedelta(
        seconds=settings.candidate_login_otp_resend_cooldown_seconds
    )
    _consume_open_challenges(db, candidate.id, now)
    otp = _generate_otp()
    challenge = CandidateLoginChallenge(
        candidate_id=candidate.id,
        delivery_channel="email",
        otp_hash=_hash_otp(otp),
        expires_at=expires_at,
        request_ip_hash=_hash_request_ip(request_ip),
    )
    db.add(challenge)
    db.flush()
    send_candidate_login_otp(
        to_email=candidate.email or "",
        candidate_name=candidate.name,
        otp=otp,
        expires_at=expires_at,
    )
    db.commit()
    db.refresh(challenge)
    return CandidateLoginChallengeResponse(
        challenge_id=challenge.id,
        expires_at=challenge.expires_at,
        resend_available_at=resend_available_at,
    )


def verify_candidate_login_challenge(
    db: Session, payload: CandidateLoginVerifyRequest
) -> CandidateLoginResponse:
    challenge = db.get(CandidateLoginChallenge, payload.challenge_id)
    if challenge is None:
        raise CandidateLoginChallengeError()
    now = datetime.now(UTC)
    if (
        challenge.consumed_at is not None
        or ensure_aware(challenge.expires_at) <= now
        or challenge.attempt_count >= settings.candidate_login_otp_attempt_limit
    ):
        raise CandidateLoginChallengeError()

    if not hmac.compare_digest(challenge.otp_hash, _hash_otp(payload.otp.strip())):
        # Conditional increment: only count if still unconsumed / not over limit /
        # not expired. Closes the lost-update window where two concurrent wrong-OTP
        # requests both read attempt_count=N and both write N+1.
        _increment_attempt_count(db, challenge.id, now)
        db.commit()
        raise CandidateLoginChallengeError()

    # Authoritative atomic consume. If another concurrent request already
    # consumed this challenge (or the attempt_count was just bumped to the
    # limit by the failed-OTP branch), the WHERE clause matches zero rows
    # and we reject — closing the read-check-then-write replay window.
    result = _consume_challenge(db, challenge.id, now)
    if result == 0:
        db.rollback()
        raise CandidateLoginChallengeError()

    candidate = db.get(Candidate, challenge.candidate_id)
    if candidate is None or candidate.status != "active" or not candidate.email:
        # Don't let a stale/invalid candidate consume a valid OTP silently.
        db.rollback()
        raise CandidateLoginChallengeError()
    db.commit()
    db.refresh(candidate)
    return _with_token(candidate)


def _increment_attempt_count(db: Session, challenge_id: int, now: datetime) -> None:
    """Atomically bump attempt_count, gated on the row still being open."""
    (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.id == challenge_id,
            CandidateLoginChallenge.consumed_at.is_(None),
            CandidateLoginChallenge.attempt_count
            < settings.candidate_login_otp_attempt_limit,
            CandidateLoginChallenge.expires_at > now,
        )
        .update(
            {
                CandidateLoginChallenge.attempt_count: CandidateLoginChallenge.attempt_count
                + 1
            },
            synchronize_session=False,
        )
    )


def _consume_challenge(db: Session, challenge_id: int, now: datetime) -> int:
    """Atomically mark consumed_at; returns the rowcount (0 means lost the race)."""
    return (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.id == challenge_id,
            CandidateLoginChallenge.consumed_at.is_(None),
            CandidateLoginChallenge.attempt_count
            < settings.candidate_login_otp_attempt_limit,
            CandidateLoginChallenge.expires_at > now,
        )
        .update(
            {CandidateLoginChallenge.consumed_at: now},
            synchronize_session=False,
        )
    )


def _find_login_candidate(db: Session, payload: CandidateLoginRequest) -> Candidate:
    name = payload.name.strip()
    email = str(payload.email).strip().lower() if payload.email else None
    if not name or not email:
        raise CandidateLoginError()

    if payload.employee_no:
        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.name == name,
                Candidate.employee_no == payload.employee_no.strip(),
                func.lower(Candidate.email) == email,
                Candidate.status == "active",
            )
            .one_or_none()
        )
        if candidate is None:
            raise CandidateLoginError()
        return candidate

    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.name == name,
            func.lower(Candidate.email) == email,
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
    return candidates[0]


def _consume_open_challenges(db: Session, candidate_id: int, now: datetime) -> None:
    (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.candidate_id == candidate_id,
            CandidateLoginChallenge.consumed_at.is_(None),
        )
        .update({"consumed_at": now}, synchronize_session=False)
    )


def _generate_otp() -> str:
    return f"{randbelow(1_000_000):06d}"


def _hash_otp(otp: str) -> str:
    key = settings.token_secret.encode("utf-8")
    payload = f"candidate-login-otp:{otp}".encode()
    return hmac.new(key, payload, sha256).hexdigest()


def _hash_request_ip(request_ip: str | None) -> str | None:
    if not request_ip:
        return None
    digest = hashlib.sha256(request_ip.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
