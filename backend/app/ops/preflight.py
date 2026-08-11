"""Fail-closed checks invoked by the versioned Windows PowerShell preflight."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.services.email_service import send_candidate_login_otp


class PreflightError(RuntimeError):
    """A required preflight condition failed without exposing secret values."""


def send_smtp_probe(recipient: str) -> dict[str, str]:
    if settings.environment not in {"internal", "production"}:
        raise PreflightError("SMTP probe requires a formal runtime profile.")
    if settings.candidate_login_email_delivery_mode.strip().lower() != "smtp":
        raise PreflightError("SMTP delivery mode is not enabled.")
    if not recipient.strip() or "@" not in recipient:
        raise PreflightError("PREFLIGHT_SMTP_RECIPIENT is missing or invalid.")

    sent_at = datetime.now(UTC)
    send_candidate_login_otp(
        to_email=recipient.strip(),
        candidate_name="Internal Exam Preflight",
        otp="000000",
        expires_at=sent_at + timedelta(minutes=1),
    )
    return {
        "status": "passed",
        "check": "real_smtp_delivery",
        "sent_at": sent_at.isoformat(),
        "recipient_domain": recipient.strip().rsplit("@", 1)[-1].lower(),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Internal exam formal preflight")
    subparsers = parser.add_subparsers(dest="action", required=True)
    smtp_parser = subparsers.add_parser("smtp", help="Send one real SMTP probe")
    smtp_parser.add_argument(
        "--recipient", default=os.getenv("PREFLIGHT_SMTP_RECIPIENT", "")
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = send_smtp_probe(args.recipient)
    except Exception as exc:
        sys.stderr.write(f"preflight_failed check=smtp error={type(exc).__name__}\n")
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
