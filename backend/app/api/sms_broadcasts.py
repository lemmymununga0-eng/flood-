"""Administrator-triggered SMS: preview, test send, confirmed group broadcast, history,
and the provider's delivery-report / STOP callbacks.

There is no automatic path into this module: every send is an explicit ADMIN request that
carries a confirmation flag and the recipient count the admin was shown.
"""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import sms
from app.core.audit import record_audit_event
from app.core.config import get_settings
from app.core.deps import require_roles
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.models.location import Location
from app.models.sms_broadcast import SmsBroadcast, SmsMessage
from app.models.sms_subscriber import SmsSubscriber
from app.models.user import User
from app.schemas.sms_broadcast import (
    BroadcastDetail,
    BroadcastOut,
    Compose,
    MessageOut,
    Preview,
    PreviewRecipient,
    PreviewRequest,
    ProviderStatus,
    SendBroadcast,
    SendTest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sms", tags=["sms"])
_admin = require_roles("ADMIN")

MAX_SEGMENTS = 3
_STOP_WORDS = {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"error": code, "message": message})


# --- helpers -----------------------------------------------------------------------------


def _location(db: Session, location_id: int) -> Location:
    loc = db.get(Location, location_id)
    if loc is None:
        raise _err(400, "unknown_location", "Unknown location_id")
    return loc


def _eligible(db: Session, location_id: int) -> tuple[list[SmsSubscriber], int]:
    """Active, consenting, not-opted-out subscribers for this location (or all areas),
    minus anything outside the optional allowlist. Returns (recipients, allowlist_skipped)."""
    rows = db.scalars(
        select(SmsSubscriber)
        .where(
            SmsSubscriber.active.is_(True),
            SmsSubscriber.consent_at.is_not(None),
            SmsSubscriber.opted_out_at.is_(None),
            (SmsSubscriber.location_id == location_id) | SmsSubscriber.location_id.is_(None),
        )
        .order_by(SmsSubscriber.id)
    ).all()
    allowed = [s for s in rows if sms.is_allowed(s.phone)]
    return allowed, len(rows) - len(allowed)


def _real_test_accepted(db: Session) -> bool:
    cfg = get_settings()
    if cfg.sms_provider == "simulated":
        return False
    return (
        db.scalar(
            select(SmsBroadcast.id)
            .where(
                SmsBroadcast.kind == "test",
                SmsBroadcast.provider == cfg.sms_provider,
                SmsBroadcast.environment == cfg.africastalking_environment,
                SmsBroadcast.status == "submitted",
            )
            .limit(1)
        )
        is not None
    )


def _provider_status(db: Session) -> ProviderStatus:
    info = sms.provider_status()
    tested = _real_test_accepted(db)
    return ProviderStatus(
        **info,
        real_test_accepted=tested,
        group_broadcast_unlocked=(
            info["configured"] and (not info["real"] or (info["broadcast_enabled"] and tested))
        ),
    )


def _blocking(db: Session, *, kind: str, count: int, segments: int) -> list[str]:
    status = _provider_status(db)
    reasons: list[str] = []
    if not status.configured:
        reasons.append("Provider is not configured: " + "; ".join(status.missing))
    if count == 0:
        reasons.append(
            "No recipient: the number must be active, have recorded consent, and match this location."
            if kind == "test"
            else "No eligible recipients: none are active, consenting and subscribed to this location."
        )
    if segments > MAX_SEGMENTS:
        reasons.append(f"Message is {segments} SMS parts; shorten it to {MAX_SEGMENTS} or fewer.")
    if kind == "broadcast" and status.real:
        if not status.broadcast_enabled:
            reasons.append("Group broadcasts are switched off (set SMS_BROADCAST_ENABLED=true).")
        if not status.real_test_accepted:
            reasons.append(
                "Send a test SMS to your own phone first; a real test must be accepted by the "
                "provider before group broadcasts unlock."
            )
    return reasons


