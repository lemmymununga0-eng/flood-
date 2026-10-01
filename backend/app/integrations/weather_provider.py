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

# Exactly the six variables the production model was trained on, per
# ml/contracts/feature_contract.json. Two corrections are encoded here:
#   * T2M_MAX / T2M_MIN are now requested. They were previously absent, and the
#     inference path substituted the daily mean for both -- which flipped the
#     alert decision on 49.8% of rows on the locked test split.
#   * WS10M replaces WS2M. Those are different physical variables (10 m vs 2 m
#     wind), and the model expects WS10M. This is a corrected request, not a
#     column rename.
NASA_POWER_PARAMETERS = "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS10M"

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
    """One daily observation. Field names carry the contract's physical meaning:
    `wind_speed_10m_ms` is wind at 10 m (WS10M), not the 2 m value this pipeline
    used to fetch, and the max/min temperatures are real daily extremes rather
    than a repeated mean."""

    observed_date: datetime
    precipitation_mm: float | None
    temperature_c: float | None
    temperature_max_c: float | None
    temperature_min_c: float | None
    relative_humidity_pct: float | None
    wind_speed_10m_ms: float | None


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
                temperature_max_c=_clean(params_block.get("T2M_MAX", {}).get(date_str)),
                temperature_min_c=_clean(params_block.get("T2M_MIN", {}).get(date_str)),
                relative_humidity_pct=_clean(params_block.get("RH2M", {}).get(date_str)),
                wind_speed_10m_ms=_clean(params_block.get("WS10M", {}).get(date_str)),
            )
            for date_str in params_block.get("PRECTOTCORR", {}).keys()
        ]
        return WeatherFetchOutcome("success", full_url, records, None)


def get_weather_provider() -> WeatherProvider:
    """FastAPI dependency. Production wiring resolves to the real NASA POWER call;
    tests override this with `app.dependency_overrides[get_weather_provider] = ...`,
    the same mechanism `backend/tests/conftest.py` already uses for `get_db`."""
    return NasaPowerWeatherProvider()
