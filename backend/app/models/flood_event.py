from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class FloodEvent(Base):
    """A reported historical flood event. Sourced from
    ai-engine/data/external/zambia_flood_events_log.csv (11 rows, see that file's
    README for provenance and confidence caveats). This is NOT a validated ground-truth
    label yet — see docs/ML-METHODOLOGY.md."""

    __tablename__ = "flood_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    start_date: Mapped[str] = mapped_column(Date)
    end_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    provinces: Mapped[str] = mapped_column(String(200))
    districts: Mapped[str] = mapped_column(Text, default="")
    rivers: Mapped[str] = mapped_column(String(200), default="")
    impact_note: Mapped[str] = mapped_column(Text, default="")
    deaths: Mapped[int | None] = mapped_column(nullable=True)
    source_name: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    confidence_notes: Mapped[str] = mapped_column(Text, default="")
