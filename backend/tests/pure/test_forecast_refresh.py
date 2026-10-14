"""POST /forecast/outlook/refresh: real-weather scoring with an injected provider (SQLite)."""
import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import forecast
from app.core.deps import get_current_user
from app.database.session import Base, get_db
from app.integrations.weather_provider import WeatherFetchOutcome, WeatherRecord, get_weather_provider
from app.models.location import Location
from app.models.prediction import ModelVersion, Prediction
from app.models.user import Role, User
from app.models.weather_observation import WeatherObservation

TODAY = dt.datetime.now(dt.timezone.utc).date()
OBS_DAY = dt.datetime.combine(TODAY - dt.timedelta(days=3), dt.time())


class Provider:
    def __init__(self, outcome):
        self.outcome = outcome

    def fetch_daily_point(self, **kw):
        return self.outcome


def record(day, **over):
    vals = dict(precipitation_mm=45.0, temperature_c=22.0, temperature_max_c=27.0, temperature_min_c=17.0,
                relative_humidity_pct=88.0, wind_speed_10m_ms=3.5)
    vals.update(over)
    return WeatherRecord(observed_date=day, **vals)


def make(outcome, role="ADMIN"):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Location.__table__, ModelVersion.__table__,
                                             Prediction.__table__, WeatherObservation.__table__])
    S = sessionmaker(bind=engine)
    with S() as s:
        s.add(Location(name="Lusaka", province="Lusaka", latitude=-15.4, longitude=28.3))
        s.add(ModelVersion(version="flood_risk_lr_v1", model_type="lr", training_period_start=dt.datetime(2000, 1, 1),
                           training_period_end=dt.datetime(2020, 1, 1), metrics_json="{}", artifact_path="x"))
        s.commit()
    app = FastAPI()
    app.include_router(forecast.router, prefix="/api/v1")

    def _db():
        with S() as s:
            yield s
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_weather_provider] = lambda: Provider(outcome)
    user = User(id=1, email="a@b.c", full_name="t", hashed_password="x", role=Role(id=1, name=role))
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), S


def ok(*records):
    return WeatherFetchOutcome("success", "http://x", list(records), None)


def test_refresh_scores_latest_complete_day_and_fills_the_outlook():
    c, S = make(ok(record(OBS_DAY - dt.timedelta(days=1)), record(OBS_DAY)))
    j = c.post("/api/v1/forecast/outlook/refresh?location_id=1").json()
    wp = j["window_prediction"]
    assert wp["observation_date"] == OBS_DAY.date().isoformat()
    assert wp["window_start"] == (OBS_DAY + dt.timedelta(days=1)).date().isoformat()
    assert wp["risk_level"].lower() == "high" and wp["model_version"] == "flood_risk_lr_v1"
    assert j["status"] == "partial" and not j["stale"]
    covered = [d for d in j["days"] if d["in_prediction_window"]]
    assert 0 < len(covered) < 7 and all(d["daily_flood_prediction"] is None for d in j["days"])
    with S() as s:
        assert len(s.scalars(select(WeatherObservation)).all()) == 2
        assert len(s.scalars(select(Prediction)).all()) == 1


def test_refresh_supersedes_previous_and_does_not_duplicate_weather():
    c, S = make(ok(record(OBS_DAY)))
    c.post("/api/v1/forecast/outlook/refresh?location_id=1")
    c.post("/api/v1/forecast/outlook/refresh?location_id=1")
    with S() as s:
        preds = s.scalars(select(Prediction).order_by(Prediction.id)).all()
        assert [p.is_stale for p in preds] == [True, False]
        assert len(s.scalars(select(WeatherObservation)).all()) == 1


def test_provider_failure_stores_nothing_and_reports_it():
    c, S = make(WeatherFetchOutcome("failed", "http://x", [], "boom"))
    r = c.post("/api/v1/forecast/outlook/refresh?location_id=1")
    assert r.status_code == 502 and r.json()["detail"]["error"] == "weather_unavailable"
    with S() as s:
        assert s.scalars(select(Prediction)).all() == []


def test_incomplete_weather_is_not_patched_or_scored():
    c, S = make(ok(record(OBS_DAY, temperature_max_c=None)))
    assert c.post("/api/v1/forecast/outlook/refresh?location_id=1").status_code == 502
    with S() as s:
        assert s.scalars(select(Prediction)).all() == [] and s.scalars(select(WeatherObservation)).all() == []


def test_requires_privileged_role_and_known_location():
    c, _ = make(ok(record(OBS_DAY)), role="CITIZEN")
    assert c.post("/api/v1/forecast/outlook/refresh?location_id=1").status_code == 403
    c, _ = make(ok(record(OBS_DAY)))
    assert c.post("/api/v1/forecast/outlook/refresh?location_id=99").status_code == 404
