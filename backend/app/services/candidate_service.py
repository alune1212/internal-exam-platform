import hashlib
import hmac
import logging
from dataclasses import dataclass
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
from app.services.operational_lock_service import assert_backup_write_allowed

logger = logging.getLogger(__name__)


class CandidateLoginError(DomainError):
    """Reserved for callers that need to surface an identity error.

    The challenge request path no longer raises this — it returns a uniform
    200 envelope for every outcome. It is kept for callers (e.g., admin
    flows) that still need a typed 404.
    """

    status_code = 404

    def __init__(self) -> None:
        super().__init__("未找到匹配的考试人员")


class CandidateLoginAmbiguousError(DomainError):
    """Reserved for callers that need to surface an ambiguity error.

    The challenge request path no longer raises this. It is kept for callers
    that still need a typed 409.
    """

    status_code = 409

    def __init__(self) -> None:
        super().__init__("姓名匹配到多名考试人员，请填写员工号")


class CandidateLoginChallengeError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("验证码无效或已过期")


@dataclass(frozen=True)
class CandidateLoginEmailPayload:
    """Arguments the route should pass to ``send_candidate_login_otp``.

    ``None`` from the service means "do not send an email" — used for the
    sentinel path so that unknown / ambiguous / inactive / missing-email
    identities do not leak via SMTP side effects.
    """

    to_email: str
    candidate_name: str
    otp: str
    expires_at: datetime


@dataclass(frozen=True)
class CandidateLoginChallengeRequestResult:
    response: CandidateLoginChallengeResponse
    email: CandidateLoginEmailPayload | None


def _with_token(candidate: Candidate) -> CandidateLoginResponse:
    candidate_read = CandidateRead.model_validate(candidate)
    return CandidateLoginResponse(
        **candidate_read.model_dump(),
        token=create_candidate_token(candidate.id),
    )


def request_candidate_login_challenge(
    db: Session, payload: CandidateLoginRequest, *, request_ip: str | None = None
) -> CandidateLoginChallengeRequestResult:
    """Persist a challenge row, then return the uniform response.

    The challenge row is committed before any email delivery is considered,
    so SMTP latency / failure cannot roll back the persisted state. Email
    delivery is the route's responsibility — it should enqueue
    ``send_candidate_login_otp`` via FastAPI ``BackgroundTasks`` when
    ``result.email`` is not None.

    For unknown, ambiguous, inactive, or missing-email identities, the
    challenge row is created against a designated sentinel candidate and
    no email is sent. The response envelope, status code, and timing are
    identical to a valid request, so the caller cannot enumerate the
    roster from the response.
    """
    # Login challenge rows, including sentinel rows for unknown identities,
    # are formal data writes and must stop during cutover.
    assert_backup_write_allowed(db)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.candidate_login_otp_ttl_seconds)
    resend_available_at = now + timedelta(
        seconds=settings.candidate_login_otp_resend_cooldown_seconds
    )
    request_ip_hash = _hash_request_ip(request_ip)

    real_candidate, lookup_outcome = _resolve_login_candidate(db, payload)
    target = (
        real_candidate if real_candidate is not None else _get_sentinel_candidate(db)
    )

    if real_candidate is None:
        _audit_unknown_identity(payload, lookup_outcome, request_ip_hash)

    _consume_open_challenges(db, target.id, now)

    otp = _generate_otp()
    challenge = CandidateLoginChallenge(
        candidate_id=target.id,
        delivery_channel="email",
        otp_hash=_hash_otp(otp),
        expires_at=expires_at,
        request_ip_hash=request_ip_hash,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    email_payload: CandidateLoginEmailPayload | None = None
    if real_candidate is not None and real_candidate.email:
        email_payload = CandidateLoginEmailPayload(
            to_email=real_candidate.email,
            candidate_name=real_candidate.name,
            otp=otp,
            expires_at=expires_at,
        )

    return CandidateLoginChallengeRequestResult(
        response=CandidateLoginChallengeResponse(
            challenge_id=challenge.id,
            expires_at=challenge.expires_at,
            resend_available_at=resend_available_at,
        ),
        email=email_payload,
    )


def verify_candidate_login_challenge(
    db: Session, payload: CandidateLoginVerifyRequest
) -> CandidateLoginResponse:
    # Wrong-OTP attempt counters and successful challenge consumption both
    # mutate the shared formal dataset.
    assert_backup_write_allowed(db)
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
    if (
        candidate is None
        or candidate.is_login_sentinel
        or candidate.status != "active"
        or not candidate.email
    ):
        # Sentinel challenges, inactive candidates, and rows without email
        # all reject here — without surfacing the outcome to the caller.
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


def _resolve_login_candidate(
    db: Session, payload: CandidateLoginRequest
) -> tuple[Candidate | None, str]:
    """Resolve a login request to a real candidate, or classify the failure.

    Returns ``(candidate, outcome)`` where ``outcome`` is one of
    ``"found" | "invalid_input" | "not_found" | "ambiguous" | "inactive" |
    "missing_email"``. On any non-``"found"`` outcome ``candidate`` is None
    and the caller should fall back to the sentinel row.
    """
    name = payload.name.strip()
    email = str(payload.email).strip().lower() if payload.email else None
    if not name or not email:
        return None, "invalid_input"

    if payload.employee_no:
        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.name == name,
                Candidate.employee_no == payload.employee_no.strip(),
                func.lower(Candidate.email) == email,
            )
            .one_or_none()
        )
        if candidate is None:
            return None, "not_found"
    else:
        candidates = (
            db.query(Candidate)
            .filter(
                Candidate.name == name,
                func.lower(Candidate.email) == email,
            )
            .order_by(Candidate.id)
            .limit(2)
            .all()
        )
        if not candidates:
            return None, "not_found"
        if len(candidates) > 1:
            return None, "ambiguous"
        candidate = candidates[0]

    if candidate.is_login_sentinel:
        # The sentinel row matches its own name; treat as not_found so we
        # do not surface the sentinel through the lookup path.
        return None, "not_found"
    if candidate.status != "active":
        return None, "inactive"
    if not candidate.email:
        return None, "missing_email"
    return candidate, "found"


