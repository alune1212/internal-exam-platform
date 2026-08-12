"""Email OTP authentication and platform-account lifecycle services."""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.rate_limit import check_candidate_otp_send_rate_limit
from app.core.security import create_candidate_token
from app.core.time import ensure_aware
from app.models import Candidate, CandidateLoginChallenge, ExamCandidateScope
from app.schemas.candidate import (
    AccountAdminRead,
    AccountProfileRead,
    AccountUnavailableResponse,
    AuthenticatedCandidateLoginResponse,
    CandidateLoginChallengeResponse,
    CandidateLoginRequest,
    CandidateLoginVerifyRequest,
    CandidateLoginVerifyResponse,
    CandidateProfileUpdate,
    CandidateRead,
    RegistrationCompleteRequest,
    RegistrationRequiredResponse,
    normalize_email,
)
from app.services.operational_lock_service import assert_backup_write_allowed

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import Request
    from sqlalchemy.orm import Session


class CandidateLoginChallengeError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("验证码无效或已过期")


class RegistrationCredentialError(DomainError):
    status_code = 400

    def __init__(self) -> None:
        super().__init__("注册凭证无效或已过期")


class AccountUnavailableError(DomainError):
    status_code = 403

    def __init__(self) -> None:
        super().__init__("账号暂不可用，请联系管理员重新激活。")


class AccountNotFoundError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("账号不存在")


class AccountStatusTransitionError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("仅已完成注册的账号支持启用或停用")


@dataclass(frozen=True)
class CandidateLoginEmailPayload:
    """Data handed to the route's post-commit delivery task."""

    to_email: str
    candidate_name: str
    otp: str
    expires_at: datetime


@dataclass(frozen=True)
class CandidateLoginChallengeRequestResult:
    response: CandidateLoginChallengeResponse
    email: CandidateLoginEmailPayload


