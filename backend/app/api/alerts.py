from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.deps import require_roles
from app.core.pagination import Pagination, pagination_params
from app.database.session import get_db
from app.models.alert import Alert
from app.models.location import Location
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    risk_level: str | None = None,
    location_id: int | None = None,
    page: Pagination = Depends(pagination_params),
) -> list[Alert]:
    query = select(Alert).order_by(Alert.created_at.desc())
    if risk_level:
        query = query.where(Alert.risk_level == risk_level)
    if location_id is not None:
        query = query.where(Alert.location_id == location_id)
    return db.scalars(query.limit(page.limit).offset(page.offset)).all()


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    issuer: User = Depends(require_roles("ADMIN", "ANALYST", "OPERATOR")),
) -> Alert:
    # RBAC added in the backend-integration build: previously anonymous, now requires
    # a role, since an unauthenticated public dashboard should not be able to issue
    # flood alerts to a citizen audience — see docs/PROJECT-MEMORY.md.
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=400, detail={"error": "unknown_location", "message": "Unknown location_id"})
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
    db.flush()
    record_audit_event(
        db, user_id=issuer.id, action="alert_issued", entity_type="alert", entity_id=alert.id
    )
    db.commit()
    db.refresh(alert)
    return alert
