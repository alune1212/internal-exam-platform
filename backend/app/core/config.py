from functools import lru_cache
from ipaddress import ip_address
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_SAMPLE_ADMIN_PASSWORDS = {
    "change-me",
    "local-dev-admin-password",
}
REPOSITORY_SAMPLE_TOKEN_SECRETS = {
    "change-me-in-production",
    "local-dev-token-secret-change-before-production",
}
REPOSITORY_SAMPLE_DATABASE_PASSWORDS = {
    "exam",
    "local-dev-postgres-password",
}
VALID_ENVIRONMENTS = {"development", "internal", "production"}
VALID_APP_ROLES = {"backend", "worker"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "internal-exam-platform"
    app_version: str = "0.1.0"
    git_commit: str = "development"
    environment: str = "development"
    app_role: str = "backend"
    database_url: str = "postgresql+psycopg://exam:exam@db:5432/internal_exam"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    primary_operator_username: str = ""
    primary_operator_password: str = ""
    backup_operator_username: str = ""
    backup_operator_password: str = ""
    backup_operator_enabled: bool = False
    token_secret: str = Field(default="change-me-in-production", min_length=8)
    token_ttl_seconds: int = 12 * 60 * 60
    admin_token_ttl_seconds: int = Field(default=4 * 60 * 60, ge=60)
    candidate_token_ttl_seconds: int = Field(default=4 * 60 * 60, ge=60)
    internal_lan_bind_ip: str = ""
    public_token_rate_limit_count: int = Field(default=60, ge=1)
    public_token_rate_limit_window_seconds: int = Field(default=60, ge=1)
    public_token_rate_limit_max_keys: int = Field(default=10_000, ge=2)
    candidate_login_otp_ttl_seconds: int = Field(default=10 * 60, ge=60)
    candidate_login_otp_attempt_limit: int = Field(default=5, ge=1)
    candidate_login_otp_resend_cooldown_seconds: int = Field(default=60, ge=0)
    candidate_registration_credential_ttl_seconds: int = Field(default=10 * 60, ge=60)
    candidate_login_email_rate_limit_count: int = Field(default=5, ge=1)
    candidate_login_email_rate_limit_window_seconds: int = Field(default=10 * 60, ge=1)
    candidate_login_source_rate_limit_count: int = Field(default=30, ge=1)
    candidate_login_source_rate_limit_window_seconds: int = Field(default=10 * 60, ge=1)
    candidate_login_global_rate_limit_count: int = Field(default=10_000, ge=1)
    candidate_login_global_rate_limit_window_seconds: int = Field(
        default=24 * 60 * 60, ge=1
    )
    candidate_login_cleanup_batch_size: int = Field(default=100, ge=1, le=10_000)
    candidate_login_challenge_retention_seconds: int = Field(
        default=24 * 60 * 60, ge=60
    )
    candidate_login_test_otp: str = ""
    candidate_login_email_delivery_mode: str = "memory"
    candidate_login_email_max_attempts: int = Field(default=3, ge=1, le=10)
    candidate_login_email_retry_base_seconds: float = Field(default=1.0, ge=0, le=30)
    candidate_login_email_from: str = ""
    candidate_login_smtp_host: str = ""
    candidate_login_smtp_port: int = Field(default=587, ge=1)
    candidate_login_smtp_username: str = ""
    candidate_login_smtp_password: str = ""
    candidate_login_smtp_use_tls: bool = True
    candidate_login_smtp_use_ssl: bool = False
    candidate_public_base_url: str = "http://localhost:8080"
    invitation_send_batch_size: int = Field(default=200, ge=1, le=5000)
    invitation_claim_ttl_seconds: int = Field(default=5 * 60, ge=30)
    invitation_admin_rate_limit_count: int = Field(default=10, ge=1)
    invitation_admin_rate_limit_window_seconds: int = Field(default=60, ge=1)
    import_max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    import_max_rows: int = Field(default=5000, ge=1)
    import_max_sheets: int = Field(default=1, ge=1)
    learning_media_storage_dir: str = "/app/learning-media"
    learning_media_public_path: str = "/media/learning"
    learning_video_max_upload_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    learning_video_allowed_content_types: str = "video/mp4,video/webm"
    lifecycle_archive_dir: str = "/app/lifecycle/archives"
    backup_storage_dir: str = "/app/backups"
    operations_evidence_dir: str = "/app/evidence"
    storage_min_free_bytes: int = Field(default=20 * 1024**3, ge=1)
    storage_footprint_multiplier: int = Field(default=3, ge=1)
    auto_submit_check_interval_seconds: int = Field(default=30, ge=1)
    auto_submit_batch_size: int = Field(default=100, ge=1)
    auto_submit_heartbeat_path: str = "/tmp/internal-exam-auto-submit.heartbeat"  # noqa: S108
    auto_submit_heartbeat_max_age_seconds: int = Field(default=90, ge=1)

    @model_validator(mode="after")
    def validate_runtime_profile(self) -> "Settings":
        if self.environment not in VALID_ENVIRONMENTS:
            raise ValueError("ENVIRONMENT 只能是 development、internal 或 production")
        if self.app_role not in VALID_APP_ROLES:
            raise ValueError("APP_ROLE 只能是 backend 或 worker")
        if (
            self.app_role == "worker"
            and self.auto_submit_heartbeat_max_age_seconds
            < self.auto_submit_check_interval_seconds
        ):
            raise ValueError(
                "AUTO_SUBMIT_HEARTBEAT_MAX_AGE_SECONDS 不能小于 "
                "AUTO_SUBMIT_CHECK_INTERVAL_SECONDS"
            )

        delivery_mode = self.candidate_login_email_delivery_mode.strip().lower()
        if self.candidate_login_test_otp and (
            self.environment != "development"
            or len(self.candidate_login_test_otp) != 6
            or not self.candidate_login_test_otp.isdigit()
        ):
            raise ValueError("CANDIDATE_LOGIN_TEST_OTP 仅允许 development 使用六位数字")
        if delivery_mode not in {"memory", "smtp"}:
            raise ValueError(
                "CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE 只能是 memory 或 smtp"
            )
        if self.candidate_login_smtp_use_ssl and self.candidate_login_smtp_use_tls:
            raise ValueError(
                "CANDIDATE_LOGIN_SMTP_USE_SSL 与 CANDIDATE_LOGIN_SMTP_USE_TLS "
                "不能同时为 true"
            )
        smtp_username_configured = bool(self.candidate_login_smtp_username.strip())
        smtp_password_configured = bool(self.candidate_login_smtp_password)
        if delivery_mode == "smtp" and (
            smtp_username_configured != smtp_password_configured
        ):
            raise ValueError(
                "CANDIDATE_LOGIN_SMTP_USERNAME 与 CANDIDATE_LOGIN_SMTP_PASSWORD "
                "必须同时配置或同时留空"
            )
        if (
            self.candidate_registration_credential_ttl_seconds
            > self.candidate_login_otp_ttl_seconds
        ):
            raise ValueError(
                "CANDIDATE_REGISTRATION_CREDENTIAL_TTL_SECONDS 不能超过验证码有效期"
            )
        if self.candidate_login_challenge_retention_seconds < max(
            self.candidate_login_email_rate_limit_window_seconds,
            self.candidate_login_source_rate_limit_window_seconds,
            self.candidate_login_global_rate_limit_window_seconds,
            self.candidate_registration_credential_ttl_seconds,
        ):
            raise ValueError(
                "CANDIDATE_LOGIN_CHALLENGE_RETENTION_SECONDS 不能小于验证码限流或注册凭据窗口"
            )

        if self.environment == "internal" or (
            self.environment == "production" and self.app_role == "worker"
        ):
            self._validate_formal_database_credentials()

        if self.app_role == "worker":
            return self

        self._validate_candidate_public_base_url()

        if self.environment in {"internal", "production"}:
            if self.environment == "internal":
                self._validate_operator_configuration()
            elif self.admin_password in REPOSITORY_SAMPLE_ADMIN_PASSWORDS:
                raise ValueError("production 环境必须配置 ADMIN_PASSWORD")
            if self.token_secret in REPOSITORY_SAMPLE_TOKEN_SECRETS:
                raise ValueError(f"{self.environment} 环境必须配置 TOKEN_SECRET")
            if delivery_mode != "smtp":
                raise ValueError(
                    f"{self.environment} 环境必须使用 SMTP 发送考试人登录验证码"
                )
            if not self.candidate_login_email_from.strip():
                raise ValueError(
                    f"{self.environment} 环境必须配置 CANDIDATE_LOGIN_EMAIL_FROM"
                )
            if not self.candidate_login_smtp_host.strip():
                raise ValueError(
                    f"{self.environment} 环境必须配置 CANDIDATE_LOGIN_SMTP_HOST"
                )
            if not (
                self.candidate_login_smtp_use_ssl or self.candidate_login_smtp_use_tls
            ):
                raise ValueError(
                    f"{self.environment} 环境必须启用 SMTP SSL 或 STARTTLS"
                )

        if self.environment == "internal":
            self._validate_internal_network_boundary()
        elif self.environment == "production":
            self._validate_production_cors()
        return self

    def _validate_operator_configuration(self) -> None:
        if not self.primary_operator_username.strip():
            raise ValueError(
                f"{self.environment} 环境必须配置 PRIMARY_OPERATOR_USERNAME"
            )
        if (
            not self.primary_operator_password
            or self.primary_operator_password in REPOSITORY_SAMPLE_ADMIN_PASSWORDS
        ):
            raise ValueError(
                f"{self.environment} 环境必须配置 PRIMARY_OPERATOR_PASSWORD"
            )
        if not self.backup_operator_username.strip():
            raise ValueError(
                f"{self.environment} 环境必须配置 BACKUP_OPERATOR_USERNAME"
            )
        if (
            not self.backup_operator_password
            or self.backup_operator_password in REPOSITORY_SAMPLE_ADMIN_PASSWORDS
        ):
            raise ValueError(
                f"{self.environment} 环境必须配置 BACKUP_OPERATOR_PASSWORD"
            )
        if self.primary_operator_username == self.backup_operator_username:
            raise ValueError("主操作员与备份操作员登录名必须不同")
        if (
            self.admin_token_ttl_seconds != 4 * 60 * 60
            or self.candidate_token_ttl_seconds != 4 * 60 * 60
        ):
            raise ValueError("internal/production 正式 Token 有效期必须为 4 小时")

    def _validate_formal_database_credentials(self) -> None:
        password = urlparse(self.database_url).password
        if not password or password in REPOSITORY_SAMPLE_DATABASE_PASSWORDS:
            raise ValueError(f"{self.environment} 环境必须配置安全的 DATABASE_URL")

    def _validate_internal_network_boundary(self) -> None:
        try:
            bind_ip = ip_address(self.internal_lan_bind_ip.strip())
        except ValueError:
            raise ValueError("internal 环境必须配置私有 INTERNAL_LAN_BIND_IP") from None
        if (
            bind_ip.version != 4
            or not bind_ip.is_private
            or bind_ip.is_loopback
            or bind_ip.is_unspecified
            or bind_ip.is_link_local
        ):
            raise ValueError("internal 环境必须配置私有 INTERNAL_LAN_BIND_IP")

        origins = self.cors_origin_list
        expected_origin = f"http://{bind_ip}:8080"
        if origins != [expected_origin]:
            raise ValueError(
                "internal 环境的 CORS_ORIGINS 必须仅包含固定考试人入口的 8080 端口"
            )
        for origin in origins:
            parsed = urlparse(origin)
            try:
                parsed_port = parsed.port
            except ValueError:
                raise ValueError("internal 环境必须配置精确的 CORS_ORIGINS") from None
            if (
                origin == "*"
                or parsed.scheme != "http"
                or parsed.hostname != str(bind_ip)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.params
                or parsed.query
                or parsed.fragment
                or parsed_port is None
            ):
                raise ValueError("internal 环境必须配置精确的 CORS_ORIGINS")
        if self.candidate_public_base_url.rstrip("/") != expected_origin:
            raise ValueError(
                "internal 环境的 CANDIDATE_PUBLIC_BASE_URL 必须等于固定考试人入口"
            )

    def _validate_production_cors(self) -> None:
        origins = self.cors_origin_list
        if not origins:
            raise ValueError("production 环境必须配置安全的 CORS_ORIGINS")
        for origin in origins:
            parsed = urlparse(origin)
            if (
                origin == "*"
                or parsed.scheme != "https"
                or parsed.hostname in {"localhost", "127.0.0.1", "0.0.0.0"}  # noqa: S104
            ):
                raise ValueError("production 环境必须配置安全的 CORS_ORIGINS")

    def _validate_candidate_public_base_url(self) -> None:
        raw_value = self.candidate_public_base_url.strip()
        parsed = urlparse(raw_value)
        try:
            parsed_port = parsed.port
        except ValueError:
            raise ValueError("CANDIDATE_PUBLIC_BASE_URL 必须是有效的站点来源") from None
        if (
            not raw_value
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
            or parsed.fragment
            or (parsed_port is not None and not 1 <= parsed_port <= 65_535)
        ):
            raise ValueError("CANDIDATE_PUBLIC_BASE_URL 必须是无路径和凭据的站点来源")
        if self.environment == "production" and parsed.scheme != "https":
            raise ValueError(
                "production 环境的 CANDIDATE_PUBLIC_BASE_URL 必须使用 HTTPS"
            )
        if self.environment == "production" and raw_value.rstrip("/") not in {
            origin.rstrip("/") for origin in self.cors_origin_list
        }:
            raise ValueError(
                "production 环境的 CANDIDATE_PUBLIC_BASE_URL 必须属于 CORS_ORIGINS"
            )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def configured_primary_operator(self) -> tuple[str, str]:
        return (
            self.primary_operator_username.strip() or self.admin_username,
            self.primary_operator_password or self.admin_password,
        )

    @property
    def configured_backup_operator(self) -> tuple[str, str]:
        return (
            self.backup_operator_username.strip(),
            self.backup_operator_password,
        )

    @property
    def configured_active_operator(self) -> tuple[str, str]:
        """Return the only operator credential pair valid at this moment."""
        if self.backup_operator_enabled:
            return self.configured_backup_operator
        return self.configured_primary_operator

    @property
    def learning_video_allowed_content_type_set(self) -> set[str]:
        return {
            content_type.strip().lower()
            for content_type in self.learning_video_allowed_content_types.split(",")
            if content_type.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
