from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SmsSubscriber(Base):
    """A phone number staff have registered to receive flood-alert SMS. location_id NULL
    means "all areas"; otherwise only alerts for that location are sent to this number."""

    __tablename__ = "sms_subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime)
