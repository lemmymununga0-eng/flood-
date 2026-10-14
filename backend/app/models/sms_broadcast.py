from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SmsBroadcast(Base):
    """One administrator-triggered send (a single test message or a group broadcast).
    `status` summarises SUBMISSION to the provider only; delivery is per message."""

    __tablename__ = "sms_broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(12))  # test | broadcast
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    segments: Mapped[int] = mapped_column(Integer, default=1)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String(30))
    environment: Mapped[str] = mapped_column(String(20), default="none")
    # sending | submitted | partial | failed | unknown | simulated
    status: Mapped[str] = mapped_column(String(12), default="sending")
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SmsMessage(Base):
    """One recipient of one broadcast: what the provider said at submission time, and
    (separately) what a delivery report later said."""

    __tablename__ = "sms_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(ForeignKey("sms_broadcasts.id"), index=True)
    subscriber_id: Mapped[int | None] = mapped_column(
        ForeignKey("sms_subscribers.id", ondelete="SET NULL"), nullable=True
    )
    phone_masked: Mapped[str] = mapped_column(String(20))
    submission_status: Mapped[str] = mapped_column(String(12), default="pending")
    submission_detail: Mapped[str] = mapped_column(String(300), default="")
    provider_message_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    provider_status: Mapped[str] = mapped_column(String(60), default="")
    provider_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[str | None] = mapped_column(String(30), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # not_reported | pending | delivered | failed - changed ONLY by a delivery report.
    delivery_status: Mapped[str] = mapped_column(String(14), default="not_reported")
    delivery_reported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[str] = mapped_column(String(200), default="")
