"""Centralized configuration, read from environment variables (.env in dev).

No secrets are hardcoded here. See ../../../.env.example for every variable this
project's backend recognizes.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql://floodshield:changeme_dev_only@localhost:5432/floodshield_zambia"
    secret_key: str = "changeme"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal"
    openweather_api_key: str = ""

    model_artifact_dir: str = "./ai-engine/models"
    active_model_version: str = ""

    # Auth (JWT). secret_key above is reused as the signing key — see .env.example;
    # it MUST be overridden in any non-local environment (default is a dev placeholder).
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
