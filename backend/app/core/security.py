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


def verify_session_token(token: str, *, subject: str, secret: str) -> bool:
    parts = token.split(".")
    if len(parts) != 4:
        return False
    token_subject, issued_at, nonce, signature = parts
    if token_subject != subject or not issued_at.isdigit() or not nonce:
        return False
    payload = ".".join(parts[:3])
    return constant_time_equals(signature, _sign(payload, secret=secret))


def _sign(payload: str, *, secret: str | None = None) -> str:
    from app.core.config import settings

    key = (secret or settings.token_secret).encode("utf-8")
    digest = hmac.new(key, payload.encode("utf-8"), sha256).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