def request_candidate_login_challenge(
    db: Session,
    payload: CandidateLoginRequest,
    *,
    request_ip: str | None = None,
) -> CandidateLoginChallengeRequestResult:
    """Create an email-bound OTP challenge and commit before delivery.

    The lookup is deliberately performed only to associate an existing
    account/suggested name.  Unknown valid mailboxes follow the same path and
    are sent a real OTP; no sentinel row is created or consulted.
    """

    assert_backup_write_allowed(db)
    email = normalize_email(payload.email)
    now = datetime.now(UTC)
    request_ip_hash = _hash_request_source(request_ip)
    check_candidate_otp_send_rate_limit(
        db, normalized_email=email, request_ip_hash=request_ip_hash, now=now
    )

    _cleanup_expired_challenges(db, now)
    _enforce_resend_cooldown(db, email, now)
    _consume_open_challenges(db, email, now)

    account = _find_account_by_email(db, email)
    otp = _generate_otp()
    expires_at = now + timedelta(seconds=settings.candidate_login_otp_ttl_seconds)
    challenge = CandidateLoginChallenge(
        candidate_id=account.id if account is not None else None,
        email=email,
        delivery_channel="email",
        otp_hash=_hash_otp(otp),
        expires_at=expires_at,
        request_ip_hash=request_ip_hash,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    logger.info(
        "candidate_login.challenge_created",
        extra={
            "event": "candidate_login.challenge_created",
            "challenge_id": challenge.id,
            "account_id": account.id if account is not None else None,
            "request_ip_hash": request_ip_hash,
        },
    )

    candidate_name = (
        (getattr(account, "name", None) or "用户") if account is not None else "用户"
    )
    return CandidateLoginChallengeRequestResult(
        response=CandidateLoginChallengeResponse(
            challenge_id=challenge.id,
            expires_at=ensure_aware(challenge.expires_at),
            resend_available_at=now
            + timedelta(seconds=settings.candidate_login_otp_resend_cooldown_seconds),
        ),
        email=CandidateLoginEmailPayload(
            to_email=email,
            candidate_name=candidate_name,
            otp=otp,
            expires_at=expires_at,
        ),
    )


def verify_candidate_login_challenge(
    db: Session, payload: CandidateLoginVerifyRequest
) -> CandidateLoginVerifyResponse:
    """Atomically consume an OTP and return the appropriate auth outcome."""

    assert_backup_write_allowed(db)
    challenge = db.get(CandidateLoginChallenge, payload.challenge_id)
    if challenge is None:
        raise CandidateLoginChallengeError()
    now = datetime.now(UTC)
    if not _challenge_is_open(challenge, now):
        raise CandidateLoginChallengeError()
    if not hmac.compare_digest(challenge.otp_hash, _hash_otp(payload.otp)):
        _increment_attempt_count(db, challenge.id, now)
        db.commit()
        raise CandidateLoginChallengeError()

    if _consume_challenge(db, challenge.id, now) == 0:
        db.rollback()
        raise CandidateLoginChallengeError()

    email = normalize_email(challenge.email)
    account = _find_account_by_email(db, email)
    if account is not None and account.status == "inactive":
        db.commit()
        logger.info(
            "candidate_login.verified",
            extra={
                "event": "candidate_login.verified",
                "challenge_id": challenge.id,
                "account_id": account.id,
                "outcome": "account_unavailable",
            },
        )
        return AccountUnavailableResponse(outcome="account_unavailable")

    if account is not None and account.status == "active":
        db.commit()
        db.refresh(account)
        logger.info(
            "candidate_login.verified",
            extra={
                "event": "candidate_login.verified",
                "challenge_id": challenge.id,
                "account_id": account.id,
                "outcome": "authenticated",
            },
        )
        return _authenticated_response(account)

    credential = token_urlsafe(32)
    challenge.registration_credential_hash = _hash_registration_credential(credential)
    registration_expires_at = now + timedelta(
        seconds=_registration_credential_ttl_seconds()
    )
    challenge.registration_credential_expires_at = registration_expires_at
    challenge.registration_credential_consumed_at = None
    # Pending imports keep their account association; unknown mailboxes remain
    # unassociated until registration completion creates the account.
    if account is not None and getattr(challenge, "candidate_id", None) is None:
        challenge.candidate_id = account.id
    db.commit()
    logger.info(
        "candidate_login.verified",
        extra={
            "event": "candidate_login.verified",
            "challenge_id": challenge.id,
            "account_id": account.id if account is not None else None,
            "outcome": "registration_required",
        },
    )
    return RegistrationRequiredResponse(
        outcome="registration_required",
        registration_credential=credential,
        registration_expires_at=registration_expires_at,
        email=email,
        suggested_display_name=_registration_name_suggestion(db, account),
    )


def complete_registration(
    db: Session, payload: RegistrationCompleteRequest
) -> AuthenticatedCandidateLoginResponse:
    """Consume a registration credential and activate/create the account."""

    assert_backup_write_allowed(db)
    now = datetime.now(UTC)
    credential_hash = _hash_registration_credential(payload.registration_credential)
    challenge = (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.registration_credential_hash == credential_hash,
            CandidateLoginChallenge.registration_credential_consumed_at.is_(None),
            CandidateLoginChallenge.registration_credential_expires_at > now,
        )
        .order_by(CandidateLoginChallenge.id.desc())
        .first()
    )
    if challenge is None:
        raise RegistrationCredentialError()

    # The conditional update closes replay races between two completion calls.
    consumed = (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.id == challenge.id,
            CandidateLoginChallenge.registration_credential_consumed_at.is_(None),
            CandidateLoginChallenge.registration_credential_expires_at > now,
        )
        .update(
            {CandidateLoginChallenge.registration_credential_consumed_at: now},
            synchronize_session=False,
        )
    )
    if consumed == 0:
        db.rollback()
        raise RegistrationCredentialError()

    email = normalize_email(challenge.email)
    account = _find_account_by_email(db, email)
    if account is None:
        account = Candidate(email=email, name=payload.display_name, status="active")
        try:
            # Keep the credential-consumption update in the outer transaction
            # while isolating only the unique-email insert in a savepoint.  A
            # concurrent completion may win the unique race; rolling back the
            # whole session here would make our credential replayable.
            with db.begin_nested():
                db.add(account)
                db.flush()
        except IntegrityError:
            account = _find_account_by_email(db, email)
            if account is None:
                # The insert lost a unique race but the winner disappeared
                # before it could be read.  Persist the credential consume so
                # this ambiguous completion cannot be replayed.
                db.commit()
                raise RegistrationCredentialError() from None

    # Re-evaluate the winner's status after a unique-email race as well as
    # for an account that was present before completion.  Never mint a token
    # for an inactive/pending/non-standard state, and only complete a pending
    # account with this one-time credential.  An active winner's display name
    # is intentionally left untouched.
    if account.status == "inactive":
        db.commit()
        raise AccountUnavailableError()
    if account.status == "pending":
        account.name = payload.display_name
        account.status = "active"
    if account.status != "active":
        db.commit()
        raise RegistrationCredentialError()
    # A concurrent/duplicate completion must not overwrite an active name.
    challenge.candidate_id = account.id
    db.commit()
    db.refresh(account)
    logger.info(
        "candidate_account.registration_completed",
        extra={
            "event": "candidate_account.registration_completed",
            "challenge_id": challenge.id,
            "account_id": account.id,
            "status": account.status,
        },
    )
    return _authenticated_response(account)


