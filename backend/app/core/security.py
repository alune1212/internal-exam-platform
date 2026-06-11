from datetime import UTC, datetime
from secrets import token_urlsafe


def create_session_token(subject: str) -> str:
    issued_at = int(datetime.now(UTC).timestamp())
    nonce = token_urlsafe(16)
    return f"{subject}.{issued_at}.{nonce}"


def constant_time_equals(left: str, right: str) -> bool:
    if len(left) != len(right):
        return False
    result = 0
    for left_char, right_char in zip(left.encode(), right.encode(), strict=True):
        result |= left_char ^ right_char
    return result == 0
