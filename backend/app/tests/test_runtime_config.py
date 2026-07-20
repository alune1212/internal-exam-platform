import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**overrides: object) -> Settings:
    return Settings.model_validate(overrides)


def _valid_internal_backend(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "internal",
        "app_role": "backend",
        "database_url": "postgresql+psycopg://exam:strong-db-password@db:5432/internal_exam",
        "cors_origins": "http://192.168.50.10:8080",
        "internal_lan_bind_ip": "192.168.50.10",
        "admin_password": "strong-admin-password",
        "token_secret": "strong-token-secret",
        "candidate_login_email_delivery_mode": "smtp",
        "candidate_login_email_from": "exam@example.com",
        "candidate_login_smtp_host": "smtp.example.com",
    }
    values.update(overrides)
    return _settings(**values)


@pytest.mark.parametrize("app_role", ["backend", "worker"])
def test_development_accepts_supported_roles(app_role: str) -> None:
    configured = _settings(app_role=app_role)

    assert configured.environment == "development"
    assert configured.app_role == app_role


def test_email_retry_defaults_are_bounded() -> None:
    configured = _settings()

    assert configured.candidate_login_email_max_attempts == 3
    assert configured.candidate_login_email_retry_base_seconds == 1.0


def test_smtp_transport_defaults_to_starttls() -> None:
    configured = _settings()

    assert configured.candidate_login_smtp_use_tls is True
    assert configured.candidate_login_smtp_use_ssl is False


def test_smtp_transport_rejects_ssl_and_starttls_together() -> None:
    with pytest.raises(ValidationError, match="不能同时为 true"):
        _settings(
            candidate_login_smtp_use_ssl=True,
            candidate_login_smtp_use_tls=True,
        )


@pytest.mark.parametrize(
    ("username", "password"),
    [("mailer@example.com", ""), ("", "smtp-password")],
)
def test_smtp_authentication_requires_username_password_pair(
    username: str, password: str
) -> None:
    with pytest.raises(ValidationError, match="必须同时配置或同时留空"):
        _settings(
            candidate_login_email_delivery_mode="smtp",
            candidate_login_smtp_username=username,
            candidate_login_smtp_password=password,
        )


def test_internal_backend_accepts_controlled_lan_configuration() -> None:
    configured = _valid_internal_backend()

    assert configured.internal_lan_bind_ip == "192.168.50.10"
    assert configured.cors_origin_list == ["http://192.168.50.10:8080"]


def test_internal_backend_accepts_implicit_smtp_ssl() -> None:
    configured = _valid_internal_backend(
        candidate_login_smtp_port=994,
        candidate_login_smtp_use_tls=False,
        candidate_login_smtp_use_ssl=True,
    )

    assert configured.candidate_login_smtp_port == 994
    assert configured.candidate_login_smtp_use_ssl is True


def test_internal_backend_rejects_unencrypted_smtp() -> None:
    with pytest.raises(ValidationError, match="必须启用 SMTP SSL 或 STARTTLS"):
        _valid_internal_backend(
            candidate_login_smtp_use_tls=False,
            candidate_login_smtp_use_ssl=False,
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"admin_password": "local-dev-admin-password"}, "ADMIN_PASSWORD"),
        (
            {"token_secret": "local-dev-token-secret-change-before-production"},
            "TOKEN_SECRET",
        ),
        (
            {
                "database_url": "postgresql+psycopg://exam:local-dev-postgres-password@db:5432/internal_exam"
            },
            "DATABASE_URL",
        ),
        ({"candidate_login_email_delivery_mode": "memory"}, "SMTP"),
        ({"candidate_login_email_from": ""}, "CANDIDATE_LOGIN_EMAIL_FROM"),
        ({"candidate_login_smtp_host": ""}, "CANDIDATE_LOGIN_SMTP_HOST"),
        ({"internal_lan_bind_ip": ""}, "INTERNAL_LAN_BIND_IP"),
        ({"internal_lan_bind_ip": "0.0.0.0"}, "INTERNAL_LAN_BIND_IP"),  # noqa: S104
        ({"internal_lan_bind_ip": "127.0.0.1"}, "INTERNAL_LAN_BIND_IP"),
        ({"internal_lan_bind_ip": "8.8.8.8"}, "INTERNAL_LAN_BIND_IP"),
        ({"cors_origins": "*"}, "CORS_ORIGINS"),
        ({"cors_origins": "http://192.168.50.11:8080"}, "CORS_ORIGINS"),
        ({"cors_origins": "https://192.168.50.10"}, "CORS_ORIGINS"),
    ],
)
def test_internal_backend_rejects_unsafe_configuration(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _valid_internal_backend(**overrides)


def test_internal_validation_does_not_echo_secret_values() -> None:
    exposed_secret = "local-dev-token-secret-change-before-production"  # noqa: S105

    with pytest.raises(ValidationError) as exc_info:
        _valid_internal_backend(token_secret=exposed_secret)

    assert exposed_secret not in str(exc_info.value)


@pytest.mark.parametrize("environment", ["internal", "production"])
def test_formal_worker_only_requires_strong_database_credentials(
    environment: str,
) -> None:
    configured = _settings(
        environment=environment,
        app_role="worker",
        database_url="postgresql+psycopg://exam:strong-db-password@db:5432/internal_exam",
    )

    assert configured.app_role == "worker"
    assert configured.candidate_login_email_delivery_mode == "memory"


def test_formal_worker_rejects_sample_database_credentials() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        _settings(environment="internal", app_role="worker")


def test_worker_rejects_heartbeat_age_shorter_than_scan_interval() -> None:
    with pytest.raises(ValidationError, match="AUTO_SUBMIT_HEARTBEAT_MAX_AGE_SECONDS"):
        _settings(
            app_role="worker",
            auto_submit_check_interval_seconds=30,
            auto_submit_heartbeat_max_age_seconds=29,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("environment", "staging"), ("app_role", "scheduler")],
)
def test_settings_reject_unknown_runtime_dimensions(field: str, value: str) -> None:
    with pytest.raises(ValidationError, match=field.upper()):
        _settings(**{field: value})
