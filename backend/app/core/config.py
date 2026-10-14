"""Centralized configuration, read from environment variables (.env in dev).

No secrets are hardcoded here. See ../../../.env.example for every variable this
project's backend recognizes.
"""
import pathlib
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator, model_validator
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
    # ALLOWED_ORIGINS is the deployment name; CORS_ORIGINS is the older name and still works.
    # Production must list the exact Vercel origin, e.g. https://your-app.vercel.app
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )

    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal"
    openweather_api_key: str = ""

    # MODEL_PATH is the deployment name; MODEL_ARTIFACT_DIR is the older name and still
    # works. It is the directory CONTAINING versioned model folders.
    model_artifact_dir: str = Field(
        default="./ml_artifacts",
        validation_alias=AliasChoices("MODEL_PATH", "MODEL_ARTIFACT_DIR"),
    )
    active_model_version: str = ""

    # Manual, administrator-triggered SMS. "simulated" (default) sends nothing and records
    # the attempt as "simulated"; "africastalking" submits to the real provider. Group
    # broadcasts to a real provider stay off until SMS_BROADCAST_ENABLED=true AND a real
    # test SMS has been accepted by that provider. Nothing here ever sends automatically.
    sms_provider: str = "simulated"
    sms_max_recipients: int = 20
    sms_allowed_numbers: str = ""  # optional comma-separated allowlist (E.164); empty = any
    sms_broadcast_enabled: bool = False
    sms_message_prefix: str = "FloodShield DEMO"
    sms_duplicate_window_minutes: int = 10
    # Shared secret for the provider's delivery-report and inbound (STOP) callbacks, sent
    # as ?token=... Empty = both callbacks are disabled (they answer 503).
    sms_webhook_secret: str = ""
    africastalking_environment: str = "sandbox"  # sandbox | production
    africastalking_username: str = ""
    africastalking_api_key: str = ""
    africastalking_sender_id: str = ""

    # Auth (JWT). secret_key above is reused as the signing key — see .env.example;
    # it MUST be overridden in any non-local environment (default is a dev placeholder).
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        # Railway/Heroku-style providers can hand out "postgres://", which SQLAlchemy 2
        # rejects. Same database, correct dialect name.
        return "postgresql://" + v[len("postgres://"):] if v.startswith("postgres://") else v

    @field_validator("sms_provider", "africastalking_environment")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()

    @property
    def sms_allowed_list(self) -> list[str]:
        return [n.strip() for n in self.sms_allowed_numbers.split(",") if n.strip()]

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
    def _refuse_wildcard_cors_outside_development(self) -> "Settings":
        # The API sends credentials (Authorization header, allow_credentials=True), so an
        # open origin list would let any website drive a signed-in user's session.
        if self.environment.lower() != "development" and "*" in self.cors_origins_list:
            raise ValueError(
                "ALLOWED_ORIGINS must list exact origins (e.g. https://your-app.vercel.app), "
                "not '*', outside development."
            )
        return self

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
