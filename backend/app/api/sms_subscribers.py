from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.deps import require_roles
from app.core.sms import send_sms
from app.database.session import get_db
from app.models.location import Location
from app.models.sms_subscriber import SmsSubscriber
from app.models.user import User
from app.schemas.alert import SmsDelivery
from app.schemas.sms_subscriber import SubscriberCreate, SubscriberOut

router = APIRouter(prefix="/sms-subscribers", tags=["sms-subscribers"])
_staff = require_roles("ADMIN", "ANALYST", "OPERATOR")


@router.get("", response_model=list[SubscriberOut])
def list_subscribers(db: Session = Depends(get_db), _: User = Depends(_staff)):
    return db.scalars(select(SmsSubscriber).order_by(SmsSubscriber.created_at.desc())).all()


@router.post("", response_model=SubscriberOut, status_code=201)
def add_subscriber(
    payload: SubscriberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    if payload.location_id is not None and db.get(Location, payload.location_id) is None:
        raise HTTPException(400, detail={"error": "unknown_location", "message": "Unknown location_id"})
    if db.scalar(select(SmsSubscriber.id).where(SmsSubscriber.phone == payload.phone)) is not None:
        raise HTTPException(409, detail={"error": "duplicate", "message": "That number is already registered"})
    sub = SmsSubscriber(
        phone=payload.phone,
        name=payload.name,
        location_id=payload.location_id,
        active=True,
        created_by=user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(sub)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail={"error": "duplicate", "message": "That number is already registered"})
    record_audit_event(db, user_id=user.id, action="sms_subscriber_added", entity_type="sms_subscriber", entity_id=sub.id)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{subscriber_id}")
def remove_subscriber(subscriber_id: int, db: Session = Depends(get_db), user: User = Depends(_staff)):
    sub = db.get(SmsSubscriber, subscriber_id)
    if sub is None:
        raise HTTPException(404, detail={"error": "not_found", "message": "Subscriber not found"})
    db.delete(sub)
    record_audit_event(db, user_id=user.id, action="sms_subscriber_removed", entity_type="sms_subscriber", entity_id=subscriber_id)
    db.commit()
    return {"deleted": subscriber_id}


@router.post("/{subscriber_id}/test", response_model=list[SmsDelivery])
def send_test_sms(subscriber_id: int, db: Session = Depends(get_db), user: User = Depends(_staff)):
    """Send one clearly-labelled test message to a single registered number."""
    sub = db.get(SmsSubscriber, subscriber_id)
    if sub is None:
        raise HTTPException(404, detail={"error": "not_found", "message": "Subscriber not found"})
    results = send_sms([sub.phone], "FloodShield DEMO: test message. Your number is registered for flood alerts.")
    record_audit_event(db, user_id=user.id, action="sms_test_sent", entity_type="sms_subscriber", entity_id=sub.id)
    db.commit()
    return [SmsDelivery(**r.as_dict()) for r in results]
