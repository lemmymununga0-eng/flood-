from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ml.predictor import ModelArtifactsUnavailable, predict_risk
from app.models.location import Location
from app.models.prediction import Prediction
from app.schemas.inference import RiskPredictionRequest, RiskPredictionResponse
from app.schemas.prediction import PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=list[PredictionOut])
def list_predictions(db: Session = Depends(get_db)) -> list[Prediction]:
    """Stored predictions only. Rows appear here once inference has actually been run
    and persisted; an empty list is an honest empty state, never a fabricated figure.
    To score a weather observation on demand, use POST /predictions/predict."""
    return db.scalars(select(Prediction).order_by(Prediction.predicted_at.desc())).all()


@router.post("/predict", response_model=RiskPredictionResponse)
def predict(payload: RiskPredictionRequest, db: Session = Depends(get_db)) -> dict:
    """Run the real trained model against a supplied weather observation.

    This is on-demand inference over caller-supplied weather — it does NOT fetch live
    weather and does not claim to be a real-time forecast (NASA POWER lags 2-3 days;
    see the research bundle's docs/PRODUCTION_PREDICTION.md). The result is a risk
    probability and category with explicit caveats, never a deterministic claim that a
    flood will occur."""
    name = payload.location_name
    latitude = longitude = None

    if payload.location_id is not None:
        location = db.get(Location, payload.location_id)
        if location is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Location not found"},
            )
        name, latitude, longitude = location.name, location.latitude, location.longitude
    elif not name:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_request",
                "message": "Supply either location_id or location_name.",
            },
        )

    try:
        return predict_risk(
            location_name=name,
            latitude=latitude,
            longitude=longitude,
            precipitation_mm=payload.precipitation_mm,
            temperature_c=payload.temperature_c,
            temperature_max_c=payload.temperature_max_c,
            temperature_min_c=payload.temperature_min_c,
            relative_humidity_pct=payload.relative_humidity_pct,
            wind_speed_10m_ms=payload.wind_speed_10m_ms,
            observation_date=payload.observation_date,
        )
    except ModelArtifactsUnavailable as exc:
        # Reported honestly as unavailable — never substituted with a synthetic result.
        raise HTTPException(
            status_code=503,
            detail={"error": "model_unavailable", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_input", "message": str(exc)}
        ) from exc
