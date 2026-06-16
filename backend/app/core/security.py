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
    if now - int(issued_at) > max_age_seconds:
        return False
    payload = ".".join(parts[:3])
    return constant_time_equals(signature, _sign(payload, secret=secret))


def create_candidate_token(candidate_id: int) -> str:
    return create_session_token(f"candidate:{candidate_id}")


def parse_candidate_token(token: str) -> int | None:
    from app.core.config import settings

    parts = token.split(".")
    if len(parts) != 4 or not parts[0].startswith("candidate:"):
        return None
    raw_id = parts[0].removeprefix("candidate:")
    if not raw_id.isdigit():
        return None
    if not verify_session_token(token, subject=parts[0], secret=settings.token_secret):
        return None
    return int(raw_id)


def _sign(payload: str, *, secret: str | None = None) -> str:
    from app.core.config import settings

    key = (secret or settings.token_secret).encode("utf-8")
    digest = hmac.new(key, payload.encode("utf-8"), sha256).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
