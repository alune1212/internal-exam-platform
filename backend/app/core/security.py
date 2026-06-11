import hmac
from datetime import UTC, datetime
from secrets import token_urlsafe


def create_session_token(subject: str) -> str:
    issued_at = int(datetime.now(UTC).timestamp())
    nonce = token_urlsafe(16)
    return f"{subject}.{issued_at}.{nonce}"


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
