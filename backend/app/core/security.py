import hmac
from base64 import urlsafe_b64encode
from datetime import UTC, datetime
from hashlib import sha256
from secrets import token_urlsafe


def create_session_token(subject: str) -> str:
    issued_at = int(datetime.now(UTC).timestamp())
    nonce = token_urlsafe(16)
    payload = f"{subject}.{issued_at}.{nonce}"
    return f"{payload}.{_sign(payload)}"


def verify_session_token(
    token: str, *, subject: str, secret: str, max_age_seconds: int | None = None
) -> bool:
    parts = token.split(".")
    if len(parts) != 4:
        return False
    token_subject, issued_at, nonce, signature = parts
    if token_subject != subject or not issued_at.isdigit() or not nonce:
        return False
    if max_age_seconds is None:
        from app.core.config import settings

        max_age_seconds = settings.token_ttl_seconds
    now = int(datetime.now(UTC).timestamp())
    issued_at_int = int(issued_at)
    if issued_at_int > now:
        return False
    if now - issued_at_int > max_age_seconds:
        return False
    payload = ".".join(parts[:3])
    return constant_time_equals(signature, _sign(payload, secret=secret))


def create_candidate_token(candidate_id: int) -> str:
    return create_session_token(f"candidate:{candidate_id}")


def create_admin_token(operator_username: str) -> str:
    return create_session_token(f"admin:{operator_username}")


def parse_admin_token(token: str) -> str | None:
    from app.core.config import settings

    active_username, _active_password = settings.configured_active_operator
    if not active_username:
        return None
    if verify_session_token(
        token,
        subject=f"admin:{active_username}",
        secret=settings.token_secret,
        max_age_seconds=settings.admin_token_ttl_seconds,
    ):
        return active_username
    # Keep the pre-named-operator token shape for development fixtures only,
    # while retaining the same single-active-operator switch semantics.
    if (
        settings.environment == "development"
        and not settings.backup_operator_enabled
        and verify_session_token(
            token,
            subject=active_username,
            secret=settings.token_secret,
            max_age_seconds=settings.admin_token_ttl_seconds,
        )
    ):
        return active_username
    return None


def parse_candidate_token(
    token: str, *, max_age_seconds: int | None = None
) -> int | None:
    from app.core.config import settings

    parts = token.split(".")
    if len(parts) != 4 or not parts[0].startswith("candidate:"):
        return None
    raw_id = parts[0].removeprefix("candidate:")
    if not raw_id.isdigit():
        return None
    configured_max_age = (
        settings.candidate_token_ttl_seconds
        if max_age_seconds is None
        else max_age_seconds
    )
    effective_max_age = min(configured_max_age, 4 * 60 * 60)
    if not verify_session_token(
        token,
        subject=parts[0],
        secret=settings.token_secret,
        max_age_seconds=effective_max_age,
    ):
        return None
    return int(raw_id)


def _sign(payload: str, *, secret: str | None = None) -> str:
    from app.core.config import settings

    key = (secret or settings.token_secret).encode("utf-8")
    digest = hmac.new(key, payload.encode("utf-8"), sha256).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
