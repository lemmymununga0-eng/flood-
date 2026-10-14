"""Persistence for `WeatherObservation` rows. Wraps the exact db.add()/db.commit()
sequence that used to sit inline in `app/services/weather_ingestion.py` — same fields,
same `retrieved_at` stamp, one commit per batch.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.weather_provider import WeatherRecord
from app.models.weather_observation import WeatherObservation


class WeatherObservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_add(self, location_id: int, records: list[WeatherRecord], source: str = "NASA POWER") -> int:
        now = datetime.now(timezone.utc)
        stored = 0
        # One observation per location per calendar day. Repeated or concurrent ingestion
        # (this is reachable from a public endpoint) must not multiply rows or skew averages.
        known = {
            d.date() if isinstance(d, datetime) else d
            for (d,) in self.db.execute(
                select(WeatherObservation.observed_date).where(
                    WeatherObservation.location_id == location_id)
            ).all()
        }
        for record in records:
            day = record.observed_date.date() if isinstance(record.observed_date, datetime) else record.observed_date
            if day in known:
                continue
            known.add(day)
            self.db.add(
                WeatherObservation(
                    location_id=location_id,
                    observed_date=record.observed_date,
                    precipitation_mm=record.precipitation_mm,
                    temperature_c=record.temperature_c,
                    temperature_max_c=record.temperature_max_c,
                    temperature_min_c=record.temperature_min_c,
                    relative_humidity_pct=record.relative_humidity_pct,
                    wind_speed_10m_ms=record.wind_speed_10m_ms,
                    source=source,
                    retrieved_at=now,
                )
            )
            stored += 1
        self.db.commit()
        return stored
