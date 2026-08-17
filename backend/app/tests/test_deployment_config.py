import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_COMPOSE_FILE = REPO_ROOT / "docker-compose.test.yml"
WINDOWS_OPS = REPO_ROOT / "ops" / "windows"


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


def _compose_service_section(service_name: str) -> str:
    lines = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8").splitlines()
    service_start = lines.index(f"  {service_name}:")
    section: list[str] = []
    for line in lines[service_start + 1 :]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        section.append(line)
    return "\n".join(section)


def _dotenv_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def test_candidate_and_operator_gateways_are_split() -> None:
    assert _compose_service_ports("nginx") == [
        "${INTERNAL_LAN_BIND_IP:-127.0.0.1}:${CANDIDATE_GATEWAY_PORT:-28080}:80"
    ]
    assert _compose_service_ports("operator-nginx") == [
        "127.0.0.1:${OPERATOR_GATEWAY_PORT:-28081}:80"
    ]


def test_compose_project_identities_are_explicit_and_distinct() -> None:
    development_env = _dotenv_values(REPO_ROOT / ".env.example")
    assert development_env["COMPOSE_PROJECT_NAME"] == "internal-exam-dev"
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    test_compose = TEST_COMPOSE_FILE.read_text(encoding="utf-8")
    assert "name: ${COMPOSE_PROJECT_NAME:-internal-exam-dev}" in compose
    assert "name: ${COMPOSE_TEST_PROJECT_NAME:-internal-exam-test}" in test_compose
    assert development_env["INTERNAL_LAN_BIND_IP"] == "127.0.0.1"
    assert development_env["CANDIDATE_GATEWAY_PORT"] == "28080"
    assert development_env["OPERATOR_GATEWAY_PORT"] == "28081"
    assert development_env["POSTGRES_LOOPBACK_PORT"] == "25432"
    assert development_env["FRONTEND_LOOPBACK_PORT"] == "25173"

    windows_scripts = "\n".join(
        path.read_text(encoding="utf-8") for path in WINDOWS_OPS.glob("*.ps1")
    )
    assert "internal-exam-formal" in windows_scripts
    assert "internal-exam-staging-$shortCommit" in windows_scripts
    staging_script = (WINDOWS_OPS / "Invoke-Staging.ps1").read_text(encoding="utf-8")
    assert "internal-exam-formal" not in staging_script


def test_development_bind_mount_defaults_remain_separate_from_formal_paths() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${INTERNAL_EXAM_LIFECYCLE_HOST_DIR:-./.runtime/lifecycle}" in compose
    assert "${INTERNAL_EXAM_BACKUP_HOST_DIR:-./.runtime/backups}" in compose
    assert "${INTERNAL_EXAM_EVIDENCE_HOST_DIR:-./.runtime/evidence}" in compose


def test_release_evidence_contract_is_architecture_aware_and_redacted() -> None:
    bundle_generator = (WINDOWS_OPS / "New-ReleaseBundle.ps1").read_text(
        encoding="utf-8"
    )
    lowered = bundle_generator.lower()
    for field in (
        "applicationversion",
        "gitcommit",
        "migrationhead",
        "hostos",
        "architecture",
        "imagedigests",
    ):
        assert field in lowered
    assert "securityevidence" in lowered
    assert "token_secret" not in lowered
    assert "admin_password" not in lowered

    release_root = REPO_ROOT / "ops" / "release"
    image_digests = json.loads(
        (release_root / "image-digests.json").read_text(encoding="utf-8")
    )
    platform_support = json.loads(
        (release_root / "platform-support.json").read_text(encoding="utf-8")
    )
    required_platforms = {"linux/amd64", "linux/arm64"}
    assert set(platform_support["required_platforms"]) == required_platforms
    assert set(platform_support["images"]) == set(image_digests)
    for name, image_ref in image_digests.items():
        support = platform_support["images"][name]
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", support["index_digest"])
        assert image_ref.endswith(f"@{support['index_digest']}")
        assert set(support["platforms"]) == required_platforms


def test_database_and_direct_frontend_ports_stay_loopback_only() -> None:
    assert _compose_service_ports("db") == [
        "127.0.0.1:${POSTGRES_LOOPBACK_PORT:-25432}:5432"
    ]
    assert _compose_service_ports("frontend") == [
        "127.0.0.1:${FRONTEND_LOOPBACK_PORT:-25173}:80"
    ]


def test_postgres_test_service_is_disposable_and_isolated() -> None:
    compose = TEST_COMPOSE_FILE.read_text(encoding="utf-8")

    assert "image: postgres:16-alpine@sha256:" in compose
    assert "POSTGRES_DB: internal_exam_test" in compose
    assert '"127.0.0.1:55432:5432"' in compose
    assert "tmpfs:" in compose
    assert "/var/lib/postgresql/data" in compose
    assert "postgres_data" not in compose


