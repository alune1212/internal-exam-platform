import hashlib
from collections import OrderedDict, deque
from time import monotonic

from fastapi import Request

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
