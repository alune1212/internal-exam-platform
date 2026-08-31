"""Fail-closed checks invoked by the versioned Windows PowerShell preflight."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Network, ip_address, ip_network
from pathlib import Path

from app.core.config import settings
from app.services.email_service import send_candidate_login_otp


class PreflightError(RuntimeError):
    """A required preflight condition failed without exposing secret values."""


_RFC1918_NETWORKS: tuple[IPv4Network, ...] = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)
_DEVELOPMENT_GATEWAY_SUBNET = IPv4Network("172.30.0.0/24")
_DEVELOPMENT_GATEWAY_IP_RANGE = IPv4Network("172.30.0.128/25")


def validate_proxy_network(
    environment: str,
    gateway_subnet: str | None,
    candidate_gateway_ip: str | None,
    operator_gateway_ip: str | None,
    forwarded_allow_ips: str | None,
    *,
    gateway_ip_range: str | None = None,
    active_networks: Sequence[str] = (),
    rendered_config: str | None = None,
) -> dict[str, str]:
    """Validate the exact two-peer gateway network contract.

    Formal and staging callers must provide every value explicitly.  The
    development defaults live in Compose, but this helper never invents a
    subnet or peer address and therefore cannot silently widen a formal gate.
    """

    profile = environment.strip().lower() if isinstance(environment, str) else ""
    if not profile:
        raise PreflightError("proxy_network_environment_missing")
    if profile not in {"development", "internal", "production", "staging", "formal"}:
        raise PreflightError("proxy_network_environment_invalid")
    values = (
        gateway_subnet,
        candidate_gateway_ip,
        operator_gateway_ip,
        forwarded_allow_ips,
    )
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise PreflightError("proxy_network_configuration_missing")
    if not isinstance(active_networks, Sequence) or isinstance(active_networks, str):
        raise PreflightError("proxy_network_active_invalid")
    if rendered_config is not None and not isinstance(rendered_config, str):
        raise PreflightError("proxy_network_rendered_invalid")
    assert isinstance(gateway_subnet, str)
    assert isinstance(candidate_gateway_ip, str)
    assert isinstance(operator_gateway_ip, str)
    assert isinstance(forwarded_allow_ips, str)

    try:
        gateway = ip_network(gateway_subnet.strip(), strict=True)
    except ValueError:
        raise PreflightError("proxy_network_subnet_invalid") from None
    if (
        gateway.version != 4
        or gateway.prefixlen > 30
        or not any(gateway.subnet_of(approved) for approved in _RFC1918_NETWORKS)
        or (
            profile in {"internal", "production", "staging", "formal"}
            and gateway == _DEVELOPMENT_GATEWAY_SUBNET
        )
    ):
        raise PreflightError("proxy_network_subnet_unapproved")

    if gateway_ip_range is None:
        if profile == "development" and gateway == _DEVELOPMENT_GATEWAY_SUBNET:
            gateway_ip_range = _DEVELOPMENT_GATEWAY_IP_RANGE.with_prefixlen
        else:
            raise PreflightError("proxy_network_configuration_missing")
    if not isinstance(gateway_ip_range, str) or not gateway_ip_range.strip():
        raise PreflightError("proxy_network_configuration_missing")
    try:
        dynamic_range = ip_network(gateway_ip_range.strip(), strict=True)
    except ValueError:
        raise PreflightError("proxy_network_ip_range_invalid") from None
    if (
        dynamic_range.version != 4
        or not dynamic_range.subnet_of(gateway)
        or dynamic_range == gateway
    ):
        raise PreflightError("proxy_network_ip_range_invalid")

    try:
        candidate_ip = ip_address(candidate_gateway_ip.strip())
        operator_ip = ip_address(operator_gateway_ip.strip())
    except ValueError:
        raise PreflightError("proxy_network_gateway_ip_invalid") from None
    if (
        candidate_ip.version != 4
        or operator_ip.version != 4
        or candidate_ip == operator_ip
        or candidate_ip not in gateway
        or operator_ip not in gateway
        or candidate_ip in {gateway.network_address, gateway.broadcast_address}
        or operator_ip in {gateway.network_address, gateway.broadcast_address}
    ):
        raise PreflightError("proxy_network_gateway_ip_mismatch")
    if candidate_ip in dynamic_range or operator_ip in dynamic_range:
        raise PreflightError("proxy_network_ip_range_conflict")

    allowlist = [value.strip() for value in forwarded_allow_ips.split(",")]
    if len(allowlist) != 2 or set(allowlist) != {str(candidate_ip), str(operator_ip)}:
        raise PreflightError("proxy_network_allowlist_mismatch")
    try:
        if any(ip_address(value).version != 4 for value in allowlist):
            raise ValueError
    except ValueError:
        raise PreflightError("proxy_network_allowlist_invalid") from None

    for active_network in active_networks:
        try:
            active = ip_network(active_network.strip(), strict=False)
        except (AttributeError, ValueError):
            raise PreflightError("proxy_network_active_invalid") from None
        if active.version == 4 and gateway.overlaps(active):
            raise PreflightError("proxy_network_overlap")

    if rendered_config is not None:
        expected_markers = (
            f"subnet: {gateway.with_prefixlen}",
            f"ip_range: {dynamic_range.with_prefixlen}",
            f"ipv4_address: {candidate_ip}",
            f"ipv4_address: {operator_ip}",
        )
        if (
            any(marker not in rendered_config for marker in expected_markers)
            or not any(
                marker in rendered_config
                for marker in (
                    f"--forwarded-allow-ips={candidate_ip},{operator_ip}",
                    f"--forwarded-allow-ips={operator_ip},{candidate_ip}",
                )
            )
            or re.search(r"--forwarded-allow-ips=(?:\*|[^\s\"']*/\d+)", rendered_config)
        ):
            raise PreflightError("proxy_network_rendered_mismatch")

    return {
        "environment": profile,
        "gateway_subnet": gateway.with_prefixlen,
        "gateway_ip_range": dynamic_range.with_prefixlen,
        "candidate_gateway_ip": str(candidate_ip),
        "operator_gateway_ip": str(operator_ip),
        "forwarded_allow_ips": f"{candidate_ip},{operator_ip}",
    }


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
    network_parser = subparsers.add_parser(
        "network", help="Validate the static gateway network contract"
    )
    network_parser.add_argument("--environment", default=os.getenv("ENVIRONMENT", ""))
    network_parser.add_argument("--gateway-subnet", default=os.getenv("GATEWAY_SUBNET"))
    network_parser.add_argument(
        "--gateway-ip-range", default=os.getenv("GATEWAY_IP_RANGE")
    )
    network_parser.add_argument(
        "--candidate-gateway-ip", default=os.getenv("CANDIDATE_GATEWAY_IP")
    )
    network_parser.add_argument(
        "--operator-gateway-ip", default=os.getenv("OPERATOR_GATEWAY_IP")
    )
    forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS")
    if forwarded_allow_ips is None:
        candidate_ip = os.getenv("CANDIDATE_GATEWAY_IP", "").strip()
        operator_ip = os.getenv("OPERATOR_GATEWAY_IP", "").strip()
        forwarded_allow_ips = f"{candidate_ip},{operator_ip}"
    network_parser.add_argument("--forwarded-allow-ips", default=forwarded_allow_ips)
    network_parser.add_argument("--active-network", action="append", default=[])
    network_parser.add_argument("--rendered-config", type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.action == "smtp":
            result = send_smtp_probe(args.recipient)
        else:
            rendered_config = (
                args.rendered_config.read_text(encoding="utf-8")
                if args.rendered_config
                else None
            )
            result = validate_proxy_network(
                args.environment,
                args.gateway_subnet,
                args.candidate_gateway_ip,
                args.operator_gateway_ip,
                args.forwarded_allow_ips,
                gateway_ip_range=args.gateway_ip_range,
                active_networks=args.active_network,
                rendered_config=rendered_config,
            )
    except Exception as exc:
        sys.stderr.write(
            f"preflight_failed check={args.action} error={type(exc).__name__}\n"
        )
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
