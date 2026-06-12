from functools import lru_cache

from pydantic import Field
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
