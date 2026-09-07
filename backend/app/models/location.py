from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Location(Base):
    """A monitored location. Coordinates for compound/settlement-level locations
    (Kanyama, Ng'ombe) are city-approximate, not independently geocoded — see
    `coordinate_confidence`. Do not treat them as survey-grade."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    province: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    coordinate_confidence: Mapped[str] = mapped_column(
        String(80), default="city-approximate"
    )
    evidence_note: Mapped[str] = mapped_column(Text, default="")
    evidence_source_url: Mapped[str] = mapped_column(Text, default="")
