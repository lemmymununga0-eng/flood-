from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.integrations.weather_provider import WeatherProvider, get_weather_provider
from app.models.location import Location
from app.models.weather_observation import WeatherObservation
from app.schemas.weather import WeatherIngestResult, WeatherObservationOut
from app.services.weather_ingestion import fetch_and_store_nasa_power

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/{location_id}", response_model=list[WeatherObservationOut])
def list_observations(location_id: int, db: Session = Depends(get_db)) -> list[WeatherObservation]:
    return db.scalars(
        select(WeatherObservation)
        .where(WeatherObservation.location_id == location_id)
        .order_by(WeatherObservation.observed_date)
    ).all()


@router.post("/{location_id}/ingest", response_model=WeatherIngestResult)
def ingest_observations(
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
