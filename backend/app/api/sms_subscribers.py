from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.deps import require_roles
from app.database.session import get_db
from app.models.location import Location
from app.models.sms_subscriber import SmsSubscriber
from app.models.user import User
from app.schemas.sms_subscriber import ConsentIn, SubscriberCreate, SubscriberOut

router = APIRouter(prefix="/sms-subscribers", tags=["sms-subscribers"])
_admin = require_roles("ADMIN")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get(db: Session, subscriber_id: int) -> SmsSubscriber:
    sub = db.get(SmsSubscriber, subscriber_id)
    if sub is None:
        raise HTTPException(404, detail={"error": "not_found", "message": "Subscriber not found"})
    return sub


@router.get("", response_model=list[SubscriberOut])
def list_subscribers(db: Session = Depends(get_db), _: User = Depends(_admin)):
    return db.scalars(select(SmsSubscriber).order_by(SmsSubscriber.created_at.desc())).all()


@router.post("", response_model=SubscriberOut, status_code=201)
def add_subscriber(
    payload: SubscriberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_admin),
):
    if payload.location_id is not None and db.get(Location, payload.location_id) is None:
        raise HTTPException(400, detail={"error": "unknown_location", "message": "Unknown location_id"})
    dup = {"error": "duplicate", "message": "That number is already registered"}
    if db.scalar(select(SmsSubscriber.id).where(SmsSubscriber.phone == payload.phone)) is not None:
        raise HTTPException(409, detail=dup)
    now = _now()
    sub = SmsSubscriber(
        phone=payload.phone,
        name=payload.name,
        location_id=payload.location_id,
        active=True,
        consent_at=now,
        consent_note=payload.consent_note,
        created_by=user.id,
        created_at=now,
    )
    db.add(sub)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail=dup)
    record_audit_event(db, user_id=user.id, action="sms_subscriber_added", entity_type="sms_subscriber", entity_id=sub.id)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/{subscriber_id}/opt-out", response_model=SubscriberOut)
def opt_out(subscriber_id: int, db: Session = Depends(get_db), user: User = Depends(_admin)):
    """Record that this person no longer wants SMS. Kept (not deleted) so the opt-out is
    remembered and the number cannot be silently re-added."""
    sub = _get(db, subscriber_id)
    sub.active = False
    sub.opted_out_at = _now()
    record_audit_event(db, user_id=user.id, action="sms_subscriber_opted_out", entity_type="sms_subscriber", entity_id=sub.id)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/{subscriber_id}/resubscribe", response_model=SubscriberOut)
def resubscribe(
    subscriber_id: int,
    payload: ConsentIn,
    db: Session = Depends(get_db),
    user: User = Depends(_admin),
):
    sub = _get(db, subscriber_id)
    sub.active = True
    sub.opted_out_at = None
    sub.consent_at = _now()
    sub.consent_note = payload.consent_note.strip()[:200]
    record_audit_event(db, user_id=user.id, action="sms_subscriber_resubscribed", entity_type="sms_subscriber", entity_id=sub.id)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{subscriber_id}")
def remove_subscriber(subscriber_id: int, db: Session = Depends(get_db), user: User = Depends(_admin)):
    sub = _get(db, subscriber_id)
    db.delete(sub)
    record_audit_event(db, user_id=user.id, action="sms_subscriber_removed", entity_type="sms_subscriber", entity_id=subscriber_id)
    db.commit()
    return {"deleted": subscriber_id}