def _test_recipient(db: Session, subscriber_id: int) -> SmsSubscriber:
    sub = db.get(SmsSubscriber, subscriber_id)
    if sub is None:
        raise _err(404, "not_found", "Subscriber not found")
    if not sub.can_receive:
        raise _err(400, "no_consent", "That number is not active with recorded consent.")
    if not sms.is_allowed(sub.phone):
        raise _err(400, "not_allowlisted", "That number is not on SMS_ALLOWED_NUMBERS.")
    return sub


def _counts(messages: list[SmsMessage]) -> dict:
    return {
        "accepted_count": sum(m.submission_status == "accepted" for m in messages),
        "delivered_count": sum(m.delivery_status == "delivered" for m in messages),
        "delivery_failed_count": sum(m.delivery_status == "failed" for m in messages),
    }


def _out(b: SmsBroadcast, messages: list[SmsMessage]) -> BroadcastOut:
    return BroadcastOut.model_validate({**BroadcastOut.model_validate(b).model_dump(), **_counts(messages)})


def _detail(db: Session, b: SmsBroadcast, replayed: bool = False) -> BroadcastDetail:
    msgs = db.scalars(select(SmsMessage).where(SmsMessage.broadcast_id == b.id).order_by(SmsMessage.id)).all()
    base = _out(b, list(msgs)).model_dump()
    return BroadcastDetail(**base, messages=[MessageOut.model_validate(m) for m in msgs], replayed=replayed)


def _summarise(results: list[sms.ProviderResult]) -> str:
    kinds = {r.submission for r in results}
    accepted = sum(r.submission == "accepted" for r in results)
    if kinds == {"simulated"}:
        return "simulated"
    if accepted == len(results):
        return "submitted"
    if accepted:
        return "partial"
    return "unknown" if "unknown" in kinds else "failed"


def _execute(
    db: Session,
    user: User,
    *,
    kind: str,
    payload: Compose,
    location: Location,
    recipients: list[SmsSubscriber],
    key: str,
) -> BroadcastDetail:
    cfg = get_settings()
    existing = db.scalar(select(SmsBroadcast).where(SmsBroadcast.idempotency_key == key))
    if existing is not None:
        return _detail(db, existing, replayed=True)

    body = sms.build_body(payload.risk_level, location.name, payload.message, test=kind == "test")
    segments = sms.count_segments(body)
    chash = hashlib.sha256(
        f"{kind}|{location.id}|{body}|{','.join(str(s.id) for s in recipients)}".encode()
    ).hexdigest()
    window_start = _now() - timedelta(minutes=cfg.sms_duplicate_window_minutes)
    if db.scalar(
        select(SmsBroadcast.id).where(
            SmsBroadcast.content_hash == chash,
            SmsBroadcast.created_at >= window_start,
            SmsBroadcast.status != "failed",  # a send that definitely failed may be retried
        )
    ):
        raise _err(
            409,
            "duplicate_send",
            f"The same message was already sent to the same recipients in the last "
            f"{cfg.sms_duplicate_window_minutes} minutes. Change the text or wait.",
        )

    info = sms.provider_status()
    broadcast = SmsBroadcast(
        kind=kind, idempotency_key=key, content_hash=chash, location_id=location.id,
        risk_level=payload.risk_level, body=body, segments=segments,
        recipient_count=len(recipients), provider=info["provider"], environment=info["environment"],
        status="sending", created_by=user.id, created_at=_now(),
    )
    db.add(broadcast)
    try:
        db.flush()
    except IntegrityError:  # same key raced in from a parallel request
        db.rollback()
        again = db.scalar(select(SmsBroadcast).where(SmsBroadcast.idempotency_key == key))
        if again is None:
            raise _err(409, "duplicate_send", "Send already in progress.")
        return _detail(db, again, replayed=True)

    rows = {
        s.phone: SmsMessage(broadcast_id=broadcast.id, subscriber_id=s.id, phone_masked=sms.mask(s.phone))
        for s in recipients
    }
    db.add_all(rows.values())
    record_audit_event(
        db, user_id=user.id, action="sms_test_sent" if kind == "test" else "sms_broadcast_sent",
        entity_type="sms_broadcast", entity_id=broadcast.id,
    )
    db.commit()  # the attempt is on record BEFORE anything is handed to the provider

    results = sms.submit([s.phone for s in recipients], body)
    submitted = _now()
    for r in results:
        m = rows[r.phone]
        m.submission_status = r.submission
        m.submission_detail = r.detail[:300]
        m.provider_message_id = r.message_id
        m.provider_status = r.provider_status[:60]
        m.provider_status_code = r.status_code
        m.cost = r.cost
        m.submitted_at = submitted
    broadcast.status = _summarise(results)
    broadcast.completed_at = submitted
    db.commit()
    db.refresh(broadcast)
    return _detail(db, broadcast)


