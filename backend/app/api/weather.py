from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.integrations.weather_provider import WeatherProvider, get_weather_provider
from app.models.location import Location
from app.models.weather_observation import WeatherObservation
from app.schemas.weather import WeatherIngestResult, WeatherObservationOut
from app.services.weather_ingestion import fetch_and_store_nasa_power

router = APIRouter(prefix="/weather", tags=["weather"])


# NOTE: declared BEFORE /{location_id} on purpose — FastAPI matches routes in
# declaration order, and "summary" would otherwise be parsed as an int location_id.
@router.get("/summary")
def weather_summary(db: Session = Depends(get_db)) -> dict:
    """Real daily aggregates across every location that has stored observations.

    Aggregated from actual NASA POWER rows already in the database; nothing is
    interpolated or back-filled. Days with no usable reading simply do not appear."""
    rows = db.execute(
        select(
            WeatherObservation.observed_date,
            func.avg(WeatherObservation.precipitation_mm),
            func.max(WeatherObservation.precipitation_mm),
            func.avg(WeatherObservation.temperature_c),
            func.avg(WeatherObservation.relative_humidity_pct),
            func.count(WeatherObservation.id),
        )
        .where(WeatherObservation.precipitation_mm.isnot(None))
        .group_by(WeatherObservation.observed_date)
        .order_by(WeatherObservation.observed_date)
    ).all()

    return {
        "source": "NASA POWER (MERRA-2 reanalysis)",
        "days": [
            {
                "date": d.strftime("%Y-%m-%d"),
                "mean_rainfall_mm": round(float(avg_r), 3) if avg_r is not None else None,
                "max_rainfall_mm": round(float(max_r), 3) if max_r is not None else None,
                "mean_temperature_c": round(float(avg_t), 2) if avg_t is not None else None,
                "mean_humidity_pct": round(float(avg_h), 2) if avg_h is not None else None,
                "observations": int(n),
            }
            for d, avg_r, max_r, avg_t, avg_h, n in rows
        ],
    }


@router.get("/{location_id}", response_model=list[WeatherObservationOut])
def list_observations(location_id: int, db: Session = Depends(get_db)) -> list[WeatherObservation]:
    return db.scalars(
        select(WeatherObservation)
        .where(WeatherObservation.location_id == location_id)
        .order_by(WeatherObservation.observed_date)
    ).all()


@router.post("/{location_id}/ingest", response_model=WeatherIngestResult)
# Unauthenticated by design, but each call makes a real outbound NASA POWER request,
# so it is trivially abusable as an amplification vector without a cap. Same limiter
# and same style as the /auth routes.
@limiter.limit("10/minute")
def ingest_observations(
    request: Request,
    location_id: int,
    db: Session = Depends(get_db),
    provider: WeatherProvider = Depends(get_weather_provider),
) -> dict:
    """Attempt a real NASA POWER fetch for this location (last 10 days). Reports
    success or failure honestly — never substitutes fabricated data on failure."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=10)
    result = fetch_and_store_nasa_power(
        db, location, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), provider
    )
    return result
