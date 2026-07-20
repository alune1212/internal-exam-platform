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


def _compose_service_environment(service_name: str) -> set[str]:
    lines = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8").splitlines()
    service_header = f"  {service_name}:"
    service_start = lines.index(service_header)
    environment: set[str] = set()
    in_environment_block = False

    for line in lines[service_start + 1 :]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        if line == "    environment:":
            in_environment_block = True
            continue
        if not in_environment_block:
            continue
        if line.startswith("      ") and ":" in line:
            environment.add(line.strip().split(":", 1)[0])
            continue
        if line.startswith("    ") and not line.startswith("      "):
            break

    return environment


def test_default_nginx_publish_allows_lan_access() -> None:
    assert _compose_service_ports("nginx") == [
        "${INTERNAL_LAN_BIND_IP:-0.0.0.0}:8080:80"
    ]


def test_database_and_direct_frontend_ports_stay_loopback_only() -> None:
    assert _compose_service_ports("db") == ["127.0.0.1:5432:5432"]
    assert _compose_service_ports("frontend") == ["127.0.0.1:5173:80"]


def test_backend_receives_all_supported_runtime_overrides() -> None:
    environment = _compose_service_environment("backend")

    assert {
        "APP_ROLE",
        "TOKEN_TTL_SECONDS",
        "PUBLIC_TOKEN_RATE_LIMIT_COUNT",
        "PUBLIC_TOKEN_RATE_LIMIT_WINDOW_SECONDS",
        "PUBLIC_TOKEN_RATE_LIMIT_MAX_KEYS",
        "CANDIDATE_LOGIN_OTP_TTL_SECONDS",
        "CANDIDATE_LOGIN_OTP_ATTEMPT_LIMIT",
        "CANDIDATE_LOGIN_OTP_RESEND_COOLDOWN_SECONDS",
        "CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE",
        "CANDIDATE_LOGIN_EMAIL_MAX_ATTEMPTS",
        "CANDIDATE_LOGIN_EMAIL_RETRY_BASE_SECONDS",
        "CANDIDATE_LOGIN_EMAIL_FROM",
        "CANDIDATE_LOGIN_SMTP_HOST",
        "CANDIDATE_LOGIN_SMTP_PORT",
        "CANDIDATE_LOGIN_SMTP_USERNAME",
        "CANDIDATE_LOGIN_SMTP_PASSWORD",
        "CANDIDATE_LOGIN_SMTP_USE_TLS",
        "CANDIDATE_LOGIN_SMTP_USE_SSL",
        "IMPORT_MAX_UPLOAD_BYTES",
        "IMPORT_MAX_ROWS",
        "IMPORT_MAX_SHEETS",
        "INTERNAL_LAN_BIND_IP",
    } <= environment


def test_worker_environment_is_role_scoped_and_least_privileged() -> None:
    environment = _compose_service_environment("auto-submit-worker")

    assert {
        "ENVIRONMENT",
        "APP_ROLE",
        "DATABASE_URL",
        "AUTO_SUBMIT_CHECK_INTERVAL_SECONDS",
        "AUTO_SUBMIT_BATCH_SIZE",
        "AUTO_SUBMIT_HEARTBEAT_PATH",
        "AUTO_SUBMIT_HEARTBEAT_MAX_AGE_SECONDS",
    } <= environment
    assert "ADMIN_PASSWORD" not in environment
    assert "TOKEN_SECRET" not in environment
    assert "CANDIDATE_LOGIN_SMTP_PASSWORD" not in environment
    assert "CANDIDATE_LOGIN_SMTP_USE_SSL" not in environment
    assert "CANDIDATE_LOGIN_EMAIL_MAX_ATTEMPTS" not in environment


def test_backend_healthcheck_uses_dependency_aware_readiness() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "http://127.0.0.1:8000/api/ready" in compose
    assert "healthcheck:" in compose


def test_nginx_waits_for_healthy_backend() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nginx_section = compose.split("  nginx:", 1)[1]

    assert "backend:\n        condition: service_healthy" in nginx_section


def test_worker_healthcheck_uses_heartbeat_command() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    worker_section = compose.split("  auto-submit-worker:", 1)[1].split(
        "  frontend:", 1
    )[0]

    assert (
        'python", "-m", "app.core.auto_submit_worker", "healthcheck' in worker_section
    )
    assert "healthcheck:" in worker_section


def test_container_commands_never_sync_dependencies_at_runtime() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "uv run --no-sync alembic upgrade head" in compose
    assert '"uv", "run", "--no-sync", "python"' in compose
    assert 'CMD ["uv", "run", "--no-sync", "uvicorn"' in dockerfile


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
