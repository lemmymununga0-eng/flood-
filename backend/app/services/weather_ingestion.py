"""Real NASA POWER ingestion attempt.

This makes an actual HTTP request — it does not fabricate a response on failure. If the
request fails (network policy, API outage, bad params), the failure is logged and
reported honestly to the caller; no synthetic weather values are substituted. See
docs/DATA-SOURCES.md for why this specific call is expected to fail in this project's
current cloud development sandbox (egress policy), while remaining expected to work
from an unrestricted environment (a developer machine, or the eventual production host).
"""
import logging
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.location import Location
from app.models.weather_observation import WeatherObservation

logger = logging.getLogger(__name__)
settings = get_settings()

NASA_POWER_PARAMETERS = "PRECTOTCORR,T2M,RH2M,WS2M"


def fetch_and_store_nasa_power(
    db: Session, location: Location, start: str, end: str, timeout_s: float = 15.0
) -> dict:
    """Attempt a real NASA POWER daily-point request for `location` between `start`
    and `end` (YYYYMMDD). Returns a dict describing exactly what happened — success or
    failure — for the API layer to relay honestly to clients."""
    url = f"{settings.nasa_power_base_url}/daily/point"
    params = {
        "parameters": NASA_POWER_PARAMETERS,
        "community": "AG",
        "longitude": location.longitude,
        "latitude": location.latitude,
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
        logger.warning("NASA POWER request failed for location_id=%s: %s", location.id, exc)
        return {
            "status": "failed",
            "location_id": location.id,
            "source_url_attempted": full_url,
            "observations_stored": 0,
            "error_detail": f"{type(exc).__name__}: {exc}",
        }

    try:
        params_block = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        logger.warning("NASA POWER response shape unexpected for location_id=%s: %s", location.id, exc)
        return {
            "status": "failed",
            "location_id": location.id,
            "source_url_attempted": full_url,
            "observations_stored": 0,
            "error_detail": f"Unexpected response shape: {exc}",
        }

    stored = 0
    now = datetime.now(timezone.utc)
    dates = params_block.get("PRECTOTCORR", {}).keys()
    for date_str in dates:
        obs = WeatherObservation(
            location_id=location.id,
            observed_date=datetime.strptime(date_str, "%Y%m%d"),
            precipitation_mm=params_block.get("PRECTOTCORR", {}).get(date_str),
            temperature_c=params_block.get("T2M", {}).get(date_str),
            relative_humidity_pct=params_block.get("RH2M", {}).get(date_str),
            wind_speed_ms=params_block.get("WS2M", {}).get(date_str),
            source="NASA POWER",
            retrieved_at=now,
        )
        db.add(obs)
        stored += 1
    db.commit()

    return {
        "status": "success",
        "location_id": location.id,
        "source_url_attempted": full_url,
        "observations_stored": stored,
        "error_detail": None,
    }