def get_account_profile(db: Session, candidate_id: int) -> AccountProfileRead:
    account = _get_account(db, candidate_id)
    return AccountProfileRead.model_validate(account)


def update_account_profile(
    db: Session, candidate_id: int, payload: CandidateProfileUpdate
) -> AccountProfileRead:
    assert_backup_write_allowed(db)
    account = _get_account(db, candidate_id)
    account.name = payload.display_name.strip()
    db.commit()
    db.refresh(account)
    logger.info(
        "candidate_account.profile_updated",
        extra={
            "event": "candidate_account.profile_updated",
            "account_id": account.id,
            "status": account.status,
        },
    )
    return AccountProfileRead.model_validate(account)


def list_accounts(
    db: Session,
    *,
    query: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AccountAdminRead]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    statement = db.query(Candidate)
    if query and query.strip():
        search = query.strip().lower()
        statement = statement.filter(
            (func.lower(Candidate.email).contains(search))
            | (func.lower(Candidate.name).contains(search))
        )
    if status in {"pending", "active", "inactive"}:
        statement = statement.filter(Candidate.status == status)
    accounts = statement.order_by(Candidate.id).offset(offset).limit(limit).all()
    return [AccountAdminRead.model_validate(account) for account in accounts]


def set_account_status(
    db: Session,
    candidate_id: int,
    status: str,
    *,
    operator_subject: str | None = None,
    request: Request | None = None,
) -> AccountAdminRead:
    if status not in {"active", "inactive"}:
        raise AccountStatusTransitionError()
    assert_backup_write_allowed(db)
    account = _get_account(db, candidate_id)
    if (
        account.status == "pending"
        or not (getattr(account, "name", None) or "").strip()
    ):
        raise AccountStatusTransitionError()
    previous_status = account.status
    if previous_status == status:
        return AccountAdminRead.model_validate(account)
    account.status = status
    if operator_subject:
        # Import lazily to keep the account service usable by worker jobs that
        # do not initialize the admin API module.
        from app.services.audit_service import record_admin_event

        record_admin_event(
            db,
            operator_subject=operator_subject,
            action=(
                "account_activated" if status == "active" else "account_deactivated"
            ),
            target_type="account",
            target_id=account.id,
            metadata={
                "account_id": account.id,
                "from_status": previous_status,
                "to_status": status,
            },
            request=request,
        )
    db.commit()
    db.refresh(account)
    logger.info(
        "candidate_account.status_changed",
        extra={
            "event": "candidate_account.status_changed",
            "account_id": account.id,
            "status": account.status,
        },
    )
    return AccountAdminRead.model_validate(account)


def get_active_account(db: Session, candidate_id: int) -> Candidate:
    """Load the current account state for the shared candidate dependency."""

    account = _get_account(db, candidate_id)
    if account.status != "active":
        raise AccountUnavailableError()
    return account


def _authenticated_response(account: Candidate) -> AuthenticatedCandidateLoginResponse:
    token_expires_at = datetime.now(UTC) + timedelta(
        seconds=_candidate_token_ttl_seconds()
    )
    return AuthenticatedCandidateLoginResponse(
        outcome="authenticated",
        account=CandidateRead.model_validate(account),
        token=create_candidate_token(account.id),
        token_expires_at=token_expires_at,
    )


def _get_account(db: Session, candidate_id: int) -> Candidate:
    account = db.get(Candidate, candidate_id, populate_existing=True)
    if account is None:
        raise AccountNotFoundError()
    return account


