from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Dam(Base):
    """A reservoir under study. Every descriptive field except identity is nullable on
    purpose: nothing here may be invented. Coordinates/capacity stay NULL until a verified
    source is recorded in `coordinate_source` / `capacity_source`."""

    __tablename__ = "dams"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    river_system: Mapped[str | None] = mapped_column(String(120), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    province: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    coordinate_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_provider: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # no_data | historical_only | manual_import | live  (live stays unused until a feed exists)
    data_status: Mapped[str] = mapped_column(String(20), default="no_data")
    last_successful_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    verification_required: Mapped[bool] = mapped_column(Boolean, default=True)


class DamObservation(Base):
    """One time-stamped set of measurements. NULL means 'not measured', never zero.
    observed_at (when it happened) is distinct from retrieved_at (when we stored it)."""

    __tablename__ = "dam_observations"
    __table_args__ = (
        UniqueConstraint("dam_id", "observed_at", "provider", name="uq_dam_obs_dam_time_provider"),
        Index("ix_dam_obs_dam_time", "dam_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dam_id: Mapped[int] = mapped_column(ForeignKey("dams.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # live | historical | manual_import | synthetic_test
    data_kind: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(160))
    source_reference: Mapped[str] = mapped_column(Text)
    quality_flag: Mapped[str] = mapped_column(String(20), default="unverified")

    reservoir_level_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    inflow_m3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    outflow_m3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    spillway_m3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    turbine_m3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    downstream_level_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    downstream_discharge_m3s: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_observed_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_forecast_mm: Mapped[float | None] = mapped_column(Float, nullable=True)


class DamReleaseNotice(Base):
    """A verified, officially published release announcement (verbatim description + reference)."""

    __tablename__ = "dam_release_notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    dam_id: Mapped[int] = mapped_column(ForeignKey("dams.id"), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(Text)
    issuing_body: Mapped[str] = mapped_column(String(160))
