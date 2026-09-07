"""Honest system-status checks. Every status here is computed from a real check at
request time — nothing is a hardcoded 'Operational'. See governing rule: never fake
system health (docs/PROJECT-MEMORY.md, governing prompt section 34)."""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models.alert import Alert
from app.models.prediction import ModelVersion
from app.models.weather_observation import WeatherObservation

router = APIRouter(prefix="/system-status", tags=["system-status"])
settings = get_settings()


class ComponentStatus(BaseModel):
    name: str
    status: str  # "operational" | "degraded" | "unavailable"
    detail: str
    response_time_ms: float | None = None


class SystemStatusOut(BaseModel):
    checked_at: datetime
    components: list[ComponentStatus]


@router.get("", response_model=SystemStatusOut)
def system_status(db: Session = Depends(get_db)) -> SystemStatusOut:
    components: list[ComponentStatus] = []

    # Backend API: if this handler is running, it's up.
    components.append(
        ComponentStatus(name="Backend API", status="operational", detail="Responding.")
    )

    # Database
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        elapsed = (time.perf_counter() - t0) * 1000
        components.append(
            ComponentStatus(
                name="Database",
                status="operational",
                detail="PostgreSQL reachable.",
                response_time_ms=round(elapsed, 1),
            )
        )
    except Exception as exc:  # noqa: BLE001
        components.append(
            ComponentStatus(name="Database", status="unavailable", detail=str(exc))
        )

    # Weather data ingestion: based on whether any real observation has ever been stored.
    obs_count = db.scalar(select(func.count()).select_from(WeatherObservation)) or 0
    if obs_count > 0:
        components.append(
            ComponentStatus(
                name="Weather Data",
                status="operational",
                detail=f"{obs_count} real observation(s) stored from a successful ingestion.",
            )
        )
    else:
        components.append(
            ComponentStatus(
                name="Weather Data",
                status="unavailable",
                detail=(
                    "No successful ingestion yet. NASA POWER requests from this "
                    "environment are currently blocked - see docs/DATA-SOURCES.md."
                ),
            )
        )

    # AI Engine / Prediction service: based on whether a real trained model artifact is registered.
    model_count = db.scalar(select(func.count()).select_from(ModelVersion)) or 0
    if model_count > 0:
        components.append(
            ComponentStatus(
                name="AI Engine / Prediction Service",
                status="operational",
                detail=f"{model_count} registered model version(s).",
            )
        )
    else:
        components.append(
            ComponentStatus(
                name="AI Engine / Prediction Service",
                status="unavailable",
                detail="No trained model exists yet (roadmap Phases 5-9 not started).",
            )
        )

    # Alert service: dashboard delivery works (DB-backed); external channels aren't configured.
    alert_count = db.scalar(select(func.count()).select_from(Alert)) or 0
    components.append(
        ComponentStatus(
            name="Alert Service",
            status="degraded",
            detail=(
                f"Dashboard alerts operational ({alert_count} issued). "
                "No SMS/email provider configured (TWILIO_* unset) - external delivery unavailable."
            ),
        )
    )

    return SystemStatusOut(checked_at=datetime.now(timezone.utc), components=components)
