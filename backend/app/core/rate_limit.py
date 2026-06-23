from collections import defaultdict, deque
from time import monotonic

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import DomainError


class PublicTokenRateLimitError(DomainError):
    status_code = 429

    def __init__(self) -> None:
        super().__init__("请求过于频繁，请稍后再试。")


_attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)


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
    queues = [_attempts[key] for key in keys]
    for queue in queues:
        _prune(queue, now, window_seconds)
    if any(len(queue) >= max_attempts for queue in queues):
        raise PublicTokenRateLimitError()
    for queue in queues:
        queue.append(now)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _normalize_identifier(identifier: str | None) -> str:
    return (identifier or "unknown").strip().lower() or "unknown"


def _prune(queue: deque[float], now: float, window_seconds: int) -> None:
    while queue and now - queue[0] >= window_seconds:
        queue.popleft()
