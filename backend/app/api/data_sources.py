from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database.session import get_db
from app.models.data_source import DataSource
from app.models.user import User
from app.schemas.data_source import DataSourceOut
from app.services.data_source_health import check_data_source

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("", response_model=list[DataSourceOut])
def list_data_sources(db: Session = Depends(get_db)) -> list[DataSource]:
    return db.scalars(select(DataSource).order_by(DataSource.name)).all()


@router.post("/{source_id}/check", response_model=DataSourceOut)
def check_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ANALYST", "OPERATOR")),
) -> DataSource:
    source = db.get(DataSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Data source not found"})
    return check_data_source(db, source)
