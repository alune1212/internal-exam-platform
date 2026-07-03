from functools import lru_cache
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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "internal-exam-platform"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://exam:exam@db:5432/internal_exam"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    token_secret: str = Field(default="change-me-in-production", min_length=8)
    token_ttl_seconds: int = 12 * 60 * 60
    public_token_rate_limit_count: int = Field(default=60, ge=1)
    public_token_rate_limit_window_seconds: int = Field(default=60, ge=1)
    public_token_rate_limit_max_keys: int = Field(default=10_000, ge=2)
    candidate_login_otp_ttl_seconds: int = Field(default=10 * 60, ge=60)
    candidate_login_otp_attempt_limit: int = Field(default=5, ge=1)
    candidate_login_otp_resend_cooldown_seconds: int = Field(default=60, ge=0)
    candidate_login_email_delivery_mode: str = "memory"
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

    @model_validator(mode="after")
    def reject_production_defaults(self) -> "Settings":
        delivery_mode = self.candidate_login_email_delivery_mode.strip().lower()
        if delivery_mode not in {"memory", "smtp"}:
            raise ValueError(
                "CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE 只能是 memory 或 smtp"
            )
        if self.environment == "production":
            if self.admin_password in REPOSITORY_SAMPLE_ADMIN_PASSWORDS:
                raise ValueError("production 环境必须配置 ADMIN_PASSWORD")
            if self.token_secret in REPOSITORY_SAMPLE_TOKEN_SECRETS:
                raise ValueError("production 环境必须配置 TOKEN_SECRET")
            if delivery_mode != "smtp":
                raise ValueError("production 环境必须使用 SMTP 发送考试人登录验证码")
            if not self.candidate_login_email_from.strip():
                raise ValueError("production 环境必须配置 CANDIDATE_LOGIN_EMAIL_FROM")
            if not self.candidate_login_smtp_host.strip():
                raise ValueError("production 环境必须配置 CANDIDATE_LOGIN_SMTP_HOST")
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
        return self

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