def test_backend_receives_all_supported_runtime_overrides() -> None:
    environment = _compose_service_environment("backend")

    assert {
        "APP_ROLE",
        "CAPACITY_RUN_ID",
        "CAPACITY_PROJECT_NAME",
        "TOKEN_TTL_SECONDS",
        "ADMIN_TOKEN_TTL_SECONDS",
        "CANDIDATE_TOKEN_TTL_SECONDS",
        "PRIMARY_OPERATOR_USERNAME",
        "PRIMARY_OPERATOR_PASSWORD",
        "BACKUP_OPERATOR_USERNAME",
        "BACKUP_OPERATOR_PASSWORD",
        "BACKUP_OPERATOR_ENABLED",
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
    assert "PRIMARY_OPERATOR_PASSWORD" not in environment
    assert "BACKUP_OPERATOR_PASSWORD" not in environment
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


def test_gateway_is_built_from_a_digest_pinned_patched_runtime() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "nginx" / "Dockerfile").read_text(encoding="utf-8")

    assert "-gateway:${APP_VERSION_TAG:-dev}" in compose
    assert "FROM nginx:1.27-alpine@sha256:" in dockerfile
    assert "RUN apk upgrade --no-cache" in dockerfile


def test_database_is_built_from_a_patched_digest_pinned_runtime() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "database" / "Dockerfile").read_text(encoding="utf-8")

    assert "-database:${APP_VERSION_TAG:-dev}" in compose
    assert "FROM postgres:16-alpine@sha256:" in dockerfile
    assert "RUN apk upgrade --no-cache" in dockerfile
    assert "apk add --no-cache su-exec" in dockerfile
    assert "rm -f /usr/local/bin/gosu" in dockerfile


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


def test_gateways_use_same_origin_csp_and_candidate_denies_admin_routes() -> None:
    candidate_conf = (REPO_ROOT / "nginx" / "candidate.conf").read_text(
        encoding="utf-8"
    )
    operator_conf = (REPO_ROOT / "nginx" / "operator.conf").read_text(encoding="utf-8")

    for nginx_conf in (candidate_conf, operator_conf):
        assert "https://fonts.googleapis.com" not in nginx_conf
        assert "https://fonts.gstatic.com" not in nginx_conf
        assert "font-src 'self'" in nginx_conf
        assert "object-src 'none'" in nginx_conf
        assert "media-src 'self'" in nginx_conf
    assert "media-src 'self';" in candidate_conf
    assert "media-src 'self' blob:;" in operator_conf
    for denied_route in (
        "location ^~ /admin",
        "location = /operations",
        "location ^~ /operations/",
        "location ^~ /api/admin/",
        "location ^~ /api/operations",
        "location = /api/ready",
        "location = /docs",
        "location = /openapi.json",
    ):
        assert denied_route in candidate_conf
    assert "location /docs" in operator_conf


def test_nginx_serves_learning_media_from_named_volume() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    candidate_conf = (REPO_ROOT / "nginx" / "candidate.conf").read_text(
        encoding="utf-8"
    )
    operator_conf = (REPO_ROOT / "nginx" / "operator.conf").read_text(encoding="utf-8")

    assert "learning_media:/app/learning-media" in compose
    assert "learning_media:/var/lib/nginx/learning-media:ro" in compose
    for nginx_conf in (candidate_conf, operator_conf):
        assert "location /media/learning/" in nginx_conf
        assert "alias /var/lib/nginx/learning-media/" in nginx_conf
    assert "client_max_body_size 10m" in candidate_conf
    assert "client_max_body_size 500m" in operator_conf


def test_formal_services_restart_and_rotate_logs() -> None:
    for service_name in (
        "db",
        "backend",
        "auto-submit-worker",
        "frontend",
        "nginx",
        "operator-nginx",
    ):
        section = _compose_service_section(service_name)
        assert "restart: unless-stopped" in section
        assert "logging:" in section

    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'max-size: "10m"' in compose
    assert 'max-file: "5"' in compose


def test_formal_base_images_are_pinned_by_digest() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    backend_dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    frontend_dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    database_dockerfile = (REPO_ROOT / "database" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    for line in compose.splitlines():
        if line.strip().startswith("image:") and "${APP_IMAGE_REPOSITORY" not in line:
            assert "@sha256:" in line
    assert "@sha256:" in database_dockerfile.splitlines()[0]
    assert "@sha256:" in backend_dockerfile.splitlines()[0]
    assert sum("@sha256:" in line for line in frontend_dockerfile.splitlines()) == 2


def test_frontend_and_worker_do_not_receive_formal_secrets() -> None:
    worker_environment = _compose_service_environment("auto-submit-worker")
    frontend_section = _compose_service_section("frontend")
    secret_names = {
        "ADMIN_PASSWORD",
        "PRIMARY_OPERATOR_PASSWORD",
        "BACKUP_OPERATOR_PASSWORD",
        "TOKEN_SECRET",
        "CANDIDATE_LOGIN_SMTP_PASSWORD",
    }

    assert worker_environment.isdisjoint(secret_names)
    assert all(secret not in frontend_section for secret in secret_names)
