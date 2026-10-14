"""API behaviour against in-memory SQLite (no Postgres needed for these tests)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import dams, forecast
from app.core.deps import get_current_user
from app.database.session import Base, get_db
from app.models.dam import Dam, DamObservation, DamReleaseNotice
from app.models.location import Location
from app.models.prediction import ModelVersion, Prediction
from app.models.user import Role, User

CSV = ("observed_at,reservoir_level_m,inflow_m3s,provider,source_reference,quality_flag\n"
       "2026-01-01T00:00:00Z,480.2,,ZRA,report-1,good\n"
       "2026-01-02T00:00:00Z,480.4,0,ZRA,report-1,good\n")
BAD = CSV + "2026-01-03T00:00:00Z,abc,,ZRA,report-1,good\n"


def _make(role_name):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[
        Dam.__table__, DamObservation.__table__, DamReleaseNotice.__table__, Location.__table__,
        ModelVersion.__table__, Prediction.__table__])
    S = sessionmaker(bind=engine)
    with S() as s:
        s.add(Dam(slug="kariba", name="Kariba Dam", river_system="Zambezi"))
        s.add(Location(name="Lusaka", province="Lusaka", latitude=-15.4, longitude=28.3))
        s.commit()
    app = FastAPI()
    app.include_router(dams.router, prefix="/api/v1")
    app.include_router(forecast.router, prefix="/api/v1")

    def _db():
        with S() as s:
            yield s
    app.dependency_overrides[get_db] = _db
    user = User(id=1, email="a@b.c", full_name="t", hashed_password="x",
                role=Role(id=1, name=role_name)) if role_name else None
    if user:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.fixture()
def client():
    return _make("ADMIN")


def test_unverified_dam_has_no_invented_fields(client):
    d = client.get("/api/v1/dams").json()[0]
    assert d["latitude"] is None and d["capacity_m3"] is None and d["latest"] is None
    assert d["freshness"] == "no_data" and d["verification_required"] is True


def test_unknown_resources_404(client):
    assert client.get("/api/v1/dams/nope").status_code == 404
    assert client.get("/api/v1/forecast/outlook?location_id=999").status_code == 404


def test_assessment_with_no_data_is_insufficient(client):
    assert client.get("/api/v1/dams/kariba/assessment").json()["status"] == "insufficient_data"


def test_import_keeps_missing_missing_and_is_idempotent(client):
    url = "/api/v1/dams/kariba/import?data_kind=historical"
    h = {"Content-Type": "text/csv"}
    r = client.post(url, content=CSV, headers=h)
    assert r.status_code == 200 and r.json()["added"] == 2
    assert client.post(url, content=CSV, headers=h).json() == {
        "added": 0, "skipped_existing": 2, "data_kind": "historical"}
    d = client.get("/api/v1/dams/kariba").json()
    first, second = d["observations"]
    assert first["inflow_m3s"] is None and second["inflow_m3s"] == 0.0
    assert first["data_kind"] == "historical" and first["retrieved_at"] != first["observed_at"]
    assert d["dam"]["data_status"] == "historical_only" and d["dam"]["freshness"] == "stale"


def test_invalid_row_rejects_whole_import(client):
    r = client.post("/api/v1/dams/kariba/import?data_kind=historical", content=BAD,
                    headers={"Content-Type": "text/csv"})
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["line"] == 4
    assert client.get("/api/v1/dams/kariba").json()["observations"] == []


def test_live_kind_refused_and_synthetic_labelled(client):
    h = {"Content-Type": "text/csv"}
    assert client.post("/api/v1/dams/kariba/import?data_kind=live", content=CSV, headers=h).status_code == 422
    assert client.post("/api/v1/dams/kariba/import?data_kind=synthetic_test", content=CSV, headers=h).status_code == 200
    d = client.get("/api/v1/dams/kariba").json()
    assert {o["data_kind"] for o in d["observations"]} == {"synthetic_test"}
    assert d["dam"]["data_status"] == "no_data"      # synthetic data never upgrades the status


def test_import_requires_privileged_role():
    assert _make("CITIZEN").post("/api/v1/dams/kariba/import?data_kind=historical", content=CSV,
                                 headers={"Content-Type": "text/csv"}).status_code == 403


def test_forecast_outlook_without_predictions_is_honest(client):
    j = client.get("/api/v1/forecast/outlook?location_id=1").json()
    assert j["status"] == "no_prediction" and len(j["days"]) == 7
    assert j["timezone"] == "Africa/Lusaka"
