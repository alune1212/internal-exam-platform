from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _compose_service_ports(service_name: str) -> list[str]:
    lines = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8").splitlines()
    service_header = f"  {service_name}:"
    service_start = lines.index(service_header)
    ports: list[str] = []
    in_ports_block = False

    for line in lines[service_start + 1 :]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        if line == "    ports:":
            in_ports_block = True
            continue
        if not in_ports_block:
            continue
        if line.startswith("      - "):
            ports.append(line.removeprefix("      - ").strip().strip('"'))
            continue
        if line.startswith("    ") and not line.startswith("      "):
            break

    return ports


def test_default_nginx_publish_uses_loopback_host() -> None:
    assert _compose_service_ports("nginx") == ["127.0.0.1:8080:80"]
