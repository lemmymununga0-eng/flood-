from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.flood_event import FloodEvent
from app.schemas.flood_event import FloodEventOut

router = APIRouter(prefix="/flood-events", tags=["flood-events"])


@router.get("", response_model=list[FloodEventOut])
def list_flood_events(db: Session = Depends(get_db)) -> list[FloodEvent]:
    """Real, sourced historical flood events — NOT a validated ground-truth label yet.
    See docs/ML-METHODOLOGY.md and ai-engine/data/external/README.md."""
    return db.scalars(select(FloodEvent).order_by(FloodEvent.start_date)).all()
