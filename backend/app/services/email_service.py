import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

from app.core.config import settings
from app.core.exceptions import DomainError


class EmailDeliveryError(DomainError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("验证码发送失败，请稍后重试。")


@dataclass(frozen=True)
class CandidateLoginEmail:
    to_email: str
    candidate_name: str
    otp: str
    expires_at: datetime


candidate_login_email_outbox: list[CandidateLoginEmail] = []


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
    raise EmailDeliveryError()


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
    except OSError as exc:
        raise EmailDeliveryError() from exc