def _find_account_by_email(db: Session, email: str) -> Candidate | None:
    return (
        db.query(Candidate)
        .filter(func.lower(Candidate.email) == normalize_email(email))
        .order_by(Candidate.id)
        .first()
    )


def _registration_name_suggestion(db: Session, account: Candidate | None) -> str | None:
    if account is None:
        return None
    account_name = (getattr(account, "name", None) or "").strip()
    if account_name:
        return account_name
    scope = (
        db.query(ExamCandidateScope)
        .filter(ExamCandidateScope.candidate_id == account.id)
        .order_by(ExamCandidateScope.id.desc())
        .first()
    )
    return (scope.roster_name or "").strip() if scope is not None else None


def _challenge_is_open(challenge: CandidateLoginChallenge, now: datetime) -> bool:
    return (
        challenge.consumed_at is None
        and ensure_aware(challenge.expires_at) > now
        and challenge.attempt_count < settings.candidate_login_otp_attempt_limit
    )


def _increment_attempt_count(db: Session, challenge_id: int, now: datetime) -> None:
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
    return (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.id == challenge_id,
            CandidateLoginChallenge.consumed_at.is_(None),
            CandidateLoginChallenge.attempt_count
            < settings.candidate_login_otp_attempt_limit,
            CandidateLoginChallenge.expires_at > now,
        )
        .update({CandidateLoginChallenge.consumed_at: now}, synchronize_session=False)
    )


def _consume_open_challenges(db: Session, email: str, now: datetime) -> None:
    (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.email == email,
            CandidateLoginChallenge.consumed_at.is_(None),
        )
        .update({CandidateLoginChallenge.consumed_at: now}, synchronize_session=False)
    )


def _enforce_resend_cooldown(db: Session, email: str, now: datetime) -> None:
    cooldown = settings.candidate_login_otp_resend_cooldown_seconds
    if cooldown <= 0:
        return
    latest = (
        db.query(CandidateLoginChallenge)
        .filter(CandidateLoginChallenge.email == email)
        .order_by(CandidateLoginChallenge.created_at.desc())
        .first()
    )
    if latest is None:
        return
    if (now - ensure_aware(latest.created_at)).total_seconds() < cooldown:
        from app.core.rate_limit import PublicTokenRateLimitError

        raise PublicTokenRateLimitError()


def _cleanup_expired_challenges(db: Session, now: datetime) -> None:
    batch_size = max(
        1, int(getattr(settings, "candidate_login_cleanup_batch_size", 100))
    )
    retention_seconds = max(
        int(
            getattr(
                settings,
                "candidate_login_challenge_retention_seconds",
                getattr(
                    settings,
                    "candidate_login_global_rate_limit_window_seconds",
                    24 * 60 * 60,
                ),
            )
        ),
        60,
    )
    cleanup_before = now - timedelta(seconds=retention_seconds)
    expired = (
        db.query(CandidateLoginChallenge)
        .filter(
            CandidateLoginChallenge.created_at <= cleanup_before,
            CandidateLoginChallenge.expires_at <= now,
        )
        .order_by(CandidateLoginChallenge.id)
        .limit(batch_size)
        .all()
    )
    for challenge in expired:
        db.delete(challenge)
    if expired:
        db.flush()


def _generate_otp() -> str:
    test_otp = settings.candidate_login_test_otp
    if test_otp:
        return test_otp
    from secrets import randbelow

    return f"{randbelow(1_000_000):06d}"


def _hash_otp(otp: str) -> str:
    key = settings.token_secret.encode("utf-8")
    payload = f"candidate-login-otp:{otp}".encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _hash_registration_credential(credential: str) -> str:
    key = settings.token_secret.encode("utf-8")
    payload = f"candidate-registration:{credential}".encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _hash_request_source(request_ip: str | None) -> str | None:
    if not request_ip:
        return None
    digest = hashlib.sha256(request_ip.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _registration_credential_ttl_seconds() -> int:
    return min(
        settings.candidate_login_otp_ttl_seconds,
        int(
            getattr(
                settings,
                "candidate_registration_credential_ttl_seconds",
                settings.candidate_login_otp_ttl_seconds,
            )
        ),
    )


def _candidate_token_ttl_seconds() -> int:
    return min(int(settings.candidate_token_ttl_seconds), 4 * 60 * 60)
