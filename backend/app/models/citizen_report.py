from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CitizenReport(Base):
    """A real, citizen-submitted ground observation (e.g. "water rising near X
    bridge"). Distinct from `FloodEvent` (curated, sourced, historical) and from
    `Prediction` (model output) — this is unverified first-hand reporting and is
    explicitly labeled as such until a human moderator reviews it. Never auto-promoted
    into flood_events or used as a training label without human review."""

    __tablename__ = "citizen_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="unknown")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
