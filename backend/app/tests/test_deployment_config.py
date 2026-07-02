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


def test_frontend_csp_allows_configured_font_hosts() -> None:
    nginx_conf = (REPO_ROOT / "nginx" / "default.conf").read_text(encoding="utf-8")

    assert "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com" in nginx_conf
    assert "font-src 'self' data: https://fonts.gstatic.com" in nginx_conf
    assert "media-src 'self'" in nginx_conf


def test_nginx_serves_learning_media_from_named_volume() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nginx_conf = (REPO_ROOT / "nginx" / "default.conf").read_text(encoding="utf-8")

    assert "learning_media:/app/learning-media" in compose
    assert "learning_media:/var/lib/nginx/learning-media:ro" in compose
    assert "location /media/learning/" in nginx_conf
    assert "alias /var/lib/nginx/learning-media/" in nginx_conf
    assert "client_max_body_size 500m" in nginx_conf
