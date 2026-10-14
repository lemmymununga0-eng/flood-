"""Deployment configuration: env-var names, CORS safety, health endpoints."""
import pytest

from app.core.config import Settings


def _settings(monkeypatch, **env):
    for k in ("ALLOWED_ORIGINS", "CORS_ORIGINS", "MODEL_PATH", "MODEL_ARTIFACT_DIR"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return Settings(_env_file=None)


def test_allowed_origins_is_the_deployment_name(monkeypatch):
    s = _settings(monkeypatch, ALLOWED_ORIGINS="https://a.vercel.app, http://localhost:5173")
    assert s.cors_origins_list == ["https://a.vercel.app", "http://localhost:5173"]


def test_legacy_cors_origins_name_still_works(monkeypatch):
    assert _settings(monkeypatch, CORS_ORIGINS="https://old.example").cors_origins_list == [
        "https://old.example"
    ]


def test_dev_defaults_cover_vite_and_cra_ports(monkeypatch):
    assert _settings(monkeypatch).cors_origins_list == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


def test_model_path_alias(monkeypatch):
    s = _settings(monkeypatch, MODEL_PATH="/srv/models")
    assert s.model_artifact_dir == "/srv/models"


def test_wildcard_origin_refused_outside_development(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example/x")
    with pytest.raises(ValueError, match="exact origins"):
        _settings(monkeypatch, ENVIRONMENT="production", ALLOWED_ORIGINS="*")


def test_wildcard_tolerated_in_development(monkeypatch):
    assert _settings(monkeypatch, ENVIRONMENT="development", ALLOWED_ORIGINS="*").cors_origins_list == ["*"]


def test_postgres_scheme_is_normalised(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/db")
    assert _settings(monkeypatch).database_url.startswith("postgresql://u:p@host")


def test_liveness_is_dependency_free(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_readiness_reports_database_and_model(client):
    body = client.get("/health/ready").json()
    assert body["database"] == "ok"
    assert body["model"] in ("ok", "unavailable")
    assert body["status"] in ("ready", "degraded")
