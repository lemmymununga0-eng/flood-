"""Centralized configuration, read from environment variables (.env in dev).

No secrets are hardcoded here. See ../../../.env.example for every variable this
project's backend recognizes.
"""
import pathlib
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEV_SECRET_KEY = "changeme"
_INSECURE_DEV_DATABASE_URL = (
    "postgresql://floodshield:changeme_dev_only@localhost:5432/floodshield_zambia"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = _INSECURE_DEV_DATABASE_URL
    secret_key: str = _INSECURE_DEV_SECRET_KEY
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal"
    openweather_api_key: str = ""

    model_artifact_dir: str = "./ml_artifacts"
    active_model_version: str = ""

    # Auth (JWT). secret_key above is reused as the signing key — see .env.example;
    # it MUST be overridden in any non-local environment (default is a dev placeholder).
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def model_artifact_path(self) -> pathlib.Path:
        """Absolute artifact directory.

        `model_artifact_dir` defaults to the relative "./ml_artifacts", which silently
        resolved against the current working directory — so inference succeeded when
        launched from backend/ and raised ModelArtifactsUnavailable when launched from
        the repository root or from a test runner. A relative value is now anchored to
        the backend package root instead of the CWD.
        """
        p = pathlib.Path(self.model_artifact_dir).expanduser()
        if p.is_absolute():
            return p
        return (pathlib.Path(__file__).resolve().parents[2] / p).resolve()

    @model_validator(mode="after")
    def _refuse_insecure_defaults_outside_development(self) -> "Settings":
        # Fail fast instead of silently booting with a public, guessable JWT
        # signing key / DB credential — see docs/deployment-readiness.md P0.
        if self.environment.lower() != "development":
            if self.secret_key == _INSECURE_DEV_SECRET_KEY:
                raise ValueError(
                    f"SECRET_KEY is still the insecure default 'changeme' while "
                    f"ENVIRONMENT={self.environment!r}. Set a real random SECRET_KEY "
                    f"in .env before starting outside development."
                )
            if self.database_url == _INSECURE_DEV_DATABASE_URL:
                raise ValueError(
                    f"DATABASE_URL is still the insecure default dev credential while "
                    f"ENVIRONMENT={self.environment!r}. Set a real DATABASE_URL in .env "
                    f"before starting outside development."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
