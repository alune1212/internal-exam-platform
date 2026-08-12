import hashlib
from collections import OrderedDict, deque
from datetime import UTC, datetime, timedelta
from time import monotonic

from fastapi import Request
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainError


class PublicTokenRateLimitError(DomainError):
    status_code = 429

    def __init__(self) -> None:
        super().__init__("请求过于频繁，请稍后再试。")


# OrderedDict preserves insertion order so we can evict the oldest key in O(1)
# without scanning all keys to find the smallest timestamp.
_attempts: OrderedDict[tuple[str, str], deque[float]] = OrderedDict()
_IDENTIFIER_KEY_PREFIX = "sha256:"
# A single transaction-scoped PostgreSQL advisory lock keeps the quota
# count-and-insert boundary serialized across workers.  A conservative global
# lock is acceptable for the first phase's bounded OTP traffic and avoids
# introducing Redis/Celery.  SQLite test sessions intentionally no-op.
_OTP_QUOTA_ADVISORY_LOCK_KEY = 0x4558504F545F5154


def check_public_token_rate_limit(
    request: Request, *, bucket: str, identifier: str | None
) -> None:
    now = monotonic()
    window_seconds = settings.public_token_rate_limit_window_seconds
    max_attempts = settings.public_token_rate_limit_count
    keys = [
        (bucket, f"ip:{_client_ip(request)}"),
        (bucket, f"id:{_normalize_identifier(identifier)}"),
    ]
    for key in keys:
        if key in _attempts:
            _attempts.move_to_end(key)
    queues = [_attempts.setdefault(key, deque()) for key in keys]
    for queue in queues:
        _prune(queue, now, window_seconds)
    if any(len(queue) >= max_attempts for queue in queues):
        raise PublicTokenRateLimitError()
    for queue in queues:
        queue.append(now)
    _enforce_max_keys(now, window_seconds)


def check_candidate_otp_send_rate_limit(
    db: Session,
    *,
    normalized_email: str,
    request_ip_hash: str | None,
    now: datetime | None = None,
) -> None:
    """Enforce persisted OTP send windows.

    The in-memory limiter above is intentionally retained as a cheap burst
    guard.  These counters are derived from committed challenge rows so a
    process restart or a second backend worker cannot reset per-email,
    per-source, or global quotas.  Invitation delivery never calls this
    function and therefore has an independent budget.
    """

    now = now or datetime.now(UTC)
    window_seconds = int(
        getattr(
            settings,
            "candidate_login_email_rate_limit_window_seconds",
            settings.public_token_rate_limit_window_seconds,
        )
    )
    source_window_seconds = int(
        getattr(
            settings,
            "candidate_login_source_rate_limit_window_seconds",
            window_seconds,
        )
    )
    global_window_seconds = int(
        getattr(
            settings,
            "candidate_login_global_rate_limit_window_seconds",
            window_seconds,
        )
    )
    email_limit = int(getattr(settings, "candidate_login_email_rate_limit_count", 5))
    source_limit = int(getattr(settings, "candidate_login_source_rate_limit_count", 20))
    global_limit = int(
        getattr(settings, "candidate_login_global_rate_limit_count", 100)
    )

    # Import lazily to avoid a core -> models import cycle at module import
    # time.  ``normalized_email`` is indexed by the migration.
    from app.models import CandidateLoginChallenge

    _acquire_otp_quota_lock(db)

    email_since = now - timedelta(seconds=max(window_seconds, 1))
    email_count = (
        db.query(func.count(CandidateLoginChallenge.id))
        .filter(
            CandidateLoginChallenge.email == normalized_email,
            CandidateLoginChallenge.created_at >= email_since,
        )
        .scalar()
        or 0
    )
    if email_count >= email_limit:
        raise PublicTokenRateLimitError()

    if request_ip_hash:
        source_since = now - timedelta(seconds=max(source_window_seconds, 1))
        source_count = (
            db.query(func.count(CandidateLoginChallenge.id))
            .filter(
                CandidateLoginChallenge.request_ip_hash == request_ip_hash,
                CandidateLoginChallenge.created_at >= source_since,
            )
            .scalar()
            or 0
        )
        if source_count >= source_limit:
            raise PublicTokenRateLimitError()

    global_since = now - timedelta(seconds=max(global_window_seconds, 1))
    global_count = (
        db.query(func.count(CandidateLoginChallenge.id))
        .filter(CandidateLoginChallenge.created_at >= global_since)
        .scalar()
        or 0
    )
    if global_count >= global_limit:
        raise PublicTokenRateLimitError()


def _acquire_otp_quota_lock(db: Session) -> None:
    """Serialize persisted quota check + challenge insert on PostgreSQL."""

    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _OTP_QUOTA_ADVISORY_LOCK_KEY},
    )


# Descriptive alias used by tests and future callers that want to be explicit
# about this being the persisted (rather than burst-only) limiter.
check_persisted_candidate_otp_rate_limit = check_candidate_otp_send_rate_limit


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _normalize_identifier(identifier: str | None) -> str:
    normalized = (identifier or "unknown").strip().lower() or "unknown"
    if normalized == "unknown":
        return normalized
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{_IDENTIFIER_KEY_PREFIX}{digest}"


def _prune(queue: deque[float], now: float, window_seconds: int) -> None:
    while queue and now - queue[0] >= window_seconds:
        queue.popleft()


def _enforce_max_keys(now: float, window_seconds: int) -> None:
    """Drop expired keys first, then evict the oldest by insertion time."""
    max_keys = settings.public_token_rate_limit_max_keys
    if len(_attempts) <= max_keys:
        return
    for key in list(_attempts):
        queue = _attempts[key]
        _prune(queue, now, window_seconds)
        if not queue:
            del _attempts[key]
            if len(_attempts) <= max_keys:
                return
    # Still over the cap after pruning: drop the oldest inserted key in O(1)
    # using OrderedDict's insertion order.
    while len(_attempts) > max_keys:
        _attempts.popitem(last=False)
