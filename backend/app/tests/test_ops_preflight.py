from datetime import UTC, datetime
from typing import Any, cast

import pytest

from app.ops import preflight


def _proxy_values(**overrides: object) -> dict[str, Any]:
    values: dict[str, Any] = {
        "environment": "staging",
        "gateway_subnet": "172.31.0.0/24",
        "gateway_ip_range": "172.31.0.128/25",
        "candidate_gateway_ip": "172.31.0.2",
        "operator_gateway_ip": "172.31.0.3",
        "forwarded_allow_ips": "172.31.0.2,172.31.0.3",
    }
    values.update(overrides)
    return values


def test_proxy_network_preflight_requires_explicit_non_overlapping_values() -> None:
    result = preflight.validate_proxy_network(**_proxy_values())
    assert result["gateway_subnet"] == "172.31.0.0/24"

    with pytest.raises(preflight.PreflightError, match="configuration_missing"):
        preflight.validate_proxy_network(**_proxy_values(gateway_subnet=None))
    with pytest.raises(preflight.PreflightError, match="subnet_unapproved"):
        preflight.validate_proxy_network(**_proxy_values(gateway_subnet="192.0.2.0/24"))
    with pytest.raises(preflight.PreflightError, match="subnet_unapproved"):
        preflight.validate_proxy_network(
            **_proxy_values(gateway_subnet="172.30.0.0/24")
        )
    with pytest.raises(preflight.PreflightError, match="configuration_missing"):
        preflight.validate_proxy_network(**_proxy_values(gateway_ip_range=None))
    with pytest.raises(preflight.PreflightError, match="ip_range_invalid"):
        preflight.validate_proxy_network(
            **_proxy_values(gateway_ip_range="172.32.0.128/25")
        )
    with pytest.raises(preflight.PreflightError, match="ip_range_conflict"):
        preflight.validate_proxy_network(
            **_proxy_values(gateway_ip_range="172.31.0.0/29")
        )
    with pytest.raises(preflight.PreflightError, match="overlap"):
        preflight.validate_proxy_network(
            **_proxy_values(active_networks=("172.31.0.0/16",))
        )


def test_proxy_network_preflight_rejects_peer_and_rendered_config_mismatch() -> None:
    with pytest.raises(preflight.PreflightError, match="allowlist_mismatch"):
        preflight.validate_proxy_network(**_proxy_values(forwarded_allow_ips="*"))

    with pytest.raises(preflight.PreflightError, match="rendered_mismatch"):
        preflight.validate_proxy_network(
            **_proxy_values(
                rendered_config=(
                    "subnet: 172.31.0.0/24\n"
                    "ipv4_address: 172.31.0.2\n"
                    "ipv4_address: 172.31.0.3\n"
                    "--forwarded-allow-ips=172.30.0.2,172.30.0.3\n"
                )
            )
        )


def test_smtp_probe_rejects_non_formal_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight.settings, "environment", "development")

    with pytest.raises(preflight.PreflightError):
        preflight.send_smtp_probe("operator@example.com")


def test_smtp_probe_sends_redacted_formal_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deliveries: list[dict[str, object]] = []
    monkeypatch.setattr(preflight.settings, "environment", "internal")
    monkeypatch.setattr(
        preflight.settings, "candidate_login_email_delivery_mode", "smtp"
    )
    monkeypatch.setattr(
        preflight,
        "send_candidate_login_otp",
        lambda **kwargs: deliveries.append(kwargs),
    )

    result = preflight.send_smtp_probe("Operator@Example.com")

    assert result["status"] == "passed"
    assert result["recipient_domain"] == "example.com"
    assert "operator" not in str(result).lower()
    assert deliveries[0]["otp"] == "000000"
    assert cast("datetime", deliveries[0]["expires_at"]) > datetime.now(UTC)
