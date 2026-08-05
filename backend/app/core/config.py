from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPSFORGE_",
        extra="ignore",
    )

    app_name: str = "OpsForge ERP"
    app_version: str = "0.1.0"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://opsforge:opsforge_local_only@localhost:5432/opsforge"
    secret_key: SecretStr = SecretStr("replace-this-local-development-secret")
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"
    session_ttl_minutes: int = 480

    @model_validator(mode="after")
    def reject_default_secret_outside_local_environments(self) -> Settings:
        if (
            self.environment not in {"local", "test"}
            and self.secret_key.get_secret_value() == "replace-this-local-development-secret"
        ):
            raise ValueError("OPSFORGE_SECRET_KEY must be changed outside local/test environments")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