# --- admin endpoints ---------------------------------------------------------------------


@router.get("/status", response_model=ProviderStatus)
def status(db: Session = Depends(get_db), _: User = Depends(_admin)):
    return _provider_status(db)


@router.post("/preview", response_model=Preview)
def preview(payload: PreviewRequest, db: Session = Depends(get_db), _: User = Depends(_admin)):
    loc = _location(db, payload.location_id)
    test = payload.subscriber_id is not None
    if test:
        sub = db.get(SmsSubscriber, payload.subscriber_id)
        recipients = [sub] if sub is not None and sub.can_receive and sms.is_allowed(sub.phone) else []
        skipped = 0
    else:
        recipients, skipped = _eligible(db, payload.location_id)
    body = sms.build_body(payload.risk_level, loc.name, payload.message, test=test)
    segments = sms.count_segments(body)
    reasons = _blocking(db, kind="test" if test else "broadcast", count=len(recipients), segments=segments)
    return Preview(
        body=body, length=len(body), segments=segments, recipient_count=len(recipients),
        recipients=[PreviewRecipient(subscriber_id=s.id, name=s.name, phone_masked=sms.mask(s.phone)) for s in recipients],
        skipped_not_allowlisted=skipped, can_send=not reasons, blocking_reasons=reasons,
    )


@router.post("/test", response_model=BroadcastDetail)
@limiter.limit("5/minute")
def send_test(request: Request, payload: SendTest, db: Session = Depends(get_db), user: User = Depends(_admin)):
    """One clearly-labelled test message to one registered, consenting number."""
    if not payload.confirm:
        raise _err(400, "confirmation_required", "Explicit confirmation is required to send.")
    loc = _location(db, payload.location_id)
    sub = _test_recipient(db, payload.subscriber_id)
    body = sms.build_body(payload.risk_level, loc.name, payload.message, test=True)
    reasons = _blocking(db, kind="test", count=1, segments=sms.count_segments(body))
    if reasons:
        raise _err(409, "send_blocked", " ".join(reasons))
    return _execute(db, user, kind="test", payload=payload, location=loc, recipients=[sub], key=payload.idempotency_key)


@router.post("/broadcasts", response_model=BroadcastDetail)
@limiter.limit("3/minute")
def send_broadcast(request: Request, payload: SendBroadcast, db: Session = Depends(get_db), user: User = Depends(_admin)):
    """Group broadcast. Requires confirm=true and the exact recipient count the admin saw."""
    if not payload.confirm:
        raise _err(400, "confirmation_required", "Explicit confirmation is required to send.")
    loc = _location(db, payload.location_id)
    recipients, _skipped = _eligible(db, payload.location_id)
    if len(recipients) != payload.expected_recipient_count:
        raise _err(
            409, "recipient_count_changed",
            f"The recipient list changed: you confirmed {payload.expected_recipient_count} "
            f"but there are now {len(recipients)}. Review the preview again.",
        )
    if len(recipients) > get_settings().sms_max_recipients:
        raise _err(400, "too_many_recipients", f"Over the {get_settings().sms_max_recipients}-recipient limit (SMS_MAX_RECIPIENTS).")
    body = sms.build_body(payload.risk_level, loc.name, payload.message)
    reasons = _blocking(db, kind="broadcast", count=len(recipients), segments=sms.count_segments(body))
    if reasons:
        raise _err(409, "send_blocked", " ".join(reasons))
    return _execute(db, user, kind="broadcast", payload=payload, location=loc, recipients=recipients, key=payload.idempotency_key)


