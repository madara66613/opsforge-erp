from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
