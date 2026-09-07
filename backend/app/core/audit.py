"""Write-path helper for the append-only audit log. Called at the point an action
happens (login, alert issued, citizen report moderated) — never reconstructed
after the fact."""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str = "",
    entity_id: int | None = None,
    detail: str = "",
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    db.flush()
    return entry
