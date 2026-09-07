from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class DataSource(Base):
    """The real catalog of external data sources this project depends on (NASA POWER,
    CHIRPS, DMMU/WARMA, the hand-compiled flood-event log). `last_check_status` and
    `last_check_detail` are only ever written by an actual connectivity check
    (`app/services/data_source_health.py`) — never hardcoded to "operational"."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(60))
    base_url: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_check_status: Mapped[str] = mapped_column(String(20), default="unknown")
    last_check_detail: Mapped[str] = mapped_column(Text, default="")
