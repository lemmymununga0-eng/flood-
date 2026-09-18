"""Write-path helper for real, user-facing notifications. Mirrors
app/core/audit.py's record_audit_event() shape exactly: constructs the row, add()s and
flush()es it, and lets the caller commit as part of its own transaction. Only ever
called with a real, unambiguous recipient user_id — see docs/ARCHITECTURE.md for why
alert issuance does not (yet) generate notifications."""
from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify_user(
    db: Session,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    message: str = "",
    entity_type: str = "",
    entity_id: int | None = None,
) -> Notification:
    entry = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(entry)
    db.flush()
    return entry
