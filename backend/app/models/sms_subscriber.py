from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SmsSubscriber(Base):
    """A phone number registered to receive flood-alert SMS. location_id NULL means "all
    areas". A number may be texted only while active AND consent_at is set AND opted_out_at
    is null: rows created before consent tracking existed have no consent_at, so they are
    never texted until consent is recorded."""

    __tablename__ = "sms_subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_note: Mapped[str] = mapped_column(String(200), default="")
    opted_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    @property
    def can_receive(self) -> bool:
        return bool(self.active and self.consent_at is not None and self.opted_out_at is None)
