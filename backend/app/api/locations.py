from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import Pagination, pagination_params
from app.database.session import get_db
from app.models.location import Location
from app.schemas.location import LocationOut

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationOut])
def list_locations(
    db: Session = Depends(get_db),
    province: str | None = None,
    page: Pagination = Depends(pagination_params),
) -> list[Location]:
    query = select(Location).order_by(Location.name)
    if province:
        query = query.where(Location.province == province)
    return db.scalars(query.limit(page.limit).offset(page.offset)).all()
