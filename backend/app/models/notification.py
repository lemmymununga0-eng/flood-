from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Notification(Base):
    """A real, user-facing notification. Currently written only from
    app/api/citizen_reports.py's moderate_report (via app/core/notifications.py's
    notify_user()) — the one place in the app with an unambiguous single recipient
    (the report's original reporter). Alert issuance does NOT generate notifications:
    Alert.audience is free text, not a set of real user ids, so there is no real
    targeting mechanism to notify against yet. See docs/ARCHITECTURE.md for the scope
    note."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
