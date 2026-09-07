from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import Pagination, pagination_params
from app.database.session import get_db
from app.models.flood_event import FloodEvent
from app.schemas.flood_event import FloodEventOut

router = APIRouter(prefix="/flood-events", tags=["flood-events"])


@router.get("", response_model=list[FloodEventOut])
def list_flood_events(
    db: Session = Depends(get_db),
    province: str | None = None,
    sort: str = "start_date",
    page: Pagination = Depends(pagination_params),
) -> list[FloodEvent]:
    """Real, sourced historical flood events — NOT a validated ground-truth label yet.
    See docs/ML-METHODOLOGY.md and ai-engine/data/external/README.md."""
    sort_column = {
        "start_date": FloodEvent.start_date,
        "deaths": FloodEvent.deaths,
    }.get(sort, FloodEvent.start_date)
    query = select(FloodEvent).order_by(sort_column)
    if province:
        query = query.where(FloodEvent.provinces.ilike(f"%{province}%"))
    return db.scalars(query.limit(page.limit).offset(page.offset)).all()
