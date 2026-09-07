from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeatherObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    observed_date: datetime
    precipitation_mm: float | None
    temperature_c: float | None
    relative_humidity_pct: float | None
    wind_speed_ms: float | None
    source: str
    retrieved_at: datetime


class WeatherIngestResult(BaseModel):
    """Honest result of an ingestion attempt. `status` is one of
    'success' | 'failed' — never a fabricated success when the fetch didn't happen."""

    status: str
    location_id: int
    source_url_attempted: str
    observations_stored: int
    error_detail: str | None = None