@router.get("/broadcasts", response_model=list[BroadcastOut])
def list_broadcasts(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    rows = db.scalars(select(SmsBroadcast).order_by(SmsBroadcast.id.desc()).limit(limit).offset(offset)).all()
    msgs = db.scalars(select(SmsMessage).where(SmsMessage.broadcast_id.in_([b.id for b in rows]))).all() if rows else []
    by_b: dict[int, list[SmsMessage]] = {}
    for m in msgs:
        by_b.setdefault(m.broadcast_id, []).append(m)
    return [_out(b, by_b.get(b.id, [])) for b in rows]


@router.get("/broadcasts/{broadcast_id}", response_model=BroadcastDetail)
def get_broadcast(broadcast_id: int, db: Session = Depends(get_db), _: User = Depends(_admin)):
    b = db.get(SmsBroadcast, broadcast_id)
    if b is None:
        raise _err(404, "not_found", "Broadcast not found")
    return _detail(db, b)


# --- provider callbacks (no login; authenticated by a shared secret) -----------------------


def _check_token(token: str) -> None:
    secret = get_settings().sms_webhook_secret
    if not secret:
        raise _err(503, "callbacks_disabled", "SMS callbacks are not configured.")
    if not hmac.compare_digest(token.encode(), secret.encode()):
        raise _err(403, "forbidden", "Invalid callback token.")


_DELIVERY_MAP = {
    "success": "delivered",
    "sent": "pending", "submitted": "pending", "buffered": "pending", "queued": "pending",
    "failed": "failed", "rejected": "failed",
}


@router.post("/delivery-report", response_class=PlainTextResponse)
@limiter.limit("120/minute")
async def delivery_report(request: Request, token: str = "", db: Session = Depends(get_db)):
    """Africa's Talking delivery report (form fields: id, status, failureReason, ...).
    This is the ONLY place delivery_status changes."""
    _check_token(token)
    form = await request.form()
    message_id = str(form.get("id", "")).strip()
    raw = str(form.get("status", "")).strip()
    msg = db.scalar(select(SmsMessage).where(SmsMessage.provider_message_id == message_id)) if message_id else None
    if msg is not None:
        mapped = _DELIVERY_MAP.get(raw.lower(), "pending")
        if msg.delivery_status != "delivered":  # a late 'buffered' must not undo 'delivered'
            msg.delivery_status = mapped
            msg.delivery_reported_at = _now()
            msg.failure_reason = str(form.get("failureReason", ""))[:200] if mapped == "failed" else ""
            db.commit()
    return "OK"


@router.post("/inbound", response_class=PlainTextResponse)
@limiter.limit("120/minute")
async def inbound(request: Request, token: str = "", db: Session = Depends(get_db)):
    """Incoming SMS callback: a STOP-style reply opts that number out."""
    _check_token(token)
    form = await request.form()
    phone = sms.normalise(str(form.get("from", "")))
    text = str(form.get("text", "")).strip().upper()
    if text in _STOP_WORDS and phone:
        sub = db.scalar(select(SmsSubscriber).where(SmsSubscriber.phone == phone))
        if sub is not None and sub.active:
            sub.active = False
            sub.opted_out_at = _now()
            record_audit_event(db, user_id=None, action="sms_subscriber_opted_out_by_reply", entity_type="sms_subscriber", entity_id=sub.id)
            db.commit()
    return "OK"
