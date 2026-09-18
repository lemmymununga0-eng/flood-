"""Persistence for `WeatherObservation` rows. Wraps the exact db.add()/db.commit()
sequence that used to sit inline in `app/services/weather_ingestion.py` — same fields,
same `retrieved_at` stamp, one commit per batch.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.weather_provider import WeatherRecord
from app.models.weather_observation import WeatherObservation


class WeatherObservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_add(self, location_id: int, records: list[WeatherRecord], source: str = "NASA POWER") -> int:
        now = datetime.now(timezone.utc)
        stored = 0
        for record in records:
            self.db.add(
                WeatherObservation(
                    location_id=location_id,
                    observed_date=record.observed_date,
                    precipitation_mm=record.precipitation_mm,
                    temperature_c=record.temperature_c,
                    relative_humidity_pct=record.relative_humidity_pct,
                    wind_speed_ms=record.wind_speed_ms,
                    source=source,
                    retrieved_at=now,
                )
            )
            stored += 1
        self.db.commit()
        return stored
