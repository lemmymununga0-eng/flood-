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
    relative_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(80))
    retrieved_at: Mapped[str] = mapped_column(DateTime)
