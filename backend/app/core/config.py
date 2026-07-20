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
    environment: str = "development"
    app_role: str = "backend"
    database_url: str = "postgresql+psycopg://exam:exam@db:5432/internal_exam"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    token_secret: str = Field(default="change-me-in-production", min_length=8)
    token_ttl_seconds: int = 12 * 60 * 60
    internal_lan_bind_ip: str = ""
    public_token_rate_limit_count: int = Field(default=60, ge=1)
    public_token_rate_limit_window_seconds: int = Field(default=60, ge=1)
    public_token_rate_limit_max_keys: int = Field(default=10_000, ge=2)
    candidate_login_otp_ttl_seconds: int = Field(default=10 * 60, ge=60)
    candidate_login_otp_attempt_limit: int = Field(default=5, ge=1)
    candidate_login_otp_resend_cooldown_seconds: int = Field(default=60, ge=0)
    candidate_login_email_delivery_mode: str = "memory"
    candidate_login_email_max_attempts: int = Field(default=3, ge=1, le=10)
    candidate_login_email_retry_base_seconds: float = Field(default=1.0, ge=0, le=30)
    candidate_login_email_from: str = ""
    candidate_login_smtp_host: str = ""
    candidate_login_smtp_port: int = Field(default=587, ge=1)
    candidate_login_smtp_username: str = ""
    candidate_login_smtp_password: str = ""
    candidate_login_smtp_use_tls: bool = True
    import_max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    import_max_rows: int = Field(default=5000, ge=1)
    import_max_sheets: int = Field(default=1, ge=1)
    learning_media_storage_dir: str = "/app/learning-media"
    learning_media_public_path: str = "/media/learning"
    learning_video_max_upload_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    learning_video_allowed_content_types: str = "video/mp4,video/webm"
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
        if delivery_mode not in {"memory", "smtp"}:
            raise ValueError(
                "CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE 只能是 memory 或 smtp"
            )

        if self.environment == "internal" or (
            self.environment == "production" and self.app_role == "worker"
        ):
            self._validate_formal_database_credentials()

        if self.app_role == "worker":
            return self

        if self.environment in {"internal", "production"}:
            if self.admin_password in REPOSITORY_SAMPLE_ADMIN_PASSWORDS:
                raise ValueError(f"{self.environment} 环境必须配置 ADMIN_PASSWORD")
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

        if self.environment == "internal":
            self._validate_internal_network_boundary()
        elif self.environment == "production":
            self._validate_production_cors()
        return self

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
            not bind_ip.is_private
            or bind_ip.is_loopback
            or bind_ip.is_unspecified
            or bind_ip.is_link_local
        ):
            raise ValueError("internal 环境必须配置私有 INTERNAL_LAN_BIND_IP")

        origins = self.cors_origin_list
        if not origins:
            raise ValueError("internal 环境必须配置精确的 CORS_ORIGINS")
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

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