def _get_sentinel_candidate(db: Session) -> Candidate:
    """Return the designated sentinel candidate used for unknown identities.

    The migration ``202607030002_candidate_login_sentinel`` ensures exactly
    one such row exists. The lookup is cached per request via the session.
    """
    sentinel = (
        db.query(Candidate).filter(Candidate.is_login_sentinel.is_(True)).one_or_none()
    )
    if sentinel is None:
        # Defensive: if the sentinel is missing, fail closed rather than
        # leaking the response differential. This should never happen in
        # production once the migration has run.
        raise RuntimeError(
            "candidate login sentinel row missing; run "
            "alembic upgrade head to install it"
        )
    return sentinel


def _audit_unknown_identity(
    payload: CandidateLoginRequest, outcome: str, request_ip_hash: str | None
) -> None:
    """Emit a single structured WARN log line for unknown-identity attempts.

    The log is the only audit signal — the response is uniform and never
    reveals the outcome. Identity fields are hashed to avoid logging
    plaintext roster data. The rate limiter on the route already caps
    the request rate, so this is a secondary audit trail.
    """
    name_hash = hashlib.sha256(payload.name.encode("utf-8")).hexdigest()
    email_hash = hashlib.sha256(str(payload.email or "").encode("utf-8")).hexdigest()
    employee_no_hash = hashlib.sha256(
        (payload.employee_no or "").encode("utf-8")
    ).hexdigest()
    logger.warning(
        "candidate_login.unknown_identity",
        extra={
            "event": "candidate_login.unknown_identity",
            "outcome": outcome,
            "name_sha256": f"sha256:{name_hash}",
            "email_sha256": f"sha256:{email_hash}",
            "employee_no_sha256": f"sha256:{employee_no_hash}",
            "request_ip_hash": request_ip_hash,
        },
    )


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
    if settings.candidate_login_test_otp:
        return settings.candidate_login_test_otp
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
