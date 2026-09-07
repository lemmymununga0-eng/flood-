from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Alert(Base):
    """A dashboard early-warning alert. Real create/list only — no delivery workflow
    (SMS/email/USSD) is wired up, since no provider is configured (see
    docs/DATA-SOURCES.md / .env.example: TWILIO_* are empty). Every alert created here
    is genuinely persisted and genuinely visible on /alerts - it is not a static mock."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    risk_level: Mapped[str] = mapped_column(String(20))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    message: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(120), default="")
    channels: Mapped[str] = mapped_column(String(120), default="Dashboard")
    status: Mapped[str] = mapped_column(String(20), default="issued")
    valid_until: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime)
