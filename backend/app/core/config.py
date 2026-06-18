from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    import_max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    import_max_rows: int = Field(default=5000, ge=1)
    import_max_sheets: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def reject_production_defaults(self) -> "Settings":
        if self.environment == "production":
            if self.admin_password == "change-me":
                raise ValueError("production 环境必须配置 ADMIN_PASSWORD")
            if self.token_secret == "change-me-in-production":
                raise ValueError("production 环境必须配置 TOKEN_SECRET")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
