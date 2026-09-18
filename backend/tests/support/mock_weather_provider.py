"""Test-only stand-in for NasaPowerWeatherProvider. Deliberately lives under
`backend/tests/`, never under `app/`, so it can never be reached by a production
import path — the only way to use it is an explicit
`app.dependency_overrides[get_weather_provider] = ...` inside a test."""
from app.integrations.weather_provider import WeatherFetchOutcome


class MockWeatherProvider:
    def __init__(self, outcome: WeatherFetchOutcome):
        self._outcome = outcome

    def fetch_daily_point(self, *, latitude, longitude, start, end, timeout_s=15.0) -> WeatherFetchOutcome:
        return self._outcome
