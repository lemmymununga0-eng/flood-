"""Real NASA POWER ingestion attempt.

This makes an actual HTTP request — it does not fabricate a response on failure. If the
request fails (network policy, API outage, bad params), the failure is logged and
reported honestly to the caller; no synthetic weather values are substituted. See
docs/DATA-SOURCES.md for why this specific call is expected to fail in this project's
current cloud development sandbox (egress policy), while remaining expected to work
from an unrestricted environment (a developer machine, or the eventual production host).

The actual HTTP call and persistence are delegated to `app.integrations.weather_provider`
and `app.repositories.weather_observation_repository` respectively — this module is pure
orchestration so a test can inject a fake provider without a network dependency.
"""
import logging

from sqlalchemy.orm import Session

from app.integrations.weather_provider import WeatherProvider
from app.models.location import Location
from app.repositories.weather_observation_repository import WeatherObservationRepository

logger = logging.getLogger(__name__)


def fetch_and_store_nasa_power(
    db: Session, location: Location, start: str, end: str, provider: WeatherProvider, timeout_s: float = 15.0
) -> dict:
    """Attempt a real NASA POWER daily-point request for `location` between `start`
    and `end` (YYYYMMDD). Returns a dict describing exactly what happened — success or
    failure — for the API layer to relay honestly to clients."""
    outcome = provider.fetch_daily_point(
        latitude=location.latitude, longitude=location.longitude, start=start, end=end, timeout_s=timeout_s
    )

    if outcome.status == "failed":
        logger.warning("NASA POWER request failed for location_id=%s: %s", location.id, outcome.error_detail)
        return {
            "status": "failed",
            "location_id": location.id,
            "source_url_attempted": outcome.source_url_attempted,
            "observations_stored": 0,
            "error_detail": outcome.error_detail,
        }

    stored = WeatherObservationRepository(db).bulk_add(location.id, outcome.records)
    return {
        "status": "success",
        "location_id": location.id,
        "source_url_attempted": outcome.source_url_attempted,
        "observations_stored": stored,
        "error_detail": None,
    }
