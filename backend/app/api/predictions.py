from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=list[PredictionOut])
def list_predictions(db: Session = Depends(get_db)) -> list[Prediction]:
    """Real predictions only. No model has been trained yet (Phases 5-9 not started),
    so this legitimately returns an empty list — the frontend renders that as an
    honest empty state, never a fabricated risk figure."""
    return db.scalars(select(Prediction).order_by(Prediction.predicted_at.desc())).all()
