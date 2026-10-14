import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database.session import get_db
from app.integrations.weather_provider import WeatherProvider, get_weather_provider
from app.ml.predictor import MODEL_VERSION, ModelArtifactsUnavailable, predict_risk
from app.models.location import Location
from app.models.prediction import ModelVersion, Prediction
from app.models.user import User
from app.models.weather_observation import WeatherObservation
from app.repositories.weather_observation_repository import WeatherObservationRepository
from app.services.forecast_outlook import WindowPrediction, build_outlook, local_today

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _d(value) -> dt.date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, dt.datetime) else value


@router.get("/outlook")
def seven_day_outlook(location_id: int, db: Session = Depends(get_db)) -> dict:
    """Read-only. Dated seven-day calendar plus the latest STORED window prediction for the
    location. Does not run or alter the model."""
    if db.get(Location, location_id) is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Location not found"})

    row = db.scalars(
        select(Prediction)
        .where(Prediction.location_id == location_id)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    ).first()

    prediction = None
    if row is not None and row.target_window_start and row.target_window_end:
        mv = db.get(ModelVersion, row.model_version_id)
        prediction = WindowPrediction(
            risk_level=row.risk_level,
            probability=row.prediction_probability,
            window_start=_d(row.target_window_start),
            window_end=_d(row.target_window_end),
            observation_date=_d(row.observation_date),
            model_version=mv.version if mv else None,
            predicted_at=row.predicted_at,
        )
    return build_outlook(local_today(), prediction)


_FEATURES = ("precipitation_mm", "temperature_c", "temperature_max_c", "temperature_min_c",
             "relative_humidity_pct", "wind_speed_10m_ms")
_NASA_LAG_DAYS = 3  # NASA POWER publishes with a lag; asking for later days returns sentinels


@router.post("/outlook/refresh")
def refresh_outlook(
    location_id: int,
    db: Session = Depends(get_db),
    provider: WeatherProvider = Depends(get_weather_provider),
    _: User = Depends(require_roles("ADMIN", "ANALYST", "OPERATOR")),
) -> dict:
    """Fetch the latest REAL NASA POWER weather for the location, score the newest complete
    day with the unchanged production model and store the result (superseding the previous
    prediction for the location). Fails honestly: no weather => no prediction. The model,
    thresholds and bands are not touched; this is the same flow as scripts/populate_real_data.py."""
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Location not found"})

    mv = db.scalar(select(ModelVersion).where(ModelVersion.version == MODEL_VERSION))
    if mv is None:
        raise HTTPException(status_code=503, detail={
            "error": "model_not_registered", "message": "No registered model version; cannot store a prediction."})

    end = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=_NASA_LAG_DAYS)
    start = end - dt.timedelta(days=10)
    outcome = provider.fetch_daily_point(latitude=location.latitude, longitude=location.longitude,
                                         start=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d"))
    if outcome.status == "failed":
        raise HTTPException(status_code=502, detail={
            "error": "weather_unavailable",
            "message": "Weather data could not be retrieved, so no prediction was made."})

    usable = sorted((r for r in outcome.records if all(getattr(r, f) is not None for f in _FEATURES)),
                    key=lambda r: r.observed_date)
    if not usable:
        raise HTTPException(status_code=502, detail={
            "error": "no_complete_weather",
            "message": "The provider returned no complete day of weather, so no prediction was made."})

    known = {_d(d) for (d,) in db.execute(select(WeatherObservation.observed_date).where(
        WeatherObservation.location_id == location_id)).all()}
    fresh = [r for r in usable if _d(r.observed_date) not in known]
    if fresh:
        WeatherObservationRepository(db).bulk_add(location_id, fresh)

    latest = usable[-1]
    try:
        result = predict_risk(
            location_name=location.name, latitude=location.latitude, longitude=location.longitude,
            precipitation_mm=latest.precipitation_mm, temperature_c=latest.temperature_c,
            temperature_max_c=latest.temperature_max_c, temperature_min_c=latest.temperature_min_c,
            relative_humidity_pct=latest.relative_humidity_pct, wind_speed_10m_ms=latest.wind_speed_10m_ms,
            observation_date=latest.observed_date.strftime("%Y-%m-%d"))
    except ModelArtifactsUnavailable as exc:
        raise HTTPException(status_code=503, detail={
            "error": "model_unavailable", "message": "The prediction model is not currently available."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_input", "message": str(exc)}) from exc

    for old in db.scalars(select(Prediction).where(
            Prediction.location_id == location_id, Prediction.is_stale.is_(False))).all():
        old.is_stale = True
    obs_date = latest.observed_date
    db.add(Prediction(
        location_id=location_id, model_version_id=mv.id,
        predicted_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
        prediction_probability=result["risk_probability_calibrated"],
        risk_level=result["risk_level"].lower(),
        prediction_horizon=f"{result['prediction_horizon_days']} days",
        observation_date=obs_date,
        target_window_start=obs_date + dt.timedelta(days=1),
        target_window_end=obs_date + dt.timedelta(days=result["prediction_horizon_days"]),
        feature_contract_version=result["feature_contract_version"], is_stale=False,
        explanation=json.dumps({"observation_date": obs_date.strftime("%Y-%m-%d"),
                                "raw_score": result["risk_probability_raw"],
                                "feature_contract_version": result["feature_contract_version"]})))
    db.commit()
    return seven_day_outlook(location_id, db)
