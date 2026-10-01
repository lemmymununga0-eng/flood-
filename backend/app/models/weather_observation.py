from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class WeatherObservation(Base):
    """A real meteorological observation for a location. Populated only from an
    actual successful ingestion call (see app/services/weather_ingestion.py) — never
    backfilled with placeholder values. Empty until a real fetch succeeds."""

    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    observed_date: Mapped[str] = mapped_column(DateTime)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Real daily extremes. The model requires these as distinct inputs; before the
    # feature-contract repair they were absent here, so the inference path passed the
    # daily mean three times over. See ml/contracts/feature_contract.json.
    temperature_max_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_min_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Wind at 10 m (NASA POWER WS10M), matching the trained feature. The legacy
    # `wind_speed_ms` column held 2 m wind and is retained, unused, so existing rows
    # are not silently reinterpreted as something they are not.
    wind_speed_10m_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(80))
    retrieved_at: Mapped[str] = mapped_column(DateTime)
