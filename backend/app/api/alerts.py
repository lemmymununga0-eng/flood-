from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.alert import Alert
from app.models.location import Location
from app.schemas.alert import AlertCreate, AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db)) -> list[Alert]:
    return db.scalars(select(Alert).order_by(Alert.created_at.desc())).all()


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)) -> Alert:
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=400, detail="Unknown location_id")
    alert = Alert(
        title=payload.title,
        risk_level=payload.risk_level,
        location_id=payload.location_id,
        message=payload.message,
        audience=payload.audience,
        channels=payload.channels,
        status="issued",
        valid_until=payload.valid_until,
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
