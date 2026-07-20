import logging
import smtplib
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

from app.core.config import settings
from app.core.exceptions import DomainError

logger = logging.getLogger(__name__)

# Bounded in-memory outbox used by the `memory` delivery mode (dev / test only).
# `deque(maxlen=N)` evicts the oldest entry when full, so a long-lived process
# cannot grow the queue without bound and accumulate plaintext OTPs in memory.
CANDIDATE_LOGIN_EMAIL_OUTBOX_MAXLEN = 64


class EmailDeliveryError(DomainError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("验证码发送失败，请稍后重试。")


class TransientEmailDeliveryError(EmailDeliveryError):
    pass


class PermanentEmailDeliveryError(EmailDeliveryError):
    pass


@dataclass(frozen=True)
class CandidateLoginEmail:
    to_email: str
    candidate_name: str
    otp: str
    expires_at: datetime


candidate_login_email_outbox: deque[CandidateLoginEmail] = deque(
    maxlen=CANDIDATE_LOGIN_EMAIL_OUTBOX_MAXLEN
)


def clear_candidate_login_email_outbox() -> None:
    """Test fixture helper: drain the in-memory outbox between cases."""
    candidate_login_email_outbox.clear()


def send_candidate_login_otp(
    *, to_email: str, candidate_name: str, otp: str, expires_at: datetime
) -> None:
    delivery = CandidateLoginEmail(
        to_email=to_email,
        candidate_name=candidate_name,
        otp=otp,
        expires_at=expires_at,
    )
    mode = settings.candidate_login_email_delivery_mode.strip().lower()
    if mode == "memory":
        candidate_login_email_outbox.append(delivery)
        return
    if mode == "smtp":
        _send_smtp(delivery)
        return
    raise PermanentEmailDeliveryError()


def deliver_candidate_login_otp(
    *,
    challenge_id: int,
    to_email: str,
    candidate_name: str,
    otp: str,
    expires_at: datetime,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    max_attempts = settings.candidate_login_email_max_attempts
    base_seconds = settings.candidate_login_email_retry_base_seconds
    delivery_kwargs = {
        "to_email": to_email,
        "candidate_name": candidate_name,
        "otp": otp,
        "expires_at": expires_at,
    }

    for attempt in range(1, max_attempts + 1):
        try:
            send_candidate_login_otp(**delivery_kwargs)
        except TransientEmailDeliveryError as exc:
            if attempt == max_attempts:
                _log_delivery_failure(challenge_id, attempt, exc)
                return False
            logger.warning(
                "candidate_login.email_delivery_retry",
                extra={
                    "event": "candidate_login.email_delivery_retry",
                    "challenge_id": challenge_id,
                    "attempt": attempt,
                    "error_type": type(exc).__name__,
                },
            )
            sleep(base_seconds * (2 ** (attempt - 1)))
        except Exception as exc:
            _log_delivery_failure(challenge_id, attempt, exc)
            return False
        else:
            logger.info(
                "candidate_login.email_delivery_succeeded",
                extra={
                    "event": "candidate_login.email_delivery_succeeded",
                    "challenge_id": challenge_id,
                    "attempt": attempt,
                },
            )
            return True
    return False


def _log_delivery_failure(challenge_id: int, attempt: int, exc: Exception) -> None:
    logger.warning(
        "candidate_login.email_delivery_failed",
        extra={
            "event": "candidate_login.email_delivery_failed",
            "challenge_id": challenge_id,
            "attempt": attempt,
            "error_type": type(exc).__name__,
        },
    )


def _send_smtp(delivery: CandidateLoginEmail) -> None:
    message = EmailMessage()
    message["From"] = settings.candidate_login_email_from
    message["To"] = delivery.to_email
    message["Subject"] = "考试平台登录验证码"
    message.set_content(
        "\n".join(
            [
                f"{delivery.candidate_name}，您好：",
                "",
                f"您的考试平台登录验证码是：{delivery.otp}",
                f"验证码将在 {delivery.expires_at.isoformat()} 过期。",
                "",
                "如果不是您本人操作，请忽略本邮件。",
            ]
        )
    )
    try:
        with smtplib.SMTP(
            settings.candidate_login_smtp_host,
            settings.candidate_login_smtp_port,
            timeout=10,
        ) as smtp:
            if settings.candidate_login_smtp_use_tls:
                smtp.starttls()
            if settings.candidate_login_smtp_username:
                smtp.login(
                    settings.candidate_login_smtp_username,
                    settings.candidate_login_smtp_password,
                )
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        if _is_transient_delivery_error(exc):
            raise TransientEmailDeliveryError() from exc
        raise PermanentEmailDeliveryError() from exc


def _is_transient_delivery_error(exc: Exception) -> bool:
    if isinstance(exc, smtplib.SMTPResponseException):
        return 400 <= exc.smtp_code < 500
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return True
    if isinstance(exc, smtplib.SMTPException):
        return False
    return isinstance(exc, OSError)
