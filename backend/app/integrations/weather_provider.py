"""Abstraction over "fetch weather observations for a point in time". The real
implementation (`NasaPowerWeatherProvider`) makes the exact same HTTP request that used
to be inline in `app/services/weather_ingestion.py` — this module only relocates that
logic behind an interface so it can be swapped for a test double via FastAPI's
`dependency_overrides` (see `backend/tests/support/mock_weather_provider.py`). No
production behavior changes: same URL, same params, same failure semantics (a real
exception is reported honestly, never papered over with fabricated data).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

import requests

from app.core.config import get_settings

NASA_POWER_PARAMETERS = "PRECTOTCORR,T2M,RH2M,WS2M"

# NASA POWER's documented sentinel for "no data yet" (near-real-time days a few days
# behind, or any other gap) -- the response's own "fill_value" field confirms this.
# Storing -999 as a literal temperature/humidity/etc. reading would be worse than an
# honest null: it looks like real (if extreme) data instead of an absent measurement.
_NASA_POWER_FILL_VALUE = -999.0


def _clean(value: float | None) -> float | None:
    if value is None or value == _NASA_POWER_FILL_VALUE:
        return None
    return value


@dataclass
class WeatherRecord:
    observed_date: datetime
    precipitation_mm: float | None
    temperature_c: float | None
    relative_humidity_pct: float | None
    wind_speed_ms: float | None


@dataclass
class WeatherFetchOutcome:
    status: Literal["success", "failed"]
    source_url_attempted: str
    records: list[WeatherRecord]
    error_detail: str | None


class WeatherProvider(Protocol):
    def fetch_daily_point(
        self, *, latitude: float, longitude: float, start: str, end: str, timeout_s: float = 15.0
    ) -> WeatherFetchOutcome: ...


class NasaPowerWeatherProvider:
    """Real implementation. Verbatim logic moved from the previous
    `fetch_and_store_nasa_power` — same NASA POWER daily-point endpoint, same params,
    same JSON-shape parsing. Takes plain coordinates rather than an ORM `Location`, so
    it has no dependency on `app.models`."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or get_settings().nasa_power_base_url

    def fetch_daily_point(
        self, *, latitude: float, longitude: float, start: str, end: str, timeout_s: float = 15.0
    ) -> WeatherFetchOutcome:
        url = f"{self.base_url}/daily/point"
        params = {
            "parameters": NASA_POWER_PARAMETERS,
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": start,
            "end": end,
            "format": "JSON",
        }
        full_url = requests.Request("GET", url, params=params).prepare().url

        try:
            response = requests.get(url, params=params, timeout=timeout_s)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return WeatherFetchOutcome("failed", full_url, [], f"{type(exc).__name__}: {exc}")

        try:
            params_block = payload["properties"]["parameter"]
        except (KeyError, TypeError) as exc:
            return WeatherFetchOutcome("failed", full_url, [], f"Unexpected response shape: {exc}")

        records = [
            WeatherRecord(
                observed_date=datetime.strptime(date_str, "%Y%m%d"),
                precipitation_mm=_clean(params_block.get("PRECTOTCORR", {}).get(date_str)),
                temperature_c=_clean(params_block.get("T2M", {}).get(date_str)),
                relative_humidity_pct=_clean(params_block.get("RH2M", {}).get(date_str)),
                wind_speed_ms=_clean(params_block.get("WS2M", {}).get(date_str)),
            )
            for date_str in params_block.get("PRECTOTCORR", {}).keys()
        ]
        return WeatherFetchOutcome("success", full_url, records, None)


def get_weather_provider() -> WeatherProvider:
    """FastAPI dependency. Production wiring resolves to the real NASA POWER call;
    tests override this with `app.dependency_overrides[get_weather_provider] = ...`,
    the same mechanism `backend/tests/conftest.py` already uses for `get_db`."""
    return NasaPowerWeatherProvider()
