"""Automated coverage for POST /api/v1/weather/{location_id}/ingest and
GET /api/v1/weather/{location_id}, using a MockWeatherProvider instead of a real NASA
POWER call — closes docs/bug-register.md BUG-08 for the weather endpoints without
depending on network access this sandbox doesn't have."""
from datetime import datetime, timezone

from app.integrations.weather_provider import WeatherFetchOutcome, WeatherRecord, get_weather_provider
from app.main import app
from tests.support.mock_weather_provider import MockWeatherProvider


def _override_provider(client, outcome: WeatherFetchOutcome) -> None:
    app.dependency_overrides[get_weather_provider] = lambda: MockWeatherProvider(outcome)


def test_ingest_success_stores_observations(client, seeded_location):
    records = [
        WeatherRecord(
            observed_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            precipitation_mm=12.5,
            temperature_c=24.0,
            relative_humidity_pct=80.0,
            wind_speed_ms=3.1,
        ),
        WeatherRecord(
            observed_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
            precipitation_mm=0.0,
            temperature_c=26.5,
            relative_humidity_pct=55.0,
            wind_speed_ms=2.0,
        ),
    ]
    _override_provider(client, WeatherFetchOutcome("success", "https://example.test/mock", records, None))

    resp = client.post(f"/api/v1/weather/{seeded_location.id}/ingest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["observations_stored"] == 2
    assert body["error_detail"] is None

    listed = client.get(f"/api/v1/weather/{seeded_location.id}")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 2
    assert all(r["source"] == "NASA POWER" for r in rows)
    assert {r["precipitation_mm"] for r in rows} == {12.5, 0.0}


def test_ingest_failure_reports_honestly_and_stores_nothing(client, seeded_location):
    _override_provider(
        client,
        WeatherFetchOutcome("failed", "https://example.test/mock", [], "ConnectionError: simulated network failure"),
    )

    resp = client.post(f"/api/v1/weather/{seeded_location.id}/ingest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "failed"
    assert body["observations_stored"] == 0
    assert "simulated network failure" in body["error_detail"]

    listed = client.get(f"/api/v1/weather/{seeded_location.id}")
    assert listed.json() == []


def test_ingest_unknown_location_returns_404(client):
    _override_provider(client, WeatherFetchOutcome("success", "https://example.test/mock", [], None))

    resp = client.post("/api/v1/weather/999999/ingest")
    assert resp.status_code == 404
