"""Disposable SMTP capture service used only by the Compose browser gate."""

from __future__ import annotations

import asyncio
import json
import re
from collections import deque
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs, urlparse

SMTP_PORT = 1025
HTTP_PORT = 8025
OTP_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
MESSAGES: deque[dict[str, str]] = deque(maxlen=100)


def _latest_message(recipient: str = "", kind: str = "") -> dict[str, str] | None:
    """Return the latest captured message matching safe test-only filters."""

    return next(
        (
            item
            for item in reversed(MESSAGES)
            if (not recipient or item["to"].casefold() == recipient)
            and (not kind or (kind == "otp" and bool(item["otp"])))
        ),
        None,
    )


async def _smtp_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    writer.write(b"220 fake-smtp ESMTP ready\r\n")
    await writer.drain()
    data_mode = False
    body: list[bytes] = []
    try:
        while line := await reader.readline():
            stripped = line.rstrip(b"\r\n")
            if data_mode:
                if stripped == b".":
                    _capture_message(b"\n".join(body))
                    body.clear()
                    data_mode = False
                    writer.write(b"250 2.0.0 queued\r\n")
                else:
                    body.append(
                        stripped[1:] if stripped.startswith(b"..") else stripped
                    )
                await writer.drain()
                continue

            command = stripped.decode("ascii", errors="ignore").upper()
            if command.startswith(("EHLO", "HELO")):
                writer.write(b"250-fake-smtp\r\n250 SIZE 1048576\r\n")
            elif command.startswith(("MAIL FROM", "RCPT TO", "RSET", "NOOP")):
                writer.write(b"250 2.0.0 ok\r\n")
            elif command == "DATA":
                data_mode = True
                writer.write(b"354 end with <CRLF>.<CRLF>\r\n")
            elif command == "QUIT":
                writer.write(b"221 2.0.0 bye\r\n")
                await writer.drain()
                break
            else:
                writer.write(b"502 5.5.1 unsupported\r\n")
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


def _capture_message(raw: bytes) -> None:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    content = message.get_body(preferencelist=("plain",))
    text = content.get_content() if content is not None else message.get_content()
    otp_match = OTP_PATTERN.search(str(text))
    MESSAGES.append(
        {
            "to": str(message.get("To", "")),
            "subject": str(message.get("Subject", "")),
            "otp": otp_match.group(1) if otp_match else "",
        }
    )


async def _http_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        request_line = (
            (await reader.readline()).decode("ascii", errors="ignore").strip()
        )
        while (await reader.readline()) not in {b"\r\n", b"\n", b""}:
            pass
        method, target, _ = request_line.split(" ", 2)
        parsed = urlparse(target)
        recipient = parse_qs(parsed.query).get("recipient", [""])[0].casefold()
        kind = parse_qs(parsed.query).get("kind", [""])[0].casefold()
        if kind not in {"", "otp"}:
            status, payload = "400 Bad Request", {"error": "unsupported kind"}
        elif method != "GET" or parsed.path != "/messages/latest":
            status, payload = "404 Not Found", {"error": "not found"}
        else:
            message = _latest_message(recipient, kind)
            status = "200 OK" if message else "404 Not Found"
            payload = message or {"error": "message not found"}
    except (ValueError, UnicodeError):
        status, payload = "400 Bad Request", {"error": "bad request"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    writer.write(
        (
            f"HTTP/1.1 {status}\r\nContent-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
        ).encode("ascii")
        + body
    )
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main() -> None:
    smtp = await asyncio.start_server(_smtp_client, "0.0.0.0", SMTP_PORT)  # noqa: S104
    http = await asyncio.start_server(_http_client, "0.0.0.0", HTTP_PORT)  # noqa: S104
    async with smtp, http:
        await asyncio.gather(smtp.serve_forever(), http.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
