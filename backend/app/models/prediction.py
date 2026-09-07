from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ModelVersion(Base):
    """The model registry: a trained, packaged model artifact's metadata. Empty until
    Phase 9 (Model Packaging) actually produces one — this table existing is not a
    claim that a model exists. `is_active` marks the single version (if any) currently
    used for inference; `registered_at` is set when the row is created, not backdated
    to a claimed training date."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True)
    model_type: Mapped[str] = mapped_column(String(40))
    training_period_start: Mapped[str] = mapped_column(DateTime)
    training_period_end: Mapped[str] = mapped_column(DateTime)
    metrics_json: Mapped[str] = mapped_column(Text)
    artifact_path: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    """A model-generated flood-risk prediction. Empty until a real trained model
    (ModelVersion) exists and inference has actually run — see
    docs/ARCHITECTURE.md's training/inference separation rule. Never seeded with
    invented probabilities."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"))
    predicted_at: Mapped[str] = mapped_column(DateTime)
    prediction_probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20))
    prediction_horizon: Mapped[str] = mapped_column(String(40))
    explanation: Mapped[str] = mapped_column(Text, default="")
